# Marketing Testing Tool — Product Plan

**Codename**: CrowdTest (working name)
**What it is**: A social simulation engine that tests marketing materials against AI-generated crowds before you spend a dollar on ads.
**How it's different**: Not just "AI rates your copy." It simulates actual social dynamics — agents share, debate, ignore, and react to your material in a realistic social environment. You see what would happen before it happens.

---

## 1. Core Concept

You submit marketing material (ad copy, landing page, email). The system:

1. **Builds a crowd** — generates 20-100+ agents from pre-designed persona archetypes matched to your target demographic
2. **Runs a social simulation** — agents encounter your material in a simulated social feed, react, comment, share (or don't), debate with each other
3. **Produces outputs** — engagement scores, a simulated social feed you can read, actionable recommendations, and visual comparison reports

The magic is in step 2. Existing tools give you a score. CrowdTest gives you a *simulation* — you can read what "Sarah, 34, skeptical SaaS buyer" actually said about your ad to her friend "Mike, 28, early adopter."

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                   Web Dashboard                  │
│         (React/Next.js + Tailwind CSS)           │
└──────────────────────┬──────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────┐
│                  API Server                      │
│              (Node.js / FastAPI)                  │
│                                                  │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Material │  │ Simulation│  │   Report     │  │
│  │ Ingestion│  │  Engine   │  │  Generator   │  │
│  └──────────┘  └───────────┘  └──────────────┘  │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              Simulation Engine                    │
│                                                  │
│  ┌─────────────────────────────────────────┐     │
│  │         Persona Generator               │     │
│  │  (Archetypes × Context → Unique Agents) │     │
│  └─────────────────────────────────────────┘     │
│                                                  │
│  ┌─────────────────────────────────────────┐     │
│  │         Social Graph Builder            │     │
│  │  (Relationships, influence, clusters)   │     │
│  └─────────────────────────────────────────┘     │
│                                                  │
│  ┌─────────────────────────────────────────┐     │
│  │         Simulation Runner               │     │
│  │  (Turn-based: expose → react → spread)  │     │
│  └─────────────────────────────────────────┘     │
│                                                  │
│  ┌─────────────────────────────────────────┐     │
│  │         Analysis & Scoring              │     │
│  │  (Aggregate metrics + recommendations)  │     │
│  └─────────────────────────────────────────┘     │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                 LLM Layer                        │
│  Claude API (persona gen, analysis, reports)     │
│  + configurable provider for bulk sim turns      │
└─────────────────────────────────────────────────┘
```

---

## 3. Persona System

### 3.1 Archetype Library

Pre-designed persona archetypes organized by dimension, not industry. Mix and match to build any audience.

**Psychographic Archetypes** (core personality patterns):
- The Skeptic — needs proof, asks hard questions, resistant to hype
- The Early Adopter — excited by novelty, forgives rough edges, shares discoveries
- The Pragmatist — "does it solve my problem?" ROI-focused, comparison shopper
- The Loyalist — brand-attached, defensive of current tools, high switching cost
- The Influencer — shares opinions publicly, shapes others' views, status-driven
- The Lurker — reads everything, shares nothing, decides privately
- The Budget-Conscious — price-sensitive, hunts deals, needs justification
- The Expert — deep domain knowledge, detects BS instantly, values precision
- The Overwhelmed — too many options, decision fatigue, wants simplicity
- The Aspirational — wants to level up, motivated by success stories

**Demographic Modifiers** (layered on top):
- Age bands: Gen Z (18-26), Millennial (27-42), Gen X (43-58), Boomer (59-77)
- Tech savviness: digital native, competent, reluctant, resistant
- Role: IC, manager, exec, founder, freelancer, student
- Company size: solo, startup, SMB, mid-market, enterprise

**Industry Packs** (pre-configured crowd compositions):
- **SaaS B2B**: heavy on Pragmatists + Experts + Budget-Conscious, skews manager/exec
- **E-commerce DTC**: heavy on Early Adopters + Aspirational + Budget-Conscious, skews younger
- **Fintech**: heavy on Skeptics + Experts + Pragmatists, mixed ages
- **Health/Wellness**: heavy on Aspirational + Overwhelmed + Skeptics
- **Creator Economy**: heavy on Influencers + Early Adopters + Aspirational
- **Enterprise Sales**: heavy on Pragmatists + Loyalists + Experts, skews exec
- **Consumer App**: heavy on Early Adopters + Lurkers + Influencers, skews Gen Z/Millennial

### 3.2 Persona Generation Flow

```
User provides:
  - Target audience description (natural language)
  - Industry pack (optional, for defaults)
  - Any specific persona overrides

System generates:
  1. Parse audience description → map to archetype distribution
  2. Apply industry pack defaults (if selected)
  3. Generate N unique personas by combining:
     - Base archetype (personality, decision patterns, objection style)
     - Demographic modifiers (age, role, tech level)
     - Unique backstory + current situation (LLM-generated)
     - Social graph position (influencer, connector, peripheral)
  4. Build social graph (who knows whom, who influences whom)
```

Each generated persona has:
- **Name & background** (realistic, diverse)
- **Archetype blend** (e.g., 60% Skeptic + 30% Expert + 10% Pragmatist)
- **Decision triggers** — what makes them act
- **Objection patterns** — what makes them resist
- **Communication style** — how they talk (formal, casual, emoji-heavy, terse)
- **Platform behavior** — how they use social media (scroll, engage, share, create)
- **Influence score** — 1-10, affects spread dynamics
- **Network connections** — links to other personas in the simulation

---

## 4. Simulation Engine

### 4.1 Turn-Based Social Simulation

The simulation runs in discrete turns, modeling how content spreads through a social network.

**Phase 1: Seeding (Turn 0)**
- Material appears in the feed of "seed" personas (high-exposure agents)
- Number of seeds depends on simulated ad spend / organic reach setting

**Phase 2: Initial Reactions (Turns 1-3)**
- Each exposed persona decides: ignore, read, react, comment, share
- Decision based on persona archetype + material relevance + attention budget
- Comments and reactions are generated by LLM in-character
- Each action has a probability weight (Skeptics less likely to share, Influencers more likely)

**Phase 3: Spread & Discussion (Turns 4-10)**
- Shared content reaches connected personas in the social graph
- "Social proof" modifier: seeing friends engage increases engagement probability
- Debates emerge: Skeptics challenge, Early Adopters defend, Experts weigh in
- Some personas see competitors' responses and react
- Viral threshold: if share rate exceeds threshold, exponential spread begins

**Phase 4: Settling (Turns 11-15)**
- Engagement tapers off naturally
- Late adopters and Lurkers make final decisions
- "Would you buy/sign up/click?" final action captured per persona
- Net sentiment stabilizes

### 4.2 Simulation Parameters

Users can configure:
- **Crowd size**: 20 (quick test) / 50 (standard) / 100+ (deep analysis)
- **Platform simulation**: Twitter/X-style, LinkedIn-style, Instagram-style, Reddit-style (affects behavior norms)
- **Reach mode**: Organic (slow spread) / Paid (wide initial seed) / Viral (optimistic spread)
- **Competitor context**: Optional competitor materials shown alongside
- **A/B mode**: Run 2-4 variants simultaneously against the same crowd

---

## 5. Output System

### 5.1 Scores & Metrics
- **Engagement Score** (0-100): overall predicted engagement
- **Sentiment Distribution**: positive / neutral / negative / hostile breakdown
- **Virality Index**: predicted share-to-view ratio
- **Conversion Probability**: % of crowd that would take the CTA action
- **Objection Map**: top reasons people resisted, ranked by frequency
- **Demographic Heatmap**: which segments loved it vs. hated it

### 5.2 Simulated Social Feed
- Actual rendered feed showing agent posts, comments, shares, threads
- Readable like a real social media thread
- Highlights key moments: "This is where it went viral" or "This comment killed momentum"
- Filterable by persona archetype, sentiment, influence level

### 5.3 Actionable Recommendations
- **What worked**: specific phrases, hooks, or angles that drove engagement
- **What didn't**: specific elements that triggered objections or disengagement
- **Suggested rewrites**: LLM-generated alternative copy addressing the top objections
- **Segment-specific advice**: "For Skeptics, add social proof. For Budget-Conscious, lead with ROI."
- **Priority ranking**: which changes would have the biggest impact

### 5.4 Visual Reports
- Engagement timeline chart (how engagement evolved over turns)
- Sentiment flow (Sankey diagram: initial impression → final sentiment)
- Demographic comparison matrix (heatmap: segment × metric)
- A/B comparison dashboard (side-by-side variant performance)
- Social graph visualization (how content spread through the network)
- Exportable as PDF / PNG / shareable link

---

## 6. Tech Stack (Proposed)

### Backend
- **Python (FastAPI)** — API server, simulation orchestration
- **PostgreSQL** — user accounts, simulation history, results
- **Redis** — job queue, caching, rate limiting
- **Celery** — async simulation workers (sims take 30s-5min)

### Frontend
- **Next.js + React** — dashboard, report viewer
- **Tailwind CSS** — styling
- **Recharts or D3** — data visualization
- **Framer Motion** — social feed animation

### AI/LLM
- **Claude API** — persona generation, report synthesis, recommendations
- **Configurable provider** — bulk simulation turns (Claude / OpenAI / local)
- **Structured outputs** — JSON mode for consistent persona + reaction formats

### Infrastructure
- **Docker** — containerized deployment
- **Fly.io or Railway** — initial hosting (simple, scalable)
- **S3-compatible storage** — report assets, exports
- **Stripe** — billing

---

## 7. Data Model (Core)

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
  │     │     ├── demographic_config, custom_overrides
  │     │     └── generated_personas[] (JSON)
  │     │
  │     └── Simulations[]
  │           ├── id, status (queued|running|complete|failed)
  │           ├── material_ids[], persona_pack_id
  │           ├── config (crowd_size, platform, reach_mode)
  │           ├── results (JSON: scores, feed, recommendations)
  │           ├── social_graph (JSON: nodes + edges)
  │           ├── turn_log[] (JSON: per-turn events)
  │           └── duration_ms, token_cost, created_at
  │
  └── ApiKeys[]
        ├── id, key_hash, name, permissions
        └── rate_limit, last_used_at
```

---

## 8. API Design (Key Endpoints)

```
POST   /api/v1/simulations          — Create & run a simulation
GET    /api/v1/simulations/:id      — Get simulation status + results
GET    /api/v1/simulations/:id/feed — Get simulated social feed
GET    /api/v1/simulations/:id/report — Get full analysis report

POST   /api/v1/materials            — Upload marketing material
GET    /api/v1/materials/:id        — Get material details

GET    /api/v1/personas/archetypes  — List available archetypes
POST   /api/v1/personas/generate    — Generate persona pack from description
GET    /api/v1/personas/packs       — List saved persona packs
GET    /api/v1/personas/packs/:id   — Get pack details + individual personas

POST   /api/v1/projects             — Create project
GET    /api/v1/projects             — List projects
```

---

## 9. Pricing Model (Strawman)

| Plan | Price | Simulations/mo | Crowd Size | Features |
|------|-------|----------------|------------|----------|
| Free | $0 | 3 | 20 agents | Basic scores only |
| Starter | $49/mo | 20 | 50 agents | Full reports, 1 industry pack |
| Pro | $149/mo | 100 | 100 agents | All packs, A/B, API access |
| Enterprise | Custom | Unlimited | Custom | SSO, custom archetypes, white-label |

---

## 10. MVP Scope (Phase 1)

Build the minimum to validate the concept and get first paying users.

### MVP Includes:
1. **Single-page submission form** — paste your copy, describe your audience, pick platform
2. **3 industry packs** (SaaS B2B, E-commerce DTC, Consumer App)
3. **10 persona archetypes** (the core psychographic set)
4. **30-agent simulation** — 10 turns, basic social graph
5. **Results page** with:
   - Engagement score + sentiment breakdown
   - Simulated social feed (scrollable)
   - Top 3 recommendations with suggested rewrites
   - Basic bar charts (sentiment, engagement by segment)
6. **Auth** (email + password or Google OAuth)
7. **3 free runs** then paywall

### MVP Excludes (Phase 2+):
- A/B variant comparison
- Full API access
- Custom persona packs
- PDF/PNG export
- Social graph visualization
- Competitor context mode
- Stripe billing (manual onboarding for early users)
- Team/org accounts

---

## 11. Build Sequence

### Phase 1: Core Engine (Week 1-2)
- [ ] Persona archetype definitions (10 archetypes as structured data)
- [ ] Persona generator (archetype × demographics → unique agent)
- [ ] Social graph builder (small-world network generation)
- [ ] Simulation runner (turn-based loop with LLM calls)
- [ ] Scoring engine (aggregate simulation results → metrics)
- [ ] CLI proof-of-concept (run a sim from command line, output JSON)

### Phase 2: API + Basic Frontend (Week 3-4)
- [ ] FastAPI server with core endpoints
- [ ] PostgreSQL schema + migrations
- [ ] Celery worker for async simulation
- [ ] Next.js app scaffold
- [ ] Material submission form
- [ ] Results page (scores + feed + recommendations)
- [ ] Auth (NextAuth or similar)

### Phase 3: Polish + Launch (Week 5-6)
- [ ] Industry pack configurations
- [ ] Visual charts on results page
- [ ] Prompt engineering refinement (persona quality, reaction realism)
- [ ] Rate limiting + usage tracking
- [ ] Landing page
- [ ] Deploy to production

### Phase 4: Growth Features (Post-launch)
- [ ] A/B testing mode
- [ ] API access for Pro users
- [ ] PDF report export
- [ ] Social graph visualization
- [ ] Custom archetype builder
- [ ] Stripe billing integration
- [ ] Webhook notifications (sim complete)

---

## 12. Key Technical Decisions to Make

1. **LLM cost management** — A 50-agent, 10-turn simulation = ~500 LLM calls. At Claude Sonnet pricing (~$3/M input, $15/M output), a single sim could cost $0.50-$2.00. Need to optimize: batch calls, use smaller models for reactions, cache persona behaviors.

2. **Simulation fidelity vs. speed** — Full agent-to-agent LLM conversations are expensive and slow. Options:
   - Every reaction is a full LLM call (highest quality, slowest, most expensive)
   - Hybrid: LLM for "interesting" reactions, rule-based for simple ones (ignore, basic like)
   - Batch: send multiple agent reactions in a single prompt with structured output

3. **Persona consistency** — Agents need to behave consistently across turns. Options:
   - Include full persona in every prompt (token-heavy but consistent)
   - Use system prompt caching (if available)
   - Summarize persona to key traits for reaction calls

4. **Where to build it** — Options:
   - Separate repo (clean, independent product)
   - Inside device-link repo (leverage existing infra)
   - Monorepo with shared packages

5. **Name** — CrowdTest is a working name. Others: SimAudience, CrowdLens, AdSim, MarketMirror, TestCrowd, SimPanel, CrowdScope

---

## 13. Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM costs too high per sim | Unprofitable unit economics | Hybrid approach: LLM for key moments, rules for simple reactions. Batch calls. |
| Simulations feel fake/useless | No product-market fit | Heavy prompt engineering investment. Real A/B test validation against actual campaign data. |
| Slow simulation (>5 min) | Poor UX, users bounce | Progressive results (show feed as it generates). Optimize with parallel LLM calls. |
| Persona quality varies | Inconsistent value | Curated archetype library with tested prompts. Quality scoring on outputs. |
| Competition copies the approach | Market share loss | Speed to market. Industry pack depth. Network effects from shared results. |
