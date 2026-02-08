#!/bin/bash

# Portuguese Parliament AWS Deployment Script
set -e

# Configuration
AWS_REGION="eu-west-1"
PROJECT_NAME="parliament"
ENVIRONMENT="prod"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏛️  Portuguese Parliament Deployment Script${NC}"
echo "============================================="

# Function to print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed"
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed"
        exit 1
    fi
    
    log_success "All prerequisites are installed"
}

# Get AWS account ID
get_aws_account_id() {
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_info "AWS Account ID: $AWS_ACCOUNT_ID"
}

# Deploy infrastructure
deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."
    
    cd terraform
    
    # Initialize Terraform
    terraform init
    
    # Plan the deployment
    terraform plan -var="aws_region=$AWS_REGION" -var="environment=$ENVIRONMENT"
    
    # Apply the configuration
    log_warning "This will create AWS resources. Continue? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        terraform apply -var="aws_region=$AWS_REGION" -var="environment=$ENVIRONMENT" -auto-approve
        log_success "Infrastructure deployed successfully"
    else
        log_info "Infrastructure deployment cancelled"
        exit 0
    fi
    
    # Get outputs
    ECR_REPOSITORY=$(terraform output -raw ecr_repository_url)
    S3_BUCKET=$(terraform output -raw s3_bucket_name)
    CLOUDFRONT_DISTRIBUTION_ID=$(terraform output -raw cloudfront_distribution_id)
    ECS_CLUSTER=$(terraform output -raw ecs_cluster_name)
    ECS_SERVICE=$(terraform output -raw ecs_service_name)
    
    # Export for use in other functions
    export ECR_REPOSITORY S3_BUCKET CLOUDFRONT_DISTRIBUTION_ID ECS_CLUSTER ECS_SERVICE
    
    cd ..
}

# Build and push Docker image
deploy_backend() {
    log_info "Building and deploying backend..."
    
    # Login to ECR
    log_info "Logging into Amazon ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY
    
    # Build Docker image
    log_info "Building Docker image..."
    docker build -t $PROJECT_NAME-backend .
    
    # Tag image
    docker tag $PROJECT_NAME-backend:latest $ECR_REPOSITORY:latest
    docker tag $PROJECT_NAME-backend:latest $ECR_REPOSITORY:$(date +%Y%m%d-%H%M%S)
    
    # Push image
    log_info "Pushing image to ECR..."
    docker push $ECR_REPOSITORY:latest
    docker push $ECR_REPOSITORY:$(date +%Y%m%d-%H%M%S)
    
    # Update ECS service
    log_info "Updating ECS service..."
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $ECS_SERVICE \
        --force-new-deployment \
        --region $AWS_REGION
    
    log_success "Backend deployed successfully"
}

# Build and deploy frontend
deploy_frontend() {
    log_info "Building and deploying frontend..."
    
    cd frontend
    
    # Install dependencies
    log_info "Installing frontend dependencies..."
    npm ci
    
    # Build the React app
    log_info "Building React app..."
    npm run build
    
    # Upload to S3
    log_info "Uploading to S3..."
    aws s3 sync build/ s3://$S3_BUCKET --delete
    
    # Invalidate CloudFront cache
    log_info "Invalidating CloudFront cache..."
    aws cloudfront create-invalidation \
        --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
        --paths "/*"
    
    cd ..
    
    log_success "Frontend deployed successfully"
}

# Main deployment flow
main() {
    log_info "Starting deployment process..."
    
    check_prerequisites
    get_aws_account_id
    
    # Deploy in order
    deploy_infrastructure
    deploy_backend
    deploy_frontend
    
    echo ""
    log_success "🎉 Deployment completed successfully!"
    echo ""
    echo "Infrastructure:"
    echo "  - S3 Bucket: $S3_BUCKET"
    echo "  - CloudFront Distribution: $CLOUDFRONT_DISTRIBUTION_ID"
    echo "  - ECS Cluster: $ECS_CLUSTER"
    echo "  - ECS Service: $ECS_SERVICE"
    echo ""
    echo "Next steps:"
    echo "  1. Check ECS service health in AWS Console"
    echo "  2. Test the application at the CloudFront URL"
    echo "  3. Monitor logs in CloudWatch"
}

# Run main function
main "$@"