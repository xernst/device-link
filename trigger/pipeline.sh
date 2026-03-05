#!/usr/bin/env bash
# Device Link — 3-Tier Model Pipeline
#
# Tier 1: ChatGPT (OpenAI API) — reasoning and planning
# Tier 2: Claude — verification and quality check
# Tier 3: Ollama (local) — fast execution of routine tasks
#
# Usage:
#   ./pipeline.sh <brain> <host> <task>
#   ./pipeline.sh left helper-left "run all tests"
#
# The pipeline can also be called directly for local-only use:
#   ./pipeline.sh local localhost "explain this function"
#
# Environment:
#   OPENAI_API_KEY       — required for Tier 1 (ChatGPT reasoning)
#   ANTHROPIC_API_KEY    — required for Tier 2 (Claude verification)
#   OLLAMA_HOST          — defaults to localhost:11434

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
OPENAI_MODEL="${DEVICE_LINK_OPENAI_MODEL:-gpt-4o}"
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

# --- Tier 1: ChatGPT Reasoning ---

tier1_chatgpt() {
    local task="$1"
    local brain="$2"
    local output_file="$RUN_DIR/tier1-reasoning.md"

    echo "[Tier 1] ChatGPT reasoning..."

    if [[ -z "${OPENAI_API_KEY:-}" ]]; then
        echo "[Tier 1] OPENAI_API_KEY not set — skipping ChatGPT, passing task directly to Claude" >&2
        echo "$task" > "$output_file"
        cat "$output_file"
        return 0
    fi

    local system_prompt
    if [[ "$brain" == "left" ]]; then
        system_prompt="You are an analytical AI assistant. Break down the following task into a clear, step-by-step plan. Focus on: correctness, testing strategy, edge cases, security implications. Be specific about what commands to run and what to check. Output a structured plan in markdown."
    else
        system_prompt="You are a creative AI assistant. Analyze the following task and produce a thoughtful approach. Focus on: architecture, user experience, design patterns, documentation structure. Suggest multiple options where appropriate. Output a structured plan in markdown."
    fi

    local response
    response=$(curl -s --max-time 60 "https://api.openai.com/v1/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${OPENAI_API_KEY}" \
        -d "$(jq -n \
            --arg model "$OPENAI_MODEL" \
            --arg system "$system_prompt" \
            --arg user "$task" \
            '{
                model: $model,
                messages: [
                    {role: "system", content: $system},
                    {role: "user", content: $user}
                ],
                temperature: 0.7,
                max_tokens: 4096
            }')")

    local content
    content=$(echo "$response" | jq -r '.choices[0].message.content // empty')

    if [[ -z "$content" ]]; then
        local error
        error=$(echo "$response" | jq -r '.error.message // "Unknown error"')
        echo "[Tier 1] ChatGPT error: $error — falling back to raw task" >&2
        echo "$task" > "$output_file"
    else
        echo "$content" > "$output_file"
    fi

    cat "$output_file"
}

# --- Tier 2: Claude Verification ---

tier2_claude() {
    local reasoning="$1"
    local task="$2"
    local brain="$3"
    local host="$4"
    local output_file="$RUN_DIR/tier2-verification.md"

    echo "[Tier 2] Claude verification..."

    local verify_prompt="## Original Task
${task}

## Proposed Plan (from ChatGPT)
${reasoning}

## Your Job
Review this plan critically. Check for:
1. Correctness — will this plan actually accomplish the task?
2. Security — any risks, exposed secrets, unsafe commands?
3. Completeness — anything missing or overlooked?
4. Efficiency — any unnecessary steps?

Output your verdict:
- APPROVED: plan is good, proceed to execution
- MODIFIED: plan needs changes (provide the corrected plan)
- REJECTED: plan is fundamentally wrong (explain why)

Format:
## Verdict: APPROVED|MODIFIED|REJECTED
## Notes: <your analysis>
## Final Plan: <the plan to execute (original or modified)>"

    if [[ "$host" == "localhost" ]]; then
        # Local mode — run claude directly
        echo "$verify_prompt" | claude --print - > "$output_file" 2>&1
    else
        # Remote mode — run claude on the helper
        ssh -o ConnectTimeout=10 "${SSH_USER}@${host}" \
            "cd ~/.device-link/workspace/${PROJECT} 2>/dev/null || cd ~/.device-link/workspace; \
             echo $(printf '%q' "$verify_prompt") | claude --print -" \
            > "$output_file" 2>&1
    fi

    cat "$output_file"
}

