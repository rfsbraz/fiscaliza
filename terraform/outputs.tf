# Cost-Optimized Terraform Outputs
# Key information for the deployed cost-optimized infrastructure

# Application URLs
output "alb_dns_name" {
  description = "Application Load Balancer DNS name (stable endpoint)"
  value       = var.enable_alb ? aws_lb.main[0].dns_name : "ALB disabled"
}

output "alb_http_endpoint" {
  description = "ALB HTTP endpoint (redirects to HTTPS)"
  value       = var.enable_alb ? "http://${aws_lb.main[0].dns_name}" : "ALB disabled"
}

output "alb_https_endpoint" {
  description = "ALB HTTPS endpoint for testing"
  value       = var.enable_alb ? "https://${aws_lb.main[0].dns_name}" : "ALB disabled"
}

output "website_url" {
  description = "Static website URL"
  value       = var.cloudflare_zone_id != "" ? "https://${var.domain_name}" : aws_s3_bucket_website_configuration.static_website.website_endpoint
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for cache invalidation"
  value       = var.enable_cloudfront_for_website ? aws_cloudfront_distribution.static_website[0].id : "CloudFront not enabled"
}

output "api_url" {
  description = "API endpoint URL"
  value       = var.enable_alb && var.cloudflare_zone_id != "" ? "https://${local.api_domain_name}" : (var.enable_alb ? "https://${aws_lb.main[0].dns_name}" : "API not configured")
}

output "s3_website_endpoint" {
  description = "S3 static website endpoint"
  value       = aws_s3_bucket_website_configuration.static_website.website_endpoint
}

output "s3_bucket_name" {
  description = "S3 bucket name for frontend deployment"
  value       = aws_s3_bucket.static_website.bucket
}

output "load_balancer_status" {
  description = "Current load balancer configuration"
  value = {
    alb_enabled           = var.enable_alb
    nlb_enabled           = var.enable_nlb
    ip_automation_enabled = var.enable_ip_automation
  }
}

output "ecs_cluster_name" {
  description = "ECS Cluster name"
  value       = aws_ecs_cluster.parliament.name
}

output "ecs_service_name" {
  description = "ECS Service name"
  value       = aws_ecs_service.parliament.name
}

# Import Pipeline Outputs
output "ecs_import_discovery_task_arn" {
  description = "ECS task definition ARN for discovery"
  value       = aws_ecs_task_definition.import_discovery.arn
}

output "ecs_import_importer_task_arn" {
  description = "ECS task definition ARN for importer"
  value       = aws_ecs_task_definition.import_importer.arn
}

output "ecs_import_log_group" {
  description = "CloudWatch log group for import tasks"
  value       = aws_cloudwatch_log_group.ecs_import.name
}

output "ecs_import_security_group_id" {
  description = "Security group ID for import tasks"
  value       = aws_security_group.ecs_import.id
}

output "import_schedule_status" {
  description = "Status of scheduled import tasks"
  value = {
    enabled            = var.enable_scheduled_import
    discovery_schedule = "Daily at 2 AM UTC"
    importer_schedule  = "Daily at 4 AM UTC"
  }
}

output "spot_import_function_url" {
  description = "Lambda Function URL for manual data import triggers (when enabled)"
  value       = var.enable_automated_import ? aws_lambda_function_url.spot_launcher[0].function_url : "Not enabled"
}

output "cloudflare_domain" {
  description = "Main domain served through Cloudflare"
  value       = var.cloudflare_zone_id != "" ? var.domain_name : "Not configured"
}


# Database Information
output "database_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.parliament.endpoint
  sensitive   = true
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.parliament.db_name
}

