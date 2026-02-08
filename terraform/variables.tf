# Cost-Optimized Variables for Portuguese Parliament Transparency Application
# Target: $11-17/month (reduced from $35-50/month)

variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
  default     = "default"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1" # Ireland - closest to Portugal
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "fiscaliza.pt"
}

# Cost Optimization Mode
variable "cost_optimization_mode" {
  description = "Enable aggressive cost optimization mode"
  type        = bool
  default     = true
}

# NAT Gateway - Major cost driver (~€35/month)
variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnet internet access. Disable to save ~€35/month (resources will use public subnets or VPC endpoints)"
  type        = bool
  default     = false # Disabled by default for cost optimization
}

# Database Configuration - Standard RDS PostgreSQL
variable "db_engine" {
  description = "Database engine (postgresql for cost optimization)"
  type        = string
  default     = "postgres"
  validation {
    condition     = var.db_engine == "postgres"
    error_message = "Only PostgreSQL is supported in cost optimization mode."
  }
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
  validation {
    condition     = contains(["db.t4g.micro", "db.t4g.small"], var.db_instance_class)
    error_message = "Only db.t4g.micro and db.t4g.small are supported for cost optimization."
  }
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS (GB)"
  type        = number
  default     = 20
  validation {
    condition     = var.db_allocated_storage >= 20 && var.db_allocated_storage <= 100
    error_message = "Storage must be between 20 and 100 GB for cost optimization."
  }
}

variable "db_storage_type" {
  description = "Storage type for RDS"
  type        = string
  default     = "gp3"
  validation {
    condition     = contains(["gp3", "gp2"], var.db_storage_type)
    error_message = "Only gp3 or gp2 storage types are supported."
  }
}

variable "db_backup_retention_period" {
  description = "Backup retention period (days)"
  type        = number
  default     = 1
  validation {
    condition     = var.db_backup_retention_period >= 1 && var.db_backup_retention_period <= 7
    error_message = "Backup retention must be between 1 and 7 days for cost optimization."
  }
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = false # Single AZ for cost optimization
}

# ECS Fargate Configuration - Optimized
variable "fargate_cpu" {
  description = "CPU units for Fargate task (1024 = 1 vCPU)"
  type        = number
  default     = 256
  validation {
    condition     = contains([256, 512, 1024, 2048, 4096], var.fargate_cpu)
    error_message = "Fargate CPU must be one of: 256, 512, 1024, 2048, 4096."
  }
}

variable "fargate_memory" {
  description = "Memory for Fargate task (MB)"
  type        = number
  default     = 512
  validation {
    condition     = var.fargate_memory >= 512 && var.fargate_memory <= 30720
    error_message = "Fargate memory must be between 512 MB and 30720 MB."
  }
}

variable "fargate_desired_count" {
  description = "Desired number of Fargate tasks"
  type        = number
  default     = 1
  validation {
    condition     = var.fargate_desired_count >= 1 && var.fargate_desired_count <= 10
    error_message = "Desired count must be between 1 and 10 for cost optimization."
  }
}

variable "fargate_min_capacity" {
  description = "Minimum number of Fargate tasks for auto-scaling"
  type        = number
  default     = 1
  validation {
    condition     = var.fargate_min_capacity >= 1 && var.fargate_min_capacity <= 5
    error_message = "Minimum capacity must be between 1 and 5."
  }
}

variable "fargate_max_capacity" {
  description = "Maximum number of Fargate tasks for auto-scaling"
  type        = number
  default     = 3
  validation {
    condition     = var.fargate_max_capacity >= 2 && var.fargate_max_capacity <= 10
    error_message = "Maximum capacity must be between 2 and 10 for cost optimization."
  }
}

variable "cloudflare_ip_ranges" {
  description = "CloudFlare IP ranges for security group access"
  type        = list(string)
  default = [
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22"
  ]
}


# Cloudflare Configuration
variable "cloudflare_zone_id" {
  description = "Cloudflare Zone ID for fiscaliza.pt"
  type        = string
  default     = ""
}

# Load Balancer Configuration
variable "enable_alb" {
  description = "Enable Application Load Balancer (HTTP/HTTPS, ~€16/month). Disable to save costs - CloudFlare will connect directly to ECS public IP"
  type        = bool
  default     = false # Disabled by default for cost optimization
}

