---
description: Generate and run end-to-end tests with Playwright for critical user flows.
---

# E2E Command

Invoke the **e2e-runner** agent to generate and execute E2E tests for $ARGUMENTS.

1. **Analyze user flow** and identify test scenarios
2. **Generate Playwright test** using Page Object Model pattern
3. **Run tests** across browsers
4. **Capture failures** with screenshots, videos, traces
5. **Identify flaky tests** and recommend fixes

```bash
npx playwright test                      # Run all
npx playwright test --headed             # See browser
npx playwright test --debug              # Debug mode
npx playwright show-report              # View report
```
