#!/bin/bash
# Portuguese Parliament Database Testing Toolkit
# Provides safe testing environments for destructive database changes

set -e

# Configuration
PROJECT_NAME="parliament"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
Portuguese Parliament Database Testing Toolkit

USAGE:
    $0 <command> [options]

COMMANDS:
    create-test-env <env_name>     Create isolated test environment
    clone-prod <env_name>          Clone production database to test environment
    snapshot <env_name> <name>     Create named snapshot of environment
    restore <env_name> <snapshot>  Restore environment from snapshot
    list-snapshots <env_name>      List available snapshots
    cleanup <env_name>             Delete test environment and snapshots
    run-tests <env_name>           Run database tests against environment
    compare <env1> <env2>          Compare two database environments

ENVIRONMENTS:
    prod    - Production database (read-only operations)
    test    - Primary test environment  
    dev     - Development environment
    staging - Staging environment

EXAMPLES:
    # Create a test environment and clone production data
    $0 create-test-env test-migration
    $0 clone-prod test-migration
    
    # Create snapshot before risky operation
    $0 snapshot test-migration before-schema-changes
    
    # Run your destructive tests...
    # If something goes wrong, restore:
    $0 restore test-migration before-schema-changes
    
    # Clean up when done
    $0 cleanup test-migration

COST OPTIMIZATION:
    - Test environments use Aurora Serverless v2 (scales to 0.5 ACU when idle)
    - Snapshots only store changed data (copy-on-write)
    - Automatic cleanup after 7 days (configurable)

EOF
}

# Get AWS account and region
get_aws_info() {
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
    AWS_REGION=$(aws configure get region 2>/dev/null || echo "eu-west-1")
    
    if [[ -z "$AWS_ACCOUNT_ID" ]]; then
        echo_error "AWS credentials not configured. Run 'aws configure'"
        exit 1
    fi
}

# Create test environment
create_test_env() {
    local env_name="$1"
    if [[ -z "$env_name" ]]; then
        echo_error "Environment name required"
        exit 1
    fi
    
    echo_info "Creating test environment: $env_name"
    
    # Deploy test infrastructure with Terraform
    cd "$PROJECT_ROOT/terraform"
    
    terraform workspace new "test-$env_name" 2>/dev/null || terraform workspace select "test-$env_name"
    
    terraform plan \
        -var="deployment_type=serverless" \
        -var="environment=test-$env_name" \
        -var="aws_region=$AWS_REGION" \
        -var="aurora_min_capacity=0.5" \
        -var="aurora_max_capacity=1" \
        -out="test-$env_name.tfplan"
    
    terraform apply "test-$env_name.tfplan"
    
    echo_success "Test environment '$env_name' created"
    
    # Get connection details
    CLUSTER_ENDPOINT=$(terraform output -raw aurora_cluster_endpoint 2>/dev/null || echo "")
    if [[ -n "$CLUSTER_ENDPOINT" ]]; then
        echo_info "Aurora cluster endpoint: $CLUSTER_ENDPOINT"
    fi
}

# Clone production database
clone_prod_database() {
    local env_name="$1"
    if [[ -z "$env_name" ]]; then
        echo_error "Environment name required"
        exit 1
    fi
    
    echo_info "Cloning production database to: $env_name"
    
    # Create clone using Aurora fast cloning
    PROD_CLUSTER_ID="$PROJECT_NAME-prod-aurora"
    TEST_CLUSTER_ID="$PROJECT_NAME-test-$env_name-aurora"
    
    echo_info "Creating Aurora clone (this may take 10-15 minutes)..."
    
    aws rds create-db-cluster \
        --db-cluster-identifier "$TEST_CLUSTER_ID" \
        --engine aurora-mysql \
        --source-db-cluster-identifier "$PROD_CLUSTER_ID" \
        --tags Key=Environment,Value="test-$env_name" \
              Key=Purpose,Value="Testing" \
              Key=AutoCleanup,Value="7days" \
              Key=CreatedBy,Value="$(whoami)" \
              Key=CreatedAt,Value="$(date -Iseconds)"
    
    # Wait for clone to be available
    echo_info "Waiting for clone to be ready..."
    aws rds wait db-cluster-available --db-cluster-identifier "$TEST_CLUSTER_ID"
    
    echo_success "Production database cloned to $env_name"
}

