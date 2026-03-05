#!/usr/bin/env bash
# Install and configure Tailscale for secure mesh networking.
set -euo pipefail

if command -v tailscale &>/dev/null; then
    echo "  Tailscale already installed: $(tailscale version | head -1)"
    return 0 2>/dev/null || exit 0
fi

# Install via Mac App Store CLI or Homebrew
if command -v mas &>/dev/null; then
    echo "  Installing Tailscale via Mac App Store..."
    mas install 1475387142
else
    echo "  Installing Tailscale via Homebrew..."
    brew install --cask tailscale
fi

echo "  Tailscale installed."
echo "  Run 'tailscale up' to authenticate after setup completes."
