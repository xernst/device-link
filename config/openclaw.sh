#!/usr/bin/env bash
# Device Link — Install/update OpenClaw gateway on a helper Mac.
#
# Handles:
#   - Fresh installs
#   - Updating old/vulnerable OpenClaw versions to latest
#   - Configuring Ollama provider
#   - Binding to Tailscale only
#   - Setting up auth token
#   - Installing as LaunchAgent daemon
#
# Usage:
#   bash openclaw.sh <left|right>

set -euo pipefail

BRAIN="${1:-}"
if [[ -z "$BRAIN" ]]; then
    echo "Usage: $0 <left|right>" >&2
    exit 1
fi

OPENCLAW_MIN_SAFE="2026.2.26"
OPENCLAW_PORT=18789
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
OPENCLAW_ENV="$HOME/.openclaw/.env"

# --- Helpers ---
version_gte() {
    # Returns 0 if $1 >= $2 (version comparison)
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# --- Check for existing OpenClaw ---
if command -v openclaw &>/dev/null; then
    CURRENT_VERSION=$(openclaw --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "0.0.0")
    echo "  Found existing OpenClaw: v${CURRENT_VERSION}"

    if version_gte "$CURRENT_VERSION" "$OPENCLAW_MIN_SAFE"; then
        echo "  Version is safe (>= $OPENCLAW_MIN_SAFE). Updating to latest..."
    else
        echo "  WARNING: Version $CURRENT_VERSION has known CVEs!"
        echo "  Updating to latest (minimum safe: $OPENCLAW_MIN_SAFE)..."
    fi

    # Stop existing gateway before update
    openclaw gateway stop 2>/dev/null || true
    sleep 1
else
    echo "  No existing OpenClaw found. Installing fresh..."
fi

# --- Ensure Node.js is available ---
if ! command -v node &>/dev/null; then
    echo "  Installing Node.js..."
    brew install node
fi

# Check Node.js version (OpenClaw needs 22+)
NODE_VERSION=$(node --version | grep -oE '[0-9]+' | head -1)
if [[ "$NODE_VERSION" -lt 22 ]]; then
    echo "  Upgrading Node.js (need v22+, have v${NODE_VERSION})..."
    brew upgrade node
fi

# --- Install/update OpenClaw ---
echo "  Installing OpenClaw (latest)..."
npm install -g openclaw@latest 2>&1 | tail -1

NEW_VERSION=$(openclaw --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown")
echo "  OpenClaw v${NEW_VERSION} installed."

# --- Configure ---
mkdir -p "$HOME/.openclaw"

# Generate auth token if not already set
if [[ ! -f "$OPENCLAW_ENV" ]] || ! grep -q "OPENCLAW_GATEWAY_TOKEN" "$OPENCLAW_ENV" 2>/dev/null; then
    TOKEN=$(node -e "console.log(require('crypto').randomBytes(48).toString('hex'))")
    echo "OPENCLAW_GATEWAY_TOKEN=$TOKEN" >> "$OPENCLAW_ENV"
    echo "  Generated new gateway auth token."
else
    TOKEN=$(grep "OPENCLAW_GATEWAY_TOKEN" "$OPENCLAW_ENV" | cut -d= -f2-)
    echo "  Using existing gateway auth token."
fi

# Configure gateway
openclaw config set gateway.bind "tailnet" 2>/dev/null || true
openclaw config set gateway.port "$OPENCLAW_PORT" 2>/dev/null || true
openclaw config set gateway.auth.token "$TOKEN" 2>/dev/null || true

# Configure Ollama provider
openclaw config set models.providers.ollama.apiKey "ollama-local" 2>/dev/null || true
openclaw config set models.providers.ollama.baseUrl "http://127.0.0.1:11434" 2>/dev/null || true

# Set default model based on brain type
if [[ "$BRAIN" == "left" ]]; then
    openclaw config set models.defaults.model "ollama/qwen2.5-coder:7b" 2>/dev/null || true
else
    openclaw config set models.defaults.model "ollama/llama3.1:8b" 2>/dev/null || true
fi

# Lock down file permissions
chmod 600 "$OPENCLAW_ENV" 2>/dev/null || true
chmod 600 "$OPENCLAW_CONFIG" 2>/dev/null || true

# Set Ollama context window if not already set
if ! grep -q "OLLAMA_NUM_CTX" "$HOME/.zshrc" 2>/dev/null; then
    echo "" >> "$HOME/.zshrc"
    echo "# OpenClaw — Ollama needs larger context for agent tasks" >> "$HOME/.zshrc"
    echo "export OLLAMA_NUM_CTX=24576" >> "$HOME/.zshrc"
fi

# --- Install as daemon ---
echo "  Installing OpenClaw gateway daemon..."
openclaw gateway install 2>/dev/null || true
openclaw gateway start 2>/dev/null || true

# --- Verify ---
echo "  Running diagnostics..."
openclaw doctor 2>/dev/null || true

echo ""
echo "  OpenClaw setup complete."
echo "  Gateway: http://<tailscale-ip>:${OPENCLAW_PORT}"
echo "  Auth token: saved in ${OPENCLAW_ENV}"
echo ""
echo "  Save this token on your main Mac:"
echo "    export OPENCLAW_GATEWAY_TOKEN=\"${TOKEN}\""
