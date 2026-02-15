#!/bin/bash

# Script to restart GitHub Actions self-hosted runner
# Usage: ./scripts/restart-runner.sh

set -e

echo "🔄 Restarting GitHub Actions Runner..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find runner directory
RUNNER_DIR=""
if [ -d "$HOME/actions-runner" ]; then
    RUNNER_DIR="$HOME/actions-runner"
elif [ -d "/opt/actions-runner" ]; then
    RUNNER_DIR="/opt/actions-runner"
elif [ -d "/home/runner/actions-runner" ]; then
    RUNNER_DIR="/home/runner/actions-runner"
else
    echo -e "${YELLOW}⚠️  Runner directory not found in common locations${NC}"
    echo "Please specify the runner directory:"
    read -p "Runner directory path: " RUNNER_DIR
fi

if [ ! -d "$RUNNER_DIR" ]; then
    echo -e "${RED}❌ Runner directory not found: $RUNNER_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found runner directory: $RUNNER_DIR${NC}"
cd "$RUNNER_DIR"

# Check if running as systemd service
SERVICE_NAME=$(systemctl list-units --type=service --all | grep -i "actions.runner" | awk '{print $1}' | head -1)

if [ -n "$SERVICE_NAME" ]; then
    echo -e "${YELLOW}📦 Found systemd service: $SERVICE_NAME${NC}"
    echo "Stopping service..."
    sudo systemctl stop "$SERVICE_NAME" || true
    sleep 2
    echo "Starting service..."
    sudo systemctl start "$SERVICE_NAME"
    sleep 3
    echo "Checking status..."
    sudo systemctl status "$SERVICE_NAME" --no-pager -l | head -20
else
    echo -e "${YELLOW}⚠️  No systemd service found, checking for manual runner process...${NC}"
    
    # Kill existing runner processes
    if pgrep -f "Runner.Listener" > /dev/null; then
        echo "Stopping existing runner processes..."
        pkill -f "Runner.Listener" || true
        sleep 2
    fi
    
    # Start runner
    echo "Starting runner..."
    if [ -f "./run.sh" ]; then
        nohup ./run.sh > runner.log 2>&1 &
        echo "Runner started in background"
        echo "Check logs with: tail -f $RUNNER_DIR/runner.log"
    else
        echo -e "${RED}❌ run.sh not found in $RUNNER_DIR${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}✅ Runner restart completed!${NC}"
echo ""
echo "To verify runner is online:"
echo "1. Check GitHub Actions > Settings > Runners"
echo "2. Run: ./scripts/check-runner.sh"
echo "3. Check logs: tail -f $RUNNER_DIR/_diag/Runner_*.log"

