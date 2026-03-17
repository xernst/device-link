# SimCrowd — Business Requirements Document

**Product**: SimCrowd — Social Simulation Engine for Marketing
**Domain**: simcrowd.ai | **Version**: 1.0 | **Date**: March 2026 | **Status**: Draft

---

## 1. Executive Summary

SimCrowd is a social simulation engine that tests marketing materials against AI-generated crowds before ad spend. Unlike scoring tools that output "7/10," SimCrowd generates 20-100+ AI personas with psychographic archetypes and worldview dimensions, places marketing material in a simulated social feed, and produces a readable simulation showing exactly how different audience segments react, debate, share, or ignore the content. The result: actionable insights and AI-generated rewrites — in under 2 minutes, at $0.05-$0.15 per simulation.

## 2. Business Objectives

| Objective | Measure | Target |
|-----------|---------|--------|
| Reduce wasted ad spend | Pre-launch testing adoption rate | 30%+ of users test before launching |
| Replace expensive focus groups | Cost per insight vs. traditional testing | 99.7% cheaper ($0.15 vs $5-50K) |
| Achieve product-market fit | Free → Paid conversion | > 5% conversion |
| Build sustainable unit economics | LLM cost per simulation | < $0.15 (94%+ gross margin) |
| Reach scale | Monthly active users at 6 months | 500+ |
| Generate revenue | Monthly recurring revenue at 6 months | $10K+ MRR |

## 3. Stakeholders

| Stakeholder | Role | Interest |
|-------------|------|----------|
| Marketing teams | Primary user | Pre-launch copy validation, A/B testing |
| Solo founders / indie hackers | Primary user | Cheap, fast audience validation |
| Marketing agencies | Secondary user | Scale testing across multiple clients |
| Growth / performance marketers | Secondary user | Conversion optimization |
| Content creators | Tertiary user | Audience reaction prediction |

## 4. Business Requirements

### BR-1: Marketing Material Ingestion
**Need**: Users must be able to submit any type of marketing material for testing.
**Justification**: Marketing spans multiple formats — ad copy, landing pages, emails, social posts. The system must handle all of them to be useful.
**Acceptance Criteria**:
- Accept ad copy (text), landing page content, email copy, social post content
- Support paste-in text and URL scraping (future)
- Allow labeling material with platform context (Twitter, LinkedIn, Instagram, Reddit)
- Support multiple variants for A/B testing (Pro tier)
- Store materials per project for re-testing

### BR-2: AI Persona Generation with Worldview Dimensions
**Need**: The system must generate diverse, realistic AI personas that go beyond basic demographics to include psychographic profiles and worldview dimensions.
**Justification**: This is the core differentiator. Two "Skeptics" with different worldviews (Progressive vs. Libertarian) object to completely different things. Without worldview dimensions, simulations produce generic, useless feedback.
**Acceptance Criteria**:
- 10 psychographic archetypes: Skeptic, Early Adopter, Pragmatist, Loyalist, Influencer, Lurker, Budget-Conscious, Expert, Overwhelmed, Aspirational
- 7 worldview dimensions with 35 total modifiers:
  - Political Orientation (7): Progressive, Moderate Left, Centrist, Moderate Right, Conservative, Libertarian, Apolitical
  - Religious/Spiritual (4): Secular, Spiritual Not Religious, Mainstream Religious, Devout
  - Cultural Orientation (5): Individualist, Collectivist, Traditionalist, Cosmopolitan, Multicultural
  - Economic Worldview (4): Free Market, Conscious Capitalist, Anti-Consumerist, Aspiring Affluent
  - Media Diet (5): Mainstream, Alternative Media, Academic, Social Media Native, News Avoidant
  - Trust Orientation (4): Institution-Trusting, Peer-Trusting, Self-Reliant, Authority-Skeptical
  - Generational Identity (4): Gen Z, Millennial, Gen X, Boomer
- Each modifier carries trust modifiers (numeric), positive/negative triggers (phrases), and sensitivity topics
- Personas generated from natural language audience descriptions
- Persona packs saveable and reusable across simulations

