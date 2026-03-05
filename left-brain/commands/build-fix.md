# Build and Fix

Incrementally fix build and type errors with minimal, safe changes.

## Step 1: Detect Build System
Run the appropriate build command for this project.

## Step 2: Parse and Group Errors
1. Run build command and capture stderr
2. Group errors by file path
3. Sort by dependency order
4. Count total errors for progress tracking

## Step 3: Fix Loop (One Error at a Time)
For each error:
1. Read the file — see error context
2. Diagnose — identify root cause
3. Fix minimally — smallest change that resolves the error
4. Re-run build — verify error is gone
5. Move to next

## Step 4: Guardrails
Stop and ask user if:
- Fix introduces more errors than it resolves
- Same error persists after 3 attempts
- Fix requires architectural changes
- Build errors stem from missing dependencies

Fix one error at a time for safety. Prefer minimal diffs over refactoring.
