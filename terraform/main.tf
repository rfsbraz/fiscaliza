# Portuguese Parliament Transparency Platform - Main Configuration
# Fiscaliza.pt - Cost-optimized architecture with PostgreSQL RDS and Lambda Function URL
# Target cost: $11-17/month

# AWS provider configuration moved to terraform.tf to avoid duplicates

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# Local values
locals {
  name_prefix = "fiscaliza-${var.environment}"

  # Enhanced tagging strategy for cost analysis and resource management
  # Filter out empty values to prevent AWS validation errors
  base_tags = {
    Project                = var.project_name
    Application            = var.application_name
    Environment            = var.environment
    ManagedBy              = "Terraform"
    BusinessUnit           = var.business_unit
    CostCenter             = var.cost_center
    OwnerTeam              = var.owner_team
    DataClassification     = var.data_classification
    ComplianceRequirements = var.compliance_requirements
    BackupSchedule         = var.backup_schedule
    MonitoringLevel        = var.monitoring_level
    AutoShutdown           = var.auto_shutdown ? "enabled" : "disabled"
    CostOptimized          = var.cost_optimization_mode ? "true" : "false"
    Website                = replace(var.domain_name, ".", "-")
    TargetCost             = "8_12_USD_monthly"
    Terraform              = "true"
    Repository             = "parliament"
    CreatedDate            = formatdate("YYYY_MM_DD", timestamp())
    LastModified           = formatdate("YYYY_MM_DD", timestamp())
  }

  # Add optional tags only if they have values
  optional_tags = var.owner_email != "" ? {
    OwnerEmail = var.owner_email
  } : {}

  common_tags = merge(
    local.base_tags,
    local.optional_tags,
    var.additional_tags
  )

  # Backwards compatibility - remove this after migration
  tags = local.common_tags

  # Component-specific tag sets for different resource types
  compute_tags = merge(local.common_tags, {
    ComponentType = "compute"
    ServiceType   = "ecs-fargate"
    Billable      = "true"
  })

  database_tags = merge(local.common_tags, {
    ComponentType = "database"
    ServiceType   = "rds"
    Billable      = "true"
    DataStore     = "true"
  })

  storage_tags = merge(local.common_tags, {
    ComponentType = "storage"
    ServiceType   = "s3"
    Billable      = "true"
  })

  network_tags = merge(local.common_tags, {
    ComponentType = "network"
    ServiceType   = "vpc"
    Billable      = "conditional"
  })

  monitoring_tags = merge(local.common_tags, {
    ComponentType = "monitoring"
    ServiceType   = "cloudwatch"
    Billable      = "true"
  })

  security_tags = merge(local.common_tags, {
    ComponentType = "security"
    ServiceType   = "iam"
    Billable      = "false"
  })

  # Calculate number of availability zones (minimum 2 for redundancy)
  azs = slice(data.aws_availability_zones.available.names, 0, 2)

  # API domain name (computed from subdomain + main domain)
  api_domain_name = var.api_domain_name != "" ? var.api_domain_name : "${var.api_subdomain}.${var.domain_name}"
}

# VPC for cost-optimized infrastructure
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-vpc"
    ResourceType = "vpc"
    Purpose      = "main-network-infrastructure"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-igw"
    ResourceType = "internet-gateway"
    Purpose      = "internet-access"
  })
}

# Public subnets (for NAT Gateway)
resource "aws_subnet" "public" {
  count = length(local.azs)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-public-${count.index + 1}"
    ResourceType = "subnet"
    SubnetType   = "public"
    Purpose      = "public-subnet-${count.index + 1}"
    AZ           = local.azs[count.index]
  })
}

# Private subnets (for Lambda and RDS)
resource "aws_subnet" "private" {
  count = length(local.azs)

  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = local.azs[count.index]

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-private-${count.index + 1}"
    ResourceType = "subnet"
    SubnetType   = "private"
    Purpose      = "private-subnet-${count.index + 1}"
    AZ           = local.azs[count.index]
  })
}

