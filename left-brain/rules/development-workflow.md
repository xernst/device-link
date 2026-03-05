# Development Workflow — Left Brain

## Feature Implementation Pipeline

1. **Research & Reuse** (mandatory before new implementation)
   - Search for existing implementations before writing new code
   - Check package registries before writing utilities
   - Prefer battle-tested libraries over hand-rolled solutions

2. **Plan First**
   - Break down into phases with file paths
   - Identify dependencies and risks

3. **TDD Approach**
   - Use **tdd-guide** agent
   - Write tests first (RED)
   - Implement to pass tests (GREEN)
   - Refactor (IMPROVE)
   - Verify 80%+ coverage

4. **Code Review**
   - Use **code-reviewer** agent immediately after writing code
   - Address CRITICAL and HIGH issues
   - Fix MEDIUM issues when possible

5. **Verify**
   - Run full build, lint, type check, test suite
   - Use **verification-loop** skill

6. **Commit**
   - Detailed commit messages
   - Follow conventional commits format
