# Daily Brief — Main Mac Command

Generate a morning briefing by pulling status from both helper machines.

## What It Does

1. Checks if both brains (left + right) are online via Tailscale
2. Fetches recent results from `~/.device-link/results/`
3. Checks Mission Control dashboard status (if running)
4. Synthesizes everything into one actionable morning brief

## Output Format

```
# Daily Brief — [Date]

## Swarm Status
| Brain | Status | Last Activity |
|-------|--------|---------------|
| Left  | ONLINE | [time]        |
| Right | ONLINE | [time]        |

## Overnight Results
[Summary of completed work from both helpers]

## Pending Tasks
[Queued or in-progress work]

## Today's Focus
[Suggested priorities]

## Quick Actions
- /left-brain [task]
- /right-brain [task]
- /both-brains [task]
```

## Installation

This command is installed to `~/.claude/commands/daily-brief.md` on your main Mac.

```bash
# Run from Claude Code:
/daily-brief

# Or from terminal:
claude "/daily-brief"
```
