---
name: autonomous-loops
description: Patterns for autonomous Claude Code loops — sequential pipelines, multi-agent DAGs, and continuous development.
---

# Autonomous Loops

## Pattern Spectrum

| Pattern | Complexity | Best For |
|---------|-----------|----------|
| Sequential Pipeline | Low | Daily dev steps, scripted workflows |
| Infinite Agentic Loop | Medium | Parallel content generation |
| Continuous PR Loop | Medium | Multi-day iterative projects with CI gates |
| De-Sloppify Pattern | Add-on | Quality cleanup after implementation |
| RFC-Driven DAG | High | Large features, parallel work with merge queue |

## 1. Sequential Pipeline (`claude -p`)

```bash
#!/bin/bash
set -e
claude -p "Implement feature with TDD."
claude -p "Cleanup pass: remove test/code slop, run tests."
claude -p "Run build + lint + tests. Fix failures."
claude -p "Commit with message: feat: add feature"
```

## 2. De-Sloppify Pattern

Let the implementer be thorough, then add a focused cleanup:

```bash
# Step 1: Implement (thorough)
claude -p "Implement the feature with full TDD."

# Step 2: De-sloppify (focused cleanup)
claude -p "Review changes. Remove tests that verify language behavior, redundant type checks, over-defensive error handling, console.logs, commented-out code. Run tests after cleanup."
```

## 3. Model Routing

```bash
claude -p --model opus "Analyze architecture and write plan..."
claude -p "Implement according to plan..."
claude -p --model opus "Review for security, race conditions..."
```

## Anti-Patterns

1. Infinite loops without exit conditions
2. No context bridge between iterations
3. Retrying same failure without context
4. Negative instructions instead of cleanup passes
5. All agents in one context window
