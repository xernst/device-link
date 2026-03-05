# Test Coverage

Analyze test coverage, identify gaps, and generate missing tests to reach 80%+.

## Step 1: Detect Test Framework and Run Coverage

## Step 2: Analyze Coverage Report
1. List files below 80% coverage, sorted worst-first
2. For each under-covered file, identify untested functions and missing branches

## Step 3: Generate Missing Tests
Priority:
1. Happy path — core functionality with valid inputs
2. Error handling — invalid inputs, missing data
3. Edge cases — empty arrays, null/undefined, boundary values
4. Branch coverage — each if/else, switch case

## Step 4: Verify
1. Run full test suite — all tests must pass
2. Re-run coverage — verify improvement
3. Repeat if still below 80%

## Step 5: Report
```
Coverage Report
──────────────────────────────
File                   Before  After
src/services/auth.ts   45%     88%
──────────────────────────────
Overall:               67%     84%
```
