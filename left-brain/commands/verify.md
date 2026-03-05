# Verification Command

Run comprehensive verification on current codebase state.

Execute in this exact order:

1. **Build Check** — Run build command. If it fails, report and STOP.
2. **Type Check** — Run type checker. Report errors with file:line.
3. **Lint Check** — Run linter. Report warnings and errors.
4. **Test Suite** — Run all tests. Report pass/fail count and coverage.
5. **Console.log Audit** — Search for console.log in source files.
6. **Git Status** — Show uncommitted changes.

## Output

```
VERIFICATION: [PASS/FAIL]

Build:    [OK/FAIL]
Types:    [OK/X errors]
Lint:     [OK/X issues]
Tests:    [X/Y passed, Z% coverage]
Logs:     [OK/X console.logs]

Ready for PR: [YES/NO]
```

$ARGUMENTS can be: `quick` (build + types only), `full` (all checks), `pre-commit`, `pre-pr` (+ security scan)
