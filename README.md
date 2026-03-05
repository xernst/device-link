# Device Link

A multi-machine AI agent swarm for macOS. Two helper laptops run headless in the corner of your room, acting as your "left brain" (analytical) and "right brain" (creative). Trigger tasks from your main Mac — from anywhere.

## How It Works

```
Main Mac (on the go)
    |
    | Tailscale encrypted mesh
    |
    +--- Left Brain (analytical helper)
    |    Code review, testing, debugging, security
    |    ChatGPT reasoning -> Claude verification -> Ollama execution
    |
    +--- Right Brain (creative helper)
         Design, research, planning, documentation
         ChatGPT reasoning -> Claude verification -> Ollama execution
```

### Model Stack
- **ChatGPT** (paid plan) — primary reasoning and task planning
- **Claude** — verification and quality checks on ChatGPT's output
- **Ollama** (local, open-source) — fast execution of routine tasks

## Quick Start

### 1. Set up helpers

Copy the `device-link/` folder to each helper Mac via USB, AirDrop, or git clone.

On the first helper:
```bash
cd device-link
chmod +x setup.sh config/*.sh left-brain/start.sh right-brain/start.sh trigger/*.sh shared/healthcheck.sh
./setup.sh left
```

On the second helper:
```bash
cd device-link
chmod +x setup.sh config/*.sh left-brain/start.sh right-brain/start.sh trigger/*.sh shared/healthcheck.sh
./setup.sh right
```

### 2. Connect Tailscale

On each machine (including your main Mac):
```bash
tailscale up
```

Sign in with the same Tailscale account on all three machines.

### 3. Configure your main Mac

Create `~/.device-link/config`:
```bash
mkdir -p ~/.device-link
cat > ~/.device-link/config << 'EOF'
DEVICE_LINK_LEFT_HOST=helper-left
DEVICE_LINK_RIGHT_HOST=helper-right
DEVICE_LINK_USER=yourusername
EOF
```

Copy the trigger scripts:
```bash
cp -r trigger/ ~/.device-link/trigger/
```

### 4. Use it

From terminal:
```bash
device-link left "run all tests on my-app and report failures"
device-link right "design the authentication system for my-app"
device-link both "review PR #42 from all angles"
device-link status
```

From Claude Code:
```
/left-brain run all tests and report failures
/right-brain design the authentication system
/both-brains review this PR from all angles
/swarm-status
```

## What Gets Installed on Helpers

- **Tailscale** — encrypted mesh VPN (no ports exposed)
- **Ollama** — local LLM inference
- **mosh** — resilient remote shell
- **tmux** — persistent terminal sessions
- **Claude Code** — AI agent (requires API key)
- **LaunchAgent** — auto-starts the brain on login

## Security

- All traffic encrypted via Tailscale (WireGuard)
- SSH key auth only (no passwords)
- Ollama accessible only within Tailscale mesh
- No ports exposed to the public internet
- Git is the sync mechanism (no direct filesystem sharing)

## Customization

### Change Ollama models

Edit `left-brain/ollama-models.txt` or `right-brain/ollama-models.txt`, then re-run:
```bash
bash config/ollama.sh left   # or right
```

### Modify brain personalities

Edit `left-brain/profile.md` or `right-brain/profile.md`. These define how each brain approaches tasks.

## Requirements

- macOS on all machines
- Same Tailscale account on all machines
- Claude Code API key (for Claude-powered tasks)
- ChatGPT Plus subscription (for primary reasoning)
- Homebrew (installed automatically if missing)