# Single NAT Gateway for cost optimization (instead of one per AZ)
# CONDITIONAL: Only created when enable_nat_gateway = true
# Saves ~€35/month when disabled
resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? 1 : 0
  domain = "vpc"

  depends_on = [aws_internet_gateway.main]

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-nat-eip"
    ResourceType = "elastic-ip"
    Purpose      = "nat-gateway"
    Billable     = "true"
  })
}

resource "aws_nat_gateway" "main" {
  count         = var.enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id

  depends_on = [aws_internet_gateway.main]

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-nat"
    ResourceType = "nat-gateway"
    Purpose      = "private-subnet-internet-access"
    Billable     = "true"
  })
}

# Route table for public subnets
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-public-rt"
    ResourceType = "route-table"
    Purpose      = "public-subnet-routing"
  })
}

# Route table for private subnets
# When NAT Gateway is disabled, private subnets route through IGW (cost optimization)
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  # Conditional routing: NAT Gateway when enabled, IGW when disabled
  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.main[0].id
    }
  }

  dynamic "route" {
    for_each = var.enable_nat_gateway ? [] : [1]
    content {
      cidr_block = "0.0.0.0/0"
      gateway_id = aws_internet_gateway.main.id
    }
  }

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-private-rt"
    ResourceType = "route-table"
    Purpose      = var.enable_nat_gateway ? "private-subnet-routing" : "private-subnet-routing-via-igw"
  })
}

# Route table associations
resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# VPC Endpoints for cost optimization (reduce NAT Gateway usage)
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${var.aws_region}.s3"

  tags = merge(local.network_tags, {
    Name         = "${local.name_prefix}-s3-endpoint"
    ResourceType = "vpc-endpoint"
    Purpose      = "s3-access-cost-optimization"
    EndpointType = "gateway"
  })
}

resource "aws_vpc_endpoint_route_table_association" "s3_private" {
  route_table_id  = aws_route_table.private.id
  vpc_endpoint_id = aws_vpc_endpoint.s3.id
}

# VPC Flow Logs (basic, cost-optimized)
resource "aws_flow_log" "vpc" {
  count = var.enable_basic_monitoring ? 1 : 0

  iam_role_arn    = aws_iam_role.flow_logs[0].arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs[0].arn
  traffic_type    = "REJECT" # Only log rejected traffic for security
  vpc_id          = aws_vpc.main.id

  tags = merge(local.monitoring_tags, {
    Name         = "${local.name_prefix}-vpc-flow-logs"
    ResourceType = "vpc-flow-logs"
    Purpose      = "network-security-monitoring"
    LogType      = "vpc-flow"
  })
}

resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  count = var.enable_basic_monitoring ? 1 : 0

  name              = "/aws/vpc/flowlogs/${local.name_prefix}"
  retention_in_days = 3 # Short retention for cost optimization

  tags = merge(local.monitoring_tags, {
    Name          = "${local.name_prefix}-vpc-flow-logs-group"
    ResourceType  = "cloudwatch-log-group"
    Purpose       = "vpc-flow-logs-storage"
    LogType       = "vpc-flow"
    RetentionDays = "3"
  })
}

resource "aws_iam_role" "flow_logs" {
  count = var.enable_basic_monitoring ? 1 : 0

  name = "${local.name_prefix}-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-flow-logs-role"
    ResourceType = "iam-role"
    Purpose      = "vpc-flow-logs-permissions"
    ServiceType  = "iam"
  })
}

resource "aws_iam_role_policy" "flow_logs" {
  count = var.enable_basic_monitoring ? 1 : 0

  name = "${local.name_prefix}-flow-logs-policy"
  role = aws_iam_role.flow_logs[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Basic security group for VPC endpoints
resource "aws_security_group" "vpc_endpoints" {
  name_prefix = "${local.name_prefix}-vpc-endpoints-"
  vpc_id      = aws_vpc.main.id
  description = "Security group for VPC endpoints"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.security_tags, {
    Name         = "${local.name_prefix}-vpc-endpoints-sg"
    ResourceType = "security-group"
    Purpose      = "vpc-endpoints-access-control"
  })

  lifecycle {
    create_before_destroy = true
  }
}