# Create snapshot
create_snapshot() {
    local env_name="$1"
    local snapshot_name="$2"
    
    if [[ -z "$env_name" ]] || [[ -z "$snapshot_name" ]]; then
        echo_error "Environment name and snapshot name required"
        exit 1
    fi
    
    CLUSTER_ID="$PROJECT_NAME-test-$env_name-aurora"
    SNAPSHOT_ID="$CLUSTER_ID-$snapshot_name-$(date +%Y%m%d-%H%M%S)"
    
    echo_info "Creating snapshot: $snapshot_name"
    
    aws rds create-db-cluster-snapshot \
        --db-cluster-identifier "$CLUSTER_ID" \
        --db-cluster-snapshot-identifier "$SNAPSHOT_ID" \
        --tags Key=Environment,Value="test-$env_name" \
              Key=SnapshotName,Value="$snapshot_name" \
              Key=CreatedBy,Value="$(whoami)" \
              Key=CreatedAt,Value="$(date -Iseconds)"
    
    # Wait for snapshot to complete
    echo_info "Waiting for snapshot to complete..."
    aws rds wait db-cluster-snapshot-completed --db-cluster-snapshot-identifier "$SNAPSHOT_ID"
    
    echo_success "Snapshot created: $SNAPSHOT_ID"
    echo_info "Use this ID to restore: $0 restore $env_name $SNAPSHOT_ID"
}

# Restore from snapshot
restore_from_snapshot() {
    local env_name="$1"
    local snapshot_id="$2"
    
    if [[ -z "$env_name" ]] || [[ -z "$snapshot_id" ]]; then
        echo_error "Environment name and snapshot ID required"
        exit 1
    fi
    
    CLUSTER_ID="$PROJECT_NAME-test-$env_name-aurora"
    TEMP_CLUSTER_ID="$CLUSTER_ID-restore-$(date +%Y%m%d-%H%M%S)"
    
    echo_warning "This will replace the current test database with the snapshot!"
    echo_warning "Current database will be backed up first."
    
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo_info "Restore cancelled"
        exit 0
    fi
    
    # Create backup of current state
    echo_info "Creating backup of current state..."
    BACKUP_SNAPSHOT="$CLUSTER_ID-backup-$(date +%Y%m%d-%H%M%S)"
    aws rds create-db-cluster-snapshot \
        --db-cluster-identifier "$CLUSTER_ID" \
        --db-cluster-snapshot-identifier "$BACKUP_SNAPSHOT"
    
    # Create new cluster from snapshot
    echo_info "Restoring from snapshot: $snapshot_id"
    aws rds restore-db-cluster-from-snapshot \
        --db-cluster-identifier "$TEMP_CLUSTER_ID" \
        --snapshot-identifier "$snapshot_id"
    
    # Wait for new cluster
    echo_info "Waiting for restored cluster..."
    aws rds wait db-cluster-available --db-cluster-identifier "$TEMP_CLUSTER_ID"
    
    # Delete old cluster
    echo_info "Replacing old cluster..."
    aws rds delete-db-cluster \
        --db-cluster-identifier "$CLUSTER_ID" \
        --skip-final-snapshot
    
    # Wait for deletion
    aws rds wait db-cluster-deleted --db-cluster-identifier "$CLUSTER_ID"
    
    # Rename new cluster
    aws rds modify-db-cluster \
        --db-cluster-identifier "$TEMP_CLUSTER_ID" \
        --new-db-cluster-identifier "$CLUSTER_ID" \
        --apply-immediately
    
    echo_success "Database restored from snapshot"
    echo_info "Backup of previous state: $BACKUP_SNAPSHOT"
}

