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
# Configuration:
#   Set these in ~/.device-link/config or as environment variables:
#     DEVICE_LINK_LEFT_HOST    — Tailscale hostname/IP of left brain
#     DEVICE_LINK_RIGHT_HOST   — Tailscale hostname/IP of right brain
#     DEVICE_LINK_USER         — SSH username (defaults to current user)
#     DEVICE_LINK_PROJECT      — Project path on helpers (defaults to cwd name)

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

mkdir -p "$RESULTS_DIR"

# --- Functions ---

send_task() {
    local host="$1"
    local brain="$2"
    local task="$3"
    local timestamp
    timestamp="$(date +%Y%m%d-%H%M%S)"
    local result_file="$RESULTS_DIR/${brain}-${timestamp}.md"

    echo "Sending to ${brain} brain ($host)..."

    # SSH into the helper, run claude in print mode, capture output
    ssh -o ConnectTimeout=5 "${SSH_USER}@${host}" \
        "cd ~/.device-link/workspace/${PROJECT} 2>/dev/null || cd ~/.device-link/workspace; \
         claude --print \"${task}\"" \
        > "$result_file" 2>&1

    local exit_code=$?
    if [[ $exit_code -eq 0 ]]; then
        echo "Done. Results saved to: $result_file"
        echo ""
        cat "$result_file"
    else
        echo "Error: Failed to reach ${brain} brain at ${host}" >&2
        echo "  Check: tailscale status" >&2
        echo "  Check: ssh ${SSH_USER}@${host}" >&2
        return 1
    fi
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

    # Show the 5 most recent result files
    ls -t "$RESULTS_DIR"/*.md 2>/dev/null | head -5 | while read -r f; do
        echo "--- $(basename "$f") ---"
        head -20 "$f"
        echo ""
    done
}

# --- Main ---

COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    left)
        TASK="${1:-}"
        if [[ -z "$TASK" ]]; then
            echo "Usage: device-link left \"<task description>\"" >&2
            exit 1
        fi
        send_task "$LEFT_HOST" "left" "$TASK"
        ;;
    right)
        TASK="${1:-}"
        if [[ -z "$TASK" ]]; then
            echo "Usage: device-link right \"<task description>\"" >&2
            exit 1
        fi
        send_task "$RIGHT_HOST" "right" "$TASK"
        ;;
    both)
        TASK="${1:-}"
        if [[ -z "$TASK" ]]; then
            echo "Usage: device-link both \"<task description>\"" >&2
            exit 1
        fi
        # Run both in parallel
        send_task "$LEFT_HOST" "left" "$TASK" &
        LEFT_PID=$!
        send_task "$RIGHT_HOST" "right" "$TASK" &
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
        echo "  device-link left \"<task>\"    Send task to left brain (analytical)"
        echo "  device-link right \"<task>\"   Send task to right brain (creative)"
        echo "  device-link both \"<task>\"    Send task to both in parallel"
        echo "  device-link status           Check helper status"
        echo "  device-link results          Show recent results"
        echo ""
        echo "Config: ~/.device-link/config"
        ;;
esac