variable "enable_nlb" {
  description = "Enable Network Load Balancer with Elastic IP (TCP, static IP, ~$16/month)"
  type        = bool
  default     = false
}

variable "enable_ip_automation" {
  description = "DEPRECATED: Use enable_cloudflare_dns_updater instead"
  type        = bool
  default     = false
}

# CloudFlare DNS Auto-Updater
variable "enable_cloudflare_dns_updater" {
  description = "Enable automatic CloudFlare DNS updates when ECS task IP changes. Required when ALB is disabled. Cost: ~€0.01/month"
  type        = bool
  default     = true # Enabled by default when ALB is disabled
}

# Static Website Configuration
variable "enable_cloudfront_for_website" {
  description = "Enable CloudFront for static website (better performance, extra cost)"
  type        = bool
  default     = false
}

variable "cloudfront_price_class" {
  description = "CloudFront price class for website distribution"
  type        = string
  default     = "PriceClass_100" # US, Canada, Europe only
  validation {
    condition     = contains(["PriceClass_100", "PriceClass_200", "PriceClass_All"], var.cloudfront_price_class)
    error_message = "CloudFront price class must be PriceClass_100, PriceClass_200, or PriceClass_All."
  }
}

variable "api_subdomain" {
  description = "Subdomain for API endpoints"
  type        = string
  default     = "api"
}

variable "api_domain_name" {
  description = "Full API domain name (auto-generated from api_subdomain + domain_name)"
  type        = string
  default     = ""
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token"
  type        = string
  sensitive   = true
  default     = ""
}

# Cloudflare Cache Configuration
variable "enable_cloudflare_cache" {
  description = "Enable Cloudflare caching (Free plan compatible)"
  type        = bool
  default     = true
}

variable "cloudflare_cache_level" {
  description = "Cloudflare cache level (aggressive, basic, simplified)"
  type        = string
  default     = "aggressive"
  validation {
    condition     = contains(["aggressive", "basic", "simplified"], var.cloudflare_cache_level)
    error_message = "Cache level must be aggressive, basic, or simplified."
  }
}

variable "enable_cloudflare_waf" {
  description = "Enable Cloudflare WAF (requires Pro plan or higher)"
  type        = bool
  default     = false
}

variable "enable_alb_alternative" {
  description = "Use ALB with static DNS name instead of dynamic IP (costs ~$16/month extra but more reliable)"
  type        = bool
  default     = false
}



# Monitoring Configuration - Minimal
variable "enable_basic_monitoring" {
  description = "Enable basic CloudWatch monitoring"
  type        = bool
  default     = true
}

variable "enable_detailed_monitoring" {
  description = "Enable detailed monitoring (costs extra)"
  type        = bool
  default     = false # Disabled for cost optimization
}

variable "alert_email" {
  description = "Email address for critical alerts"
  type        = string
  default     = ""
  validation {
    condition     = var.alert_email == "" || can(regex("^[\\w\\.-]+@[\\w\\.-]+\\.[a-zA-Z]{2,}$", var.alert_email))
    error_message = "Alert email must be a valid email address or empty string."
  }
}


# Application Caching Configuration
variable "enable_in_memory_cache" {
  description = "Enable in-memory caching in Lambda"
  type        = bool
  default     = true
}

variable "cache_ttl_seconds" {
  description = "Default cache TTL in seconds"
  type        = number
  default     = 300
}

variable "enable_connection_pooling" {
  description = "Enable database connection pooling"
  type        = bool
  default     = true
}

variable "max_connections" {
  description = "Maximum database connections"
  type        = number
  default     = 10
  validation {
    condition     = var.max_connections >= 6 && var.max_connections <= 50
    error_message = "Max connections must be between 6 and 50 (PostgreSQL minimum is 6)."
  }
}

variable "backend_image" {
  description = "Docker image URI for the backend Lambda function"
  type        = string
  default     = ""
}

# Import Pipeline Configuration
variable "enable_scheduled_import" {
  description = "Enable scheduled ECS tasks for data discovery and import (daily at 2 AM and 4 AM UTC)"
  type        = bool
  default     = false  # Disabled by default - enable when ready for production imports
}