### BR-3: Social Simulation Engine
**Need**: The system must simulate realistic social dynamics — not just individual reactions, but how content spreads through a network.
**Justification**: Marketing doesn't exist in a vacuum. Content goes viral because people share it. Content dies because influencers ignore it. Simulating social dynamics produces insights that individual scoring cannot.
**Acceptance Criteria**:
- Turn-based simulation with 7 phases:
  - Turn 0: Seeding (material hits seed agents)
  - Turns 1-2: Initial reactions (read, react, comment, share, ignore)
  - Turns 3-5: Spread & discussion (social proof, debates, viral threshold)
  - Turns 6-7: Settling (late adopters, final conversion decisions)
- Social graph connecting personas (relationships, influence, clusters)
- Engagement filtering: ~80% of personas scroll past per turn (rule-based, no LLM cost)
- Only ~20% active personas processed via LLM per turn
- Viral threshold mechanics: if share rate exceeds threshold, exponential spread
- Platform behavior norms (Twitter vs LinkedIn vs Instagram vs Reddit)
- Configurable crowd size: 20 (quick), 50 (standard), 100+ (deep)
- Configurable reach mode: Organic, Paid, Viral

### BR-4: Cost-Optimized LLM Pipeline
**Need**: Simulations must cost < $0.15 each to maintain 90%+ gross margins at all pricing tiers.
**Justification**: A naive approach (1 LLM call per agent per turn) would cost $0.50-$2.00 per simulation — making the $49/mo Starter plan unprofitable at 20 sims/mo.
**Acceptance Criteria**:
- Batched reactions: 5-10 agents per LLM call (structured JSON output), reducing calls by ~8x
- Engagement filtering: rule-based filter for non-engaging agents (~80%), reducing calls by ~5x
- Tiered models: Haiku for bulk reaction turns, Sonnet for persona generation + final analysis + key inflection moments
- Prompt caching: persona definitions cached across turns (~90% savings on persona tokens)
- Target cost breakdown:
  - Persona generation: 1 Sonnet call (~$0.03)
  - Engagement filter: rule-based ($0.00)
  - Batched reactions: ~50-60 Haiku calls (~$0.01-$0.04)
  - Final analysis: 2 Sonnet calls (~$0.06)
  - Total: $0.05-$0.15

### BR-5: Actionable Output System
**Need**: Results must go beyond scores to provide readable simulations and specific, actionable recommendations.
**Justification**: Scores alone ("7/10") don't help marketers improve their copy. They need to see *why* it failed and *what to change*.
**Acceptance Criteria**:
- Engagement Score (0-100), Sentiment Distribution, Virality Index, Conversion Probability
- Objection Map: top reasons people resisted, ranked by frequency
- Demographic Heatmap: which segments loved it vs. hated it
- Simulated Social Feed: scrollable, readable feed showing agent posts, comments, shares
- Key moment highlights: "This is where it went viral" or "This comment killed momentum"
- Feed filterable by archetype, sentiment, influence level
- Top 3 recommendations with AI-generated rewrites
- Segment-specific advice (e.g., "For Skeptics, add social proof")
- Priority ranking of changes by predicted impact

### BR-6: Industry Packs
**Need**: Pre-configured crowd compositions for common industries to reduce setup friction.
**Justification**: Most users don't want to manually configure archetype and worldview distributions. Industry packs provide sensible defaults that produce relevant results immediately.
**Acceptance Criteria**:
- MVP packs (3): SaaS B2B, E-commerce DTC, Consumer App
- Post-launch packs: Fintech, Health/Wellness, Creator Economy, Enterprise Sales
- Each pack includes archetype distribution + worldview distribution
- Users can customize packs or create their own (Pro tier)
- Packs saveable and shareable

### BR-7: User Authentication & Monetization
**Need**: Users must be able to sign up, receive 3 free simulations, and convert to paid plans.
**Justification**: The free tier drives trial; the paywall captures value. 3 free runs is enough to demonstrate value without giving away the product.
**Acceptance Criteria**:
- Email + password or Google OAuth signup
- 3 free simulations (20-agent crowd, basic scores only)
- Starter plan: $49/mo, 20 sims, 50 agents, full reports, 1 industry pack
- Pro plan: $149/mo, 100 sims, 100 agents, all packs, A/B mode, API access
- Enterprise: custom pricing, unlimited sims, SSO, custom archetypes, white-label
- Usage tracking and rate limiting per plan

