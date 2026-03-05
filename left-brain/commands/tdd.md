---
description: Enforce test-driven development workflow. Write tests FIRST, then implement minimal code to pass. Ensure 80%+ coverage.
---

# TDD Command

Invoke the **tdd-guide** agent to enforce TDD methodology for $ARGUMENTS.

## TDD Cycle

```
RED → GREEN → REFACTOR → REPEAT
```

1. **Define interfaces** for inputs/outputs
2. **Write tests that FAIL** (because code doesn't exist yet)
3. **Run tests** and verify they fail for the right reason
4. **Write minimal implementation** to make tests pass
5. **Run tests** and verify they pass
6. **Refactor** code while keeping tests green
7. **Check coverage** and add more tests if below 80%

Tests must be written BEFORE implementation. Never skip the RED phase.