# ============================================================================
# TAGGING CONFIGURATION FOR COST ANALYSIS AND RESOURCE MANAGEMENT
# ============================================================================

variable "project_name" {
  description = "Project name for tagging and identification"
  type        = string
  default     = "Parliament"
  validation {
    condition     = length(var.project_name) > 0 && length(var.project_name) <= 50
    error_message = "Project name must be between 1 and 50 characters."
  }
}

variable "application_name" {
  description = "Application name for tagging"
  type        = string
  default     = "Fiscaliza"
  validation {
    condition     = length(var.application_name) > 0 && length(var.application_name) <= 50
    error_message = "Application name must be between 1 and 50 characters."
  }
}

variable "cost_center" {
  description = "Cost center for billing allocation"
  type        = string
  default     = "Parliament-Analytics"
  validation {
    condition     = length(var.cost_center) > 0 && length(var.cost_center) <= 100
    error_message = "Cost center must be between 1 and 100 characters."
  }
}

variable "owner_team" {
  description = "Team responsible for the resources"
  type        = string
  default     = "DevOps"
  validation {
    condition     = length(var.owner_team) > 0 && length(var.owner_team) <= 50
    error_message = "Owner team must be between 1 and 50 characters."
  }
}

variable "owner_email" {
  description = "Email of the resource owner for contact purposes"
  type        = string
  default     = ""
  validation {
    condition     = var.owner_email == "" || can(regex("^[\\w\\.-]+@[\\w\\.-]+\\.[a-zA-Z]{2,}$", var.owner_email))
    error_message = "Owner email must be a valid email address or empty string."
  }
}

variable "business_unit" {
  description = "Business unit responsible for costs"
  type        = string
  default     = "Government-Transparency"
  validation {
    condition     = length(var.business_unit) > 0 && length(var.business_unit) <= 100
    error_message = "Business unit must be between 1 and 100 characters."
  }
}

variable "backup_schedule" {
  description = "Backup schedule for resources (daily, weekly, monthly, none)"
  type        = string
  default     = "daily"
  validation {
    condition     = contains(["daily", "weekly", "monthly", "none"], var.backup_schedule)
    error_message = "Backup schedule must be one of: daily, weekly, monthly, none."
  }
}

variable "data_classification" {
  description = "Data classification level (public, internal, confidential, restricted)"
  type        = string
  default     = "public"
  validation {
    condition     = contains(["public", "internal", "confidential", "restricted"], var.data_classification)
    error_message = "Data classification must be one of: public, internal, confidential, restricted."
  }
}

variable "compliance_requirements" {
  description = "Compliance requirements (gdpr, none, custom)"
  type        = string
  default     = "gdpr"
  validation {
    condition     = contains(["gdpr", "none", "custom"], var.compliance_requirements)
    error_message = "Compliance requirements must be one of: gdpr, none, custom."
  }
}

variable "auto_shutdown" {
  description = "Whether resources support auto-shutdown for cost optimization"
  type        = bool
  default     = false
}

variable "monitoring_level" {
  description = "Level of monitoring required (basic, standard, enhanced)"
  type        = string
  default     = "basic"
  validation {
    condition     = contains(["basic", "standard", "enhanced"], var.monitoring_level)
    error_message = "Monitoring level must be one of: basic, standard, enhanced."
  }
}

variable "additional_tags" {
  description = "Additional custom tags to apply to all resources"
  type        = map(string)
  default     = {}
  validation {
    condition     = length(var.additional_tags) <= 10
    error_message = "Additional tags cannot exceed 10 key-value pairs."
  }
}

# ============================================================================
# AUTOMATED DATA IMPORT CONFIGURATION
# ============================================================================
# Ultra-cost-effective spot instance based automated data import
# Total additional cost: ~$0.03/month for daily 20-minute imports

variable "enable_automated_import" {
  description = "Enable automated parliament data import using spot instances"
  type        = bool
  default     = true
}

# Import-related variables are defined in spot-import-variables.tf

# Remote Database Access
variable "admin_ip_address" {
  description = "IP address allowed for remote database access (your current IP)"
  type        = string
  default     = ""
  validation {
    condition     = var.admin_ip_address == "" || can(regex("^[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}$", var.admin_ip_address))
    error_message = "Admin IP address must be a valid IPv4 address or empty string."
  }
}

