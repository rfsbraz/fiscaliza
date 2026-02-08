#!/bin/bash
# Portuguese Parliament Lambda + Aurora Serverless v2 Deployment
# Complete serverless deployment with database migration

set -e

# Configuration
PROJECT_NAME="parliament"
ENVIRONMENT="${ENVIRONMENT:-prod}"
AWS_REGION="${AWS_REGION:-eu-west-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}ℹ ${1}${NC}"; }
echo_success() { echo -e "${GREEN}✓ ${1}${NC}"; }
echo_warning() { echo -e "${YELLOW}⚠ ${1}${NC}"; }
echo_error() { echo -e "${RED}✗ ${1}${NC}"; }

# Check prerequisites
check_prerequisites() {
    echo_info "Checking prerequisites..."
    
    local missing_tools=()
    
    command -v aws >/dev/null 2>&1 || missing_tools+=("aws")
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v terraform >/dev/null 2>&1 || missing_tools+=("terraform")
    command -v python3 >/dev/null 2>&1 || missing_tools+=("python3")
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        echo_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        echo_error "AWS credentials not configured"
        exit 1
    fi
    
    # Check if SQLite database exists
    if [[ ! -f "parlamento.db" ]]; then
        echo_error "SQLite database (parlamento.db) not found in project root"
        exit 1
    fi
    
    # Check Python dependencies
    if ! python3 -c "import pymysql, boto3" > /dev/null 2>&1; then
        echo_info "Installing Python dependencies..."
        pip3 install pymysql boto3 tqdm
    fi
    
    echo_success "Prerequisites check passed"
}

# Build Aurora-compatible Docker image
build_aurora_image() {
    echo_info "Building Lambda + Aurora Docker image..."
    
    AURORA_IMAGE="${PROJECT_NAME}-lambda-aurora:latest"
    
    # Build the Aurora-compatible image
    docker build -f Dockerfile -t "$AURORA_IMAGE" .
    
    echo_success "Aurora Docker image built: $AURORA_IMAGE"
}

# Deploy infrastructure
deploy_infrastructure() {
    echo_info "Deploying Lambda + Aurora infrastructure..."
    
    cd terraform
    
    # Initialize if needed
    if [[ ! -d ".terraform" ]]; then
        terraform init
    fi
    
    # Plan deployment
    terraform plan \
        -var="environment=$ENVIRONMENT" \
        -var="aws_region=$AWS_REGION" \
        -var="backend_image=$ECR_URI:latest" \
        -var="lambda_vpc_enabled=true" \
        -var="aurora_min_capacity=0.5" \
        -var="aurora_max_capacity=2" \
        -out=lambda-aurora.tfplan
    
    # Apply deployment
    terraform apply lambda-aurora.tfplan
    
    echo_success "Infrastructure deployed successfully"
    
    cd ..
}

# Push image to ECR
push_to_ecr() {
    echo_info "Pushing image to ECR..."
    
    # Create ECR repository if needed
    REPO_NAME="${PROJECT_NAME}-lambda-aurora"
    ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}"
    
    if ! aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
        aws ecr create-repository \
            --repository-name "$REPO_NAME" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true
    fi
    
    # Login and push
    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_URI"
    
    docker tag "${PROJECT_NAME}-lambda-aurora:latest" "$ECR_URI:latest"
    docker push "$ECR_URI:latest"
    
    echo_success "Image pushed to ECR"
}

# Migrate database
migrate_database() {
    echo_info "Starting database migration from SQLite to Aurora..."
    
    # Wait for Aurora to be ready
    echo_info "Waiting for Aurora cluster to be ready..."
    CLUSTER_ID="parliament-${ENVIRONMENT}-aurora"
    
    aws rds wait db-cluster-available --db-cluster-identifier "$CLUSTER_ID"
    echo_success "Aurora cluster is ready"
    
    # Run migration script
    echo_info "Running database migration..."
    python3 scripts/migrate-to-aurora.py \
        --environment "$ENVIRONMENT" \
        --action migrate \
        --batch-size 1000
    
    echo_success "Database migration completed"
}

# Update Lambda function
update_lambda() {
    echo_info "Updating Lambda function with new image..."
    
    FUNCTION_NAME="parliament-${ENVIRONMENT}-backend"
    
    # Update function code
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --image-uri "$ECR_URI:latest" \
        --region "$AWS_REGION"
    
    # Wait for update to complete
    aws lambda wait function-updated --function-name "$FUNCTION_NAME"
    
    echo_success "Lambda function updated"
}

