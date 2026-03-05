#!/usr/bin/env bash
# Device Link — Trigger tasks on helper machines.
#
# Usage:
#   device-link left "run tests on my-app"
#   device-link right "design the auth flow"
#   device-link both "review this PR"
#   device-link status
#   device-link results
#   device-link pull
#   device-link attach <left|right>
#   device-link queue left "task"
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

    # Claude review gate — quick review before delivery
    local review=""
    if [[ $rc -eq 0 ]]; then
        review=$(review_result "$brain" "$task")
    fi

    # Send Telegram notification (review first, then status)
    if type send_telegram &>/dev/null; then
        if [[ $rc -eq 0 ]]; then
            if [[ -n "$review" ]]; then
                send_telegram "Review (${brain}): ${review}"
            fi
            send_telegram "${brain} brain completed: ${task}"
        else
            send_telegram "${brain} brain failed (exit ${rc}): ${task}"
        fi
    fi

    # Log to second brain ledger
    log_to_ledger "$brain" "$task" "$mode" "$rc"

    return $rc
}

review_result() {
    local brain="$1"
    local task="$2"

    # Find the most recent result file for this brain
    local latest_result
    latest_result=$(ls -t "$RESULTS_DIR/${brain}-"*.md 2>/dev/null | head -1)
    [[ -f "$latest_result" ]] || return 0

    local snippet
    snippet=$(head -50 "$latest_result")

    local review_prompt="You are a senior reviewer. Give a 2-3 sentence executive summary of this task result. Flag any issues, gaps, or things that need attention. Be direct and concise.

Task: ${task}
Brain: ${brain}

Result:
${snippet}"

    # Use claude --print for the review (runs locally on main Mac)
    local review_output
    if review_output=$(echo "$review_prompt" | claude --print 2>/dev/null); then
        # Truncate to fit Telegram limits
        echo "${review_output:0:500}"
    fi
}

