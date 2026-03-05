#!/usr/bin/env bash
# Device Link — Trigger tasks on helper machines.
#
# Usage:
#   device-link left "run tests on my-app"
#   device-link right "design the auth flow"
#   device-link both "review this PR"
#   device-link status
#   device-link results
#
# Modes (add before the task):
#   --pipeline    3-tier: ChatGPT reasoning -> Claude verification -> Ollama execution [default]
#   --direct      Skip pipeline, send task directly to Claude on helper
#   --ollama      Send task directly to Ollama on helper (cheapest/fastest)
#
# Examples:
#   device-link left "run tests"                  # uses pipeline (default)
#   device-link left --direct "run tests"         # claude only
#   device-link left --ollama "run tests"         # ollama only
#
# Configuration:
#   Set these in ~/.device-link/config or as environment variables:
#     DEVICE_LINK_LEFT_HOST         — Tailscale hostname/IP of left brain
#     DEVICE_LINK_RIGHT_HOST        — Tailscale hostname/IP of right brain
#     DEVICE_LINK_USER              — SSH username (defaults to current user)
#     DEVICE_LINK_PROJECT           — Project path on helpers (defaults to cwd name)
#     DEVICE_LINK_MODE              — Default mode: pipeline|direct|ollama
#     OPENAI_API_KEY                — For ChatGPT reasoning (Tier 1)
#     ANTHROPIC_API_KEY             — For Claude verification (Tier 2)
#     DEVICE_LINK_OPENAI_MODEL      — OpenAI model (default: gpt-4o)
#     DEVICE_LINK_OLLAMA_MODEL_LEFT — Ollama model for left brain
#     DEVICE_LINK_OLLAMA_MODEL_RIGHT— Ollama model for right brain

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$HOME/.device-link/config"

# Load config if exists
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

LEFT_HOST="${DEVICE_LINK_LEFT_HOST:-helper-left}"
RIGHT_HOST="${DEVICE_LINK_RIGHT_HOST:-helper-right}"
SSH_USER="${DEVICE_LINK_USER:-$(whoami)}"
PROJECT="${DEVICE_LINK_PROJECT:-$(basename "$(pwd)")}"
RESULTS_DIR="$HOME/.device-link/results"
DEFAULT_MODE="${DEVICE_LINK_MODE:-pipeline}"

mkdir -p "$RESULTS_DIR"

# --- Functions ---

send_task_direct() {
    local host="$1"
    local brain="$2"
    local task="$3"
    local timestamp
    timestamp="$(date +%Y%m%d-%H%M%S)"
    local result_file="$RESULTS_DIR/${brain}-${timestamp}.md"

    echo "[direct] Sending to ${brain} brain ($host)..."

    ssh -o ConnectTimeout=5 "${SSH_USER}@${host}" \
        "cd ~/.device-link/workspace/${PROJECT} 2>/dev/null || cd ~/.device-link/workspace; \
         claude --print \"${task}\"" \
        > "$result_file" 2>&1

    local exit_code=$?
    if [[ $exit_code -eq 0 ]]; then
        echo "Done. Results: $result_file"
        echo ""
        cat "$result_file"
    else
        echo "Error: Failed to reach ${brain} brain at ${host}" >&2
        return 1
    fi
}

send_task_ollama() {
    local host="$1"
    local brain="$2"
    local task="$3"
    local timestamp
    timestamp="$(date +%Y%m%d-%H%M%S)"
    local result_file="$RESULTS_DIR/${brain}-${timestamp}.md"

    local model
    if [[ "$brain" == "left" ]]; then
        model="${DEVICE_LINK_OLLAMA_MODEL_LEFT:-qwen2.5-coder:7b}"
    else
        model="${DEVICE_LINK_OLLAMA_MODEL_RIGHT:-llama3.1:8b}"
    fi

    echo "[ollama] Sending to ${brain} brain ($host) using $model..."

    local response
    response=$(curl -s --max-time 120 "http://${host}:11434/api/chat" \
        -d "$(jq -n \
            --arg model "$model" \
            --arg content "$task" \
            '{model: $model, messages: [{role: "user", content: $content}], stream: false}')")

    local content
    content=$(echo "$response" | jq -r '.message.content // empty')

    if [[ -n "$content" ]]; then
        echo "$content" > "$result_file"
        echo "Done. Results: $result_file"
        echo ""
        cat "$result_file"
    else
        echo "Error: Ollama returned empty response from ${host}" >&2
        return 1
    fi
}

