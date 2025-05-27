#!/bin/bash

# Voice Freight Broker - Docker Management Scripts
# Usage: ./docker-scripts.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Check if .env file exists
check_env() {
    if [ ! -f .env ]; then
        print_warning ".env file not found. Creating from template..."
        if [ -f env.example ]; then
            cp env.example .env
            print_warning "Please edit .env file with your actual API keys before running the application."
        else
            print_error "env.example file not found. Please create .env manually."
            exit 1
        fi
    fi
}

# Build and start services
start() {
    print_status "Starting Voice Freight Broker application..."
    check_docker
    check_env
    docker-compose up --build -d
    print_success "Application started successfully!"
    print_status "Frontend: http://localhost:3000"
    print_status "Backend API: http://localhost:8000"
    print_status "API Docs: http://localhost:8000/docs"
}

# Stop services
stop() {
    print_status "Stopping application..."
    docker-compose down
    print_success "Application stopped successfully!"
}

# Restart services
restart() {
    print_status "Restarting application..."
    stop
    start
}

# View logs
logs() {
    if [ -z "$2" ]; then
        print_status "Showing logs for all services..."
        docker-compose logs -f
    else
        print_status "Showing logs for $2..."
        docker-compose logs -f "$2"
    fi
}

# Build only
build() {
    print_status "Building Docker images..."
    check_docker
    docker-compose build
    print_success "Images built successfully!"
}

# Clean up
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker-compose down -v
    docker image prune -f
    docker volume prune -f
    print_success "Cleanup completed!"
}

# Status check
status() {
    print_status "Checking application status..."
    docker-compose ps
    echo
    print_status "Docker resource usage:"
    docker stats --no-stream
}

# Database backup
backup_db() {
    print_status "Backing up database..."
    BACKUP_FILE="./backups/transit_$(date +%Y%m%d_%H%M%S).db"
    mkdir -p ./backups
    docker cp voice-freight-backend:/app/data/transit.db "$BACKUP_FILE"
    print_success "Database backed up to $BACKUP_FILE"
}

# Show help
show_help() {
    echo "Voice Freight Broker - Docker Management Script"
    echo
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  start         Build and start all services"
    echo "  stop          Stop all services"
    echo "  restart       Restart all services"
    echo "  logs [service] View logs (optional: specify service name)"
    echo "  build         Build Docker images"
    echo "  status        Show application and Docker status"
    echo "  cleanup       Clean up Docker resources"
    echo "  backup        Backup database"
    echo "  help          Show this help message"
    echo
    echo "Examples:"
    echo "  $0 start                    # Start the application"
    echo "  $0 logs backend            # View backend logs"
    echo "  $0 logs                    # View all logs"
}

# Main script logic
case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs "$@"
        ;;
    build)
        build
        ;;
    status)
        status
        ;;
    cleanup)
        cleanup
        ;;
    backup)
        backup_db
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac 