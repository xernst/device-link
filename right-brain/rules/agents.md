# Agent Orchestration — Right Brain

## Available Agents

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| planner | Implementation planning | Complex features, refactoring |
| architect | System design | Architectural decisions |
| researcher | Research & analysis | Market, competitive, technology research |
| prd-creator | Product requirements | New features, product specs |
| doc-updater | Documentation | Updating docs, codemaps |
| chief-of-staff | Communication | Message triage, drafts |

## Immediate Agent Usage

No user prompt needed — auto-trigger:
1. Complex feature request → **planner** agent
2. Architectural decision → **architect** agent
3. Research request → **researcher** agent
4. New product feature → **prd-creator** agent

## Parallel Execution

ALWAYS use parallel Task execution for independent operations:
- Research + architecture review
- Planning + documentation updates
- PRD creation + competitive analysis
