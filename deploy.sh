#!/usr/bin/env bash
# Device Link — Remote Deploy
# Deploy Device Link to helper Macs from your main Mac.
#
# Usage:
#   ./deploy.sh left     # Deploy to left brain helper
#   ./deploy.sh right    # Deploy to right brain helper
#   ./deploy.sh all      # Deploy to both helpers

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_URL="https://github.com/xernst/device-link.git"
CONFIG_FILE="$HOME/.device-link/config"

# Load config
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
else
    echo "Error: Config file not found at $CONFIG_FILE" >&2
    echo "Run main-mac/setup.sh first, or create it manually." >&2
    echo "See shared/config.example for the template." >&2
    exit 1
fi

LEFT_HOST="${DEVICE_LINK_LEFT_HOST:-helper-left}"
RIGHT_HOST="${DEVICE_LINK_RIGHT_HOST:-helper-right}"
SSH_USER="${DEVICE_LINK_USER:-$(whoami)}"

TARGET="${1:-}"

if [[ "$TARGET" != "left" && "$TARGET" != "right" && "$TARGET" != "all" ]]; then
    echo "Usage: $0 <left|right|all>"
    echo ""
    echo "  left   — Deploy to left brain helper ($LEFT_HOST)"
    echo "  right  — Deploy to right brain helper ($RIGHT_HOST)"
    echo "  all    — Deploy to both helpers"
    exit 1
fi

# --- Functions ---

check_ssh() {
    local host="$1"
    local label="$2"

    printf "  Checking SSH to %s (%s)... " "$label" "$host"
    if ssh -o ConnectTimeout=5 -o BatchMode=yes "${SSH_USER}@${host}" "echo ok" &>/dev/null; then
        echo "connected."
        return 0
    else
        echo "FAILED"
        echo ""
        echo "  Cannot reach ${host}. Possible causes:" >&2
        echo "    - Helper is powered off or sleeping" >&2
        echo "    - Tailscale is not running (try: tailscale up)" >&2
        echo "    - SSH key not authorized (try: ssh-copy-id ${SSH_USER}@${host})" >&2
        echo "    - Wrong hostname in ~/.device-link/config" >&2
        return 1
    fi
}

deploy_to() {
    local brain="$1"
    local host="$2"

    echo "======================================"
    echo " Deploying ${brain^^} BRAIN to ${host}"
    echo " $(date)"
    echo "======================================"
    echo ""

    # Step 1: Check connectivity
    if ! check_ssh "$host" "$brain brain"; then
        return 1
    fi

    # Step 2: Get the repo onto the helper
    echo "  Syncing device-link repo..."

    local has_git
    has_git=$(ssh -o ConnectTimeout=5 "${SSH_USER}@${host}" "command -v git &>/dev/null && echo yes || echo no")

    if [[ "$has_git" == "yes" ]]; then
        # Git available — clone or pull
        ssh -o ConnectTimeout=5 "${SSH_USER}@${host}" bash -s <<'REMOTE_GIT'
            set -euo pipefail
            REPO_URL="https://github.com/xernst/device-link.git"
            REMOTE_DIR="$HOME/device-link"

            if [[ -d "$REMOTE_DIR/.git" ]]; then
                echo "  Updating existing repo..."
                cd "$REMOTE_DIR"
                git fetch origin
                git reset --hard origin/main
                echo "  Updated to $(git rev-parse --short HEAD)"
            else
                echo "  Cloning fresh..."
                rm -rf "$REMOTE_DIR"
                git clone "$REPO_URL" "$REMOTE_DIR"
                echo "  Cloned at $(cd "$REMOTE_DIR" && git rev-parse --short HEAD)"
            fi
REMOTE_GIT
    else
        # No git — rsync fallback (setup.sh will install Homebrew+git)
        echo "  git not found on ${host} — using rsync to bootstrap..."
        rsync -az --delete \
            --exclude '.git' \
            --exclude '.DS_Store' \
            --exclude 'node_modules' \
            "${SCRIPT_DIR}/" \
            "${SSH_USER}@${host}:~/device-link/"
        echo "  Synced via rsync."
    fi

    # Step 3: Set permissions
    echo "  Setting permissions..."
    ssh -o ConnectTimeout=5 "${SSH_USER}@${host}" \
        "chmod +x ~/device-link/setup.sh ~/device-link/config/*.sh ~/device-link/left-brain/start.sh ~/device-link/right-brain/start.sh ~/device-link/trigger/*.sh ~/device-link/shared/healthcheck.sh"

    # Step 4: Run setup.sh
    echo ""
    echo "  Running setup.sh ${brain}..."
    echo "  ----------------------------------------"
    ssh -o ConnectTimeout=5 -t "${SSH_USER}@${host}" \
        "cd ~/device-link && ./setup.sh ${brain}" 2>&1
    local rc=$?
    echo "  ----------------------------------------"

    if [[ $rc -eq 0 ]]; then
        echo ""
        echo "  Deploy to ${brain} brain: SUCCESS"
    else
        echo ""
        echo "  Deploy to ${brain} brain: FAILED (exit code ${rc})" >&2
    fi

    return $rc
}

# --- Main ---

echo ""
echo "Device Link Remote Deploy"
echo "========================="
echo "Config: $CONFIG_FILE"
echo "User:   $SSH_USER"
echo ""

DEPLOY_FAILED=0

case "$TARGET" in
    left)
        deploy_to "left" "$LEFT_HOST" || DEPLOY_FAILED=1
        ;;
    right)
        deploy_to "right" "$RIGHT_HOST" || DEPLOY_FAILED=1
        ;;
    all)
        echo "Deploying to both helpers (sequentially)..."
        echo ""
        deploy_to "left" "$LEFT_HOST" || DEPLOY_FAILED=1
        echo ""
        deploy_to "right" "$RIGHT_HOST" || DEPLOY_FAILED=1
        ;;
esac

echo ""
echo "======================================"
if [[ $DEPLOY_FAILED -eq 0 ]]; then
    echo " All deployments succeeded."
else
    echo " One or more deployments failed." >&2
fi
echo "======================================"
echo ""

# Optional: Telegram notification
TELEGRAM_NOTIFY="$HOME/.device-link/telegram/notify-telegram.sh"
if [[ -f "$TELEGRAM_NOTIFY" ]]; then
    if [[ -f "$HOME/.device-link/telegram/.env" ]]; then
        set +u; source "$HOME/.device-link/telegram/.env"; set -u
    fi
    source "$TELEGRAM_NOTIFY"
    if [[ $DEPLOY_FAILED -eq 0 ]]; then
        send_telegram "Deploy ${TARGET}: SUCCESS" 2>/dev/null || true
    else
        send_telegram "Deploy ${TARGET}: FAILED" 2>/dev/null || true
    fi
fi

exit $DEPLOY_FAILED
