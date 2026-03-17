#!/usr/bin/env bash
# Device Link — Install & configure JobOps on a helper Mac.
# Self-hosted job hunting automation: scrape, score, tailor, track.
#
# Usage:
#   bash config/jobops.sh <left|right>
#
# Requires: Docker (installed via Homebrew if missing)

set -euo pipefail

BRAIN="${1:-}"
if [[ -z "$BRAIN" ]]; then
    echo "Usage: bash config/jobops.sh <left|right>" >&2
    exit 1
fi

echo ""
echo "=== JobOps — ${BRAIN} brain ==="
echo ""

JOBOPS_DIR="$HOME/.jobops"
JOBOPS_PORT="${JOBOPS_PORT:-3005}"

# --- Install Docker if missing ---

if ! command -v docker &>/dev/null; then
    echo "Installing Docker via Homebrew..."
    brew install --cask docker
    echo "Starting Docker Desktop..."
    open -a Docker
    echo "Waiting for Docker to start (up to 120s)..."
    for i in $(seq 1 24); do
        if docker info &>/dev/null 2>&1; then
            echo "Docker is ready."
            break
        fi
        if [[ $i -eq 24 ]]; then
            echo "Error: Docker did not start in time." >&2
            echo "Open Docker Desktop manually, then re-run this script." >&2
            exit 1
        fi
        sleep 5
    done
else
    echo "Docker already installed."
    if ! docker info &>/dev/null 2>&1; then
        echo "Docker is installed but not running. Starting..."
        open -a Docker
        for i in $(seq 1 24); do
            if docker info &>/dev/null 2>&1; then
                echo "Docker is ready."
                break
            fi
            if [[ $i -eq 24 ]]; then
                echo "Error: Docker did not start in time." >&2
                exit 1
            fi
            sleep 5
        done
    fi
fi

# --- Clone/update JobOps ---

if [[ -d "$JOBOPS_DIR/.git" ]]; then
    echo "Updating existing JobOps install..."
    cd "$JOBOPS_DIR"
    git pull origin main 2>/dev/null || git pull
    echo "Updated to $(git rev-parse --short HEAD)"
else
    echo "Cloning JobOps..."
    rm -rf "$JOBOPS_DIR"
    git clone https://github.com/DaKheera47/job-ops.git "$JOBOPS_DIR"
    echo "Cloned at $(cd "$JOBOPS_DIR" && git rev-parse --short HEAD)"
fi

cd "$JOBOPS_DIR"

# --- Launch with Docker Compose ---

echo "Starting JobOps with Docker Compose..."
docker compose down 2>/dev/null || true
docker compose up -d

echo ""
echo "=== JobOps Setup Complete ==="
echo ""
echo "  Dashboard:  http://localhost:${JOBOPS_PORT}"
echo "  Data dir:   ${JOBOPS_DIR}"
echo "  Logs:       docker compose -f ${JOBOPS_DIR}/docker-compose.yml logs -f"
echo ""
echo "  Open the dashboard to complete onboarding (LLM config, job criteria, resume)."
echo "  Tip: Use Ollama (already running on this helper) as the LLM endpoint:"
echo "       http://localhost:11434"
echo ""
