#!/bin/bash
# Portuguese Parliament Development Environment Starter
# Sets up local development stack with hot reload

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

show_usage() {
    cat << EOF
Portuguese Parliament Development Environment

USAGE:
    $0 <command>

COMMANDS:
    start      Start the development environment
    stop       Stop the development environment
    restart    Restart the development environment
    logs       Show logs from all services
    db         Open database management interface
    migrate    Migrate SQLite data to local MySQL
    status     Show status of all services
    clean      Clean up development environment

SERVICES:
    - Backend (Flask):     http://localhost:5000
    - Frontend (React):    http://localhost:3000  
    - Database UI:         http://localhost:8080
    - MySQL:               localhost:3306
    - Redis:               localhost:6379

EOF
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

start_services() {
    echo_info "Starting Portuguese Parliament development environment..."
    
    # Build and start services
    docker-compose up -d --build
    
    echo_success "Development environment started!"
    echo ""
    echo "📍 Services available at:"
    echo "   Backend API:    http://localhost:5000"
    echo "   Frontend:       http://localhost:3000"
    echo "   Database UI:    http://localhost:8080"
    echo ""
    echo "🔗 Database connection:"
    echo "   Host: localhost"
    echo "   Port: 3306"
    echo "   Database: parliament"
    echo "   Username: parliament_user"
    echo "   Password: parliament_pass"
    echo ""
    echo "📊 Monitor with:"
    echo "   $0 logs     # View all logs"
    echo "   $0 status   # Check service status"
}

stop_services() {
    echo_info "Stopping development environment..."
    docker-compose down
    echo_success "Development environment stopped"
}

restart_services() {
    echo_info "Restarting development environment..."
    docker-compose restart
    echo_success "Development environment restarted"
}

show_logs() {
    echo_info "Showing logs from all services (Ctrl+C to exit)..."
    docker-compose logs -f
}

open_database() {
    echo_info "Opening database management interface..."
    echo "Database UI available at: http://localhost:8080"
    echo ""
    echo "Connection details:"
    echo "  System: MySQL"
    echo "  Server: mysql"
    echo "  Username: parliament_user"
    echo "  Password: parliament_pass"
    echo "  Database: parliament"
    
    # Try to open browser if available
    if command -v open &> /dev/null; then
        open http://localhost:8080
    elif command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8080
    fi
}

migrate_sqlite() {
    echo_info "Migrating SQLite data to local MySQL..."
    
    if [[ ! -f "parlamento.db" ]]; then
        echo_error "SQLite database (parlamento.db) not found"
        exit 1
    fi
    
    # Ensure MySQL is running
    docker-compose up -d mysql
    
    # Wait for MySQL to be ready
    echo_info "Waiting for MySQL to be ready..."
    sleep 10
    
    # Run migration script inside backend container
    docker-compose run --rm backend python scripts/migrate-to-mysql.py --source /app/parlamento.db --target mysql://parliament_user:parliament_pass@mysql:3306/parliament
    
    echo_success "Migration completed!"
}

show_status() {
    echo_info "Development environment status:"
    echo ""
    docker-compose ps
}

clean_environment() {
    echo_warning "This will remove all containers, networks, and volumes!"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo_info "Cleaning up development environment..."
        docker-compose down -v --remove-orphans
        docker-compose rm -f
        echo_success "Development environment cleaned"
    else
        echo_info "Cleanup cancelled"
    fi
}

main() {
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi
    
    check_docker
    
    case "$1" in
        "start")
            start_services
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services
            ;;
        "logs")
            show_logs
            ;;
        "db")
            open_database
            ;;
        "migrate")
            migrate_sqlite
            ;;
        "status")
            show_status
            ;;
        "clean")
            clean_environment
            ;;
        *)
            echo_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"