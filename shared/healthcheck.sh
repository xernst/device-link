#!/usr/bin/env bash
# Device Link — Health check for all helpers.
# Run from main Mac to verify both brains are alive and ready.

set -euo pipefail

CONFIG_FILE="$HOME/.device-link/config"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

LEFT_HOST="${DEVICE_LINK_LEFT_HOST:-helper-left}"
RIGHT_HOST="${DEVICE_LINK_RIGHT_HOST:-helper-right}"
SSH_USER="${DEVICE_LINK_USER:-$(whoami)}"

echo "Device Link Health Check"
echo "========================"
echo ""

check_helper() {
    local brain="$1"
    local host="$2"
    local status="OK"
    local details=""

    printf "%-14s" "${brain} brain:"

    # Check SSH connectivity
    if ! ssh -o ConnectTimeout=3 "${SSH_USER}@${host}" "echo ok" &>/dev/null; then
        echo "OFFLINE (cannot reach ${host})"
        return
    fi

    # Check tmux session
    if ssh -o ConnectTimeout=3 "${SSH_USER}@${host}" "tmux has-session -t ${brain}-brain 2>/dev/null"; then
        details+="tmux=yes "
    else
        details+="tmux=NO "
        status="DEGRADED"
    fi

    # Check Ollama
    if ssh -o ConnectTimeout=3 "${SSH_USER}@${host}" "curl -s http://localhost:11434/api/tags >/dev/null 2>&1"; then
        local model_count
        model_count=$(ssh -o ConnectTimeout=3 "${SSH_USER}@${host}" "ollama list 2>/dev/null | tail -n +2 | wc -l | tr -d ' '")
        details+="ollama=yes(${model_count}models) "
    else
        details+="ollama=NO "
        status="DEGRADED"
    fi

    # Check Claude Code
    if ssh -o ConnectTimeout=3 "${SSH_USER}@${host}" "command -v claude >/dev/null 2>&1"; then
        details+="claude=yes "
    else
        details+="claude=NO "
        status="DEGRADED"
    fi

    # Check Tailscale
    local ts_ip
    ts_ip=$(ssh -o ConnectTimeout=3 "${SSH_USER}@${host}" "tailscale ip -4 2>/dev/null" || echo "none")
    details+="tailscale=${ts_ip} "

    # Check OpenClaw gateway
    local openclaw_port="${OPENCLAW_PORT:-18789}"
    if ssh -o ConnectTimeout=3 "${SSH_USER}@${host}" "curl -s -o /dev/null -w '%{http_code}' http://localhost:${openclaw_port}/v1/models 2>/dev/null" | grep -q "200"; then
        details+="openclaw=yes "
    else
        details+="openclaw=NO "
    fi

    # Check disk space
    local disk_free
    disk_free=$(ssh -o ConnectTimeout=3 "${SSH_USER}@${host}" "df -h / | tail -1 | awk '{print \$4}'")
    details+="disk=${disk_free} "

    echo "${status}  ${details}"
}

check_helper "left" "$LEFT_HOST"
check_helper "right" "$RIGHT_HOST"

echo ""
echo "Tailscale mesh:"
tailscale status 2>/dev/null | head -10 || echo "  Tailscale not running on this machine"