log_to_ledger() {
    local brain="$1"
    local task="$2"
    local mode="$3"
    local exit_code="$4"
    local vault_dir="$HOME/Documents/second-brain"
    local ledger_dir="$vault_dir/_ledger/tasks"

    # Skip if vault doesn't exist
    [[ -d "$vault_dir" ]] || return 0

    mkdir -p "$ledger_dir"

    local timestamp
    timestamp="$(date +%Y%m%d-%H%M%S)"
    local date_iso
    date_iso="$(date -Iseconds)"
    local status="completed"
    [[ "$exit_code" -ne 0 ]] && status="failed"

    local result_snippet=""
    local result_file="$RESULTS_DIR/${brain}-${timestamp}.md"
    if [[ -f "$result_file" ]]; then
        result_snippet=$(head -5 "$result_file")
    fi

    cat > "$ledger_dir/${timestamp}-${brain}.md" <<EOF
---
brain: ${brain}
task: "${task}"
mode: ${mode}
status: ${status}
timestamp: ${date_iso}
tags: [task-log, from/swarm]
---

# ${brain^} Brain — ${task}

**Status**: ${status}
**Mode**: ${mode}
**Time**: ${date_iso}

## Result Preview
${result_snippet:-"(no output captured)"}
EOF
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

pull_results() {
    echo "Pulling results from helpers..."
    echo ""

    for brain_host in "left:${LEFT_HOST}" "right:${RIGHT_HOST}"; do
        local brain="${brain_host%%:*}"
        local host="${brain_host##*:}"

        printf "%-12s " "${brain} brain:"
        if ssh -o ConnectTimeout=3 "${SSH_USER}@${host}" "test -d ~/.device-link/results" &>/dev/null; then
            rsync -az --ignore-existing \
                "${SSH_USER}@${host}:~/.device-link/results/" \
                "$RESULTS_DIR/" 2>/dev/null
            echo "synced"
        else
            echo "no results directory (or offline)"
        fi
    done

    echo ""
    echo "Local results:"
    ls -t "$RESULTS_DIR"/*.md 2>/dev/null | head -5 | while read -r f; do
        echo "  $(basename "$f")"
    done
}

attach_brain() {
    local brain="$1"
    local host

    case "$brain" in
        left)  host="$LEFT_HOST" ;;
        right) host="$RIGHT_HOST" ;;
        *)
            echo "Usage: device-link attach <left|right>" >&2
            exit 1
            ;;
    esac

    echo "Attaching to ${brain} brain ($host)..."
    if command -v mosh &>/dev/null; then
        exec mosh "${SSH_USER}@${host}" -- tmux attach -t "${brain}-brain" 2>/dev/null \
            || exec mosh "${SSH_USER}@${host}" -- tmux new -s "${brain}-brain"
    else
        exec ssh "${SSH_USER}@${host}" -t "tmux attach -t ${brain}-brain 2>/dev/null \
            || tmux new -s ${brain}-brain"
    fi
}

queue_task() {
    local brain="$1"
    local host="$2"
    local task="$3"
    local mode="$4"
    local timestamp
    timestamp="$(date +%Y%m%d-%H%M%S)"

    local queue_dir="$HOME/.device-link/queue"
    mkdir -p "$queue_dir"

    local queue_file="$queue_dir/${brain}-${timestamp}.task"
    echo "BRAIN=${brain}" > "$queue_file"
    echo "TASK=${task}" >> "$queue_file"
    echo "QUEUED=$(date -Iseconds)" >> "$queue_file"

    echo "Queued: ${brain} brain — ${task}"

    # Fire in background — detach from terminal
    (
        send_task "$host" "$brain" "$task" "$mode" &>/dev/null
        rm -f "$queue_file"
    ) &
    disown

    echo "  Running in background (PID $!)"
}

show_queue() {
    local queue_dir="$HOME/.device-link/queue"
    mkdir -p "$queue_dir"

    echo "Task Queue"
    echo "=========="
    echo ""

    local found=0
    for f in "$queue_dir"/*.task 2>/dev/null; do
        [[ -f "$f" ]] || continue
        found=1
        local brain task queued
        brain=$(grep "^BRAIN=" "$f" | cut -d= -f2)
        task=$(grep "^TASK=" "$f" | cut -d= -f2-)
        queued=$(grep "^QUEUED=" "$f" | cut -d= -f2-)
        echo "  [${brain}] ${task} (queued: ${queued})"
    done

    if [[ "$found" -eq 0 ]]; then
        echo "  No tasks in queue."
    fi
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
    pull)
        pull_results
        ;;
    attach)
        if [[ -z "${1:-}" ]]; then
            echo "Usage: device-link attach <left|right>" >&2
            exit 1
        fi
        attach_brain "$1"
        ;;
    queue)
        BRAIN_TARGET="${1:-}"
        shift || true
        read -r MODE TASK <<< "$(parse_mode_and_task "$@")"
        if [[ -z "$BRAIN_TARGET" || -z "$TASK" ]]; then
            echo "Usage: device-link queue <left|right> [--mode] \"<task>\"" >&2
            exit 1
        fi
        case "$BRAIN_TARGET" in
            left)  queue_task "left" "$LEFT_HOST" "$TASK" "$MODE" ;;
            right) queue_task "right" "$RIGHT_HOST" "$TASK" "$MODE" ;;
            *)     echo "Unknown brain: $BRAIN_TARGET (use left or right)" >&2; exit 1 ;;
        esac
        ;;
    show-queue)
        show_queue
        ;;
    digest)
        bash "$SCRIPT_DIR/digest.sh" "${1:-}"
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
        echo "  device-link pull                       Sync results from helpers"
        echo "  device-link attach <left|right>        Attach to brain tmux session"
        echo "  device-link queue <left|right> \"task\"   Fire-and-forget background task"
        echo "  device-link show-queue                 Show pending background tasks"
        echo "  device-link digest [YYYY-MM-DD]        Generate daily digest"
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