## 5. Functional Requirements

### 5.1 Persona System

| Component | Description |
|-----------|-------------|
| Archetype Library | 10 psychographic archetypes with personality patterns, decision triggers, objection styles |
| Worldview Engine | 7 dimensions × 35 modifiers, each with trust modifiers, triggers, sensitivity topics |
| Persona Generator | Combines archetype + demographics + worldviews → unique agent with backstory |
| Social Graph Builder | Small-world network connecting personas with relationships and influence weights |
| Industry Packs | Pre-configured archetype × worldview distributions per industry |

### 5.2 Simulation Engine

| Component | Description |
|-----------|-------------|
| Seeding Module | Places material in seed agents' feeds based on reach mode |
| Engagement Filter | Rule-based probability filter (~80% scroll past, ~20% engage) |
| Reaction Batcher | Groups 5-10 active agents per LLM call for cost efficiency |
| Spread Calculator | Models content propagation through social graph with viral threshold |
| Turn Manager | Orchestrates 7-turn simulation lifecycle |
| Model Router | Routes calls to Haiku (bulk) vs Sonnet (key moments + analysis) |

### 5.3 Output System

| Component | Description |
|-----------|-------------|
| Scoring Engine | Aggregates simulation data into engagement, sentiment, virality, conversion metrics |
| Feed Renderer | Generates scrollable simulated social feed with key moment highlights |
| Recommendation Engine | Analyzes objections and generates prioritized rewrites |
| Report Generator | Combines scores + feed + recommendations into cohesive report |
| Export Module | PDF/PNG/shareable link export (Pro tier, post-MVP) |

### 5.4 Platform Behavior Profiles

| Platform | Behavior Norms |
|----------|---------------|
| Twitter/X | Short-form, hot takes, quote-tweet culture, pile-ons |
| LinkedIn | Professional tone, humble-brags, engagement farming awareness |
| Instagram | Visual-first, story reactions, comment brevity |
| Reddit | Skeptical, evidence-demanding, community-policed, thread depth |

## 6. Non-Functional Requirements

| Requirement | Specification |
|-------------|---------------|
| Simulation speed | < 2 minutes for 30-agent, 7-turn simulation |
| Concurrent users | Support 100+ simultaneous simulations |
| Availability | 99.9% uptime |
| Data retention | Simulation results stored 12 months (paid), 30 days (free) |
| API rate limits | Starter: 20/mo, Pro: 100/mo, Enterprise: unlimited |
| Security | HTTPS, hashed passwords, API key auth, no PII in LLM calls |
| Scalability | Celery workers scale horizontally for simulation load |
| Progressive loading | Show feed results as simulation generates (streaming UX) |

## 7. Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend | Python (FastAPI) | Async, fast, great LLM ecosystem |
| Database | PostgreSQL | Relational for users/projects/sims, JSONB for results |
| Queue | Redis + Celery | Async simulation workers (sims take 30s-2min) |
| Frontend | Next.js + React + Tailwind | Modern, fast, good DX |
| Visualization | Recharts or D3 | Charts, heatmaps, sentiment flows |
| Animation | Framer Motion | Social feed scroll animation |
| AI (Reasoning) | Claude Sonnet | Persona generation, analysis, recommendations |
| AI (Bulk) | Claude Haiku | Batched reaction turns (cost-optimized) |
| Hosting | Fly.io or Railway | Simple, scalable initial deployment |
| Storage | S3-compatible | Report assets, exports |
| Billing | Stripe | Subscription management |
| Auth | NextAuth | Email + Google OAuth |

## 8. Data Model

