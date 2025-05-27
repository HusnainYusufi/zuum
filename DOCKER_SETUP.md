# Voice Freight Broker - Docker Setup Guide

This guide will help you set up and run the Voice Freight Broker application using Docker containers.

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your system:

- [Docker](https://docs.docker.com/get-docker/) (version 20.10 or later)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0 or later)
- Git (for cloning the repository)

## 🏗️ Architecture Overview

The application consists of two main services:
- **Backend**: Python FastAPI application with AI/ML capabilities
- **Frontend**: React TypeScript application served via Nginx

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <your-repository-url>
cd voice_freight_broker
```

### 2. Set Up Environment Variables
```bash
# Copy the environment template
cp env.example .env

# Edit the .env file with your actual API keys
nano .env  # or use your preferred editor
```

**Required Environment Variables:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `NGROK_AUTH_TOKEN`: Your Ngrok authentication token (optional)
- `RETELL_API_KEY`: Your Retell API key for voice services

### 3. Build and Run with Docker Compose
```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode (background)
docker-compose up --build -d
```

### 4. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 Development Setup

### Running Individual Services

#### Backend Only
```bash
# Build backend image
docker build -t voice-freight-backend ./backend

# Run backend container
docker run -p 8000:8000 --env-file .env voice-freight-backend
```

#### Frontend Only
```bash
# Build frontend image
docker build -t voice-freight-frontend ./transit-chat-frontend

# Run frontend container
docker run -p 3000:80 voice-freight-frontend
```

### Hot Reloading for Development

For development with hot reloading, you can mount your source code as volumes:

```yaml
# Add this to docker-compose.override.yml
version: '3.8'
services:
  backend:
    volumes:
      - ./backend:/app
      - ./backend/transit.db:/app/data/transit.db
    environment:
      - ENVIRONMENT=development
  
  frontend:
    volumes:
      - ./transit-chat-frontend/src:/app/src
```

Then run:
```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml up
```

## 🐛 Troubleshooting

### Common Issues and Solutions

#### 1. Port Already in Use
```bash
# Check what's using the port
netstat -tulpn | grep :8000

# Kill the process or use different ports in docker-compose.yml
```

#### 2. Permission Denied for Database
```bash
# Fix database permissions
chmod 664 backend/transit.db
```

#### 3. Environment Variables Not Loading
```bash
# Ensure .env file is in the root directory
ls -la .env

# Check if variables are being passed to containers
docker-compose config
```

#### 4. Frontend Can't Connect to Backend
- Check that both services are in the same Docker network
- Verify the API proxy configuration in `nginx.conf`
- Ensure backend is running and healthy

### Viewing Logs
```bash
# View logs for all services
docker-compose logs

# View logs for specific service
docker-compose logs backend
docker-compose logs frontend

# Follow logs in real-time
docker-compose logs -f
```

### Health Checks
```bash
# Check service health
docker-compose ps

# Manual health check
curl http://localhost:8000/docs
curl http://localhost:3000
```

## 🛠️ Advanced Configuration

### Custom Network Configuration
```yaml
# In docker-compose.yml
networks:
  voice-freight-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Scaling Services
```bash
# Scale backend instances
docker-compose up --scale backend=3

# Use load balancer (requires additional configuration)
```

### Production Deployment

#### Using Docker Swarm
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml voice-freight
```

#### Using Kubernetes
```bash
# Generate Kubernetes manifests
kompose convert

# Deploy to Kubernetes
kubectl apply -f .
```

## 📊 Monitoring and Maintenance

### Container Stats
```bash
# View resource usage
docker stats

# View container information
docker-compose ps
docker inspect voice-freight-backend
```

### Backup Database
```bash
# Create backup
docker cp voice-freight-backend:/app/data/transit.db ./backups/transit_$(date +%Y%m%d_%H%M%S).db

# Restore backup
docker cp ./backups/transit_20231201_120000.db voice-freight-backend:/app/data/transit.db
```

### Updating the Application
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose down
docker-compose up --build
```

### Cleanup
```bash
# Stop and remove containers
docker-compose down

# Remove containers, networks, and volumes
docker-compose down -v

# Remove unused images
docker image prune

# Full cleanup (removes all unused Docker objects)
docker system prune -a
```

## 🔒 Security Considerations

1. **Environment Variables**: Never commit `.env` files to version control
2. **API Keys**: Use Docker secrets or external secret management in production
3. **Network Security**: Configure proper firewall rules
4. **Image Security**: Regularly update base images and scan for vulnerabilities

```bash
# Scan images for vulnerabilities
docker scan voice-freight-backend
docker scan voice-freight-frontend
```

## 📈 Performance Optimization

### Production Optimizations
1. Use multi-stage builds to reduce image size
2. Implement proper caching strategies
3. Use health checks for better orchestration
4. Configure resource limits

```yaml
# Example resource limits
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## 🆘 Getting Help

If you encounter issues:

1. Check the logs: `docker-compose logs`
2. Verify environment variables: `docker-compose config`
3. Check service health: `docker-compose ps`
4. Review this guide and Docker documentation
5. Open an issue in the project repository

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://reactjs.org/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/) 