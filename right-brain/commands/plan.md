---
description: Restate requirements, assess risks, and create step-by-step implementation plan. WAIT for user CONFIRM before touching any code.
---

# Plan Command

Invoke the **planner** agent to create a comprehensive implementation plan for $ARGUMENTS.

1. **Analyze the request** and restate requirements clearly
2. **Break down into phases** with specific, actionable steps
3. **Identify dependencies** between components
4. **Assess risks** and potential blockers
5. **Estimate complexity** (High/Medium/Low)
6. **Present the plan** and WAIT for explicit confirmation

**CRITICAL**: The planner agent will NOT write any code until you explicitly confirm.

After planning:
- Use `/tdd` to implement with test-driven development
- Use `/build-fix` if build errors occur
- Use `/code-review` to review completed implementation
