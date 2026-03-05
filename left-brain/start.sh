#!/usr/bin/env bash
# Start the left-brain agent swarm in tmux.
set -euo pipefail

SESSION="left-brain"
WORK_DIR="$HOME/.device-link/workspace"

mkdir -p "$WORK_DIR"

# Kill existing session if present
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Create new session with main window
tmux new-session -d -s "$SESSION" -n "main" -c "$WORK_DIR"

# Window 1: Ollama service monitor
tmux new-window -t "$SESSION" -n "ollama" -c "$WORK_DIR"
tmux send-keys -t "$SESSION:ollama" "ollama serve 2>&1 | tee $HOME/.device-link/ollama.log" C-m

# Window 2: Ready for incoming tasks (idle)
tmux new-window -t "$SESSION" -n "tasks" -c "$WORK_DIR"
tmux send-keys -t "$SESSION:tasks" "echo 'Left brain ready. Waiting for tasks...'" C-m

# Window 3: System monitor
tmux new-window -t "$SESSION" -n "monitor" -c "$WORK_DIR"
tmux send-keys -t "$SESSION:monitor" "top -l 1 -s 0 | head -20; echo '---'; ollama list 2>/dev/null; echo '---'; tailscale status 2>/dev/null" C-m

# Select the tasks window
tmux select-window -t "$SESSION:tasks"

echo "Left brain started. Session: $SESSION"
echo "Attach with: tmux attach -t $SESSION"
