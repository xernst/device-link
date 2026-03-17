# SimCrowd — MVP Product Requirements Document

**Product**: SimCrowd — Social Simulation Engine for Marketing
**Domain**: simcrowd.ai | **Version**: MVP v1.0 | **Date**: March 2026

---

## Problem

Marketers spend thousands on ads before knowing if the copy resonates. Existing AI tools give you a score — "7/10, sounds good!" — but can't show you *why* a skeptical SaaS buyer would scroll past, or *how* a Gen Z early adopter would roast your landing page in a group chat. You're flying blind until real money is spent.

## Solution

SimCrowd builds an AI crowd matched to your target demographic, drops your marketing material into a simulated social feed, and lets you watch what happens — before you spend a dollar on ads.

1. **Build a crowd** — 20-100+ AI personas from psychographic archetypes + worldview dimensions
2. **Run the simulation** — agents encounter your material, react, comment, share (or don't), debate each other
3. **Read the results** — engagement scores, a simulated social feed you can scroll, and actionable rewrites

The magic: you can read what "Sarah, 34, skeptical SaaS buyer" actually said about your ad to "Mike, 28, early adopter." Not a score. A simulation.

## Target User

- Marketing teams testing copy before launch
- Solo founders validating positioning
- Agencies running multiple campaigns
- Growth teams optimizing conversion

## MVP Scope

| Feature | Description | Priority |
|---------|-------------|----------|
| Copy submission | Paste ad copy, landing page, email, or social post | P0 |
| Audience targeting | Describe target audience in natural language | P0 |
| 10 persona archetypes | Skeptic, Early Adopter, Pragmatist, Loyalist, Influencer, Lurker, Budget-Conscious, Expert, Overwhelmed, Aspirational | P0 |
| 7 worldview dimensions | Political, Religious, Cultural, Economic, Media Diet, Trust, Generational — 35 modifiers total | P0 |
| 30-agent simulation | 7-turn social simulation with batched LLM calls | P0 |
| Simulated social feed | Scrollable feed showing agent posts, comments, shares | P0 |
| Engagement scores | Score (0-100), sentiment distribution, virality index, conversion probability | P0 |
| Top 3 recommendations | Actionable rewrites addressing top objections | P0 |
| 3 industry packs | SaaS B2B, E-commerce DTC, Consumer App | P0 |
| Auth + paywall | Email/Google OAuth, 3 free runs then paywall | P1 |
| Platform simulation | Twitter/X, LinkedIn, Instagram, Reddit behavior norms | P1 |
| A/B variant testing | Run 2-4 variants against same crowd | P2 |
| API access | REST API for Pro users | P2 |
| PDF/PNG export | Downloadable reports | P2 |

## Key Differentiators

1. **Simulation, not scoring** — Read actual conversations, not just a number
2. **Worldview dimensions** — Two "Skeptics" with different worldviews object to different things
3. **Social dynamics** — Content spreads (or dies) through a realistic social graph
4. **Batched economics** — $0.05-$0.15 per sim = 94%+ margins at scale
5. **Industry packs** — Pre-configured crowd compositions for SaaS, DTC, Fintech, etc.

## Architecture

```
User → Submit Copy → Persona Generator → Social Graph Builder
                                              ↓
                              Simulation Runner (7 turns)
                              Turn 0: Seeding
                              Turns 1-2: Initial reactions (batched Haiku)
                              Turns 3-5: Spread & discussion
                              Turns 6-7: Settling + final actions
                                              ↓
                              Scoring Engine → Report + Feed + Recommendations
```

**Cost per simulation**: ~$0.05-$0.15 (batched Haiku for reactions, Sonnet for persona gen + analysis)

## Success Metrics

| Metric | Target |
|--------|--------|
| Simulation time | < 2 minutes for 30-agent sim |
| User activation | > 60% complete first sim |
| Free → Paid conversion | > 5% |
| Sim accuracy vs real campaigns | > 70% sentiment correlation |
| Monthly active users (6 months) | 500+ |

## Pricing

| Plan | Price | Sims/mo | Crowd Size | Features |
|------|-------|---------|------------|----------|
| Free | $0 | 3 | 20 agents | Basic scores only |
| Starter | $49/mo | 20 | 50 agents | Full reports, 1 industry pack |
| Pro | $149/mo | 100 | 100 agents | All packs, A/B, API access |
| Enterprise | Custom | Unlimited | Custom | SSO, custom archetypes, white-label |

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Core Engine | Weeks 1-2 | Persona system, simulation runner, scoring, CLI proof-of-concept |
| API + Frontend | Weeks 3-4 | FastAPI server, Next.js dashboard, submission form, results page |
| Polish + Launch | Weeks 5-6 | Industry packs, charts, prompt tuning, landing page, deploy |

---

*SimCrowd: Test your marketing on AI crowds before spending a dollar on ads.*
