# Spot Instance Import Infrastructure
# Ultra-cost-effective automated data import using spot instances (~$0.03/month)

# ============================================================================
# DATA SOURCES
# ============================================================================

# Latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ============================================================================
# LAMBDA FUNCTION FOR SPOT INSTANCE LAUNCHER
# ============================================================================

# Archive for Lambda function code
data "archive_file" "spot_launcher" {
  type        = "zip"
  output_path = "spot_launcher.zip"
  source_dir  = "../lambda-functions/spot-launcher"
  excludes    = ["package.zip"]
}

# Lambda function for spot instance launcher
resource "aws_lambda_function" "spot_launcher" {
  function_name = "${local.name_prefix}-spot-launcher"
  role          = aws_iam_role.spot_launcher.arn

  filename         = data.archive_file.spot_launcher.output_path
  source_code_hash = data.archive_file.spot_launcher.output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60  # 1 minute timeout
  memory_size      = 256 # Enough for EC2 API calls

  environment {
    variables = {
      SPOT_INSTANCE_TYPE     = var.spot_instance_type
      SPOT_MAX_PRICE         = "" # Use current spot price
      IMPORT_TIMEOUT_MINUTES = var.import_timeout_minutes
      PUBLIC_SUBNET_IDS      = join(",", aws_subnet.public[*].id)
      SECURITY_GROUP_ID      = aws_security_group.spot_import.id
      IAM_INSTANCE_PROFILE   = aws_iam_instance_profile.spot_import.name
      AMI_ID                 = data.aws_ami.amazon_linux.id
      DATABASE_SECRET_ARN    = aws_secretsmanager_secret.db_credentials.arn
      IMPORT_REPOSITORY      = "https://github.com/your-username/parliament.git"
      IMPORT_BRANCH          = "main"
      IMPORT_SCRIPT_PATH     = "scripts/data_processing/pipeline_orchestrator.py"
      PYTHON_REQUIREMENTS    = "requests sqlalchemy psycopg2-binary rich boto3"
      CLOUDWATCH_LOG_GROUP   = aws_cloudwatch_log_group.spot_import.name
      ENVIRONMENT            = var.environment
    }
  }

  tags = merge(local.compute_tags, {
    Name         = "${local.name_prefix}-spot-launcher"
    ResourceType = "lambda-function"
    Purpose      = "spot-instance-launcher"
    Runtime      = "python3.9"
    MemorySize   = "256MB"
    Timeout      = "60s"
    FunctionType = "spot-launcher"
  })
}

# Lambda Function URL for manual triggers
resource "aws_lambda_function_url" "spot_launcher" {
  count = var.enable_automated_import ? 1 : 0

  function_name      = aws_lambda_function.spot_launcher.function_name
  authorization_type = "NONE"

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["POST", "GET"]
    allow_headers     = ["date", "keep-alive", "content-type"]
    expose_headers    = ["date", "keep-alive"]
    max_age           = 86400
  }
}

# ============================================================================
# SERVICE-LINKED ROLES
# ============================================================================

# Service-linked role for EC2 Spot Instances
resource "aws_iam_service_linked_role" "ec2_spot" {
  aws_service_name = "spot.amazonaws.com"
  description      = "Service-linked role for EC2 Spot Instances"

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-ec2-spot-service-role"
    ResourceType = "service-linked-role"
    Purpose      = "ec2-spot-instance-management"
  })
}

# ============================================================================
# IAM ROLES AND POLICIES
# ============================================================================

# IAM Role for Lambda spot launcher
resource "aws_iam_role" "spot_launcher" {
  name = "${local.name_prefix}-spot-launcher-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-spot-launcher-role"
    ResourceType = "iam-role"
    Purpose      = "spot-launcher-permissions"
  })
}

# Lambda basic execution policy
resource "aws_iam_role_policy_attachment" "spot_launcher_basic" {
  role       = aws_iam_role.spot_launcher.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for EC2 spot instance management
resource "aws_iam_role_policy" "spot_launcher_ec2" {
  name = "${local.name_prefix}-spot-launcher-ec2"
  role = aws_iam_role.spot_launcher.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:RequestSpotInstances",
          "ec2:DescribeSpotInstanceRequests",
          "ec2:DescribeInstances",
          "ec2:DescribeImages",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
          "ec2:CreateTags"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = aws_iam_role.spot_import.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.spot_import.arn}:*"
      }
    ]
  })
}

# IAM Role for spot instances
resource "aws_iam_role" "spot_import" {
  name = "${local.name_prefix}-spot-import-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-spot-import-role"
    ResourceType = "iam-role"
    Purpose      = "spot-instance-import-permissions"
  })
}

# Instance profile for spot instances
resource "aws_iam_instance_profile" "spot_import" {
  name = "${local.name_prefix}-spot-import-profile"
  role = aws_iam_role.spot_import.name

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-spot-import-profile"
    ResourceType = "iam-instance-profile"
    Purpose      = "spot-instance-profile"
  })
}

