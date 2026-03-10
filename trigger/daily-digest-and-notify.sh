#!/usr/bin/env bash
# Device Link — Daily digest + Telegram notification wrapper
# Runs digest.sh, then sends a summary to Telegram.
# Called by LaunchAgent at 7:45 AM daily.

set -euo pipefail

DIGEST_SCRIPT="$HOME/.device-link/trigger/digest.sh"
NOTIFY_SCRIPT="$HOME/.device-link/telegram/notify-telegram.sh"
CONFIG_FILE="$HOME/.device-link/config"

# Load config for Telegram credentials
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
export TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# Run yesterday's digest (since this runs at 7:45 AM, yesterday's data is complete)
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
RESULT=$(bash "$DIGEST_SCRIPT" "$YESTERDAY" 2>&1 || true)

# Also run today's (in case there are overnight entries)
TODAY=$(date +%Y-%m-%d)
RESULT_TODAY=$(bash "$DIGEST_SCRIPT" "$TODAY" 2>&1 || true)

# Build notification message
MSG=""
if [[ -n "$RESULT" && "$RESULT" != *"No tasks"* ]]; then
    MSG+="📊 Yesterday ($YESTERDAY): $RESULT"
fi
if [[ -n "$RESULT_TODAY" && "$RESULT_TODAY" != *"No tasks"* ]]; then
    [[ -n "$MSG" ]] && MSG+=$'\n'
    MSG+="📊 Today ($TODAY): $RESULT_TODAY"
fi

# Send notification if there's anything to report
if [[ -n "$MSG" ]]; then
    bash "$NOTIFY_SCRIPT" "🗓 Daily Digest
$MSG

Use /brief in Telegram for the full morning briefing."
fi

echo "$RESULT"
echo "$RESULT_TODAY"
