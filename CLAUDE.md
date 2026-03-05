# Device Link

Multi-machine AI agent swarm. Two helper Macs (left brain + right brain) running headless in the corner, triggered from a main Mac on the go.

## Architecture
- **Left brain**: analytical (code review, testing, debugging, security)
- **Right brain**: creative (design, research, planning, docs)
- **Networking**: Tailscale mesh, mosh + tmux for persistence
- **Trigger**: CLI (`device-link left/right/both`) or Claude Code slash commands (`/left-brain`, `/right-brain`)
- **Model stack**: Claude (reasoning) → Ollama (execution, free)

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
- `config/claude-code.sh` — installs full toolkit (agents, skills, rules, commands)
- `trigger/trigger.sh` — CLI to send tasks from main Mac
- `left-brain/profile.md` — left brain agent personality + agent roster
- `right-brain/profile.md` — right brain agent personality + agent roster
- `shared/healthcheck.sh` — verify helpers are alive

## Commands
```bash
device-link left "run tests"     # send to left brain
device-link right "design auth"  # send to right brain
device-link both "review PR"     # send to both
device-link status               # check health
device-link results              # show recent results
```