# --- Tier 3: Ollama Execution ---

tier3_ollama() {
    local plan="$1"
    local brain="$2"
    local host="$3"
    local output_file="$RUN_DIR/tier3-execution.md"

    echo "[Tier 3] Ollama execution..."

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
        # Hit Ollama on the remote helper via Tailscale
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
        echo "[Tier 3] Ollama error or empty response — falling back to Claude for execution" >&2
        # Fallback: use Claude for execution instead
        if [[ "$host" == "localhost" ]]; then
            echo "$exec_prompt" | claude --print - > "$output_file" 2>&1
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

# Tier 1: ChatGPT reasons about the task
REASONING=$(tier1_chatgpt "$TASK" "$BRAIN")
echo ""

# Tier 2: Claude verifies the plan
VERIFICATION=$(tier2_claude "$REASONING" "$TASK" "$BRAIN" "$HOST")
echo ""

# Check verdict
VERDICT=$(echo "$VERIFICATION" | grep -i "^## Verdict:" | head -1 | sed 's/## Verdict: *//' | tr '[:lower:]' '[:upper:]' | tr -d '[:space:]')

if [[ "$VERDICT" == "REJECTED" ]]; then
    echo "[Pipeline] Claude REJECTED the plan. Stopping."
    echo ""
    echo "$VERIFICATION"

    # Save combined result
    RESULT_FILE="$RESULTS_DIR/${BRAIN}-${TIMESTAMP}.md"
    {
        echo "# Pipeline Result — ${BRAIN} brain"
        echo "## Task: ${TASK}"
        echo "## Status: REJECTED"
        echo "## Timestamp: $(date)"
        echo ""
        echo "---"
        echo "## Tier 1 — ChatGPT Reasoning"
        echo "$REASONING"
        echo ""
        echo "---"
        echo "## Tier 2 — Claude Verification"
        echo "$VERIFICATION"
    } > "$RESULT_FILE"

    echo ""
    echo "Full result saved to: $RESULT_FILE"
    exit 1
fi

# Extract the final plan (either original or modified by Claude)
FINAL_PLAN=$(echo "$VERIFICATION" | sed -n '/^## Final Plan:/,$p' | tail -n +2)
if [[ -z "$FINAL_PLAN" ]]; then
    FINAL_PLAN="$REASONING"
fi

# Tier 3: Ollama executes
EXECUTION=$(tier3_ollama "$FINAL_PLAN" "$BRAIN" "$HOST")
echo ""

# --- Save combined result ---

RESULT_FILE="$RESULTS_DIR/${BRAIN}-${TIMESTAMP}.md"
{
    echo "# Pipeline Result — ${BRAIN} brain"
    echo "## Task: ${TASK}"
    echo "## Status: COMPLETE"
    echo "## Verdict: ${VERDICT:-APPROVED}"
    echo "## Timestamp: $(date)"
    echo ""
    echo "---"
    echo "## Tier 1 — ChatGPT Reasoning"
    echo "$REASONING"
    echo ""
    echo "---"
    echo "## Tier 2 — Claude Verification"
    echo "$VERIFICATION"
    echo ""
    echo "---"
    echo "## Tier 3 — Ollama Execution"
    echo "$EXECUTION"
} > "$RESULT_FILE"

echo "======================================"
echo " Pipeline Complete"
echo " Result: $RESULT_FILE"
echo "======================================"
