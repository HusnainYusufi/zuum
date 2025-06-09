#!/bin/bash

# Voice Freight Broker - Docker Management Scripts
# Usage: ./docker-scripts.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

print_header() {
    echo -e "${CYAN}=== $1 ===${NC}"
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
            print_warning "Required keys: OPENAI_API_KEY, NGROK_AUTH_TOKEN, RETELL_API_KEY, WORKFLOW_RETELL_AGENT_ID, CHECKIN_RETELL_AGENT_ID"
        else
            print_error "env.example file not found. Please create .env manually."
            exit 1
        fi
    fi
}

# Build and start services
start() {
    print_header "Starting Voice Freight Broker Backend"
    check_docker
    check_env
    
    print_status "Building and starting containers..."
    if docker-compose up --build -d; then
        print_success "Backend started successfully!"
        echo
        print_status "Service URLs:"
        echo "  • API: http://localhost:8000"
        echo "  • API Docs: http://localhost:8000/docs"
        echo "  • Ngrok Dashboard: http://localhost:4040"
        echo
        sleep 3
        print_status "Checking service health..."
        docker-compose ps
    else
        print_error "Failed to start backend!"
        print_status "Run './docker-scripts.sh logs' to see error details."
        exit 1
    fi
}

# Stop services
stop() {
    print_header "Stopping Backend"
    if docker-compose down; then
        print_success "Backend stopped successfully!"
    else
        print_error "Failed to stop backend!"
        exit 1
    fi
}

# Restart services
restart() {
    print_header "Restarting Backend"
    stop
    sleep 2
    start
}

# View logs
logs() {
    local service="${2:-backend}"
    print_status "Showing logs for $service..."
    print_status "Press Ctrl+C to exit"
    echo
    docker-compose logs -f "$service"
}

# Build only
build() {
    print_header "Building Docker Images"
    check_docker
    if docker-compose build --no-cache; then
        print_success "Images built successfully!"
    else
        print_error "Failed to build images!"
        exit 1
    fi
}

# Clean up
cleanup() {
    print_header "Docker Cleanup"
    print_warning "This will remove all containers, volumes, and images for this project."
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleanup cancelled."
        return
    fi
    
    print_status "Cleaning up Docker resources..."
    docker-compose down -v --rmi all
    docker image prune -f
    docker volume prune -f
    print_success "Cleanup completed!"
}

# Status check
status() {
    print_header "Application Status"
    
    print_status "Container status:"
    docker-compose ps
    echo
    
    print_status "Container health:"
    docker ps --filter "name=voice-freight" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo
    
    print_status "Docker resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
}

# Database backup
backup_db() {
    print_header "Database Backup"
    print_status "Backing up database..."
    
    BACKUP_DIR="./backups"
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/transit_${TIMESTAMP}.db"
    
    if docker cp voice-freight-backend:/app/data/transit.db "$BACKUP_FILE"; then
        print_success "Database backed up to $BACKUP_FILE"
        
        # Show backup size
        if [ -f "$BACKUP_FILE" ]; then
            SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
            print_status "Backup size: $SIZE"
        fi
        
        # List recent backups
        echo
        print_status "Recent backups:"
        ls -lht "$BACKUP_DIR" | head -6
    else
        print_error "Failed to backup database!"
        exit 1
    fi
}

# Open shell in container
shell() {
    print_status "Opening shell in backend container..."
    docker exec -it voice-freight-backend /bin/bash
}

# Run tests
test() {
    print_header "Running Tests"
    print_status "Executing test suite in container..."
    docker exec voice-freight-backend python -m pytest tests/ -v
}

# Show environment info
env_info() {
    print_header "Environment Information"
    
    print_status "Docker version:"
    docker --version
    
    print_status "Docker Compose version:"
    docker-compose --version
    
    echo
    print_status "Environment variables (from .env):"
    if [ -f .env ]; then
        grep -E "^[A-Z_]+=" .env | sed 's/=.*/=<hidden>/'
    else
        print_warning ".env file not found"
    fi
}

# Show help
show_help() {
    echo "Voice Freight Broker - Docker Management Script"
    echo
    echo "Usage: $0 [command] [options]"
    echo
    echo "Commands:"
    echo "  start         Build and start the backend service"
    echo "  stop          Stop the backend service"
    echo "  restart       Restart the backend service"
    echo "  logs [service] View logs (default: backend)"
    echo "  build         Build Docker images with no cache"
    echo "  status        Show application and container status"
    echo "  cleanup       Clean up all Docker resources (WARNING: removes data)"
    echo "  backup        Backup database to ./backups/"
    echo "  shell         Open bash shell in backend container"
    echo "  test          Run test suite"
    echo "  env           Show environment information"
    echo "  help          Show this help message"
    echo
    echo "Examples:"
    echo "  $0 start                    # Start the backend"
    echo "  $0 logs                     # View backend logs"
    echo "  $0 logs backend             # View backend logs (explicit)"
    echo "  $0 backup                   # Backup the database"
    echo "  $0 shell                    # Open container shell"
    echo
    echo "Environment:"
    echo "  Make sure .env file exists with required API keys"
    echo "  See env.example for required variables"
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
    cleanup|clean)
        cleanup
        ;;
    backup)
        backup_db
        ;;
    shell|bash)
        shell
        ;;
    test)
        test
        ;;
    env|env_info|info)
        env_info
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo
        show_help
        exit 1
        ;;
esac 