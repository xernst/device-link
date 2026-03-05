# Device Link

Multi-machine AI agent swarm. Two helper Macs (left brain + right brain) running headless in the corner, triggered from a main Mac on the go.

## Architecture
- **Left brain**: analytical (code review, testing, debugging, security)
- **Right brain**: creative (design, research, planning, docs)
- **Networking**: Tailscale mesh, mosh + tmux for persistence
- **Trigger**: CLI (`device-link left/right/both`), Claude Code slash commands (`/left-brain`, `/right-brain`), or Telegram bot
- **Model stack**: Claude (reasoning) → Ollama (execution, free)
- **Gateway**: OpenClaw on each helper (always-on API, Tailscale-bound, heartbeat + cron + memory flush)
- **Browser**: Pinchtab on each helper (HTTP API for browser control)
- **Notifications**: Telegram bot with Claude review gate before delivery
- **Second Brain**: Obsidian vault at `~/Documents/second-brain/` (task ledger + knowledge base)
- **Dashboard**: Mission Control for monitoring

## Brain Toolkits

### Left Brain (Analytical)
**7 Agents**: code-reviewer, security-reviewer, tdd-guide, build-error-resolver, refactor-cleaner, database-reviewer, e2e-runner
**8 Commands**: /code-review, /tdd, /build-fix, /verify, /test-coverage, /refactor-clean, /e2e, /last30days
**4 Skills**: verification-loop, security-review, tdd-workflow, api-design
**3 Rules**: security, agents, development-workflow

### Right Brain (Creative)
**6 Agents**: planner, architect, researcher, prd-creator, doc-updater, chief-of-staff
**5 Commands**: /plan, /research, /prd, /architect, /last30days
**3 Skills**: market-research, autonomous-loops, content-engine
**3 Rules**: agents, development-workflow, creative-principles

## Key Files
- `setup.sh` — run on each helper Mac (`./setup.sh left` or `./setup.sh right`)
- `main-mac/setup.sh` — one-shot main Mac installer
- `config/claude-code.sh` — installs full toolkit (agents, skills, rules, commands)
- `config/openclaw.sh` — install/update OpenClaw gateway per helper
- `config/pinchtab.sh` — install/configure Pinchtab browser control per helper
- `trigger/trigger.sh` — CLI to send tasks from main Mac (with review gate)
- `trigger/pipeline.sh` — 2-tier pipeline with bidirectional fallback
- `trigger/digest.sh` — daily task digest generator for second brain
- `telegram/telegram-bridge.py` — Telegram bot for mobile control
- `telegram/notify-telegram.sh` — push notification helper
- `left-brain/profile.md` — left brain agent personality + agent roster
- `right-brain/profile.md` — right brain agent personality + agent roster
- `shared/healthcheck.sh` — verify helpers (SSH, tmux, Ollama, Claude, OpenClaw, Pinchtab)

## Commands
```bash
# Task dispatch
device-link left "run tests"              # pipeline mode (default)
device-link left --direct "run tests"     # claude only
device-link left --ollama "run tests"     # ollama only (fastest)
device-link left --openclaw "run tests"   # via openclaw gateway
device-link right "design auth"           # send to right brain
device-link both "review PR"              # send to both

# Monitoring
device-link status                        # check helper health
device-link results                       # show recent results
device-link pull                          # sync results from helpers
device-link digest                        # generate daily task summary

# Session management
device-link attach left                   # attach to left brain tmux
device-link attach right                  # attach to right brain tmux

# Background tasks
device-link queue left "run tests"        # fire-and-forget
device-link show-queue                    # show pending tasks
```

## Second Brain Slash Commands
```
/second-brain-interview    Personalize your vault's CLAUDE.md
/inbox-triage              Process inbox to zero (route notes)
/connection-finder <topic> Find hidden connections in Galaxy
/writing-partner <topic>   Draft content from vault notes
/journal-analysis          Analyze journal patterns
/book-coach <title>        Process book highlights into knowledge
/token-dashboard           Show token usage across all configs
/token-audit               Audit and optimize token usage
```

## OpenClaw Overnight System
Each helper runs 4 systems that make OpenClaw useful overnight:

1. **Heartbeat** — every 30 min, 8am-11pm. Checks for failed crons, disk, Ollama, Pinchtab. Quiet outside hours.
2. **Memory flush** — before every context compaction, writes learnings to `~/.openclaw/memory/daily/YYYY-MM-DD.md`. Consolidated nightly.
3. **Cron jobs** — heavy tasks (result scanning, memory consolidation) run in isolated sessions. Don't bloat main context.
4. **Fallback alerts** — heartbeat checks `~/.device-link/cron/last-run.log` for failed jobs. Alerts via Telegram before they stack up.

## Review Gate
Every task result goes through a Claude review before Telegram delivery. The review is a 2-3 sentence executive summary flagging any issues. Sent to Telegram before the completion notification.

## Telegram
Send tasks from your phone: `left: run tests` or `right: design auth`
Commands: `/status`, `/brief`, `/results`, `/help`
