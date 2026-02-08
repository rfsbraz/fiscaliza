# Terraform Backend Infrastructure Setup
# This file creates the S3 bucket and DynamoDB table needed for remote state
# Run this FIRST before configuring the main infrastructure

# Backend setup uses local state to bootstrap remote state infrastructure
# Separate provider for backend resources without default tags to avoid conflicts
provider "aws" {
  alias   = "backend"
  profile = "reddit-proxy"
  region  = var.aws_region
  # No default tags to avoid conflicts with explicit tags
}

# S3 bucket for Terraform state
resource "aws_s3_bucket" "terraform_state" {
  provider = aws.backend
  bucket = "parliament-terraform-state-eu-west-1"

  tags = {
    Name        = "Parliament Terraform State"
    Environment = "shared"
    Project     = "Parliament"
    Purpose     = "terraform-state-storage"
    CreatedBy   = "terraform"
  }
}

# Enable versioning for state file recovery
resource "aws_s3_bucket_versioning" "terraform_state_versioning" {
  provider = aws.backend
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state_encryption" {
  provider = aws.backend
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.terraform_state_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# Block public access to the state bucket
resource "aws_s3_bucket_public_access_block" "terraform_state_pab" {
  provider = aws.backend
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket lifecycle configuration to manage costs
resource "aws_s3_bucket_lifecycle_configuration" "terraform_state_lifecycle" {
  provider = aws.backend
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    id     = "terraform_state_lifecycle"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# KMS key for state encryption
resource "aws_kms_key" "terraform_state_key" {
  provider = aws.backend
  description             = "KMS key for Terraform state encryption"
  deletion_window_in_days = 7

  tags = {
    Name        = "terraform-state-key"
    Environment = "shared"
    Project     = "Parliament"
    Purpose     = "terraform-state-encryption"
  }
}

# KMS key alias
resource "aws_kms_alias" "terraform_state_key_alias" {
  provider = aws.backend
  name          = "alias/terraform-state-key"
  target_key_id = aws_kms_key.terraform_state_key.key_id
}

# DynamoDB table for state locking
resource "aws_dynamodb_table" "terraform_locks" {
  provider       = aws.backend
  name           = "parliament-terraform-locks"
  billing_mode   = "PAY_PER_REQUEST"  # Cost-optimized
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  # point_in_time_recovery disabled due to permission requirements
  # point_in_time_recovery {
  #   enabled = true
  # }

  tags = {
    Name        = "Parliament Terraform Locks"
    Environment = "shared"
    Project     = "Parliament"
    Purpose     = "terraform-state-locking"
    CreatedBy   = "terraform"
  }
}

# Outputs for reference
output "state_bucket_name" {
  description = "Name of the S3 bucket for Terraform state"
  value       = aws_s3_bucket.terraform_state.id
}

output "state_bucket_arn" {
  description = "ARN of the S3 bucket for Terraform state"
  value       = aws_s3_bucket.terraform_state.arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  value       = aws_dynamodb_table.terraform_locks.name
}

output "kms_key_id" {
  description = "ID of the KMS key for state encryption"
  value       = aws_kms_key.terraform_state_key.key_id
}

output "kms_key_arn" {
  description = "ARN of the KMS key for state encryption"
  value       = aws_kms_key.terraform_state_key.arn
}