# Code Review

Comprehensive security and quality review of uncommitted changes:

1. Get changed files: git diff --name-only HEAD

2. For each changed file, check for:

**Security Issues (CRITICAL):**
- Hardcoded credentials, API keys, tokens
- SQL injection vulnerabilities
- XSS vulnerabilities
- Missing input validation
- Insecure dependencies

**Code Quality (HIGH):**
- Functions > 50 lines
- Files > 800 lines
- Nesting depth > 4 levels
- Missing error handling
- console.log statements

**Best Practices (MEDIUM):**
- Mutation patterns (use immutable instead)
- Missing tests for new code
- Accessibility issues

3. Generate report with severity, file location, issue, suggested fix

4. Block commit if CRITICAL or HIGH issues found
