#!/bin/bash
# Portuguese Parliament Serverless Deployment Script
# This script builds and deploys the Flask backend as a Lambda function using AWS Lambda Web Adapter

set -e

# Configuration
PROJECT_NAME="parliament"
ENVIRONMENT="${ENVIRONMENT:-prod}"
AWS_REGION="${AWS_REGION:-eu-west-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

echo_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

echo_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

echo_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo_info "Checking prerequisites..."

if ! command_exists aws; then
    echo_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! command_exists docker; then
    echo_error "Docker is not installed. Please install it first."
    exit 1
fi

if ! command_exists terraform; then
    echo_error "Terraform is not installed. Please install it first."
    exit 1
fi

# Verify AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo_error "AWS credentials not configured. Please run 'aws configure'."
    exit 1
fi

echo_success "Prerequisites check passed"

# Step 1: Build the serverless Docker image
echo_info "Building serverless Docker image..."

# Ensure we're in the project root
if [[ ! -f "Dockerfile" ]]; then
    echo_error "Dockerfile not found. Please run this script from the project root."
    exit 1
fi

# Build the image
SERVERLESS_IMAGE="${PROJECT_NAME}-backend-serverless:latest"
docker build -f Dockerfile -t "$SERVERLESS_IMAGE" .

echo_success "Serverless Docker image built: $SERVERLESS_IMAGE"

# Step 2: Create ECR repository if it doesn't exist
echo_info "Setting up ECR repository..."

REPO_NAME="${PROJECT_NAME}-backend-serverless"
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}"

# Check if repository exists
if ! aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo_info "Creating ECR repository: $REPO_NAME"
    aws ecr create-repository \
        --repository-name "$REPO_NAME" \
        --region "$AWS_REGION" \
        --image-scanning-configuration scanOnPush=true
    echo_success "ECR repository created"
else
    echo_info "ECR repository already exists: $REPO_NAME"
fi

# Step 3: Push image to ECR
echo_info "Pushing image to ECR..."

# Login to ECR
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_URI"

# Tag and push
docker tag "$SERVERLESS_IMAGE" "$ECR_URI:latest"
docker push "$ECR_URI:latest"

echo_success "Image pushed to ECR: $ECR_URI:latest"

# Step 4: Deploy infrastructure with Terraform
echo_info "Deploying serverless infrastructure with Terraform..."

cd terraform

# Initialize Terraform if needed
if [[ ! -d ".terraform" ]]; then
    echo_info "Initializing Terraform..."
    terraform init
fi

# Plan the deployment
echo_info "Planning serverless deployment..."
terraform plan \
    -var="environment=$ENVIRONMENT" \
    -var="aws_region=$AWS_REGION" \
    -var="backend_image=$ECR_URI:latest" \
    -out=serverless.tfplan

# Apply the plan
echo_info "Applying serverless deployment..."
terraform apply serverless.tfplan

echo_success "Serverless infrastructure deployed!"

# Step 5: Get deployment outputs
echo_info "Getting deployment information..."

LAMBDA_FUNCTION_URL=$(terraform output -raw lambda_function_url 2>/dev/null || echo "Not available")
CLOUDFRONT_URL=$(terraform output -raw cloudfront_domain_name 2>/dev/null || echo "Not available")
S3_BUCKET=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "Not available")

cd ..

# Step 6: Display deployment summary
echo ""
echo "========================================"
echo_success "SERVERLESS DEPLOYMENT COMPLETE!"
echo "========================================"
echo ""
echo "📍 Deployment Details:"
echo "   Environment: $ENVIRONMENT"
echo "   Region: $AWS_REGION"
echo "   Account: $AWS_ACCOUNT_ID"
echo ""
echo "🚀 Endpoints:"
echo "   Lambda Function URL: $LAMBDA_FUNCTION_URL"
echo "   CloudFront URL: https://$CLOUDFRONT_URL"
echo ""
echo "📦 Resources:"
echo "   ECR Repository: $ECR_URI"
echo "   S3 Bucket: $S3_BUCKET"
echo ""
echo "💡 Next Steps:"
echo "   1. Build and deploy your React frontend to the S3 bucket"
echo "   2. Test the API endpoints via the Lambda Function URL"
echo "   3. Configure your domain name (optional)"
echo ""
echo "🔍 Monitoring:"
echo "   - Lambda logs: aws logs tail /aws/lambda/${PROJECT_NAME}-${ENVIRONMENT}-backend --follow"
echo "   - CloudFront metrics: AWS Console > CloudFront"
echo ""
echo "💰 Cost Estimate:"
echo "   - Lambda: ~$0.20-2.00/month (based on usage)"
echo "   - CloudFront: ~$1.00/month + data transfer"
echo "   - S3: ~$0.50/month"
echo "   - Total: ~$2-4/month (vs ~$176/month for Fargate)"
echo ""

# Step 7: Optional - test the deployment
echo_warning "Would you like to test the Lambda function? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo_info "Testing Lambda function..."
    
    if [[ "$LAMBDA_FUNCTION_URL" != "Not available" ]]; then
        echo_info "Testing health endpoint..."
        curl -s "${LAMBDA_FUNCTION_URL}api/health" | jq . || echo "Health check response (raw): $(curl -s "${LAMBDA_FUNCTION_URL}api/health")"
    else
        echo_warning "Lambda Function URL not available yet. Please wait a few minutes and test manually."
    fi
fi

echo ""
echo_success "Serverless deployment script completed successfully!"
echo_info "Your Flask application is now running serverless on AWS Lambda!"