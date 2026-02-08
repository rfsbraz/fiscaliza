# Terraform Configuration for Portuguese Parliament Transparency Application
# Cost-Optimized Infrastructure with PostgreSQL RDS and Lambda Function URL

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }

  # Remote state configuration
  # Note: backend blocks cannot use variables. Pass profile via CLI:
  #   terraform init -backend-config="profile=your-profile"
  backend "s3" {
    bucket         = "parliament-terraform-state-eu-west-1"
    key            = "terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true
    dynamodb_table = "parliament-terraform-locks"
  }
}

# AWS provider configuration
provider "aws" {
  profile = var.aws_profile
  region  = var.aws_region
}

# AWS provider for us-east-1 (required for CloudFront SSL certificates)
provider "aws" {
  alias   = "us_east_1"
  profile = var.aws_profile
  region  = "us-east-1"
}

# Cloudflare provider configuration
provider "cloudflare" {
  api_token = var.cloudflare_api_token
  # Alternative: use email + api_key for full access
  # email   = "your-email@example.com"
  # api_key = var.cloudflare_api_key
}