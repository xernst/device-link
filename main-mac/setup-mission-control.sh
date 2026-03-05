#!/usr/bin/env bash
# Install Mission Control — AI agent orchestration dashboard
# Run this on your MAIN Mac to monitor the Device Link swarm.
#
# Mission Control by builderz-labs:
# https://github.com/builderz-labs/mission-control
#
# Features:
#   - 26+ panels for monitoring AI agents
#   - Real-time WebSocket + SSE monitoring
#   - Kanban task board with drag-and-drop
#   - Cost tracking per model
#   - Claude Code session auto-discovery
#   - SQLite — no external services needed
#   - Role-based access control

set -euo pipefail

INSTALL_DIR="$HOME/.device-link/mission-control"

echo "==================================="
echo "  Mission Control — Agent Dashboard"
echo "==================================="
echo ""

# Check dependencies
if ! command -v pnpm &>/dev/null; then
    echo "Installing pnpm..."
    if command -v npm &>/dev/null; then
        npm install -g pnpm
    elif command -v brew &>/dev/null; then
        brew install pnpm
    else
        echo "Error: Need npm or Homebrew to install pnpm"
        exit 1
    fi
fi

# Clone or update
if [[ -d "$INSTALL_DIR" ]]; then
    echo "Updating Mission Control..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning Mission Control..."
    git clone https://github.com/builderz-labs/mission-control.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Install dependencies
echo "Installing dependencies..."
pnpm install

# Create .env if not exists
if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        cp .env.example .env
        echo "Created .env from .env.example"
        echo ""
        echo "  Edit $INSTALL_DIR/.env to set:"
        echo "    AUTH_USER=your_username"
        echo "    AUTH_PASS=your_password"
        echo ""
    else
        cat > .env << 'ENVEOF'
AUTH_USER=admin
AUTH_PASS=devicelink
ENVEOF
        echo "Created .env with default credentials (change these!)"
    fi
fi

echo ""
echo "Installation complete!"
echo ""
echo "To start Mission Control:"
echo "  cd $INSTALL_DIR && pnpm dev"
echo ""
echo "Then open: http://localhost:3000"
echo ""
echo "Mission Control will auto-discover Claude Code sessions"
echo "from ~/.claude/projects/ every 60 seconds."
