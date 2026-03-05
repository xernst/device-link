---
name: security-review
description: Security review patterns for OWASP Top 10, secrets detection, and secure coding practices.
---

# Security Review Skill

## Scan Checklist

### Secrets Detection
- Hardcoded API keys, passwords, tokens in source
- Secrets in environment files committed to git
- Secrets leaked in log output

### Input Validation
- SQL injection (parameterized queries required)
- XSS (output escaped, CSP set)
- Path traversal (user-controlled file paths sanitized)
- Command injection (shell commands with user input)
- SSRF (user-provided URLs validated)

### Authentication & Authorization
- Passwords hashed with bcrypt/argon2
- JWT properly validated (signature, expiry, audience)
- Auth middleware on all protected routes
- CORS properly configured

### Dependencies
```bash
npm audit --audit-level=high
```

### Rate Limiting
- Public endpoints throttled
- Authentication endpoints rate-limited
- API keys have per-key limits

## Severity Levels

| Level | Action |
|-------|--------|
| CRITICAL | Fix immediately, block merge |
| HIGH | Fix before merge |
| MEDIUM | Fix when possible |
| INFO | Awareness only |