# Policy for spot instances to access database and CloudWatch
resource "aws_iam_role_policy" "spot_import_permissions" {
  name = "${local.name_prefix}-spot-import-permissions"
  role = aws_iam_role.spot_import.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.db_credentials.arn,
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:fiscaliza-prod-github-deploy-key-*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.spot_import.arn}:*",
          "arn:aws:logs:${var.aws_region}:*:log-group:/aws/parliament/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "rds:DescribeDBInstances"
        ]
        Resource = aws_db_instance.parliament.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.static_website.arn}/parliament-code.zip"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      }
    ]
  })
}

# ============================================================================
# SECURITY GROUP FOR SPOT INSTANCES
# ============================================================================

resource "aws_security_group" "spot_import" {
  name_prefix = "${local.name_prefix}-spot-import-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for parliament data import spot instances"

  # Outbound HTTPS for package installation and git clone
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound HTTP for package repositories
  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # DNS resolution (required for hostname lookups)
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # PostgreSQL access to RDS (via security group reference)
  egress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.rds.id]
  }

  # Direct PostgreSQL access to RDS subnet (fallback for IP-based connections)
  egress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.1.0/24", "10.0.2.0/24"] # RDS subnets
  }

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-spot-import-sg"
    ResourceType = "security-group"
    Purpose      = "spot-instance-network-access"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Update RDS security group to allow spot instances
resource "aws_security_group_rule" "rds_from_spot" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.spot_import.id
  security_group_id        = aws_security_group.rds.id
}

# ============================================================================
# EVENTBRIDGE SCHEDULING
# ============================================================================

# EventBridge rule for scheduled execution
resource "aws_cloudwatch_event_rule" "spot_import_schedule" {
  count = var.import_automation_mode == "daily" || var.import_automation_mode == "custom" ? 1 : 0

  name                = "${local.name_prefix}-spot-import-schedule"
  description         = "Scheduled parliament data import using spot instances"
  schedule_expression = var.import_automation_mode == "daily" ? "cron(0 2 * * ? *)" : var.import_schedule
  state               = "ENABLED"

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-spot-import-schedule"
    ResourceType = "eventbridge-rule"
    Purpose      = "automated-import-scheduling"
    Schedule     = var.import_automation_mode == "daily" ? "daily-2am-utc" : "custom"
  })
}

# EventBridge target for Lambda function
resource "aws_cloudwatch_event_target" "spot_import_lambda" {
  count = var.import_automation_mode == "daily" || var.import_automation_mode == "custom" ? 1 : 0

  rule      = aws_cloudwatch_event_rule.spot_import_schedule[0].name
  target_id = "SpotImportLambdaTarget"
  arn       = aws_lambda_function.spot_launcher.arn

  input = jsonencode({
    source      = "eventbridge-schedule"
    mode        = var.import_automation_mode
    retry_count = 0
  })
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  count = var.import_automation_mode == "daily" || var.import_automation_mode == "custom" ? 1 : 0

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.spot_launcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.spot_import_schedule[0].arn
}

# ============================================================================
# CLOUDWATCH MONITORING
# ============================================================================

# CloudWatch Log Group for import jobs
resource "aws_cloudwatch_log_group" "spot_import" {
  name              = "/aws/parliament/import"
  retention_in_days = 7

  tags = merge(local.monitoring_tags, {
    Name          = "${local.name_prefix}-spot-import-logs"
    ResourceType  = "cloudwatch-log-group"
    Purpose       = "spot-import-application-logs"
    LogType       = "application"
    RetentionDays = tostring(var.import_log_retention_days)
  })
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "spot_launcher_logs" {
  name              = "/aws/lambda/${aws_lambda_function.spot_launcher.function_name}"
  retention_in_days = 7

  tags = merge(local.monitoring_tags, {
    Name          = "${local.name_prefix}-spot-launcher-logs"
    ResourceType  = "cloudwatch-log-group"
    Purpose       = "lambda-application-logs"
    LogType       = "lambda"
    RetentionDays = tostring(var.import_log_retention_days)
  })
}

# CloudWatch alarm for import failures
resource "aws_cloudwatch_metric_alarm" "import_failures" {
  count = var.enable_automated_import && var.enable_basic_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-import-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Parliament data import job is failing"

  dimensions = {
    FunctionName = aws_lambda_function.spot_launcher.function_name
  }

  alarm_actions = var.import_alert_email != "" ? [aws_sns_topic.import_alerts[0].arn] : []

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-import-failures"
    ResourceType = "cloudwatch-alarm"
    Purpose      = "import-failure-monitoring"
    AlarmType    = "import-failures"
  })
}

# SNS topic for import alerts
resource "aws_sns_topic" "import_alerts" {
  count = var.enable_automated_import && var.enable_basic_monitoring && var.import_alert_email != "" ? 1 : 0

  name = "${local.name_prefix}-import-alerts"

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-import-alerts"
    ResourceType = "sns-topic"
    Purpose      = "import-alert-notifications"
  })
}

# SNS topic subscription
resource "aws_sns_topic_subscription" "import_alerts_email" {
  count = var.enable_automated_import && var.enable_basic_monitoring && var.import_alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.import_alerts[0].arn
  protocol  = "email"
  endpoint  = var.import_alert_email
}