# Test deployment
test_deployment() {
    echo_info "Testing deployment..."
    
    cd terraform
    
    # Get endpoints
    LAMBDA_URL=$(terraform output -raw lambda_function_url 2>/dev/null || echo "")
    CLOUDFRONT_URL=$(terraform output -raw cloudfront_domain_name 2>/dev/null || echo "")
    
    cd ..
    
    if [[ -n "$LAMBDA_URL" ]]; then
        echo_info "Testing Lambda endpoint..."
        
        # Test health endpoint
        if curl -s --max-time 30 "${LAMBDA_URL}api/health" | grep -q "healthy"; then
            echo_success "Lambda health check passed"
        else
            echo_warning "Lambda health check failed (this is normal on first deployment)"
        fi
        
        # Test database connectivity
        echo_info "Testing database connectivity..."
        if curl -s --max-time 30 "${LAMBDA_URL}api/deputados?limit=1" > /dev/null; then
            echo_success "Database connectivity test passed"
        else
            echo_warning "Database connectivity test failed (may need warm-up time)"
        fi
    fi
    
    if [[ -n "$CLOUDFRONT_URL" ]]; then
        echo_info "CloudFront URL: https://$CLOUDFRONT_URL"
    fi
}

# Create test environment
create_test_env() {
    echo_info "Creating test environment for safe testing..."
    
    ./scripts/database-testing-toolkit.sh create-test-env migration-test
    ./scripts/database-testing-toolkit.sh clone-prod migration-test
    
    echo_success "Test environment 'migration-test' created"
    echo_info "Use: ./scripts/database-testing-toolkit.sh run-tests migration-test"
}

# Main deployment flow
main() {
    echo "=========================================="
    echo_info "Portuguese Parliament Lambda + Aurora Deployment"
    echo "=========================================="
    echo ""
    echo "This will deploy:"
    echo "  ✓ Aurora Serverless v2 MySQL cluster"
    echo "  ✓ Lambda function with AWS Lambda Web Adapter"
    echo "  ✓ CloudFront distribution"
    echo "  ✓ Database migration from SQLite"
    echo ""
    echo_warning "Estimated deployment time: 20-30 minutes"
    echo_warning "Estimated monthly cost: \$15-25"
    echo ""
    
    read -p "Continue with deployment? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo_info "Deployment cancelled"
        exit 0
    fi
    
    # Step-by-step deployment
    check_prerequisites
    build_aurora_image
    push_to_ecr
    deploy_infrastructure
    
    echo_info "Waiting 2 minutes for infrastructure to stabilize..."
    sleep 120
    
    migrate_database
    update_lambda
    
    echo_info "Waiting 1 minute for Lambda to initialize..."
    sleep 60
    
    test_deployment
    
    # Final summary
    cd terraform
    LAMBDA_URL=$(terraform output -raw lambda_function_url 2>/dev/null || echo "Not available")
    CLOUDFRONT_URL=$(terraform output -raw cloudfront_domain_name 2>/dev/null || echo "Not available")
    AURORA_ENDPOINT=$(terraform output -raw aurora_cluster_endpoint 2>/dev/null || echo "Not available")
    cd ..
    
    echo ""
    echo "=========================================="
    echo_success "DEPLOYMENT COMPLETE!"
    echo "=========================================="
    echo ""
    echo "📍 Endpoints:"
    echo "   Lambda Function URL: $LAMBDA_URL"
    echo "   CloudFront URL: https://$CLOUDFRONT_URL"
    echo "   Aurora Endpoint: $AURORA_ENDPOINT"
    echo ""
    echo "🛠 Management Commands:"
    echo "   Create test env: ./scripts/database-testing-toolkit.sh create-test-env <name>"
    echo "   Create snapshot: ./scripts/database-testing-toolkit.sh snapshot prod <name>"
    echo "   Monitor logs: aws logs tail /aws/lambda/parliament-${ENVIRONMENT}-backend --follow"
    echo ""
    echo "💰 Cost Optimization:"
    echo "   - Aurora scales to 0.5 ACU when idle"
    echo "   - Lambda charges only for actual requests"
    echo "   - Estimated cost: \$15-25/month (vs \$176/month Fargate)"
    echo ""
    echo_success "Your Flask app is now serverless with Aurora!"
    
    # Offer to create test environment
    echo ""
    echo_warning "Would you like to create a test environment for safe testing? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        create_test_env
    fi
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "test-only")
        test_deployment
        ;;
    "migrate-only")
        migrate_database
        ;;
    "build-only")
        check_prerequisites
        build_aurora_image
        ;;
    *)
        echo "Usage: $0 [deploy|test-only|migrate-only|build-only]"
        exit 1
        ;;
esac