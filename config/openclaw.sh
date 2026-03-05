#!/usr/bin/env bash
# Device Link — Install/update OpenClaw gateway on a helper Mac.
#
# Based on: Ollama blog tutorial, MoltFounders cheatsheet, AdvenBoost guide
#
# Handles:
#   - Fresh installs (official installer) or updating old/vulnerable versions
#   - Configuring Ollama as the model provider
#   - Binding gateway to Tailscale only
#   - Setting up auth token + sandbox hardening
#   - Brain-specific agent personality (AGENTS.md, SOUL.md)
#   - Native Telegram channel (alongside our telegram-bridge.py)
#   - Installing as LaunchAgent daemon with autostart
#
# Usage:
#   bash openclaw.sh <left|right>

set -euo pipefail

BRAIN="${1:-}"
if [[ -z "$BRAIN" ]]; then
    echo "Usage: $0 <left|right>" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OPENCLAW_MIN_SAFE="2026.2.26"
OPENCLAW_PORT=18789
OPENCLAW_DIR="$HOME/.openclaw"
OPENCLAW_CONFIG="$OPENCLAW_DIR/openclaw.json"
OPENCLAW_ENV="$OPENCLAW_DIR/.env"

# --- Helpers ---
version_gte() {
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

# --- Ensure Node.js 22+ ---
if ! command -v node &>/dev/null; then
    echo "  Installing Node.js..."
    brew install node
fi

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

# --- Generate auth token ---
mkdir -p "$OPENCLAW_DIR"

if [[ ! -f "$OPENCLAW_ENV" ]] || ! grep -q "OPENCLAW_GATEWAY_TOKEN" "$OPENCLAW_ENV" 2>/dev/null; then
    TOKEN=$(node -e "console.log(require('crypto').randomBytes(48).toString('hex'))")
    echo "OPENCLAW_GATEWAY_TOKEN=$TOKEN" >> "$OPENCLAW_ENV"
    echo "  Generated new gateway auth token."
else
    TOKEN=$(grep "OPENCLAW_GATEWAY_TOKEN" "$OPENCLAW_ENV" | cut -d= -f2-)
    echo "  Using existing gateway auth token."
fi

# ============================================================
# Gateway configuration
# ============================================================
echo "  Configuring gateway..."

# Bind to Tailscale only — never expose to public internet
openclaw config set gateway.bind "tailnet" 2>/dev/null || true
openclaw config set gateway.port "$OPENCLAW_PORT" 2>/dev/null || true
openclaw config set gateway.auth.token "$TOKEN" 2>/dev/null || true

# ============================================================
# Ollama provider — connect to local Ollama instance
# ============================================================
echo "  Configuring Ollama provider..."

# Use native Ollama API (NOT /v1 — that breaks tool calling)
openclaw config set models.providers.ollama.apiKey "ollama-local" 2>/dev/null || true
openclaw config set models.providers.ollama.baseUrl "http://127.0.0.1:11434" 2>/dev/null || true

# Set default model based on brain type
if [[ "$BRAIN" == "left" ]]; then
    openclaw config set models.defaults.model "ollama/qwen2.5-coder:7b" 2>/dev/null || true
else
    openclaw config set models.defaults.model "ollama/llama3.1:8b" 2>/dev/null || true
fi

# Ollama needs larger context window for agent tasks (default 2048 is too small)
if ! grep -q "OLLAMA_NUM_CTX" "$HOME/.zshrc" 2>/dev/null; then
    echo "" >> "$HOME/.zshrc"
    echo "# OpenClaw — Ollama needs larger context for agent tasks" >> "$HOME/.zshrc"
    echo "export OLLAMA_NUM_CTX=24576" >> "$HOME/.zshrc"
fi

# ============================================================
# Agent personality — brain-specific AGENTS.md and SOUL.md
# ============================================================
echo "  Setting up agent personality..."

AGENT_DIR="$OPENCLAW_DIR/agents/default"
mkdir -p "$AGENT_DIR"

# AGENTS.md — operating instructions for this brain
if [[ "$BRAIN" == "left" ]]; then
    cat > "$AGENT_DIR/AGENTS.md" << 'AGENTS_EOF'
# Left Brain — Analytical Agent

You are the LEFT BRAIN of a multi-machine AI agent swarm called Device Link.
Your specialty is analytical work: code review, testing, debugging, security analysis.

## Your Role
- Run tests and report failures with root cause analysis
- Review code for bugs, security issues, and best practices
- Debug complex issues methodically
- Perform security audits (OWASP Top 10)
- Refactor code for clarity and performance

## How You Work
- Be precise and evidence-based
- Always cite specific lines and files
- Provide actionable fixes, not just observations
- Run verification after making changes
- Prioritize correctness over speed

## Tools Available
- Code analysis and file operations
- Test execution and coverage reporting
- Security scanning
- Build and lint tools
AGENTS_EOF
else
    cat > "$AGENT_DIR/AGENTS.md" << 'AGENTS_EOF'
# Right Brain — Creative Agent

You are the RIGHT BRAIN of a multi-machine AI agent swarm called Device Link.
Your specialty is creative work: design, research, planning, documentation.

## Your Role
- Design system architectures and APIs
- Research technologies, markets, and competitors
- Write PRDs and technical specifications
- Plan implementation strategies
- Create and maintain documentation

## How You Work
- Think big picture before diving into details
- Consider multiple approaches and trade-offs
- Produce structured, actionable output
- Back recommendations with research
- Balance ambition with pragmatism

## Tools Available
- Web research and analysis
- Document creation and editing
- Architecture diagramming
- Market research tools
AGENTS_EOF
fi

# SOUL.md — persona and boundaries
cat > "$AGENT_DIR/SOUL.md" << SOUL_EOF
# Device Link — ${BRAIN^} Brain

I am a specialized AI agent in the Device Link swarm.
I operate autonomously on tasks dispatched from the main Mac.
I am thorough, reliable, and focused on my specialty.
I save results to ~/.device-link/results/ when tasks complete.
SOUL_EOF

# ============================================================
# Session configuration
# ============================================================
echo "  Configuring sessions..."

# Reset sessions daily at 4 AM to keep context fresh
openclaw config set sessions.reset "daily" 2>/dev/null || true

# ============================================================
# Security hardening
# ============================================================
echo "  Applying security hardening..."

# Lock down file permissions
chmod 700 "$OPENCLAW_DIR" 2>/dev/null || true
chmod 600 "$OPENCLAW_ENV" 2>/dev/null || true
chmod 600 "$OPENCLAW_CONFIG" 2>/dev/null || true

# ============================================================
# Native Telegram channel (optional — if env vars are set)
# ============================================================
if [[ -n "${TELEGRAM_BOT_TOKEN:-}" ]]; then
    echo "  Configuring native Telegram channel..."
    openclaw channels add telegram \
        --token "$TELEGRAM_BOT_TOKEN" \
        2>/dev/null || true
fi

# ============================================================
# Install daemon + autostart
# ============================================================
echo "  Installing gateway daemon..."
openclaw gateway install 2>/dev/null || true
openclaw gateway start 2>/dev/null || true

# Enable autostart on reboot
openclaw autostart enable 2>/dev/null || true

# ============================================================
# Diagnostics
# ============================================================
echo "  Running diagnostics..."
openclaw doctor --deep --yes 2>/dev/null || openclaw doctor 2>/dev/null || true

# ============================================================
# Summary
# ============================================================
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "<tailscale-ip>")

echo ""
echo "  OpenClaw setup complete for ${BRAIN} brain."
echo ""
echo "  Gateway:    http://${TAILSCALE_IP}:${OPENCLAW_PORT}"
echo "  Config:     ${OPENCLAW_CONFIG}"
echo "  Agent:      ${AGENT_DIR}/AGENTS.md"
echo "  Auth token: saved in ${OPENCLAW_ENV}"
echo "  Logs:       /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log"
echo ""
echo "  Useful commands:"
echo "    openclaw status              # check service"
echo "    openclaw health              # gateway health"
echo "    openclaw logs                # view logs"
echo "    openclaw doctor              # diagnose issues"
echo "    openclaw channels status     # check channels"
echo ""
echo "  Save this token on your main Mac:"
echo "    export OPENCLAW_GATEWAY_TOKEN=\"${TOKEN}\""
