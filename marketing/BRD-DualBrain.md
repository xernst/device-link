# DualBrain — Business Requirements Document

**Product**: DualBrain — Multi-Machine AI Agent Swarm
**Version**: 1.0 | **Date**: March 2026 | **Status**: Draft

---

## 1. Executive Summary

DualBrain transforms idle Mac hardware into an always-on AI operations team. By splitting work across two specialized "brains" — analytical (left) and creative (right) — it gives solo developers and small teams the output of a larger team without hiring, cloud dependency, or per-task SaaS costs. Tasks are dispatched from a main Mac via CLI, Claude Code, or Telegram, executed through a hybrid Claude + Ollama pipeline, and results are AI-reviewed before delivery.

## 2. Business Objectives

| Objective | Measure | Target |
|-----------|---------|--------|
| Increase developer productivity | Tasks completed autonomously per day | 20+ tasks/day |
| Reduce AI operating costs | Cost per task vs. cloud-only AI | 70% reduction |
| Maximize hardware utilization | Idle Mac uptime converted to productive work | 90%+ utilization |
| Enable overnight work | Tasks completed while user is offline | 80%+ overnight success rate |
| Reduce context-switching | Time spent switching between analytical and creative work | 50% reduction |

## 3. Stakeholders

| Stakeholder | Role | Interest |
|-------------|------|----------|
| Solo developers | Primary user | Autonomous task execution, cost savings |
| Small engineering teams (1-5) | Primary user | Team augmentation, overnight work |
| Indie hackers / makers | Secondary user | Rapid prototyping, research automation |
| Privacy-conscious developers | Secondary user | Self-hosted, no cloud dependency |

## 4. Business Requirements

### BR-1: Dual-Brain Task Dispatch
**Need**: Users must be able to send tasks to specialized analytical or creative AI agents from a single interface.
**Justification**: Context-switching between analytical and creative work reduces productivity. Specialized agents produce higher quality output than generalist AI.
**Acceptance Criteria**:
- CLI command dispatches to left brain, right brain, or both
- Claude Code slash commands trigger brain-specific workflows
- Telegram bot accepts natural language task descriptions
- Task routing is automatic based on context when using "both" mode

### BR-2: Hybrid Execution Pipeline
**Need**: Tasks must execute through a cost-optimized pipeline combining reasoning and execution models.
**Justification**: Using Claude for every operation is expensive. Ollama runs locally for free but lacks reasoning depth. A hybrid approach optimizes cost and quality.
**Acceptance Criteria**:
- Default pipeline: Claude reasons → Ollama executes
- Direct mode available for Claude-only (higher quality)
- Ollama mode available for fastest, free execution
- OpenClaw mode for gateway-routed persistent tasks
- User can select mode per task

### BR-3: Always-On Operation
**Need**: Helper Macs must continue working when the main Mac is offline or asleep.
**Justification**: Overnight and background work multiplies developer output without additional active time investment.
**Acceptance Criteria**:
- OpenClaw gateway runs continuously on each helper
- Heartbeat monitoring every 30 minutes (8am-11pm)
- Memory flush preserves learnings before context compaction
- Cron jobs execute heavy tasks in isolated sessions
- Failed job alerts sent via Telegram before they accumulate

### BR-4: Secure Private Networking
**Need**: All communication between machines must be encrypted and require no exposed ports.
**Justification**: Developer work includes proprietary code, credentials, and sensitive data. Cloud-based solutions introduce data exposure risk.
**Acceptance Criteria**:
- Tailscale mesh VPN encrypts all traffic
- No ports exposed to public internet
- SSH authentication via keys only
- All data stays on user-owned hardware
- mosh + tmux for persistent, resilient sessions

### BR-5: AI Review Gate
**Need**: Every task result must be reviewed by AI before delivery to the user.
**Justification**: Raw AI output can be noisy, incorrect, or incomplete. A review gate ensures only actionable, summarized results reach the user.
**Acceptance Criteria**:
- Claude generates 2-3 sentence executive summary of each result
- Summary flags any issues, failures, or warnings
- Review sent to Telegram before completion notification
- User receives signal, not noise

### BR-6: Knowledge Persistence
**Need**: Learnings, results, and context must persist across sessions and be searchable.
**Justification**: Without persistence, the same mistakes are repeated and useful context is lost between sessions.
**Acceptance Criteria**:
- Obsidian vault stores task ledger and knowledge base
- Daily memory files consolidate learnings
- Daily digest generator summarizes completed work
- Results stored in git-synced directory
- Second Brain slash commands enable retrieval and analysis

