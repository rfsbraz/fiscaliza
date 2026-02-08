# Cost-Optimized RDS PostgreSQL Configuration
# Replaces Aurora Serverless v2 with standard RDS PostgreSQL db.t4g.micro
# Target cost: ~$15-20/month vs ~$30-40/month for Aurora

# Random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Secrets Manager secret for database credentials
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${local.name_prefix}-db-credentials-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  description             = "Database credentials for PostgreSQL RDS"
  recovery_window_in_days = 7

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-db-credentials"
    ResourceType = "secrets-manager-secret"
    Purpose      = "database-credentials-storage"
    SecretType   = "database"
    CreatedAt    = formatdate("YYYY-MM-DD-hhmm", timestamp())
  })

  lifecycle {
    ignore_changes = [name] # Prevent recreation due to timestamp changes
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    engine   = "postgres"
    host     = aws_db_instance.parliament.endpoint
    port     = aws_db_instance.parliament.port
    database = aws_db_instance.parliament.db_name
    username = aws_db_instance.parliament.username
    password = random_password.db_password.result
  })
}

# DB Subnet Group
resource "aws_db_subnet_group" "parliament" {
  name = "${local.name_prefix}-db-subnet-group"
  # Use public subnets if admin IP is specified for remote access, otherwise use private
  subnet_ids = var.admin_ip_address != "" ? aws_subnet.public[*].id : aws_subnet.private[*].id

  tags = merge(local.database_tags, {
    Name         = "${local.name_prefix}-db-subnet-group"
    ResourceType = "db-subnet-group"
    Purpose      = "database-network-isolation"
  })
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  name_prefix = "${local.name_prefix}-rds-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for RDS PostgreSQL instance"

  ingress {
    description     = "PostgreSQL from ECS Fargate"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_service.id]
  }

  # Allow remote access from admin IP only
  dynamic "ingress" {
    for_each = var.admin_ip_address != "" ? [1] : []
    content {
      description = "PostgreSQL remote access from admin IP"
      from_port   = 5432
      to_port     = 5432
      protocol    = "tcp"
      cidr_blocks = ["${var.admin_ip_address}/32"]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-rds-sg"
    ResourceType = "security-group"
    Purpose      = "database-access-control"
    Port         = "5432"
    Protocol     = "postgresql"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "parliament" {
  identifier = "${local.name_prefix}-postgres"

  # Engine configuration
  engine         = var.db_engine
  engine_version = "15.12" # Latest PostgreSQL 15.x version
  instance_class = var.db_instance_class

  # Database configuration
  db_name  = "parliament"
  username = "parluser"
  password = random_password.db_password.result

  # Storage configuration
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_allocated_storage * 2 # Auto-scaling up to 2x
  storage_type          = var.db_storage_type
  storage_encrypted     = true

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.parliament.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = var.admin_ip_address != "" ? true : false
  parameter_group_name   = aws_db_parameter_group.parliament.name

  # Availability and backup
  multi_az                = var.db_multi_az
  backup_retention_period = var.db_backup_retention_period
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  # Performance configuration
  performance_insights_enabled = false # Costs extra
  monitoring_interval          = 0     # Disable enhanced monitoring

  # Security
  # TODO: Re-enable deletion protection after initial setup is complete
  deletion_protection       = false # Temporarily disabled for initial setup
  skip_final_snapshot       = var.environment == "prod" ? false : true
  final_snapshot_identifier = var.environment == "prod" ? "${local.name_prefix}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  # Cost optimization settings
  auto_minor_version_upgrade = true
  copy_tags_to_snapshot      = true

  tags = merge(local.database_tags, {
    Name            = "${local.name_prefix}-postgres"
    ResourceType    = "rds-instance"
    Purpose         = "primary-database"
    Engine          = "postgresql"
    EngineVersion   = "15.12"
    InstanceClass   = var.db_instance_class
    StorageType     = var.db_storage_type
    StorageSize     = "${var.db_allocated_storage}GB"
    MultiAZ         = var.db_multi_az ? "enabled" : "disabled"
    BackupRetention = "${var.db_backup_retention_period}days"
    Database        = "parliament"
  })

  lifecycle {
    ignore_changes = [password]
  }
}

# Basic CloudWatch Alarms for RDS
resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  count = var.enable_basic_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-rds-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "RDS CPU utilization is too high"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.parliament.id
  }

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-rds-cpu-alarm"
    ResourceType = "cloudwatch-alarm"
    Purpose      = "database-performance-monitoring"
    MetricName   = "CPUUtilization"
    Threshold    = "80-percent"
    AlarmType    = "high-cpu"
  })
}

resource "aws_cloudwatch_metric_alarm" "rds_connections" {
  count = var.enable_basic_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-rds-high-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "15" # 75% of max connections for t4g.micro
  alarm_description   = "RDS connection count is too high"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.parliament.id
  }

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-rds-connections-alarm"
    ResourceType = "cloudwatch-alarm"
    Purpose      = "database-connection-monitoring"
    MetricName   = "DatabaseConnections"
    Threshold    = "15"
    AlarmType    = "high-connections"
  })
}

resource "aws_cloudwatch_metric_alarm" "rds_freeable_memory" {
  count = var.enable_basic_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-rds-low-memory"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "FreeableMemory"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "104857600" # 100MB in bytes
  alarm_description   = "RDS freeable memory is too low"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.parliament.id
  }

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-rds-memory-alarm"
    ResourceType = "cloudwatch-alarm"
    Purpose      = "database-memory-monitoring"
    MetricName   = "FreeableMemory"
    Threshold    = "100MB"
    AlarmType    = "low-memory"
  })
}

# SNS Topic for RDS alerts
resource "aws_sns_topic" "rds_alerts" {
  count = var.enable_basic_monitoring && var.alert_email != "" ? 1 : 0

  name = "${local.name_prefix}-rds-alerts"

  tags = merge(local.monitoring_tags, {
    Name             = "${local.name_prefix}-rds-alerts"
    ResourceType     = "sns-topic"
    Purpose          = "database-alert-notifications"
    NotificationType = "email"
  })
}

resource "aws_sns_topic_subscription" "rds_alerts_email" {
  count = var.enable_basic_monitoring && var.alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.rds_alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ECS IAM policy for RDS access (via task role)
resource "aws_iam_role_policy" "ecs_rds_access" {
  name = "${local.name_prefix}-ecs-rds-access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.db_credentials.arn
      },
      {
        Effect = "Allow"
        Action = [
          "rds:DescribeDBInstances"
        ]
        Resource = aws_db_instance.parliament.arn
      }
    ]
  })
}


# Parameter Group for PostgreSQL optimization
resource "aws_db_parameter_group" "parliament" {
  family = "postgres15"
  name   = "${local.name_prefix}-postgres-params"

  # Optimize for small instance with limited memory
  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000" # Log slow queries (>1 second)
  }

  parameter {
    name         = "max_connections"
    value        = var.max_connections
    apply_method = "pending-reboot"
  }

  parameter {
    name  = "work_mem"
    value = "4096" # 4MB for sorting/hashing
  }

  parameter {
    name  = "maintenance_work_mem"
    value = "65536" # 64MB for maintenance operations
  }

  parameter {
    name  = "effective_cache_size"
    value = "524288" # 512MB estimate of OS cache
  }

  tags = merge(local.database_tags, {
    Name           = "${local.name_prefix}-postgres-params"
    ResourceType   = "db-parameter-group"
    Purpose        = "database-performance-optimization"
    Family         = "postgres15"
    MaxConnections = var.max_connections
  })
}