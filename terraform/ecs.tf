# ECS Fargate Infrastructure for Parliament Backend
# Cost-optimized setup with CloudFlare direct connection
# Target cost: $8-12/month (no ALB needed)

# ECS Cluster
resource "aws_ecs_cluster" "parliament" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = var.environment == "prod" ? "disabled" : "enabled" # Cost optimization
  }

  tags = merge(local.compute_tags, {
    Name         = "${local.name_prefix}-cluster"
    ResourceType = "ecs-cluster"
    Purpose      = "fargate-container-hosting"
    ServiceType  = "fargate"
  })
}

# ECS Task Definition
resource "aws_ecs_task_definition" "parliament" {
  family                   = "${local.name_prefix}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.fargate_cpu
  memory                   = var.fargate_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "parliament-backend"
      image = var.backend_image != "" ? var.backend_image : "public.ecr.aws/docker/library/python:3.12-slim"

      # Port configuration - Port 80 for CloudFlare Flexible SSL
      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
          protocol      = "tcp"
        }
      ]

      # Environment variables including secret ARN
      environment = [
        {
          name  = "FLASK_ENV"
          value = var.environment
        },
        {
          name  = "FLASK_DEBUG"
          value = var.environment == "dev" ? "1" : "0"
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
          value = var.environment == "prod" ? "WARNING" : "INFO"
        },
        {
          name  = "DATABASE_SECRET_ARN"
          value = aws_secretsmanager_secret.db_credentials.arn
        }
      ]

      # Health check
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:80/api/ping || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      # Logging
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      # Resource requirements
      essential = true
    }
  ])

  tags = merge(local.compute_tags, {
    Name         = "${local.name_prefix}-backend-task"
    ResourceType = "ecs-task-definition"
    Purpose      = "parliament-backend-container-spec"
    CPU          = "${var.fargate_cpu}m"
    Memory       = "${var.fargate_memory}MB"
  })
}

# ECS Service
resource "aws_ecs_service" "parliament" {
  name            = "${local.name_prefix}-backend-service"
  cluster         = aws_ecs_cluster.parliament.id
  task_definition = aws_ecs_task_definition.parliament.arn
  desired_count   = var.fargate_desired_count
  launch_type     = "FARGATE"

  # Network configuration - conditional based on load balancer
  network_configuration {
    subnets          = var.enable_alb ? aws_subnet.private[*].id : aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_service.id]
    assign_public_ip = var.enable_alb ? false : true # Public IP only if no ALB
  }

  # Load balancer configuration (only if ALB enabled)
  dynamic "load_balancer" {
    for_each = var.enable_alb ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.ecs[0].arn
      container_name   = "parliament-backend"
      container_port   = 80
    }
  }

  # Auto-scaling configuration
  enable_execute_command = var.environment != "prod" # Enable ECS Exec for dev/test

  # Deployment configuration - Zero-downtime with 2 tasks
  deployment_maximum_percent         = 200 # Allow 2x tasks during deployment (4 total)
  deployment_minimum_healthy_percent = 50  # Keep 50% (1 task) healthy during deployment

  # Health check grace period - optimized for faster deployments
  health_check_grace_period_seconds = 60 # 1 minute grace period

  tags = merge(local.compute_tags, {
    Name         = "${local.name_prefix}-backend-service"
    ResourceType = "ecs-service"
    Purpose      = "parliament-backend-service"
    DesiredCount = var.fargate_desired_count
  })

  # Ensure service is created after target group
  depends_on = [aws_ecs_task_definition.parliament]
}

# Auto Scaling Target - Temporarily disabled to resolve tagging conflicts
# resource "aws_appautoscaling_target" "ecs_target" {
#   max_capacity       = var.fargate_max_capacity
#   min_capacity       = var.fargate_min_capacity
#   resource_id        = "service/${aws_ecs_cluster.parliament.name}/${aws_ecs_service.parliament.name}"
#   scalable_dimension = "ecs:service:DesiredCount"
#   service_namespace  = "ecs"

#   tags = {
#     Name         = "${local.name_prefix}-autoscaling-target"
#     Project      = var.project_name
#     Application  = var.application_name
#     Environment  = var.environment
#     ManagedBy    = "Terraform"
#     ResourceType = "autoscaling-target"
#     Purpose      = "ecs-service-scaling"
#     MinCapacity  = tostring(var.fargate_min_capacity)
#     MaxCapacity  = tostring(var.fargate_max_capacity)
#   }
# }

