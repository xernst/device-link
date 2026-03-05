#!/usr/bin/env bash
# Device Link — 2-Tier Model Pipeline
#
# Tier 1: Claude — reasoning, planning, and verification
# Tier 2: Ollama (local, free) — fast execution of routine tasks
#
# No extra subscriptions needed. Claude uses your existing CLI auth.
# Ollama is free and runs locally on the helper Macs.
#
# Usage:
#   ./pipeline.sh <brain> <host> <task>
#   ./pipeline.sh left helper-left "run all tests"
#   ./pipeline.sh local localhost "explain this function"

set -euo pipefail

BRAIN="${1:-}"
HOST="${2:-}"
TASK="${3:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$HOME/.device-link/config"
RESULTS_DIR="$HOME/.device-link/results"
PIPELINE_DIR="$HOME/.device-link/pipeline"

# Load config
[[ -f "$CONFIG_FILE" ]] && source "$CONFIG_FILE"

SSH_USER="${DEVICE_LINK_USER:-$(whoami)}"
PROJECT="${DEVICE_LINK_PROJECT:-$(basename "$(pwd)")}"
OLLAMA_MODEL_LEFT="${DEVICE_LINK_OLLAMA_MODEL_LEFT:-qwen2.5-coder:7b}"
OLLAMA_MODEL_RIGHT="${DEVICE_LINK_OLLAMA_MODEL_RIGHT:-llama3.1:8b}"
OLLAMA_ENDPOINT="${OLLAMA_HOST:-http://localhost:11434}"

mkdir -p "$RESULTS_DIR" "$PIPELINE_DIR"

if [[ -z "$TASK" ]]; then
    echo "Usage: pipeline.sh <brain> <host> \"<task>\"" >&2
    exit 1
fi

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$PIPELINE_DIR/${BRAIN}-${TIMESTAMP}"
mkdir -p "$RUN_DIR"

# --- Tier 1: Claude (reasoning + verification) ---

tier1_claude() {
    local task="$1"
    local brain="$2"
    local host="$3"
    local output_file="$RUN_DIR/tier1-claude.md"

    echo "[Tier 1] Claude reasoning..."

    local brain_context
    if [[ "$brain" == "left" ]]; then
        brain_context="You are the LEFT BRAIN (analytical). Focus on: correctness, testing, edge cases, security, performance."
    else
        brain_context="You are the RIGHT BRAIN (creative). Focus on: architecture, design, UX, documentation, multiple approaches."
    fi

    local prompt="${brain_context}

## Task
${task}

## Instructions
1. Analyze this task thoroughly
2. Create a step-by-step plan to accomplish it
3. Flag any risks or concerns
4. Be specific about commands, files, and expected outcomes

## Output Format
## Plan
<numbered steps>

## Risks
<any concerns>

## Verdict: APPROVED
## Execution Steps
<the specific steps for Ollama to execute — keep these simple and concrete>"

    if [[ "$host" == "localhost" ]]; then
        echo "$prompt" | claude --print > "$output_file" 2>&1
    else
        ssh -o ConnectTimeout=10 "${SSH_USER}@${host}" \
            "cd ~/.device-link/workspace/${PROJECT} 2>/dev/null || cd ~/.device-link/workspace; \
             claude --print $(printf '%q' "$prompt")" \
            > "$output_file" 2>&1
    fi

    cat "$output_file"
}

# --- Tier 2: Ollama (local execution — free) ---

tier2_ollama() {
    local plan="$1"
    local brain="$2"
    local host="$3"
    local output_file="$RUN_DIR/tier2-ollama.md"

    echo "[Tier 2] Ollama execution..."

    local model
    if [[ "$brain" == "left" ]]; then
        model="$OLLAMA_MODEL_LEFT"
    else
        model="$OLLAMA_MODEL_RIGHT"
    fi

    local exec_prompt="Execute the following plan. For each step, show what you did and the result. Be concise.

${plan}"

    local endpoint
    if [[ "$host" == "localhost" ]]; then
        endpoint="$OLLAMA_ENDPOINT"
    else
        endpoint="http://${host}:11434"
    fi

    local response
    response=$(curl -s --max-time 120 "${endpoint}/api/chat" \
        -d "$(jq -n \
            --arg model "$model" \
            --arg content "$exec_prompt" \
            '{
                model: $model,
                messages: [{role: "user", content: $content}],
                stream: false
            }')")

    local content
    content=$(echo "$response" | jq -r '.message.content // empty')

    if [[ -z "$content" ]]; then
        echo "[Tier 2] Ollama unavailable — Claude handling execution too" >&2
        if [[ "$host" == "localhost" ]]; then
            echo "$exec_prompt" | claude --print > "$output_file" 2>&1
        else
            ssh -o ConnectTimeout=10 "${SSH_USER}@${host}" \
                "cd ~/.device-link/workspace/${PROJECT} 2>/dev/null || cd ~/.device-link/workspace; \
                 claude --print $(printf '%q' "$exec_prompt")" \
                > "$output_file" 2>&1
        fi
    else
        echo "$content" > "$output_file"
    fi

    cat "$output_file"
}

# --- Orchestrate ---

echo "======================================"
echo " Device Link Pipeline — ${BRAIN^^}"
echo " $(date)"
echo "======================================"
echo ""

# Tier 1: Claude reasons and plans
PLAN=$(tier1_claude "$TASK" "$BRAIN" "$HOST")
echo ""

# Extract execution steps for Ollama
EXEC_STEPS=$(echo "$PLAN" | sed -n '/^## Execution Steps/,$p' | tail -n +2)
if [[ -z "$EXEC_STEPS" ]]; then
    EXEC_STEPS="$PLAN"
fi

# Check if Claude rejected
if echo "$PLAN" | grep -qi "## Verdict:.*REJECTED"; then
    echo "[Pipeline] Claude flagged issues. Stopping."
    RESULT_FILE="$RESULTS_DIR/${BRAIN}-${TIMESTAMP}.md"
    {
        echo "# Pipeline Result — ${BRAIN} brain"
        echo "## Task: ${TASK}"
        echo "## Status: REJECTED"
        echo "## Timestamp: $(date)"
        echo ""
        echo "---"
        echo "$PLAN"
    } > "$RESULT_FILE"
    echo "Result: $RESULT_FILE"
    exit 1
fi

# Tier 2: Ollama executes (free, local)
EXECUTION=$(tier2_ollama "$EXEC_STEPS" "$BRAIN" "$HOST")
echo ""

# --- Save result ---

RESULT_FILE="$RESULTS_DIR/${BRAIN}-${TIMESTAMP}.md"
{
    echo "# Pipeline Result — ${BRAIN} brain"
    echo "## Task: ${TASK}"
    echo "## Status: COMPLETE"
    echo "## Timestamp: $(date)"
    echo ""
    echo "---"
    echo "## Tier 1 — Claude Plan"
    echo "$PLAN"
    echo ""
    echo "---"
    echo "## Tier 2 — Ollama Execution"
    echo "$EXECUTION"
} > "$RESULT_FILE"

echo "======================================"
echo " Pipeline Complete"
echo " Result: $RESULT_FILE"
echo "======================================"
