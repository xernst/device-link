#!/usr/bin/env bash
# Configure Claude Code with the full brain-specific toolkit:
# agents, skills, rules, commands, and profile.
set -euo pipefail

BRAIN="${1:-}"
SCRIPT_DIR="${2:-}"
CLAUDE_DIR="$HOME/.claude"
BRAIN_DIR="$SCRIPT_DIR/${BRAIN}-brain"

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

# --- Create Claude config directories ---
mkdir -p "$CLAUDE_DIR/agents"
mkdir -p "$CLAUDE_DIR/commands"
mkdir -p "$CLAUDE_DIR/rules"
mkdir -p "$CLAUDE_DIR/skills"

# --- Install Agents ---
if [[ -d "$BRAIN_DIR/agents" ]]; then
    agent_count=0
    for agent in "$BRAIN_DIR/agents"/*.md; do
        [[ -f "$agent" ]] || continue
        cp "$agent" "$CLAUDE_DIR/agents/"
        agent_count=$((agent_count + 1))
    done
    echo "  Installed $agent_count agents to $CLAUDE_DIR/agents/"
fi

# --- Install Commands (slash commands) ---
if [[ -d "$BRAIN_DIR/commands" ]]; then
    cmd_count=0
    for cmd in "$BRAIN_DIR/commands"/*.md; do
        [[ -f "$cmd" ]] || continue
        cp "$cmd" "$CLAUDE_DIR/commands/"
        cmd_count=$((cmd_count + 1))
    done
    echo "  Installed $cmd_count commands to $CLAUDE_DIR/commands/"
fi

# --- Install Rules ---
if [[ -d "$BRAIN_DIR/rules" ]]; then
    rule_count=0
    for rule in "$BRAIN_DIR/rules"/*.md; do
        [[ -f "$rule" ]] || continue
        cp "$rule" "$CLAUDE_DIR/rules/"
        rule_count=$((rule_count + 1))
    done
    echo "  Installed $rule_count rules to $CLAUDE_DIR/rules/"
fi

# --- Install Skills (directory-based) ---
if [[ -d "$BRAIN_DIR/skills" ]]; then
    skill_count=0
    for skill_dir in "$BRAIN_DIR/skills"/*/; do
        [[ -d "$skill_dir" ]] || continue
        skill_name="$(basename "$skill_dir")"
        mkdir -p "$CLAUDE_DIR/skills/$skill_name"
        cp -r "$skill_dir"* "$CLAUDE_DIR/skills/$skill_name/" 2>/dev/null || true
        skill_count=$((skill_count + 1))
    done
    echo "  Installed $skill_count skills to $CLAUDE_DIR/skills/"
fi

# --- Install Brain Profile ---
PROFILE_SRC="$BRAIN_DIR/profile.md"
if [[ -f "$PROFILE_SRC" ]]; then
    WORK_DIR="$HOME/.device-link/workspace"
    mkdir -p "$WORK_DIR"
    cp "$PROFILE_SRC" "$WORK_DIR/CLAUDE.md"
    echo "  Installed ${BRAIN}-brain profile to $WORK_DIR/CLAUDE.md"
fi

# --- Summary ---
echo ""
echo "  ${BRAIN^} Brain Toolkit Installed:"
echo "  ─────────────────────────────────"
[[ -d "$BRAIN_DIR/agents" ]] && echo "  Agents:   $(ls "$BRAIN_DIR/agents"/*.md 2>/dev/null | wc -l | tr -d ' ')"
[[ -d "$BRAIN_DIR/commands" ]] && echo "  Commands: $(ls "$BRAIN_DIR/commands"/*.md 2>/dev/null | wc -l | tr -d ' ')"
[[ -d "$BRAIN_DIR/rules" ]] && echo "  Rules:    $(ls "$BRAIN_DIR/rules"/*.md 2>/dev/null | wc -l | tr -d ' ')"
[[ -d "$BRAIN_DIR/skills" ]] && echo "  Skills:   $(ls -d "$BRAIN_DIR/skills"/*/ 2>/dev/null | wc -l | tr -d ' ')"
echo "  Profile:  ${BRAIN}-brain"
echo ""
echo "  Claude Code configured for ${BRAIN} brain."