### BR-7: Mobile Control
**Need**: Users must be able to dispatch tasks and receive results from their phone.
**Justification**: Developers are not always at their main Mac. Mobile control enables task dispatch during commutes, meetings, or downtime.
**Acceptance Criteria**:
- Telegram bot accepts task dispatch messages
- Status, brief, and results commands available
- Review-gated notifications prevent spam
- Natural language task descriptions supported

## 5. Functional Requirements

### 5.1 Agent System

| Agent (Left Brain) | Function |
|---------------------|----------|
| code-reviewer | Automated code review with line-level feedback |
| security-reviewer | Security vulnerability scanning (OWASP top 10) |
| tdd-guide | Test-driven development workflow guidance |
| build-error-resolver | Diagnose and fix build failures |
| refactor-cleaner | Code refactoring and cleanup suggestions |
| database-reviewer | Database schema and query optimization |
| e2e-runner | End-to-end test execution and reporting |

| Agent (Right Brain) | Function |
|----------------------|----------|
| planner | Strategic planning and task breakdown |
| architect | System architecture design and review |
| researcher | Market research and competitive analysis |
| prd-creator | Product requirements document generation |
| doc-updater | Documentation creation and maintenance |
| chief-of-staff | Operations coordination and task prioritization |

### 5.2 Execution Modes

| Mode | Command | Cost | Speed | Quality |
|------|---------|------|-------|---------|
| Pipeline (default) | `device-link left "task"` | Low | Medium | High |
| Direct (Claude only) | `--direct` | High | Slow | Highest |
| Ollama (local only) | `--ollama` | Free | Fast | Medium |
| OpenClaw (gateway) | `--openclaw` | Low | Medium | High |

### 5.3 Integration Points

| System | Purpose | Protocol |
|--------|---------|----------|
| Tailscale | Mesh networking | WireGuard |
| Ollama | Local model execution | HTTP API |
| Claude | AI reasoning | API |
| OpenClaw | Always-on gateway | HTTP API |
| Pinchtab | Browser control | HTTP API |
| Google Workspace | Drive, Gmail, Calendar, Sheets, Docs | MCP |
| Telegram | Mobile control + notifications | Bot API |
| Obsidian | Knowledge persistence | Filesystem |
| Git | Result sync | SSH |

## 6. Non-Functional Requirements

| Requirement | Specification |
|-------------|---------------|
| Setup time | < 30 minutes per helper Mac |
| Task dispatch latency | < 5 seconds from trigger to execution start |
| Pipeline completion | > 95% success rate |
| Uptime | 99%+ per helper (OpenClaw heartbeat monitored) |
| Security | Zero exposed ports, encrypted transit, key-only auth |
| Privacy | All data on user-owned hardware, no cloud storage |
| Resilience | mosh + tmux survive network interruptions |
| Monitoring | Heartbeat every 30 min, failed job alerting |

## 7. Constraints

- Requires macOS on helper machines (MVP)
- Requires Tailscale account (free tier sufficient)
- Requires Claude API key (paid)
- Ollama must be installed on each helper
- Minimum 2 Macs (1 main + 1 helper) for basic setup
- Recommended 3 Macs (1 main + 2 helpers) for full dual-brain

## 8. Assumptions

- Users have at least one spare Mac available as a helper
- Users are comfortable with CLI-based tools
- Tailscale network is reliable for inter-machine communication
- Claude API remains available and pricing remains viable
- Ollama models are sufficient for execution-tier tasks

## 9. Dependencies

| Dependency | Type | Risk |
|------------|------|------|
| Claude API | External service | Medium — API changes or pricing increases |
| Tailscale | External service | Low — mature, reliable service |
| Ollama | Open source | Low — actively maintained, self-hosted |
| macOS | Platform | Low — stable platform |
| Telegram Bot API | External service | Low — stable, well-documented |

## 10. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Claude API price increase | High | Medium | Ollama fallback for execution; pipeline reduces Claude usage |
| Helper Mac hardware failure | High | Low | Graceful degradation to single-brain mode |
| Tailscale outage | Medium | Low | Local network fallback for same-network Macs |
| Ollama model quality | Medium | Medium | Claude direct mode as fallback; model updates |
| Context window limits | Medium | Medium | Memory flush + Second Brain persistence |

## 11. Success Criteria

The MVP is successful when:
1. A user can set up two helper Macs in under 30 minutes each
2. Tasks can be dispatched and completed across all four execution modes
3. 13 specialized agents produce actionable output for their respective domains
4. Overnight work completes reliably with results available by morning
5. Telegram control enables full task lifecycle from mobile
6. Review gate filters noise and delivers only useful summaries
7. Knowledge persists across sessions via Second Brain integration

---

*DualBrain: Your AI ops team, running on your hardware.*
