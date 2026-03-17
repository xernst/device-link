#!/usr/bin/env bash
# CrowdTest — Paperclip setup (standalone, not device-link dependent)
#
# Sets up Paperclip orchestration for building CrowdTest with a 7-agent
# AI company: CEO, CTO, Backend Eng, Frontend Eng, LLM Eng, QA Eng, Designer.
#
# Usage:
#   ./setup.sh
#
# Requirements:
#   - Node.js 20+
#   - pnpm 9.15+
#   - Claude Code CLI (for agent adapter)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PAPERCLIP_PORT=3100

echo "======================================"
echo " CrowdTest — Paperclip Setup"
echo "======================================"
echo ""

# --- Prerequisites ---
echo "[1/4] Checking prerequisites..."

if ! command -v node &>/dev/null; then
    echo "ERROR: Node.js not found. Install: brew install node@20" >&2
    exit 1
fi

NODE_MAJOR=$(node -v | grep -oE '[0-9]+' | head -1)
if [[ "$NODE_MAJOR" -lt 20 ]]; then
    echo "ERROR: Node.js 20+ required (found v$NODE_MAJOR)" >&2
    exit 1
fi

if ! command -v pnpm &>/dev/null; then
    echo "Installing pnpm..."
    npm install -g pnpm@latest
fi

echo "  Node.js $(node -v) ✓"
echo "  pnpm $(pnpm -v) ✓"

if command -v claude &>/dev/null; then
    echo "  Claude Code ✓"
else
    echo "  Claude Code not found (agents will use shell adapter as fallback)"
fi

# --- Install Paperclip ---
echo ""
echo "[2/4] Installing Paperclip..."

if [[ -d "$PROJECT_ROOT/.paperclip/repo" ]]; then
    echo "  Updating existing installation..."
    cd "$PROJECT_ROOT/.paperclip/repo"
    git pull origin master
    pnpm install --frozen-lockfile 2>/dev/null || pnpm install
else
    mkdir -p "$PROJECT_ROOT/.paperclip"
    git clone https://github.com/paperclipai/paperclip.git "$PROJECT_ROOT/.paperclip/repo"
    cd "$PROJECT_ROOT/.paperclip/repo"
    pnpm install
fi

pnpm build
pnpm db:migrate 2>/dev/null || true
echo "  Paperclip installed ✓"

# --- Import Company ---
echo ""
echo "[3/4] Company config ready at:"
echo "  $SCRIPT_DIR/company.json"
echo ""
echo "  Org chart:"
echo ""
echo "  ┌─────────────────────────────────┐"
echo "  │           CEO (claude)          │"
echo "  │   Strategy, delegation, review  │"
echo "  └──────────┬──────────┬───────────┘"
echo "             │          │"
echo "    ┌────────▼──┐  ┌────▼──────────┐"
echo "    │  Designer │  │     CTO       │"
echo "    │  UI/UX    │  │  Architecture │"
echo "    └───────────┘  └──┬───┬───┬────┘"
echo "                      │   │   │"
echo "         ┌────────────▼┐ ┌▼───▼────────┐"
echo "         │ Backend Eng ││ Frontend Eng │"
echo "         │ Sim engine  ││ Dashboard    │"
echo "         └─────────────┘└──────────────┘"
echo "         ┌─────────────┐┌──────────────┐"
echo "         │  LLM Eng    ││   QA Eng     │"
echo "         │  Prompts    ││   Testing    │"
echo "         └─────────────┘└──────────────┘"
echo ""
echo "  7 agents, \$50/mo budget, 15-30min heartbeats"

# --- Launch instructions ---
echo ""
echo "[4/4] Ready to launch!"
echo ""
echo "  Start Paperclip:"
echo "    cd $PROJECT_ROOT/.paperclip/repo && pnpm dev"
echo ""
echo "  Then open: http://localhost:${PAPERCLIP_PORT}"
echo ""
echo "  Create company → import company.json → approve CEO hire → go."
echo ""
echo "======================================"
