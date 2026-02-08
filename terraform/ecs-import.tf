# ECS Import Pipeline Infrastructure
# Scheduled ECS tasks for data discovery and import
# Replaces the complex Spot Instance approach with simpler ECS tasks

# =============================================================================
# ECS Task Definition for Import Pipeline
# =============================================================================

resource "aws_ecs_task_definition" "import_discovery" {
  family                   = "${local.name_prefix}-import-discovery"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024  # 1 vCPU - more than backend for import processing
  memory                   = 2048  # 2 GB RAM
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_import_task.arn

  container_definitions = jsonencode([
    {
      name  = "parliament-import-discovery"
      image = var.backend_image != "" ? var.backend_image : "public.ecr.aws/docker/library/python:3.12-slim"

      # Override entrypoint to run discovery
      command = [
        "python",
        "scripts/data_processing/discovery_service.py",
        "--discover-all"
      ]

      # Environment variables
      environment = [
        {
          name  = "FLASK_ENV"
          value = var.environment
        },
        {
          name  = "DATABASE_TYPE"
          value = "postgresql"
        },
        {
          name  = "DATABASE_NAME"
          value = aws_db_instance.parliament.db_name
        },
        {
          name  = "LOG_LEVEL"
          value = "INFO"
        },
        {
          name  = "DATABASE_SECRET_ARN"
          value = aws_secretsmanager_secret.db_credentials.arn
        }
      ]

      # Logging
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_import.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "discovery"
        }
      }

      essential = true
    }
  ])

  tags = merge(local.compute_tags, {
    Name         = "${local.name_prefix}-import-discovery-task"
    ResourceType = "ecs-task-definition"
    Purpose      = "parliament-data-discovery"
    TaskType     = "scheduled-import"
  })
}

resource "aws_ecs_task_definition" "import_importer" {
  family                   = "${local.name_prefix}-import-importer"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 2048  # 2 vCPU - heavy processing
  memory                   = 4096  # 4 GB RAM
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_import_task.arn

  container_definitions = jsonencode([
    {
      name  = "parliament-import-importer"
      image = var.backend_image != "" ? var.backend_image : "public.ecr.aws/docker/library/python:3.12-slim"

      # Override entrypoint to run importer
      command = [
        "python",
        "scripts/data_processing/database_driven_importer.py"
      ]

      # Environment variables
      environment = [
        {
          name  = "FLASK_ENV"
          value = var.environment
        },
        {
          name  = "DATABASE_TYPE"
          value = "postgresql"
        },
        {
          name  = "DATABASE_NAME"
          value = aws_db_instance.parliament.db_name
        },
        {
          name  = "LOG_LEVEL"
          value = "INFO"
        },
        {
          name  = "DATABASE_SECRET_ARN"
          value = aws_secretsmanager_secret.db_credentials.arn
        }
      ]

      # Logging
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_import.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "importer"
        }
      }

      essential = true
    }
  ])

  tags = merge(local.compute_tags, {
    Name         = "${local.name_prefix}-import-importer-task"
    ResourceType = "ecs-task-definition"
    Purpose      = "parliament-data-import"
    TaskType     = "scheduled-import"
  })
}

# =============================================================================
# CloudWatch Log Group for Import Tasks
# =============================================================================

resource "aws_cloudwatch_log_group" "ecs_import" {
  name              = "/ecs/${local.name_prefix}/import"
  retention_in_days = 14  # Keep import logs longer for debugging

  tags = merge(local.monitoring_tags, {
    Name          = "${local.name_prefix}-ecs-import-logs"
    ResourceType  = "cloudwatch-log-group"
    Purpose       = "ecs-import-task-logs"
    LogType       = "import-pipeline"
    RetentionDays = "14"
  })
}

# =============================================================================
# IAM Role for Import Tasks (needs additional permissions)
# =============================================================================

resource "aws_iam_role" "ecs_import_task" {
  name = "${local.name_prefix}-ecs-import-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.security_tags, {
    Name             = "${local.name_prefix}-ecs-import-task-role"
    ResourceType     = "iam-role"
    Purpose          = "ecs-import-task-runtime-permissions"
    ServicePrincipal = "ecs-tasks.amazonaws.com"
  })
}

# Import task needs Secrets Manager access
resource "aws_iam_role_policy" "ecs_import_secrets" {
  name = "${local.name_prefix}-ecs-import-secrets-policy"
  role = aws_iam_role.ecs_import_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_credentials.arn
        ]
      }
    ]
  })
}

