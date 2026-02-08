# CloudFlare DNS Updater - Auto-update DNS when ECS IP changes
# Cost: ~€0.01/month (triggered only on ECS restarts)
# Required when ALB is disabled and ECS uses dynamic public IPs

# ============================================================================
# LAMBDA FUNCTION
# ============================================================================

# Archive for Lambda function code
data "archive_file" "cloudflare_dns_updater" {
  count       = var.enable_cloudflare_dns_updater ? 1 : 0
  type        = "zip"
  output_path = "cloudflare_dns_updater.zip"
  source_dir  = "../lambda-functions/cloudflare-dns-updater"
  excludes    = ["package.zip", "__pycache__", "*.pyc"]
}

# Lambda function for CloudFlare DNS updates
resource "aws_lambda_function" "cloudflare_dns_updater" {
  count = var.enable_cloudflare_dns_updater ? 1 : 0

  function_name = "${local.name_prefix}-cloudflare-dns-updater"
  role          = aws_iam_role.cloudflare_dns_updater[0].arn

  filename         = data.archive_file.cloudflare_dns_updater[0].output_path
  source_code_hash = data.archive_file.cloudflare_dns_updater[0].output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      CLOUDFLARE_API_TOKEN = var.cloudflare_api_token
      CLOUDFLARE_ZONE_ID   = var.cloudflare_zone_id
      DNS_RECORD_NAME      = local.api_domain_name
      ECS_CLUSTER_NAME     = aws_ecs_cluster.parliament.name
      ECS_SERVICE_NAME     = aws_ecs_service.parliament.name
    }
  }

  tags = merge(local.compute_tags, {
    Name         = "${local.name_prefix}-cloudflare-dns-updater"
    ResourceType = "lambda-function"
    Purpose      = "cloudflare-dns-auto-update"
    Runtime      = "python3.12"
    Trigger      = "ecs-task-state-change"
  })
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "cloudflare_dns_updater" {
  count = var.enable_cloudflare_dns_updater ? 1 : 0

  name              = "/aws/lambda/${local.name_prefix}-cloudflare-dns-updater"
  retention_in_days = 3 # Short retention for cost optimization

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-cloudflare-dns-updater-logs"
    ResourceType = "cloudwatch-log-group"
    Purpose      = "lambda-logs"
  })
}

# ============================================================================
# IAM ROLE AND POLICIES
# ============================================================================

resource "aws_iam_role" "cloudflare_dns_updater" {
  count = var.enable_cloudflare_dns_updater ? 1 : 0

  name = "${local.name_prefix}-cloudflare-dns-updater-role"

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
    Name         = "${local.name_prefix}-cloudflare-dns-updater-role"
    ResourceType = "iam-role"
    Purpose      = "cloudflare-dns-updater-permissions"
  })
}

# Lambda basic execution policy
resource "aws_iam_role_policy_attachment" "cloudflare_dns_updater_basic" {
  count = var.enable_cloudflare_dns_updater ? 1 : 0

  role       = aws_iam_role.cloudflare_dns_updater[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for ECS and EC2 access (to get task public IP)
resource "aws_iam_role_policy" "cloudflare_dns_updater_ecs" {
  count = var.enable_cloudflare_dns_updater ? 1 : 0

  name = "${local.name_prefix}-cloudflare-dns-updater-ecs"
  role = aws_iam_role.cloudflare_dns_updater[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeTasks",
          "ecs:ListTasks"
        ]
        Resource = "*"
        Condition = {
          ArnEquals = {
            "ecs:cluster" = aws_ecs_cluster.parliament.arn
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeNetworkInterfaces"
        ]
        Resource = "*"
      }
    ]
  })
}

# ============================================================================
# EVENTBRIDGE RULE
# ============================================================================

# EventBridge rule for ECS task state changes
resource "aws_cloudwatch_event_rule" "ecs_task_state_change" {
  count = var.enable_cloudflare_dns_updater ? 1 : 0

  name        = "${local.name_prefix}-ecs-task-state-change"
  description = "Trigger CloudFlare DNS update when ECS task starts"

  event_pattern = jsonencode({
    source      = ["aws.ecs"]
    detail-type = ["ECS Task State Change"]
    detail = {
      clusterArn    = [aws_ecs_cluster.parliament.arn]
      lastStatus    = ["RUNNING"]
      desiredStatus = ["RUNNING"]
    }
  })

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-ecs-task-state-change"
    ResourceType = "eventbridge-rule"
    Purpose      = "ecs-ip-change-detection"
  })
}

# EventBridge target
resource "aws_cloudwatch_event_target" "cloudflare_dns_updater" {
  count = var.enable_cloudflare_dns_updater ? 1 : 0

  rule      = aws_cloudwatch_event_rule.ecs_task_state_change[0].name
  target_id = "CloudFlareDNSUpdater"
  arn       = aws_lambda_function.cloudflare_dns_updater[0].arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "cloudflare_dns_updater_eventbridge" {
  count = var.enable_cloudflare_dns_updater ? 1 : 0

  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cloudflare_dns_updater[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ecs_task_state_change[0].arn
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "cloudflare_dns_updater_enabled" {
  description = "Whether CloudFlare DNS updater is enabled"
  value       = var.enable_cloudflare_dns_updater
}

output "cloudflare_dns_updater_function_arn" {
  description = "ARN of the CloudFlare DNS updater Lambda function"
  value       = var.enable_cloudflare_dns_updater ? aws_lambda_function.cloudflare_dns_updater[0].arn : null
}
