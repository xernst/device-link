---
name: tdd-workflow
description: Test-Driven Development workflow patterns, mocking strategies, and coverage targets.
---

# TDD Workflow Skill

## The Cycle

```
RED → GREEN → REFACTOR → REPEAT

RED:      Write a failing test
GREEN:    Write minimal code to pass
REFACTOR: Improve code, keep tests passing
REPEAT:   Next feature/scenario
```

## Test Types

| Type | What to Test | When |
|------|-------------|------|
| Unit | Individual functions in isolation | Always |
| Integration | API endpoints, database operations | Always |
| E2E | Critical user flows | Critical paths |

## Mocking Patterns

### External Services
```typescript
// Mock API calls
jest.mock('./api-client', () => ({
  fetchUser: jest.fn().mockResolvedValue({ id: 1, name: 'Test' }),
}))
```

### Database
```typescript
// Use test database or in-memory
beforeEach(async () => {
  await db.migrate.latest()
  await db.seed.run()
})
afterEach(async () => {
  await db.migrate.rollback()
})
```

## Coverage Requirements

- **80% minimum** for all code
- **100% required** for:
  - Financial calculations
  - Authentication logic
  - Security-critical code
  - Core business logic

## Anti-Patterns

- Testing implementation details instead of behavior
- Tests depending on each other
- Testing framework/language behavior
- Not mocking external dependencies
