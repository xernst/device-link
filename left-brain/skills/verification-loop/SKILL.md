---
name: verification-loop
description: Comprehensive verification system for code quality gates.
---

# Verification Loop

Run all quality checks in sequence after completing a feature or before a PR.

## Verification Phases

### Phase 1: Build Verification
```bash
npm run build 2>&1 | tail -20
```
If build fails, STOP and fix before continuing.

### Phase 2: Type Check
```bash
npx tsc --noEmit 2>&1 | head -30
```

### Phase 3: Lint Check
```bash
npm run lint 2>&1 | head -30
```

### Phase 4: Test Suite
```bash
npm run test -- --coverage 2>&1 | tail -50
```
Target: 80% minimum coverage.

### Phase 5: Security Scan
```bash
grep -rn "sk-" --include="*.ts" --include="*.js" . 2>/dev/null | head -10
grep -rn "console.log" --include="*.ts" --include="*.tsx" src/ 2>/dev/null | head -10
```

### Phase 6: Diff Review
```bash
git diff --stat
```

## Output Format

```
VERIFICATION REPORT
==================
Build:     [PASS/FAIL]
Types:     [PASS/FAIL]
Lint:      [PASS/FAIL]
Tests:     [PASS/FAIL] (X/Y passed, Z% coverage)
Security:  [PASS/FAIL]

Overall:   [READY/NOT READY] for PR
```
