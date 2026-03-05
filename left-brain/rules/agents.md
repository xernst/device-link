# Agent Orchestration — Left Brain

## Available Agents

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| code-reviewer | Code review | After writing/modifying code |
| security-reviewer | Security analysis | Before commits, auth code |
| tdd-guide | Test-driven development | New features, bug fixes |
| build-error-resolver | Fix build errors | When build fails |
| refactor-cleaner | Dead code cleanup | Code maintenance |
| database-reviewer | DB optimization | SQL, schema, migrations |
| e2e-runner | E2E testing | Critical user flows |

## Immediate Agent Usage

No user prompt needed — auto-trigger:
1. Code just written/modified → **code-reviewer** agent
2. Bug fix or new feature → **tdd-guide** agent
3. Build fails → **build-error-resolver** agent
4. Security-related code → **security-reviewer** agent

## Parallel Execution

ALWAYS use parallel Task execution for independent operations:
- Security analysis + performance review + type checking
- Code review + test coverage analysis
