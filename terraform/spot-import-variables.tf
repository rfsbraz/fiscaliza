# Spot Instance Import Job Variables
# Ultra-cost-effective automated data import solution using spot instances

# ============================================================================
# IMPORT AUTOMATION CONFIGURATION
# ============================================================================

variable "import_automation_mode" {
  description = "Import execution mode: disabled (no execution), manual (Function URL only), daily (scheduled + manual), custom (custom schedule)"
  type        = string
  default     = "manual"
  validation {
    condition     = contains(["disabled", "manual", "daily", "custom"], var.import_automation_mode)
    error_message = "Import automation mode must be one of: disabled, manual, daily, custom."
  }
}

variable "import_schedule" {
  description = "Custom cron schedule for import execution (used when mode=custom). Default is 2 AM UTC daily."
  type        = string
  default     = "cron(0 2 * * ? *)"
  validation {
    condition     = can(regex("^(rate\\(|cron\\()", var.import_schedule))
    error_message = "Import schedule must be a valid EventBridge schedule expression (rate() or cron())."
  }
}

variable "enable_manual_trigger" {
  description = "Enable Lambda Function URL for manual import triggering"
  type        = bool
  default     = true
}

# ============================================================================
# SPOT INSTANCE CONFIGURATION
# ============================================================================

variable "spot_instance_type" {
  description = "EC2 instance type for import jobs (optimized for cost)"
  type        = string
  default     = "t3.large"
  validation {
    condition = contains([
      "t3.nano", "t3.micro", "t3.small",
      "t4g.nano", "t4g.micro", "t4g.small", "t3.large"
    ], var.spot_instance_type)
    error_message = "Spot instance type must be a cost-optimized instance (t3.nano, t3.micro, t3.small, t4g.nano, t4g.micro, t4g.small)."
  }
}

variable "spot_max_price" {
  description = "Maximum price for spot instances (USD per hour). Empty string uses current spot price."
  type        = string
  default     = ""
  validation {
    condition     = var.spot_max_price == "" || can(tonumber(var.spot_max_price))
    error_message = "Spot max price must be empty string or a valid number."
  }
}

variable "import_timeout_minutes" {
  description = "Maximum import execution time in minutes (instance auto-terminates after this)"
  type        = number
  default     = 120 # 2 hours default timeout
  validation {
    condition     = var.import_timeout_minutes >= 10 && var.import_timeout_minutes <= 800
    error_message = "Import timeout must be between 10 and 240 minutes (4 hours max)."
  }
}

# ============================================================================
# IMPORT SCRIPT CONFIGURATION
# ============================================================================

variable "import_script_repository" {
  description = "Git repository URL for the parliament data import scripts"
  type        = string
  default     = "https://github.com/your-username/parliament.git"
}

variable "import_script_branch" {
  description = "Git branch to use for import scripts"
  type        = string
  default     = "main"
}

variable "import_script_path" {
  description = "Path to the main import script within the repository"
  type        = string
  default     = "scripts/data_processing/pipeline_orchestrator.py"
}

variable "import_python_requirements" {
  description = "Additional Python packages to install (space-separated)"
  type        = string
  default     = "requests sqlalchemy psycopg2-binary rich"
}

# ============================================================================
# MONITORING AND ALERTING
# ============================================================================

variable "enable_import_monitoring" {
  description = "Enable CloudWatch monitoring and SNS alerts for import jobs"
  type        = bool
  default     = true
}

variable "import_alert_email" {
  description = "Email address for import job failure notifications"
  type        = string
  default     = ""
  validation {
    condition     = var.import_alert_email == "" || can(regex("^[\\w\\.-]+@[\\w\\.-]+\\.[a-zA-Z]{2,}$", var.import_alert_email))
    error_message = "Import alert email must be a valid email address or empty string."
  }
}

variable "import_log_retention_days" {
  description = "CloudWatch log retention period for import jobs"
  type        = number
  default     = 7
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.import_log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

# ============================================================================
# ADVANCED CONFIGURATION
# ============================================================================

variable "spot_interruption_behavior" {
  description = "Behavior when spot instance is interrupted (stop, hibernate, terminate)"
  type        = string
  default     = "terminate"
  validation {
    condition     = contains(["stop", "hibernate", "terminate"], var.spot_interruption_behavior)
    error_message = "Spot interruption behavior must be one of: stop, hibernate, terminate."
  }
}

variable "enable_import_retries" {
  description = "Enable automatic retries on spot instance interruption"
  type        = bool
  default     = true
}

variable "max_import_retries" {
  description = "Maximum number of automatic retry attempts"
  type        = number
  default     = 2
  validation {
    condition     = var.max_import_retries >= 0 && var.max_import_retries <= 5
    error_message = "Max import retries must be between 0 and 5."
  }
}

variable "import_environment_variables" {
  description = "Additional environment variables to pass to import script"
  type        = map(string)
  default     = {}
  validation {
    condition     = length(var.import_environment_variables) <= 20
    error_message = "Cannot specify more than 20 environment variables."
  }
}