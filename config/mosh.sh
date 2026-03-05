#!/usr/bin/env bash
# Install mosh for resilient remote connections.
set -euo pipefail

if command -v mosh &>/dev/null; then
    echo "  mosh already installed."
    return 0 2>/dev/null || exit 0
fi

echo "  Installing mosh..."
brew install mosh

# Enable Remote Login (SSH) if not already enabled
if ! systemsetup -getremotelogin 2>/dev/null | grep -q "On"; then
    echo "  Enabling Remote Login (SSH)..."
    sudo systemsetup -setremotelogin on
fi

echo "  mosh installed."
echo "  Connect from main Mac: mosh <tailscale-hostname>"
