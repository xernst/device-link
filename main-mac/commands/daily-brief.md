# Daily Brief

Generate a morning briefing by pulling status from both helper machines and synthesizing into one actionable summary.

## Instructions

1. **Check helper health** — Run the Device Link healthcheck to see if both brains are online
2. **Fetch recent results** — Pull the latest completed work from both helpers via `~/.device-link/results/`
3. **Calendar context** — Note today's date and any known deadlines
4. **Synthesize** — Combine everything into the briefing format below

## Briefing Format

```markdown
# Daily Brief — [Today's Date]

## Swarm Status
| Brain | Status | Last Activity |
|-------|--------|---------------|
| Left (Analytical) | ONLINE/OFFLINE | [timestamp] |
| Right (Creative) | ONLINE/OFFLINE | [timestamp] |

## Overnight Results
### Left Brain
<summary of any completed analytical work>

### Right Brain
<summary of any completed creative work>

## Pending Tasks
<any queued or in-progress work on either helper>

## Today's Focus
<suggested priorities based on recent work and context>

## Quick Actions
- `/left-brain [task]` — send analytical work
- `/right-brain [task]` — send creative work
- `/both-brains [task]` — send to both
```

## How to Run

From your main Mac terminal or Claude Code:
```
/daily-brief
```

This checks both helpers via Tailscale, pulls results, and produces a structured morning briefing.
