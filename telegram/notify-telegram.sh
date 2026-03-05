#!/usr/bin/env bash
# Device Link — Telegram push notification helper.
# Source this file from trigger.sh or call directly.
#
# Usage:
#   source ~/.device-link/telegram/notify-telegram.sh
#   send_telegram "Task completed: run tests"
#
# Or standalone:
#   bash notify-telegram.sh "Your message here"
#
# Requires:
#   TELEGRAM_BOT_TOKEN — your bot token from @BotFather
#   TELEGRAM_CHAT_ID   — your personal chat ID

TELEGRAM_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT="${TELEGRAM_CHAT_ID:-}"

send_telegram() {
    local message="$1"

    if [[ -z "$TELEGRAM_TOKEN" || -z "$TELEGRAM_CHAT" ]]; then
        # Silent fail if not configured — don't break trigger.sh
        return 0
    fi

    curl -s -X POST \
        "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT}" \
        -d text="${message}" \
        > /dev/null 2>&1
}

# If called directly with an argument, send it
if [[ "${BASH_SOURCE[0]}" == "${0}" ]] && [[ -n "${1:-}" ]]; then
    send_telegram "$1"
fi
