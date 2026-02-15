#!/bin/bash

# Deployment script for Edify Chatbot Agent
# Usage: ./scripts/deploy.sh

set -e  # Exit on error

echo "🚀 Starting deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running!${NC}"
    exit 1
fi

# Update and get latest code
echo -e "${YELLOW}📥 Pulling latest code from repository...${NC}"
git pull || {
    echo -e "${YELLOW}⚠️  Warning: git pull failed or not in a git repository. Continuing with current code...${NC}"
}

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found!${NC}"
    echo "Please create a .env file with all required environment variables."
    exit 1
fi

# Stop existing containers
echo -e "${YELLOW}📦 Stopping and removing existing containers...${NC}"
docker-compose down 2>/dev/null || true

# Build new image
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
docker-compose build --no-cache

# Start containers
echo -e "${YELLOW}🚀 Starting containers...${NC}"
docker-compose up -d

# Wait for health check
echo -e "${YELLOW}⏳ Waiting for application to be healthy...${NC}"
sleep 10

# Check health
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Application is healthy!${NC}"
else
    echo -e "${RED}❌ Health check failed!${NC}"
    echo "Checking logs..."
    docker-compose logs --tail=50
    exit 1
fi

# Show status
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "Container status:"
docker-compose ps

echo ""
echo "Application logs (last 20 lines):"
docker-compose logs --tail=20

echo ""
echo -e "${GREEN}🎉 Deployment successful!${NC}"
echo "Application should be available at: http://localhost:8080"
echo "View logs with: docker-compose logs -f"

