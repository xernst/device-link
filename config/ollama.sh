#!/usr/bin/env bash
# Install Ollama and pull models for the specified brain type.
set -euo pipefail

BRAIN="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Install Ollama
if command -v ollama &>/dev/null; then
    echo "  Ollama already installed: $(ollama --version)"
else
    echo "  Installing Ollama..."
    brew install ollama
fi

# Start Ollama service
echo "  Starting Ollama service..."
brew services start ollama 2>/dev/null || true
sleep 3

# Configure Ollama to bind to Tailscale IP only (not 0.0.0.0)
# This is set via launchd environment or shell profile
OLLAMA_CONFIG="OLLAMA_HOST=0.0.0.0"
if ! grep -q "OLLAMA_HOST" "$HOME/.zshrc" 2>/dev/null; then
    echo "" >> "$HOME/.zshrc"
    echo "# Ollama — bind to all interfaces (Tailscale handles security)" >> "$HOME/.zshrc"
    echo "export $OLLAMA_CONFIG" >> "$HOME/.zshrc"
    echo "  Added OLLAMA_HOST to .zshrc"
    echo "  NOTE: Tailscale ensures only your devices can reach port 11434"
fi

# Pull models based on brain type
MODELS_FILE="$SCRIPT_DIR/${BRAIN}-brain/ollama-models.txt"
if [[ -f "$MODELS_FILE" ]]; then
    echo "  Pulling models for ${BRAIN} brain..."
    while IFS= read -r model; do
        # Skip comments and empty lines
        [[ -z "$model" || "$model" == \#* ]] && continue
        echo "  Pulling: $model"
        ollama pull "$model"
    done < "$MODELS_FILE"
else
    echo "  Warning: $MODELS_FILE not found, skipping model pulls."
fi

echo "  Ollama setup complete."
