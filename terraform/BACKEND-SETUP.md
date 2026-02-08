# Terraform Remote State Backend Setup

This guide explains how to set up secure remote state management for the Parliament Transparency Application.

## Overview

The Parliament project uses Terraform with **S3 remote state backend** and **DynamoDB state locking** for:

- ✅ **Multi-user collaboration** - Team can share state safely
- ✅ **State locking** - Prevents concurrent modifications
- ✅ **Encryption** - State encrypted with KMS
- ✅ **Versioning** - State history and recovery
- ✅ **Environment isolation** - Separate dev/prod states

## Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **Terraform >= 1.0** installed
3. **AWS permissions** for S3, DynamoDB, and KMS

### Required AWS Permissions

Your AWS user/role needs permissions for:
- S3 bucket creation and management
- DynamoDB table creation and management  
- KMS key creation and management
- IAM policy attachment (for cross-account access)

## Quick Setup

### 1. Configure AWS CLI

```bash
aws configure
# Enter your AWS Access Key ID, Secret, Region (eu-west-1), and output format
```

### 2. Set up Backend Infrastructure

**For Windows:**
```cmd
cd terraform
setup-backend.bat
```

**For Linux/macOS:**
```bash
cd terraform
chmod +x *.sh
./setup-backend.sh
```

### 3. Migrate to Remote State

**For Development Environment:**
```cmd
migrate-to-remote-state.bat dev    # Windows
./migrate-to-remote-state.sh dev   # Linux/macOS
```

**For Production Environment:**
```cmd
migrate-to-remote-state.bat prod   # Windows
./migrate-to-remote-state.sh prod  # Linux/macOS
```

## Manual Setup Process

If you prefer manual setup or troubleshooting:

### Step 1: Create Backend Infrastructure

```bash
# Initialize with local state for bootstrap
terraform init

# Create backend infrastructure
terraform plan -var="aws_region=eu-west-1" -out=backend.tfplan
terraform apply backend.tfplan

# Clean up bootstrap state
rm -f backend.tfplan terraform.tfstate terraform.tfstate.backup
```

### Step 2: Configure Remote Backend

```bash
# Clean existing state
rm -rf .terraform .terraform.lock.hcl

# Initialize with remote backend
terraform init \
    -backend-config="key=dev/terraform.tfstate" \
    -backend-config="bucket=parliament-terraform-state-eu-west-1" \
    -backend-config="region=eu-west-1" \
    -backend-config="dynamodb_table=parliament-terraform-locks" \
    -backend-config="encrypt=true" \
    -backend-config="kms_key_id=alias/terraform-state-key"
```

## Backend Configuration Details

### S3 Bucket Configuration
- **Name**: `parliament-terraform-state-eu-west-1`
- **Region**: `eu-west-1`
- **Encryption**: KMS with dedicated key
- **Versioning**: Enabled (30-day retention)
- **Public Access**: Blocked
- **Lifecycle**: 30-day cleanup for old versions

### DynamoDB Lock Table
- **Name**: `parliament-terraform-locks`
- **Key**: `LockID` (String)
- **Billing**: Pay-per-request (cost-optimized)
- **Point-in-time Recovery**: Enabled

### State Key Structure
```
parliament-terraform-state-eu-west-1/
├── dev/terraform.tfstate      # Development environment
└── prod/terraform.tfstate     # Production environment
```

## Daily Operations

### Development Work
```bash
# Navigate to terraform directory
cd terraform

# Plan changes
terraform plan -var-file=environments/dev.tfvars

# Apply changes  
terraform apply -var-file=environments/dev.tfvars
```

### Production Deployment
```bash
# Plan production changes
terraform plan -var-file=environments/prod.tfvars

# Apply to production
terraform apply -var-file=environments/prod.tfvars
```

### Switch Between Environments

To work with different environments, re-run the migration script:

```bash
# Switch to dev
./migrate-to-remote-state.sh dev

# Switch to prod
./migrate-to-remote-state.sh prod
```

## Security Best Practices

### 1. **KMS Encryption**
- State files encrypted with dedicated KMS key
- Key rotation enabled
- Access controlled via IAM

### 2. **IAM Permissions**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::parliament-terraform-state-eu-west-1",
        "arn:aws:s3:::parliament-terraform-state-eu-west-1/*"
      ]
    },
    {
      "Effect": "Allow", 
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:eu-west-1:*:table/parliament-terraform-locks"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:eu-west-1:*:key/*"
    }
  ]
}
```

### 3. **Access Control**
- S3 bucket blocks all public access
- DynamoDB table requires authentication
- KMS key access controlled via key policies

## Troubleshooting

### Common Issues

#### 1. **AWS CLI Not Configured**
```
Error: AWS CLI is not configured
```
**Solution:**
```bash
aws configure
aws sts get-caller-identity  # Verify
```

#### 2. **Insufficient Permissions**
```
Error: AccessDenied when calling CreateBucket
```
**Solution:** Ensure your AWS user has the required permissions listed above.

#### 3. **Backend Already Initialized**
```
Error: Backend configuration changed
```
**Solution:**
```bash
rm -rf .terraform .terraform.lock.hcl
terraform init -reconfigure
```

#### 4. **State Lock Conflicts**
```
Error: Error acquiring the state lock
```
**Solution:**
```bash
# Force unlock (use carefully)
terraform force-unlock <lock-id>
```

### Disaster Recovery

#### Restore State from Backup
```bash
# List available versions
aws s3api list-object-versions \
    --bucket parliament-terraform-state-eu-west-1 \
    --prefix dev/terraform.tfstate

# Download specific version
aws s3api get-object \
    --bucket parliament-terraform-state-eu-west-1 \
    --key dev/terraform.tfstate \
    --version-id <version-id> \
    terraform.tfstate.backup
```

## Cost Optimization

### Current Monthly Costs (Estimated)
- **S3 Storage**: ~$0.50/month (for state files)
- **DynamoDB**: ~$0.25/month (pay-per-request)
- **KMS**: ~$1.00/month (key usage)
- **Total**: ~$1.75/month

### Cost Monitoring
```bash
# Check S3 storage usage
aws s3api head-bucket --bucket parliament-terraform-state-eu-west-1

# Check DynamoDB metrics
aws dynamodb describe-table --table-name parliament-terraform-locks
```

## Multi-User Setup

### For Team Members

1. **Share these values** (not sensitive):
   - Bucket: `parliament-terraform-state-eu-west-1`
   - DynamoDB Table: `parliament-terraform-locks`
   - Region: `eu-west-1`

2. **Each team member runs:**
   ```bash
   git clone <repository>
   cd terraform
   ./migrate-to-remote-state.sh dev
   ```

3. **Configure AWS credentials** locally:
   ```bash
   aws configure
   ```

## Files Created

This setup creates the following files:
- `backend-setup.tf` - Backend infrastructure definition
- `backend-setup-variables.tf` - Variables for backend setup
- `setup-backend.sh/.bat` - Automated backend setup
- `migrate-to-remote-state.sh/.bat` - State migration scripts
- `BACKEND-SETUP.md` - This documentation

## Next Steps

After completing backend setup:

1. ✅ **Verify remote state**: `terraform state list`
2. ✅ **Test environment isolation**: Switch between dev/prod
3. ✅ **Document team access**: Share setup instructions
4. ✅ **Configure CI/CD**: Use remote state in pipelines
5. ✅ **Monitor costs**: Set up AWS billing alerts

---

**⚠️ Important Notes:**

- Backend infrastructure is shared across all environments
- Each environment has its own state file path
- Local state files are removed after migration
- Always verify AWS credentials before setup
- Keep this documentation updated for team members