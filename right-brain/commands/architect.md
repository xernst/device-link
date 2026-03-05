# Architect Command

Invoke the **architect** agent to design system architecture for $ARGUMENTS.

## What This Does

1. **Analyze existing architecture** — patterns, conventions, tech debt
2. **Gather requirements** — functional + non-functional
3. **Design proposal** — components, data models, API contracts
4. **Trade-off analysis** — pros, cons, alternatives for each decision
5. **Create ADR** — Architecture Decision Record for significant choices

## Output

- Architecture diagram (ASCII)
- Component responsibilities
- Data flow documentation
- Trade-off analysis table
- Scalability plan
- ADR for each significant decision

## Checklist

- [ ] User stories documented
- [ ] API contracts defined
- [ ] Data models specified
- [ ] Performance targets defined
- [ ] Security requirements identified
- [ ] Testing strategy planned
- [ ] Deployment strategy defined
