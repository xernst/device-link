#!/usr/bin/env bash
# Install tmux and apply Device Link config.
set -euo pipefail

TMUX_CONF_SRC="${1:-}"

if command -v tmux &>/dev/null; then
    echo "  tmux already installed: $(tmux -V)"
else
    echo "  Installing tmux..."
    brew install tmux
fi

# Copy tmux config
if [[ -n "$TMUX_CONF_SRC" && -f "$TMUX_CONF_SRC" ]]; then
    cp "$TMUX_CONF_SRC" "$HOME/.tmux.conf"
    echo "  Installed tmux config to ~/.tmux.conf"
fi

echo "  tmux setup complete."
