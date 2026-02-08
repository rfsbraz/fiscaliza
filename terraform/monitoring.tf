# Cost-Optimized Monitoring Configuration
# Minimal monitoring setup to reduce costs while maintaining operational visibility
# Target: Basic monitoring only (~$2-3/month vs ~$15-20/month with full monitoring)

# SNS Topic for critical alerts only
resource "aws_sns_topic" "critical_alerts" {
  count = var.enable_basic_monitoring && var.alert_email != "" ? 1 : 0

  name = "${local.name_prefix}-critical-alerts"

  tags = merge(local.monitoring_tags, {
    Name             = "${local.name_prefix}-critical-alerts"
    ResourceType     = "sns-topic"
    Purpose          = "critical-system-alerts"
    NotificationType = "email"
    TopicType        = "critical"
  })
}

resource "aws_sns_topic_subscription" "critical_alerts_email" {
  count = var.enable_basic_monitoring && var.alert_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.critical_alerts[0].arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch Dashboard for basic monitoring
resource "aws_cloudwatch_dashboard" "main" {
  count = var.enable_basic_monitoring ? 1 : 0

  dashboard_name = "${local.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", aws_ecs_service.parliament.name, "ClusterName", aws_ecs_cluster.parliament.name],
            [".", "MemoryUtilization", ".", ".", ".", "."],
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "ecs-fargate"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "ECS Fargate Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", aws_db_instance.parliament.id],
            [".", "DatabaseConnections", ".", "."],
            [".", "FreeableMemory", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "RDS Metrics"
          period  = 300
        }
      }
    ]
  })
}

# Basic CloudWatch alarms for application health
resource "aws_cloudwatch_metric_alarm" "application_health" {
  count = var.enable_basic_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-application-health"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "3"
  metric_name         = "Invocations"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Application is not receiving requests"
  treat_missing_data  = "breaching"

  dimensions = {
    ServiceName = aws_ecs_service.parliament.name
    ClusterName = aws_ecs_cluster.parliament.name
  }

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.critical_alerts[0].arn] : []

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-application-health-alarm"
    ResourceType = "cloudwatch-alarm"
    Purpose      = "application-health-monitoring"
    MetricName   = "Invocations"
    Threshold    = "1"
    AlarmType    = "application-health"
  })
}

# Cost alarm to monitor AWS spending
resource "aws_cloudwatch_metric_alarm" "cost_alarm" {
  count = var.enable_basic_monitoring && var.alert_email != "" ? 1 : 0

  alarm_name          = "${local.name_prefix}-cost-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400" # Daily
  statistic           = "Maximum"
  threshold           = "25" # Alert if monthly cost exceeds $25
  alarm_description   = "Monthly AWS costs are higher than expected"

  dimensions = {
    Currency = "USD"
  }

  alarm_actions = [aws_sns_topic.critical_alerts[0].arn]

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-cost-alarm"
    ResourceType = "cloudwatch-alarm"
    Purpose      = "cost-monitoring"
    MetricName   = "EstimatedCharges"
    Threshold    = "25USD"
    AlarmType    = "billing"
    Currency     = "USD"
  })
}

# Log group for application logs with cost-optimized retention
resource "aws_cloudwatch_log_group" "application_logs" {
  name              = "/fiscaliza/application"
  retention_in_days = var.environment == "prod" ? 7 : 3

  tags = merge(local.monitoring_tags, {
    Name          = "${local.name_prefix}-application-logs"
    ResourceType  = "cloudwatch-log-group"
    Purpose       = "application-logging"
    LogType       = "application"
    RetentionDays = var.environment == "prod" ? "7" : "3"
  })
}

# Metric filter for application errors
resource "aws_cloudwatch_log_metric_filter" "application_errors" {
  count = var.enable_basic_monitoring ? 1 : 0

  name           = "${local.name_prefix}-application-errors"
  log_group_name = aws_cloudwatch_log_group.ecs_backend.name
  pattern        = "ERROR"

  metric_transformation {
    name      = "ApplicationErrors"
    namespace = "Fiscaliza/Application"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "application_error_rate" {
  count = var.enable_basic_monitoring ? 1 : 0

  alarm_name          = "${local.name_prefix}-application-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ApplicationErrors"
  namespace           = "Fiscaliza/Application"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5" # More than 5 errors in 5 minutes
  alarm_description   = "Application error rate is too high"
  treat_missing_data  = "notBreaching"

  alarm_actions = var.alert_email != "" ? [aws_sns_topic.critical_alerts[0].arn] : []

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-application-error-rate-alarm"
    ResourceType = "cloudwatch-alarm"
    Purpose      = "application-error-monitoring"
    MetricName   = "ApplicationErrors"
    Threshold    = "5"
    AlarmType    = "error-rate"
  })
}