send_task_pipeline() {
    local host="$1"
    local brain="$2"
    local task="$3"

    bash "$SCRIPT_DIR/pipeline.sh" "$brain" "$host" "$task"
}

send_task() {
    local host="$1"
    local brain="$2"
    local task="$3"
    local mode="$4"

    case "$mode" in
        pipeline)  send_task_pipeline "$host" "$brain" "$task" ;;
        direct)    send_task_direct "$host" "$brain" "$task" ;;
        ollama)    send_task_ollama "$host" "$brain" "$task" ;;
        *)         send_task_pipeline "$host" "$brain" "$task" ;;
    esac
}

show_status() {
    echo "Device Link Status"
    echo "==================="
    echo ""

    for brain_host in "left:${LEFT_HOST}" "right:${RIGHT_HOST}"; do
        local brain="${brain_host%%:*}"
        local host="${brain_host##*:}"

        printf "%-12s " "${brain} brain:"
        if ssh -o ConnectTimeout=3 "${SSH_USER}@${host}" "tmux has-session -t ${brain}-brain 2>/dev/null" 2>/dev/null; then
            echo "ONLINE (tmux session active)"
        elif ssh -o ConnectTimeout=3 "${SSH_USER}@${host}" "echo ok" &>/dev/null; then
            echo "REACHABLE (but no tmux session)"
        else
            echo "OFFLINE"
        fi
    done
}

show_results() {
    echo "Recent Results"
    echo "=============="
    echo ""

    if [[ -z "$(ls -A "$RESULTS_DIR" 2>/dev/null)" ]]; then
        echo "No results yet."
        return
    fi

    ls -t "$RESULTS_DIR"/*.md 2>/dev/null | head -5 | while read -r f; do
        echo "--- $(basename "$f") ---"
        head -20 "$f"
        echo ""
    done
}

# --- Parse mode flag ---

parse_mode_and_task() {
    local mode="$DEFAULT_MODE"
    local task=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --pipeline)  mode="pipeline"; shift ;;
            --direct)    mode="direct"; shift ;;
            --ollama)    mode="ollama"; shift ;;
            *)           task="$1"; shift ;;
        esac
    done

    echo "$mode"
    echo "$task"
}

# --- Main ---

COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    left)
        read -r MODE TASK <<< "$(parse_mode_and_task "$@")"
        if [[ -z "$TASK" ]]; then
            echo "Usage: device-link left [--pipeline|--direct|--ollama] \"<task>\"" >&2
            exit 1
        fi
        send_task "$LEFT_HOST" "left" "$TASK" "$MODE"
        ;;
    right)
        read -r MODE TASK <<< "$(parse_mode_and_task "$@")"
        if [[ -z "$TASK" ]]; then
            echo "Usage: device-link right [--pipeline|--direct|--ollama] \"<task>\"" >&2
            exit 1
        fi
        send_task "$RIGHT_HOST" "right" "$TASK" "$MODE"
        ;;
    both)
        read -r MODE TASK <<< "$(parse_mode_and_task "$@")"
        if [[ -z "$TASK" ]]; then
            echo "Usage: device-link both [--pipeline|--direct|--ollama] \"<task>\"" >&2
            exit 1
        fi
        send_task "$LEFT_HOST" "left" "$TASK" "$MODE" &
        LEFT_PID=$!
        send_task "$RIGHT_HOST" "right" "$TASK" "$MODE" &
        RIGHT_PID=$!
        wait $LEFT_PID $RIGHT_PID
        ;;
    status)
        show_status
        ;;
    results)
        show_results
        ;;
    help|*)
        echo "Device Link — Trigger tasks on helper machines"
        echo ""
        echo "Usage:"
        echo "  device-link left \"<task>\"              Pipeline mode (default)"
        echo "  device-link left --direct \"<task>\"     Claude only"
        echo "  device-link left --ollama \"<task>\"     Ollama only (fastest)"
        echo "  device-link right \"<task>\"             Pipeline mode (default)"
        echo "  device-link both \"<task>\"              Both brains in parallel"
        echo "  device-link status                     Check helper status"
        echo "  device-link results                    Show recent results"
        echo ""
        echo "Pipeline: ChatGPT (reasoning) -> Claude (verification) -> Ollama (execution)"
        echo ""
        echo "Config: ~/.device-link/config"
        ;;
esac
