#!/usr/bin/env bash
# Configure Claude Code with brain-specific agent profiles.
set -euo pipefail

BRAIN="${1:-}"
SCRIPT_DIR="${2:-}"
CLAUDE_DIR="$HOME/.claude"

# Check if Claude Code is installed
if ! command -v claude &>/dev/null; then
    echo "  Claude Code not found. Install it first:"
    echo "    npm install -g @anthropic-ai/claude-code"
    echo "  Or visit: https://docs.anthropic.com/en/docs/claude-code"
    echo ""
    echo "  Skipping Claude Code config (install manually, then re-run this script)."
    return 0 2>/dev/null || exit 0
fi

echo "  Claude Code found: $(claude --version 2>/dev/null || echo 'installed')"

# Create Claude config directories
mkdir -p "$CLAUDE_DIR/commands"

# Copy brain-specific profile as the system prompt context
PROFILE_SRC="$SCRIPT_DIR/${BRAIN}-brain/profile.md"
if [[ -f "$PROFILE_SRC" ]]; then
    # Install as a project-level CLAUDE.md in the device-link working directory
    WORK_DIR="$HOME/.device-link/workspace"
    mkdir -p "$WORK_DIR"
    cp "$PROFILE_SRC" "$WORK_DIR/CLAUDE.md"
    echo "  Installed ${BRAIN}-brain profile to $WORK_DIR/CLAUDE.md"
fi

echo "  Claude Code configured for ${BRAIN} brain."
