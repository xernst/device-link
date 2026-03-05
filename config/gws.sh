#!/usr/bin/env bash
# Device Link — Install & configure Google Workspace CLI on a helper Mac.
# Gives AI agents access to Drive, Gmail, Calendar, Sheets, Docs, Chat, Admin.
#
# Based on: https://github.com/googleworkspace/cli
#
# Handles:
#   - Installing gws via npm
#   - Brain-specific agent skill sets
#   - MCP server configuration for Claude integration
#   - OAuth setup instructions (requires one-time interactive auth)
#
# Usage:
#   bash config/gws.sh <left|right>

set -euo pipefail

BRAIN="${1:-}"
if [[ -z "$BRAIN" ]]; then
    echo "Usage: $0 <left|right>" >&2
    exit 1
fi

echo ""
echo "=== Google Workspace CLI — ${BRAIN} brain ==="
echo ""

GWS_DIR="$HOME/.gws"

# --- Ensure Node.js 22+ (already handled by openclaw.sh, but just in case) ---

if ! command -v node &>/dev/null; then
    echo "  Installing Node.js..."
    brew install node
fi

NODE_VERSION=$(node --version | grep -oE '[0-9]+' | head -1)
if [[ "$NODE_VERSION" -lt 22 ]]; then
    echo "  Upgrading Node.js (need v22+, have v${NODE_VERSION})..."
    brew upgrade node
fi

# --- Install/update gws ---

if command -v gws &>/dev/null; then
    CURRENT_VER=$(gws --version 2>/dev/null | head -1 || echo "unknown")
    echo "  gws already installed: $CURRENT_VER"
    echo "  Updating..."
else
    echo "  Installing Google Workspace CLI..."
fi

npm install -g @anthropic-ai/gws@latest 2>/dev/null \
    || npm install -g @googleworkspace/cli@latest 2>/dev/null \
    || npm install -g gws@latest 2>&1 | tail -1

NEW_VER=$(gws --version 2>/dev/null | head -1 || echo "unknown")
echo "  gws v${NEW_VER} installed."

# --- Agent skills per brain ---

echo "  Installing agent skills for ${BRAIN} brain..."

mkdir -p "$GWS_DIR"

if [[ "$BRAIN" == "left" ]]; then
    # Left brain: audit-focused skills
    cat > "$GWS_DIR/skills.json" << 'SKILLS_EOF'
{
  "brain": "left",
  "skills": [
    "gws-sheets",
    "gws-drive",
    "gws-gmail",
    "gws-admin"
  ],
  "focus": [
    "Audit spreadsheets for data quality issues",
    "Scan Drive for stale or orphaned files",
    "Review Gmail for security alerts and bounced emails",
    "Check admin logs for suspicious activity"
  ]
}
SKILLS_EOF
else
    # Right brain: creative/productivity skills
    cat > "$GWS_DIR/skills.json" << 'SKILLS_EOF'
{
  "brain": "right",
  "skills": [
    "gws-docs",
    "gws-sheets",
    "gws-drive",
    "gws-gmail",
    "gws-calendar"
  ],
  "focus": [
    "Draft and format documents in Google Docs",
    "Create project trackers in Sheets",
    "Organize Drive folders for new projects",
    "Draft emails and replies",
    "Schedule meetings and check availability"
  ]
}
SKILLS_EOF
fi

chmod 600 "$GWS_DIR/skills.json"

# --- MCP server configuration for Claude ---

echo "  Configuring MCP server..."

# Create MCP config so Claude can use gws as a tool provider
MCP_CONFIG="$GWS_DIR/mcp-config.json"
if [[ "$BRAIN" == "left" ]]; then
    cat > "$MCP_CONFIG" << 'MCP_EOF'
{
  "mcpServers": {
    "gws": {
      "command": "gws",
      "args": ["mcp", "--services", "sheets,drive,gmail,admin"],
      "env": {}
    }
  }
}
MCP_EOF
else
    cat > "$MCP_CONFIG" << 'MCP_EOF'
{
  "mcpServers": {
    "gws": {
      "command": "gws",
      "args": ["mcp", "--services", "docs,sheets,drive,gmail,calendar"],
      "env": {}
    }
  }
}
MCP_EOF
fi

chmod 600 "$MCP_CONFIG"

# --- Merge MCP config into Claude's settings if possible ---

CLAUDE_MCP="$HOME/.claude/mcp.json"
if [[ -f "$CLAUDE_MCP" ]]; then
    echo "  Found existing Claude MCP config — merge gws manually if needed."
    echo "  See: $MCP_CONFIG"
else
    mkdir -p "$HOME/.claude"
    cp "$MCP_CONFIG" "$CLAUDE_MCP"
    echo "  Installed MCP config → $CLAUDE_MCP"
fi

# --- OAuth setup ---

echo ""
echo "  ==========================="
echo "  OAuth Setup Required (once)"
echo "  ==========================="
echo ""

# Check if already authenticated
if gws auth status &>/dev/null 2>&1; then
    echo "  Already authenticated."
else
    echo "  gws needs a one-time OAuth sign-in to access Google Workspace."
    echo "  Run this command interactively:"
    echo ""
    echo "    gws auth setup"
    echo ""
    echo "  This opens a browser for Google sign-in. After auth, credentials"
    echo "  are encrypted with AES-256-GCM and stored in the OS keyring."
    echo ""
    echo "  Skipping for now — run 'gws auth setup' when ready."
fi

# --- Summary ---

echo ""
echo "=== Google Workspace CLI Ready ==="
echo "  Version:  ${NEW_VER}"
echo "  Skills:   ${GWS_DIR}/skills.json"
echo "  MCP:      ${MCP_CONFIG}"
echo "  Brain:    ${BRAIN}"
echo ""
echo "  Quick test (after auth):"
echo "    gws drive files list --params '{\"pageSize\": 5}'"
echo "    gws gmail users.messages list --params '{\"maxResults\": 5}'"
echo ""
echo "  MCP server (for Claude):"
echo "    gws mcp --services sheets,drive,gmail"
echo ""
