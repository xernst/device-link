# Device Link

Multi-machine AI agent swarm. Two helper Macs (left brain + right brain) running headless in the corner, triggered from a main Mac on the go.

## Architecture
- **Left brain**: analytical (code review, testing, debugging, security)
- **Right brain**: creative (design, research, planning, docs)
- **Networking**: Tailscale mesh, mosh + tmux for persistence
- **Trigger**: CLI (`device-link left/right/both`) or Claude Code slash commands (`/left-brain`, `/right-brain`)
- **Model stack**: ChatGPT for primary reasoning, Claude for verification, Ollama (local open-source) for execution

## Key Files
- `setup.sh` — run on each helper Mac (`./setup.sh left` or `./setup.sh right`)
- `trigger/trigger.sh` — CLI to send tasks from main Mac
- `left-brain/profile.md` — left brain agent personality
- `right-brain/profile.md` — right brain agent personality
- `shared/healthcheck.sh` — verify helpers are alive

## Commands
```bash
device-link left "run tests"     # send to left brain
device-link right "design auth"  # send to right brain
device-link both "review PR"     # send to both
device-link status               # check health
device-link results              # show recent results
```