# =============================================================================
# EventBridge Scheduled Rules
# =============================================================================

resource "aws_cloudwatch_event_rule" "import_discovery_schedule" {
  name                = "${local.name_prefix}-import-discovery-schedule"
  description         = "Run parliament data discovery daily at 2 AM UTC"
  schedule_expression = "cron(0 2 * * ? *)"
  state               = var.enable_scheduled_import ? "ENABLED" : "DISABLED"

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-import-discovery-schedule"
    ResourceType = "eventbridge-rule"
    Purpose      = "scheduled-discovery-trigger"
    Schedule     = "daily-2am-utc"
  })
}

resource "aws_cloudwatch_event_rule" "import_importer_schedule" {
  name                = "${local.name_prefix}-import-importer-schedule"
  description         = "Run parliament data import daily at 4 AM UTC"
  schedule_expression = "cron(0 4 * * ? *)"
  state               = var.enable_scheduled_import ? "ENABLED" : "DISABLED"

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-import-importer-schedule"
    ResourceType = "eventbridge-rule"
    Purpose      = "scheduled-import-trigger"
    Schedule     = "daily-4am-utc"
  })
}

# =============================================================================
# EventBridge Targets (ECS Tasks)
# =============================================================================

resource "aws_cloudwatch_event_target" "import_discovery" {
  rule      = aws_cloudwatch_event_rule.import_discovery_schedule.name
  target_id = "run-discovery-task"
  arn       = aws_ecs_cluster.parliament.arn
  role_arn  = aws_iam_role.eventbridge_ecs.arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.import_discovery.arn
    task_count          = 1
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = aws_subnet.public[*].id
      security_groups  = [aws_security_group.ecs_import.id]
      assign_public_ip = true
    }
  }
}

resource "aws_cloudwatch_event_target" "import_importer" {
  rule      = aws_cloudwatch_event_rule.import_importer_schedule.name
  target_id = "run-importer-task"
  arn       = aws_ecs_cluster.parliament.arn
  role_arn  = aws_iam_role.eventbridge_ecs.arn

  ecs_target {
    task_definition_arn = aws_ecs_task_definition.import_importer.arn
    task_count          = 1
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = aws_subnet.public[*].id
      security_groups  = [aws_security_group.ecs_import.id]
      assign_public_ip = true
    }
  }
}

# =============================================================================
# IAM Role for EventBridge to Run ECS Tasks
# =============================================================================

resource "aws_iam_role" "eventbridge_ecs" {
  name = "${local.name_prefix}-eventbridge-ecs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.security_tags, {
    Name             = "${local.name_prefix}-eventbridge-ecs-role"
    ResourceType     = "iam-role"
    Purpose          = "eventbridge-ecs-task-execution"
    ServicePrincipal = "events.amazonaws.com"
  })
}

resource "aws_iam_role_policy" "eventbridge_ecs_policy" {
  name = "${local.name_prefix}-eventbridge-ecs-policy"
  role = aws_iam_role.eventbridge_ecs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask"
        ]
        Resource = [
          aws_ecs_task_definition.import_discovery.arn,
          aws_ecs_task_definition.import_importer.arn,
          # Also allow newer revisions
          "${replace(aws_ecs_task_definition.import_discovery.arn, "/:\\d+$/", "")}:*",
          "${replace(aws_ecs_task_definition.import_importer.arn, "/:\\d+$/", "")}:*"
        ]
        Condition = {
          ArnEquals = {
            "ecs:cluster" = aws_ecs_cluster.parliament.arn
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = [
          aws_iam_role.ecs_execution.arn,
          aws_iam_role.ecs_import_task.arn
        ]
      }
    ]
  })
}

# =============================================================================
# Security Group for Import Tasks
# =============================================================================

resource "aws_security_group" "ecs_import" {
  name_prefix = "${local.name_prefix}-ecs-import-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for ECS import tasks"

  # No inbound needed - import tasks only make outbound connections

  # Allow all outbound traffic (needed for RDS, parliament.pt, etc)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-ecs-import-sg"
    ResourceType = "security-group"
    Purpose      = "ecs-import-task-network-access"
    VPCId        = aws_vpc.main.id
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Allow import tasks to connect to RDS
resource "aws_security_group_rule" "rds_from_import" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs_import.id
  security_group_id        = aws_security_group.rds.id
  description              = "Allow import tasks to connect to RDS"
}