output "database_secret_arn" {
  description = "ARN of the secret containing database credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

# Infrastructure Details
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "nat_gateway_id" {
  description = "NAT Gateway ID (single NAT for cost optimization, if enabled)"
  value       = var.enable_nat_gateway ? aws_nat_gateway.main[0].id : "NAT Gateway disabled for cost optimization"
}

# Security Information
output "ecs_security_group_id" {
  description = "ECS service security group ID"
  value       = aws_security_group.ecs_service.id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = aws_security_group.rds.id
}

# Cost Optimization Status
output "cost_optimization_enabled" {
  description = "Cost optimization mode status"
  value       = var.cost_optimization_mode
}

output "estimated_monthly_cost" {
  description = "Estimated monthly cost in USD"
  value       = var.enable_automated_import ? "$8-12/month + ~$0.03/month for spot imports" : "$8-12/month (ECS Fargate with direct CloudFlare connection)"
}

output "cost_savings_vs_original" {
  description = "Cost savings compared to original architecture"
  value       = "~40-60% savings vs Aurora + enhanced API Gateway + provisioned services"
}


# Environment Information
output "environment" {
  description = "Current environment"
  value       = var.environment
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}


# Performance Configuration
output "fargate_configuration" {
  description = "ECS Fargate service configuration"
  value = {
    cpu           = var.fargate_cpu
    memory        = var.fargate_memory
    desired_count = var.fargate_desired_count
    min_capacity  = var.fargate_min_capacity
    max_capacity  = var.fargate_max_capacity
    runtime       = "ECS Fargate with Gunicorn"
  }
}

output "database_configuration" {
  description = "Database configuration"
  value = {
    engine           = var.db_engine
    instance_class   = var.db_instance_class
    storage_type     = var.db_storage_type
    storage_size     = var.db_allocated_storage
    multi_az         = var.db_multi_az
    backup_retention = var.db_backup_retention_period
  }
}

# Monitoring Information
output "monitoring_configuration" {
  description = "Monitoring configuration"
  value = {
    basic_monitoring       = var.enable_basic_monitoring
    detailed_monitoring    = var.enable_detailed_monitoring
    alert_email_configured = var.alert_email != ""
    log_retention_days     = var.environment == "prod" ? 7 : 3
  }
}

# Caching Configuration
output "caching_configuration" {
  description = "Application caching configuration"
  value = {
    in_memory_cache    = var.enable_in_memory_cache
    cache_ttl_seconds  = var.cache_ttl_seconds
    connection_pooling = var.enable_connection_pooling
    max_connections    = var.max_connections
  }
}

# ============================================================================
# COMPREHENSIVE TAGGING OUTPUTS FOR COST ANALYSIS AND VALIDATION
# ============================================================================

# Tag Validation Outputs
output "tagging_strategy" {
  description = "Comprehensive tagging strategy information"
  value = {
    project_name            = var.project_name
    application_name        = var.application_name
    environment             = var.environment
    cost_center             = var.cost_center
    business_unit           = var.business_unit
    owner_team              = var.owner_team
    owner_email             = var.owner_email
    data_classification     = var.data_classification
    compliance_requirements = var.compliance_requirements
    backup_schedule         = var.backup_schedule
    monitoring_level        = var.monitoring_level
    auto_shutdown           = var.auto_shutdown
    cost_optimized          = var.cost_optimization_mode
  }
}

output "billable_resources_summary" {
  description = "Summary of all billable AWS resources and their key cost-related tags"
  value = {
    rds_instance = {
      resource_type    = "RDS PostgreSQL Instance"
      instance_class   = var.db_instance_class
      storage_type     = var.db_storage_type
      storage_size_gb  = var.db_allocated_storage
      multi_az         = var.db_multi_az
      backup_retention = var.db_backup_retention_period
      billable         = "true"
      component_type   = "database"
    }
    ecs_fargate = {
      resource_type  = "ECS Fargate Service"
      cpu_units      = var.fargate_cpu
      memory_mb      = var.fargate_memory
      desired_count  = var.fargate_desired_count
      billable       = "true"
      component_type = "compute"
    }
    nat_gateway = var.enable_nat_gateway ? {
      resource_type  = "NAT Gateway"
      billable       = "true"
      component_type = "network"
      purpose        = "cost-optimized-single-nat"
    } : null
    elastic_ip = var.enable_nat_gateway ? {
      resource_type  = "Elastic IP"
      billable       = "true"
      component_type = "network"
      purpose        = "nat-gateway"
    } : null
    cloudwatch_logs = {
      resource_type  = "CloudWatch Log Groups"
      retention_days = var.environment == "prod" ? "7" : "3"
      billable       = "true"
      component_type = "monitoring"
      purpose        = "logging"
    }
    sns_topics = var.enable_basic_monitoring && var.alert_email != "" ? {
      resource_type  = "SNS Topics"
      billable       = "true"
      component_type = "monitoring"
      purpose        = "alerting"
    } : null
  }
}

output "cost_allocation_tags" {
  description = "Key tags for AWS Cost Explorer and billing analysis"
  value = {
    # Primary cost allocation tags
    cost_center   = var.cost_center
    business_unit = var.business_unit
    project       = var.project_name
    application   = var.application_name
    environment   = var.environment
    owner_team    = var.owner_team

    # Secondary cost analysis tags
    cost_optimized   = var.cost_optimization_mode
    backup_schedule  = var.backup_schedule
    monitoring_level = var.monitoring_level
    auto_shutdown    = var.auto_shutdown

    # Technical categorization
    managed_by = "Terraform"
    repository = "parliament"
    terraform  = "true"
  }
}

output "tag_compliance_check" {
  description = "Tag compliance verification for governance and cost analysis"
  value = {
    required_tags_present = {
      project_name        = var.project_name != ""
      application_name    = var.application_name != ""
      environment         = var.environment != ""
      cost_center         = var.cost_center != ""
      business_unit       = var.business_unit != ""
      owner_team          = var.owner_team != ""
      data_classification = contains(["public", "internal", "confidential", "restricted"], var.data_classification)
      backup_schedule     = contains(["daily", "weekly", "monthly", "none"], var.backup_schedule)
      monitoring_level    = contains(["basic", "standard", "enhanced"], var.monitoring_level)
    }
    optional_tags_present = {
      owner_email_configured = var.owner_email != ""
      additional_tags_count  = length(var.additional_tags)
    }
    governance_compliance = {
      gdpr_compliance_tagged = var.compliance_requirements == "gdpr"
      cost_center_defined    = var.cost_center != ""
      business_owner_defined = var.business_unit != "" && var.owner_team != ""
    }
  }
}

output "resource_inventory_by_component" {
  description = "Resource inventory organized by component type for cost analysis"
  value = {
    compute_resources = [
      "aws_ecs_cluster.parliament",
      "aws_ecs_service.parliament",
      "aws_ecs_task_definition.parliament"
    ]
    database_resources = [
      "aws_db_instance.parliament",
      "aws_db_parameter_group.parliament",
      "aws_db_subnet_group.parliament"
    ]
    storage_resources = []
    network_resources = concat(
      [
        "aws_vpc.main",
        "aws_subnet.public",
        "aws_subnet.private",
        "aws_internet_gateway.main",
        "aws_route_table.public",
        "aws_route_table.private"
      ],
      var.enable_nat_gateway ? [
        "aws_nat_gateway.main",
        "aws_eip.nat"
      ] : []
    )
    security_resources = [
      "aws_security_group.ecs_service",
      "aws_security_group.rds",
      "aws_security_group.vpc_endpoints",
      "aws_iam_role.ecs_execution",
      "aws_iam_role.ecs_task",
      "aws_secretsmanager_secret.db_credentials"
    ]
    monitoring_resources = concat(
      [
        "aws_cloudwatch_log_group.ecs_backend",
        "aws_cloudwatch_log_group.application_logs"
      ],
      var.enable_basic_monitoring ? [
        "aws_cloudwatch_log_group.vpc_flow_logs",
        "aws_cloudwatch_metric_alarm.ecs_cpu_high",
        "aws_cloudwatch_metric_alarm.ecs_memory_high",
        "aws_cloudwatch_metric_alarm.rds_cpu",
        "aws_cloudwatch_metric_alarm.rds_connections",
        "aws_cloudwatch_metric_alarm.rds_freeable_memory",
        "aws_cloudwatch_metric_alarm.application_health",
        "aws_cloudwatch_metric_alarm.cost_alarm",
        "aws_cloudwatch_metric_alarm.application_error_rate",
        "aws_cloudwatch_dashboard.main"
      ] : []
    )
  }
}

output "cost_optimization_summary" {
  description = "Cost optimization features and their impact on tagging"
  value = {
    optimization_mode = var.cost_optimization_mode
    cost_saving_features = {
      nat_gateway_disabled      = var.enable_nat_gateway ? "NAT Gateway enabled" : "NAT Gateway disabled (~€35/month saved)"
      alb_disabled              = var.enable_alb ? "ALB enabled" : "ALB disabled - CloudFlare direct to ECS (~€16/month saved)"
      fargate_direct_connection = "Direct CloudFlare connection eliminates API Gateway (~$3-5/month saved)"
      rds_single_az             = "Reduced database costs vs Multi-AZ"
      short_log_retention       = "Reduced CloudWatch storage costs"
      basic_monitoring_only     = "Reduced monitoring costs"
      fargate_optimized_sizing  = "Right-sized CPU/memory allocation"
      cost_optimized_cloudfront = var.enable_cloudfront_for_website ? "CloudFront enabled" : "CloudFront disabled"
    }
    target_monthly_cost     = "$8-12"
    cost_savings_percentage = "50-70% vs full-featured architecture"
    billable_resource_count = {
      always_billable      = var.enable_nat_gateway ? 4 : 2      # RDS, ECS Fargate (+ NAT Gateway, EIP if enabled)
      conditional_billable = var.enable_alb ? 1 : 0              # ALB if enabled
      monitoring_billable  = var.enable_basic_monitoring ? 3 : 1 # CloudWatch logs, alarms, SNS
    }
  }
}

# ============================================================================
# AUTOMATED IMPORT CONFIGURATION OUTPUTS
# ============================================================================

output "import_automation_status" {
  description = "Status of automated data import configuration"
  value = var.enable_automated_import ? {
    enabled                = true
    automation_mode        = var.import_automation_mode
    schedule               = var.import_automation_mode == "daily" ? "Daily at 2 AM UTC" : (var.import_automation_mode == "custom" ? var.import_schedule : "Manual only")
    spot_instance_type     = var.spot_instance_type
    timeout_minutes        = var.import_timeout_minutes
    manual_trigger_enabled = true
    monitoring_enabled     = var.enable_basic_monitoring
    estimated_cost_per_run = "~$0.001 (20 minutes on t3.nano spot)"
    estimated_monthly_cost = "~$0.03"
    } : {
    enabled = false
    message = "Set enable_automated_import = true to enable spot instance imports"
  }
}

# ============================================================================
# DATABASE CONNECTION INFORMATION
# ============================================================================

output "database_connection_info" {
  description = "Database connection information for remote access"
  value = var.admin_ip_address != "" ? {
    endpoint            = aws_db_instance.parliament.endpoint
    port                = aws_db_instance.parliament.port
    database_name       = aws_db_instance.parliament.db_name
    username            = aws_db_instance.parliament.username
    admin_ip            = var.admin_ip_address
    publicly_accessible = aws_db_instance.parliament.publicly_accessible
    connection_string   = "postgresql://${aws_db_instance.parliament.username}:PASSWORD@${aws_db_instance.parliament.endpoint}/${aws_db_instance.parliament.db_name}"
    note                = "Replace PASSWORD with the actual database password. Password is stored in AWS Secrets Manager."
    } : {
    note = "Database remote access is disabled. Set admin_ip_address variable to enable."
  }
  sensitive = false
}

output "database_security_info" {
  description = "Database security configuration"
  value = {
    security_group_id = aws_security_group.rds.id
    allowed_sources   = var.admin_ip_address != "" ? ["Lambda functions", "Admin IP: ${var.admin_ip_address}/32"] : ["Lambda functions only"]
    subnet_type       = var.admin_ip_address != "" ? "public" : "private"
  }
}