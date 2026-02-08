#!/bin/bash
# Multi-Environment Terraform Deployment Script
# Supports dev/prod environments with serverless/fargate deployment types

set -e

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

# Function to show usage
show_usage() {
    cat << EOF
Multi-Environment Terraform Deployment

USAGE:
    $0 <environment> <action>

PARAMETERS:
    environment - dev or prod
    action      - plan, apply, or destroy

EXAMPLES:
    # Deploy to dev environment
    $0 dev apply
    
    # Plan production deployment
    $0 prod plan
    
    # Destroy dev environment
    $0 dev destroy

ENVIRONMENT FILES:
    - terraform/environments/dev.tfvars
    - terraform/environments/prod.tfvars

WORKSPACES:
    - dev, prod

EOF
}

# Validate inputs
if [[ $# -ne 2 ]]; then
    show_usage
    exit 1
fi

ENVIRONMENT="$1"
ACTION="$2"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|prod)$ ]]; then
    echo_error "Environment must be 'dev' or 'prod'"
    exit 1
fi

# Validate action
if [[ ! "$ACTION" =~ ^(plan|apply|destroy)$ ]]; then
    echo_error "Action must be 'plan', 'apply', or 'destroy'"
    exit 1
fi

# Set workspace and var file
WORKSPACE="${ENVIRONMENT}"
VAR_FILE="environments/${ENVIRONMENT}.tfvars"

echo_info "Deploying Lambda + Aurora to ${ENVIRONMENT} environment"
echo_info "Workspace: ${WORKSPACE}"
echo_info "Variables: ${VAR_FILE}"

# Check if var file exists
if [[ ! -f "$VAR_FILE" ]]; then
    echo_error "Variable file not found: $VAR_FILE"
    exit 1
fi

# Initialize Terraform if needed
if [[ ! -d ".terraform" ]]; then
    echo_info "Initializing Terraform..."
    terraform init
fi

# Create or select workspace
echo_info "Setting up workspace: $WORKSPACE"
terraform workspace new "$WORKSPACE" 2>/dev/null || terraform workspace select "$WORKSPACE"

# Handle different actions
case "$ACTION" in
    "plan")
        echo_info "Planning deployment..."
        terraform plan \
            -var-file="$VAR_FILE" \
            -out="${WORKSPACE}.tfplan"
        
        echo_success "Plan completed. Review the changes above."
        echo_info "To apply: $0 $ENVIRONMENT apply"
        ;;
        
    "apply")
        # Check if plan exists
        if [[ -f "${WORKSPACE}.tfplan" ]]; then
            echo_info "Applying existing plan..."
            terraform apply "${WORKSPACE}.tfplan"
            rm -f "${WORKSPACE}.tfplan"
        else
            echo_info "No existing plan found. Creating and applying..."
            terraform apply \
                -var-file="$VAR_FILE" \
                -auto-approve
        fi
        
        echo_success "Deployment completed!"
        
        # Show outputs
        echo_info "Deployment information:"
        terraform output deployment_instructions
        
        echo_info "Estimated monthly cost:"
        terraform output estimated_monthly_cost_usd
        ;;
        
    "destroy")
        echo_warning "This will DESTROY all resources in $ENVIRONMENT!"
        echo_warning "This action cannot be undone."
        
        read -p "Type 'DESTROY' to confirm: " -r
        if [[ "$REPLY" != "DESTROY" ]]; then
            echo_info "Destroy cancelled"
            exit 0
        fi
        
        terraform destroy \
            -var-file="$VAR_FILE" \
            -auto-approve
        
        echo_success "Environment destroyed"
        ;;
esac