# Auto Scaling Policy - Temporarily disabled with target
# resource "aws_appautoscaling_policy" "ecs_scale_up" {
#   name               = "${local.name_prefix}-scale-up"
#   policy_type        = "TargetTrackingScaling"
#   resource_id        = aws_appautoscaling_target.ecs_target.resource_id
#   scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
#   service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

#   target_tracking_scaling_policy_configuration {
#     predefined_metric_specification {
#       predefined_metric_type = "ECSServiceAverageCPUUtilization"
#     }
#     target_value       = 70.0
#     scale_in_cooldown  = 300
#     scale_out_cooldown = 300
#   }
# }

# Security Group for ECS Service
resource "aws_security_group" "ecs_service" {
  name_prefix = "${local.name_prefix}-ecs-service-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for ECS Fargate service"

  # Allow inbound from CloudFlare IP ranges on port 80
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.cloudflare_ip_ranges
    description = "Allow CloudFlare proxy access on port 80"
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-ecs-service-sg"
    ResourceType = "security-group"
    Purpose      = "ecs-fargate-service-network-access"
    VPCId        = aws_vpc.main.id
  })

  lifecycle {
    create_before_destroy = true
  }
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_execution" {
  name = "${local.name_prefix}-ecs-execution-role"

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
    Name             = "${local.name_prefix}-ecs-execution-role"
    ResourceType     = "iam-role"
    Purpose          = "ecs-task-execution-permissions"
    ServicePrincipal = "ecs-tasks.amazonaws.com"
  })
}

# IAM Role for ECS Task
resource "aws_iam_role" "ecs_task" {
  name = "${local.name_prefix}-ecs-task-role"

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
    Name             = "${local.name_prefix}-ecs-task-role"
    ResourceType     = "iam-role"
    Purpose          = "ecs-task-runtime-permissions"
    ServicePrincipal = "ecs-tasks.amazonaws.com"
  })
}

# ECS Task Execution Role Policy
resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Custom policy for Secrets Manager access
resource "aws_iam_role_policy" "ecs_secrets_policy" {
  name = "${local.name_prefix}-ecs-secrets-policy"
  role = aws_iam_role.ecs_execution.id

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

# CloudWatch Log Group for ECS
resource "aws_cloudwatch_log_group" "ecs_backend" {
  name              = "/ecs/${local.name_prefix}/backend"
  retention_in_days = var.environment == "prod" ? 7 : 3 # Cost optimization

  tags = merge(local.monitoring_tags, {
    Name          = "${local.name_prefix}-ecs-backend-logs"
    ResourceType  = "cloudwatch-log-group"
    Purpose       = "ecs-container-logs"
    LogType       = "application"
    RetentionDays = var.environment == "prod" ? "7" : "3"
  })
}

# CloudWatch Alarms for ECS Service
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  count = var.enable_basic_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-ecs-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "ECS service CPU utilization is high"

  dimensions = {
    ServiceName = aws_ecs_service.parliament.name
    ClusterName = aws_ecs_cluster.parliament.name
  }

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.ecs_alerts[0].arn] : []

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-ecs-cpu-high"
    ResourceType = "cloudwatch-alarm"
    Purpose      = "ecs-cpu-monitoring"
    MetricName   = "CPUUtilization"
    Threshold    = "80"
  })
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  count = var.enable_basic_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-ecs-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "ECS service memory utilization is high"

  dimensions = {
    ServiceName = aws_ecs_service.parliament.name
    ClusterName = aws_ecs_cluster.parliament.name
  }

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.ecs_alerts[0].arn] : []

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-ecs-memory-high"
    ResourceType = "cloudwatch-alarm"
    Purpose      = "ecs-memory-monitoring"
    MetricName   = "MemoryUtilization"
    Threshold    = "85"
  })
}

# SNS Topic for ECS alerts
resource "aws_sns_topic" "ecs_alerts" {
  count = var.enable_basic_monitoring && var.alert_email != "" ? 1 : 0

  name = "${local.name_prefix}-ecs-alerts"

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-ecs-alerts"
    ResourceType = "sns-topic"
    Purpose      = "ecs-service-alerts"
  })
}

resource "aws_sns_topic_subscription" "ecs_alerts_email" {
  count = var.enable_basic_monitoring && var.alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.ecs_alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}