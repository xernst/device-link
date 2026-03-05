# Refactor Clean

Safely identify and remove dead code with test verification at every step.

## Step 1: Detect Dead Code
Run analysis tools based on project type (knip, depcheck, ts-prune, vulture, etc.)

## Step 2: Categorize Findings
- **SAFE** — Unused utilities, internal functions → delete with confidence
- **CAUTION** — Components, API routes → verify no dynamic imports
- **DANGER** — Config files, entry points → investigate first

## Step 3: Safe Deletion Loop
For each SAFE item:
1. Run full test suite (establish baseline)
2. Delete the dead code
3. Re-run tests
4. If tests fail → revert and skip
5. If tests pass → move to next

## Step 4: Consolidate Duplicates
- Near-duplicate functions → merge
- Redundant types → consolidate
- Wrapper functions adding no value → inline

## Rules
- Never delete without running tests first
- One deletion at a time
- Skip if uncertain
- Don't refactor while cleaning