```
User
  ├── id, email, name, plan, stripe_customer_id
  │
  ├── Projects[]
  │     ├── id, name, industry, target_audience_description
  │     │
  │     ├── Materials[]
  │     │     ├── id, type (ad_copy|landing_page|email|social_post)
  │     │     ├── content, title, platform, variant_label
  │     │     └── created_at
  │     │
  │     ├── PersonaPacks[]
  │     │     ├── id, name, archetype_distribution
  │     │     ├── demographic_config, worldview_distribution
  │     │     └── generated_personas[] (JSONB)
  │     │
  │     └── Simulations[]
  │           ├── id, status (queued|running|complete|failed)
  │           ├── material_ids[], persona_pack_id
  │           ├── config (crowd_size, platform, reach_mode)
  │           ├── results (JSONB: scores, feed, recommendations)
  │           ├── social_graph (JSONB: nodes + edges)
  │           ├── turn_log[] (JSONB: per-turn events)
  │           └── duration_ms, token_cost, created_at
  │
  └── ApiKeys[]
        ├── id, key_hash, name, permissions
        └── rate_limit, last_used_at
```

## 9. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/simulations | Create & run a simulation |
| GET | /api/v1/simulations/:id | Get simulation status + results |
| GET | /api/v1/simulations/:id/feed | Get simulated social feed |
| GET | /api/v1/simulations/:id/report | Get full analysis report |
| POST | /api/v1/materials | Upload marketing material |
| GET | /api/v1/materials/:id | Get material details |
| GET | /api/v1/personas/archetypes | List available archetypes |
| POST | /api/v1/personas/generate | Generate persona pack from description |
| GET | /api/v1/personas/packs | List saved persona packs |
| GET | /api/v1/personas/packs/:id | Get pack details + individual personas |
| POST | /api/v1/projects | Create project |
| GET | /api/v1/projects | List projects |

## 10. Constraints

- Requires Claude API access (Haiku + Sonnet)
- LLM response quality varies — requires ongoing prompt engineering
- Simulation realism depends on persona/worldview prompt quality
- No real user data — all insights are synthetic (feature AND limitation)
- MVP limited to text-based materials (no image/video analysis)

## 11. Assumptions

- AI-generated personas can produce insights that correlate with real audience reactions (>70% sentiment match)
- Batched Haiku calls produce sufficiently realistic individual reactions
- 7 turns capture full social dynamics (seeding → settling)
- Marketers will trust synthetic simulation data for pre-launch decisions
- $49/mo Starter pricing is competitive in the AI marketing tools market

## 12. Dependencies

| Dependency | Type | Risk |
|------------|------|------|
| Claude API (Haiku + Sonnet) | External service | Medium — pricing/availability changes |
| PostgreSQL | Infrastructure | Low — mature, self-hosted |
| Redis / Celery | Infrastructure | Low — proven async stack |
| Stripe | External service | Low — standard billing |
| Fly.io / Railway | Infrastructure | Low — easy migration if needed |
| Next.js / React | Framework | Low — stable ecosystem |

## 13. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Simulations feel fake/useless | Fatal — no PMF | Medium | Heavy prompt engineering. Validate against real A/B test data. |
| LLM costs higher than projected | Margin erosion | Low | Solved: batched Haiku + engagement filtering = $0.05-$0.15/sim |
| Slow simulations (>5 min) | Poor UX, bounces | Medium | Progressive results (stream feed). Parallel batched calls. 7 turns max. |
| Haiku quality too low for reactions | Unrealistic feed | Medium | Sonnet fallback for key moments. Haiku-specific prompt optimization. |
| Persona quality inconsistent | Inconsistent value | Medium | Curated archetype library. Quality scoring on outputs. |
| Competition copies approach | Market share loss | Medium | Speed to market. Depth of worldview system. Network effects. |
| Marketers don't trust AI simulations | Low adoption | Medium | Show correlation with real results. Offer free trials. Social proof. |

## 14. Success Criteria

The MVP is successful when:
1. A user can paste marketing copy and receive a simulation in under 2 minutes
2. The simulated social feed reads like a realistic conversation
3. Recommendations include specific, actionable rewrites that address real objections
4. Worldview dimensions produce meaningfully different reactions from same-archetype personas
5. 3 industry packs cover the top use cases (SaaS, DTC, Consumer)
6. Free → Paid conversion exceeds 5%
7. LLM cost per simulation stays below $0.15
8. At least 70% of users who complete a simulation report the insights as "useful" or better

---

*SimCrowd: Stop guessing. Start simulating.*
