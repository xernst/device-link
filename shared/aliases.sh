# Device Link — shell aliases for all machines

# Trigger scripts (main Mac only — harmless on helpers)
alias device-link='bash "$HOME/.device-link/trigger/trigger.sh"'
alias dl='device-link'
alias dl-left='device-link left'
alias dl-right='device-link right'
alias dl-both='device-link both'
alias dl-status='device-link status'
alias dl-results='device-link results'
alias dl-deploy='device-link deploy'

# Helper management
alias dl-attach-left='mosh helper-left -- tmux attach -t left-brain'
alias dl-attach-right='mosh helper-right -- tmux attach -t right-brain'

# Quick connections
alias ml='mosh helper-left'
alias mr='mosh helper-right'

# Ollama shortcuts
alias ol='ollama list'
alias or='ollama run'

# tmux shortcuts
alias ta='tmux attach -t'
alias tl='tmux ls'
alias tk='tmux kill-session -t'
