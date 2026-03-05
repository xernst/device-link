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
#   --pipeline    Claude reasoning -> Ollama execution [default]
#   --direct      Claude only (skip Ollama)
#   --ollama      Ollama only (fastest, free, no Claude)
#   --openclaw    Via OpenClaw gateway (always-on, API-driven)
#
# Examples:
#   device-link left "run tests"                  # uses pipeline (default)
#   device-link left --direct "run tests"         # claude only
#   device-link left --ollama "run tests"         # ollama only
#   device-link left --openclaw "run tests"       # via openclaw gateway
#
# Configuration:
#   Set these in ~/.device-link/config or as environment variables:
#     DEVICE_LINK_LEFT_HOST         — Tailscale hostname/IP of left brain
#     DEVICE_LINK_RIGHT_HOST        — Tailscale hostname/IP of right brain
#     DEVICE_LINK_USER              — SSH username (defaults to current user)
#     DEVICE_LINK_PROJECT           — Project path on helpers (defaults to cwd name)
#     DEVICE_LINK_MODE              — Default mode: pipeline|direct|ollama|openclaw
#     DEVICE_LINK_OLLAMA_MODEL_LEFT — Ollama model for left brain
#     DEVICE_LINK_OLLAMA_MODEL_RIGHT— Ollama model for right brain
#     OPENCLAW_GATEWAY_TOKEN        — Auth token for OpenClaw gateways
#     OPENCLAW_PORT                 — OpenClaw gateway port (default: 18789)

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
OPENCLAW_PORT="${OPENCLAW_PORT:-18789}"
OPENCLAW_TOKEN="${OPENCLAW_GATEWAY_TOKEN:-}"

mkdir -p "$RESULTS_DIR"

# Source Telegram notification helper if available
TELEGRAM_NOTIFY="$HOME/.device-link/telegram/notify-telegram.sh"
if [[ -f "$TELEGRAM_NOTIFY" ]]; then
    # Load env for Telegram credentials
    if [[ -f "$HOME/.device-link/telegram/.env" ]]; then
        set +u; source "$HOME/.device-link/telegram/.env"; set -u
    fi
    source "$TELEGRAM_NOTIFY"
fi

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

send_task_openclaw() {
    local host="$1"
    local brain="$2"
    local task="$3"
    local timestamp
    timestamp="$(date +%Y%m%d-%H%M%S)"
    local result_file="$RESULTS_DIR/${brain}-${timestamp}.md"

    if [[ -z "$OPENCLAW_TOKEN" ]]; then
        echo "Error: OPENCLAW_GATEWAY_TOKEN not set. Run 'openclaw config get gateway.auth.token' on the helper." >&2
        return 1
    fi

    echo "[openclaw] Sending to ${brain} brain ($host:$OPENCLAW_PORT)..."

    local response
    response=$(curl -s --max-time 300 \
        "http://${host}:${OPENCLAW_PORT}/v1/chat/completions" \
        -H "Authorization: Bearer ${OPENCLAW_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
            --arg content "$task" \
            --arg session "device-link-${brain}-${timestamp}" \
            '{model: "openclaw", stream: false, messages: [{role: "user", content: $content}], user: $session}')")

    local content
    content=$(echo "$response" | jq -r '.choices[0].message.content // empty')

    if [[ -n "$content" ]]; then
        echo "$content" > "$result_file"
        echo "Done. Results: $result_file"
        echo ""
        cat "$result_file"
    else
        local error
        error=$(echo "$response" | jq -r '.error.message // empty')
        echo "Error: OpenClaw returned empty response from ${host}" >&2
        [[ -n "$error" ]] && echo "  $error" >&2
        return 1
    fi
}

send_task() {
    local host="$1"
    local brain="$2"
    local task="$3"
    local mode="$4"

    local rc=0
    case "$mode" in
        pipeline)  send_task_pipeline "$host" "$brain" "$task" || rc=$? ;;
        direct)    send_task_direct "$host" "$brain" "$task" || rc=$? ;;
        ollama)    send_task_ollama "$host" "$brain" "$task" || rc=$? ;;
        openclaw)  send_task_openclaw "$host" "$brain" "$task" || rc=$? ;;
        *)         send_task_pipeline "$host" "$brain" "$task" || rc=$? ;;
    esac

    # Send Telegram notification
    if type send_telegram &>/dev/null; then
        if [[ $rc -eq 0 ]]; then
            send_telegram "${brain} brain completed: ${task}"
        else
            send_telegram "${brain} brain failed (exit ${rc}): ${task}"
        fi
    fi

    return $rc
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
            --openclaw)  mode="openclaw"; shift ;;
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
            echo "Usage: device-link left [--pipeline|--direct|--ollama|--openclaw] \"<task>\"" >&2
            exit 1
        fi
        send_task "$LEFT_HOST" "left" "$TASK" "$MODE"
        ;;
    right)
        read -r MODE TASK <<< "$(parse_mode_and_task "$@")"
        if [[ -z "$TASK" ]]; then
            echo "Usage: device-link right [--pipeline|--direct|--ollama|--openclaw] \"<task>\"" >&2
            exit 1
        fi
        send_task "$RIGHT_HOST" "right" "$TASK" "$MODE"
        ;;
    both)
        read -r MODE TASK <<< "$(parse_mode_and_task "$@")"
        if [[ -z "$TASK" ]]; then
            echo "Usage: device-link both [--pipeline|--direct|--ollama|--openclaw] \"<task>\"" >&2
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
        echo "  device-link left --openclaw \"<task>\"   Via OpenClaw gateway"
        echo "  device-link right \"<task>\"             Pipeline mode (default)"
        echo "  device-link both \"<task>\"              Both brains in parallel"
        echo "  device-link status                     Check helper status"
        echo "  device-link results                    Show recent results"
        echo ""
        echo "Modes:"
        echo "  pipeline  — Claude reasoning -> Ollama execution [default]"
        echo "  direct    — Claude only (skip Ollama)"
        echo "  ollama    — Ollama only (fastest, free)"
        echo "  openclaw  — Via OpenClaw gateway (always-on, API-driven)"
        echo ""
        echo "Config: ~/.device-link/config"
        ;;
esac
