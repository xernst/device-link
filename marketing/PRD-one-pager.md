# DualBrain — MVP Product Requirements Document

**Product**: DualBrain — Multi-Machine AI Agent Swarm
**Version**: MVP v1.0 | **Date**: March 2026 | **Owner**: Product

---

## Problem

Solo developers and small teams waste hours context-switching between analytical work (code review, testing, debugging) and creative work (design, research, planning, docs). AI assistants help, but they run on a single machine, lose context between sessions, and can't work autonomously overnight.

## Solution

DualBrain turns two spare Macs into an always-on AI ops team with specialized brains:

- **Left Brain** (Analytical): Code review, security audits, TDD, build fixes, E2E testing
- **Right Brain** (Creative): Planning, architecture, research, PRDs, documentation

Triggered from your main Mac via CLI, Claude Code, or Telegram — with results reviewed by AI before delivery.

## Target User

Solo developers, indie hackers, and small engineering teams (1-5 people) who own multiple Macs and want to maximize their hardware investment with autonomous AI agents.

## MVP Scope

| Feature | Description | Priority |
|---------|-------------|----------|
| Dual-brain dispatch | Send tasks to left, right, or both brains via CLI | P0 |
| Pipeline execution | Claude reasoning → Ollama execution (hybrid cost model) | P0 |
| Tailscale mesh networking | Encrypted, zero-config connectivity | P0 |
| 13 specialized agents | 7 analytical + 6 creative, auto-triggered by context | P0 |
| Telegram control | Mobile task dispatch + review-gated notifications | P1 |
| OpenClaw gateway | Always-on API with heartbeat, memory flush, cron | P1 |
| Second Brain integration | Obsidian vault for task ledger + knowledge base | P1 |
| Browser control (Pinchtab) | HTTP API for browser automation on helpers | P2 |
| Google Workspace CLI | Drive, Gmail, Calendar, Sheets, Docs via MCP | P2 |
| Mission Control dashboard | Visual monitoring of helper status | P2 |

## Key Differentiators

1. **Runs on your hardware** — No cloud lock-in, no per-task SaaS fees
2. **Dual specialization** — Analytical and creative brains with distinct personalities
3. **Always-on** — OpenClaw keeps working overnight with memory persistence
4. **Hybrid cost model** — Claude for reasoning (smart), Ollama for execution (free)
5. **Review gate** — AI reviews every result before notifying you

## Architecture

```
Main Mac (trigger) ──Tailscale──→ Left Brain Mac (analytical agents)
                    └──────────→ Right Brain Mac (creative agents)

Each helper runs: Claude + Ollama + OpenClaw + Pinchtab + GWS
Pipeline: Claude reasons → Ollama executes → Results reviewed → Telegram notify
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Setup time | < 30 minutes per helper |
| Task dispatch latency | < 5 seconds |
| Pipeline completion rate | > 95% |
| Review gate accuracy | > 90% useful summaries |
| Overnight task completion | > 80% success rate |

## Out of Scope (MVP)

- Windows/Linux helper support
- Cloud-hosted helpers
- Multi-user / team management
- Web dashboard (CLI + Telegram only)
- Custom agent creation UI

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Alpha | 4 weeks | Core dispatch + pipeline + 5 agents |
| Beta | 4 weeks | Full agent roster + Telegram + OpenClaw |
| MVP Launch | 2 weeks | Polish, docs, setup automation |

---

*DualBrain: Your AI ops team, running on your hardware.*
