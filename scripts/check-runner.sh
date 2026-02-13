#!/bin/bash

# Quick script to check runner status

echo "=== GitHub Actions Runner Status Check ==="
echo ""

# Check if runner process is running
echo "1. Checking runner process..."
if pgrep -f "Runner.Listener" > /dev/null; then
    echo "✅ Runner process is running"
    ps aux | grep Runner.Listener | grep -v grep
else
    echo "❌ Runner process is NOT running"
fi

echo ""

# Check systemd service
echo "2. Checking systemd service..."
if systemctl list-units --type=service | grep -q "actions.runner"; then
    SERVICE=$(systemctl list-units --type=service | grep "actions.runner" | awk '{print $1}')
    echo "Found service: $SERVICE"
    systemctl status $SERVICE --no-pager -l
else
    echo "⚠️  No runner systemd service found"
    echo "   Runner might be running manually"
fi

echo ""

# Check Docker access
echo "3. Checking Docker access..."
if docker ps > /dev/null 2>&1; then
    echo "✅ Docker is accessible"
    docker --version
else
    echo "❌ Cannot access Docker"
    echo "   Try: sudo usermod -aG docker \$USER"
fi

echo ""

# Check network connectivity
echo "4. Checking GitHub connectivity..."
if curl -s -o /dev/null -w "%{http_code}" https://github.com | grep -q "200"; then
    echo "✅ Can reach GitHub"
else
    echo "❌ Cannot reach GitHub - check network/firewall"
fi

echo ""

# Check runner directory
echo "5. Checking runner installation..."
if [ -d "$HOME/actions-runner" ]; then
    echo "✅ Runner directory exists: $HOME/actions-runner"
    ls -la $HOME/actions-runner/ | head -5
else
    echo "⚠️  Runner directory not found in $HOME/actions-runner"
    echo "   Check if runner is installed elsewhere"
fi

echo ""
echo "=== End of Status Check ==="