# List snapshots
list_snapshots() {
    local env_name="$1"
    if [[ -z "$env_name" ]]; then
        echo_error "Environment name required"
        exit 1
    fi
    
    CLUSTER_ID="$PROJECT_NAME-test-$env_name-aurora"
    
    echo_info "Snapshots for environment: $env_name"
    echo "----------------------------------------"
    
    aws rds describe-db-cluster-snapshots \
        --db-cluster-identifier "$CLUSTER_ID" \
        --query 'DBClusterSnapshots[*].[DBClusterSnapshotIdentifier,SnapshotCreateTime,Status,AllocatedStorage]' \
        --output table
}

# Run database tests
run_tests() {
    local env_name="$1"
    if [[ -z "$env_name" ]]; then
        echo_error "Environment name required"
        exit 1
    fi
    
    echo_info "Running database tests for environment: $env_name"
    
    # Update environment variables for test
    export ENVIRONMENT="test-$env_name"
    
    # Run migration validation
    if [[ -f "$PROJECT_ROOT/scripts/migrate-to-aurora.py" ]]; then
        echo_info "Running migration validation..."
        python3 "$PROJECT_ROOT/scripts/migrate-to-aurora.py" \
            --environment "test-$env_name" \
            --action validate
    fi
    
    # Run application tests if they exist
    if [[ -f "$PROJECT_ROOT/tests/test_database.py" ]]; then
        echo_info "Running application tests..."
        cd "$PROJECT_ROOT"
        python3 -m pytest tests/test_database.py -v
    fi
    
    echo_success "Tests completed"
}

# Compare two environments
compare_environments() {
    local env1="$1"
    local env2="$2"
    
    if [[ -z "$env1" ]] || [[ -z "$env2" ]]; then
        echo_error "Two environment names required"
        exit 1
    fi
    
    echo_info "Comparing environments: $env1 vs $env2"
    
    # This would require a custom comparison script
    # For now, just show basic info
    
    echo "Environment 1: $env1"
    list_snapshots "$env1"
    
    echo -e "\nEnvironment 2: $env2"
    list_snapshots "$env2"
}

# Cleanup test environment
cleanup_environment() {
    local env_name="$1"
    if [[ -z "$env_name" ]]; then
        echo_error "Environment name required"
        exit 1
    fi
    
    echo_warning "This will DELETE the test environment '$env_name' and ALL its snapshots!"
    echo_warning "This action cannot be undone."
    
    read -p "Type 'DELETE' to confirm: " -r
    if [[ "$REPLY" != "DELETE" ]]; then
        echo_info "Cleanup cancelled"
        exit 0
    fi
    
    CLUSTER_ID="$PROJECT_NAME-test-$env_name-aurora"
    
    # Delete all snapshots
    echo_info "Deleting snapshots..."
    aws rds describe-db-cluster-snapshots \
        --db-cluster-identifier "$CLUSTER_ID" \
        --query 'DBClusterSnapshots[*].DBClusterSnapshotIdentifier' \
        --output text | tr '\t' '\n' | while read -r snapshot_id; do
        if [[ -n "$snapshot_id" ]]; then
            echo_info "Deleting snapshot: $snapshot_id"
            aws rds delete-db-cluster-snapshot \
                --db-cluster-snapshot-identifier "$snapshot_id" || true
        fi
    done
    
    # Delete cluster
    echo_info "Deleting cluster..."
    aws rds delete-db-cluster \
        --db-cluster-identifier "$CLUSTER_ID" \
        --skip-final-snapshot || true
    
    # Delete Terraform workspace
    cd "$PROJECT_ROOT/terraform"
    terraform workspace select default
    terraform workspace delete "test-$env_name" || true
    
    echo_success "Environment '$env_name' cleaned up"
}

# Main script logic
main() {
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    get_aws_info
    
    local command="$1"
    shift
    
    case "$command" in
        "create-test-env")
            create_test_env "$@"
            ;;
        "clone-prod")
            clone_prod_database "$@"
            ;;
        "snapshot")
            create_snapshot "$@"
            ;;
        "restore")
            restore_from_snapshot "$@"
            ;;
        "list-snapshots")
            list_snapshots "$@"
            ;;
        "run-tests")
            run_tests "$@"
            ;;
        "compare")
            compare_environments "$@"
            ;;
        "cleanup")
            cleanup_environment "$@"
            ;;
        *)
            echo_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"