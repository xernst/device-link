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

### 3.2 Worldview Dimensions

The key differentiator. Two "Skeptics" with different worldviews object to completely different things. Each persona gets one modifier per dimension, layered on top of their psychographic archetype.

**7 Dimensions, 35 Modifiers:**

**Political Orientation** (7 modifiers) — affects trust in institutions, reaction to corporate messaging:
- Progressive, Moderate Left, Centrist, Moderate Right, Conservative, Libertarian, Apolitical

**Religious / Spiritual** (4 modifiers) — affects reaction to values-based messaging, moral framing:
- Secular, Spiritual Not Religious, Mainstream Religious, Devout

**Cultural Orientation** (5 modifiers) — affects response to individualism vs. collectivism:
- Individualist, Collectivist, Traditionalist, Cosmopolitan, Multicultural

**Economic Worldview** (4 modifiers) — affects reaction to pricing, brand positioning, consumption:
- Free Market, Conscious Capitalist, Anti-Consumerist, Aspiring Affluent

**Media Diet** (5 modifiers) — affects what sources they trust, how they verify claims:
- Mainstream, Alternative Media, Academic, Social Media Native, News Avoidant

**Trust Orientation** (4 modifiers) — affects who they believe, what evidence they need:
- Institution-Trusting, Peer-Trusting, Self-Reliant, Authority-Skeptical

**Generational Identity** (4 modifiers) — beyond just age, the cultural imprint:
- Gen Z (Digital Native), Millennial (Pragmatic Idealist), Gen X (Independent Skeptic), Boomer (Established)

Each modifier carries:
- **Trust modifiers** — numeric shifts to trust in different message types (e.g., Libertarian: government endorsement -0.3, decentralization claims +0.3)
- **Positive triggers** — phrases that activate engagement (e.g., Anti-Consumerist: "buy less", "built to last", "repair")
- **Negative triggers** — phrases that activate resistance (e.g., Anti-Consumerist: "limited edition", "flash sale", "FOMO")
- **Sensitivity topics** — subjects where strong opinions emerge (e.g., Devout: "sexuality in marketing", "traditional family")

### 3.3 How Dimensions Combine

A persona's reaction to marketing is the intersection of all their dimensions:

```
Example: "Sarah, 34, Skeptic × Progressive × Secular × Anti-Consumerist × Academic × Self-Reliant"

Sarah sees an ad for a new productivity SaaS:
- Skeptic archetype: asks hard questions, needs proof → "Where's the evidence?"
- Progressive worldview: checks for ethical labor practices → "Who built this?"
- Secular: ignores any inspirational/spiritual framing → skips the "find your purpose" copy
- Anti-Consumerist: resistant to upgrade cycles → "Will this replace 3 tools or add another?"
- Academic media diet: wants data, not testimonials → "Show me the peer-reviewed study"
- Self-Reliant trust: needs to try it herself → "Where's the free tier?"

vs.

"Mike, 28, Skeptic × Libertarian × Spiritual × Free Market × Alternative Media × Authority-Skeptical"

Same archetype, completely different objections:
- Skeptic archetype: same hard questions → "Prove it works"
- Libertarian worldview: checks for vendor lock-in → "Can I export my data?"
- Spiritual: open to mindfulness angle → doesn't mind "intentional productivity"
- Free Market: respects premium pricing if quality → "Is the paid tier worth it?"
- Alternative media: distrusts "as seen in TechCrunch" → "Who's really behind this?"
- Authority-Skeptical: won't trust enterprise endorsements → "Fortune 500 use it? So what."
```

### 3.4 Industry Packs

Pre-configured crowd compositions with both archetype AND worldview distributions:

- **SaaS B2B**: heavy Pragmatists + Experts, skews Centrist/Moderate, Institution-Trusting, Free Market
- **E-commerce DTC**: heavy Early Adopters + Aspirational, skews Progressive/Moderate Left, Social Native, Peer-Trusting
- **Fintech**: heavy Skeptics + Experts, mixed political, Academic/Mainstream media, Self-Reliant
- **Health/Wellness**: heavy Aspirational + Overwhelmed, skews Spiritual, Peer-Trusting, Conscious Capitalist
- **Creator Economy**: heavy Influencers + Early Adopters, skews Gen Z, Social Native, Individualist
- **Enterprise Sales**: heavy Pragmatists + Loyalists + Experts, skews Moderate Right/Centrist, Institution-Trusting
- **Consumer App**: heavy Early Adopters + Lurkers + Influencers, skews Gen Z/Millennial, Social Native

### 3.5 Persona Generation Flow

```
User provides:
  - Target audience description (natural language)
  - Industry pack (optional, for defaults)
  - Any specific persona or worldview overrides

System generates:
  1. Parse audience description → map to archetype distribution
  2. Apply industry pack defaults (archetypes + worldviews)
  3. Generate N unique personas by combining:
     - Base archetype (personality, decision patterns, objection style)
     - Demographic modifiers (age, role, tech level)
     - Worldview modifiers (1 per dimension, 7 total)
     - Aggregated trust profile, triggers, and sensitivity topics
     - Unique backstory + current situation (LLM-generated)
     - Social graph position (influencer, connector, peripheral)
  4. Build social graph (who knows whom, who influences whom)
```

Each generated persona has:
- **Name & background** (realistic, diverse)
- **Archetype blend** (e.g., 60% Skeptic + 30% Expert + 10% Pragmatist)
- **Worldview profile** (one modifier per dimension, 7 total)
- **Trust profile** — merged numeric modifiers across all worldviews
- **Positive triggers** — aggregated phrases that activate engagement
- **Negative triggers** — aggregated phrases that activate resistance
- **Sensitivity topics** — subjects that provoke strong reactions
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
- Engagement filter determines which seeds actively engage (~20%) vs. scroll past

**Phase 2: Initial Reactions (Turns 1-2)**
- Each exposed persona decides: ignore, read, react, comment, share
- Decision based on persona archetype + material relevance + attention budget
- Comments and reactions generated via **batched Haiku calls** (5-10 agents per call, structured JSON output)
- Each action has a probability weight (Skeptics less likely to share, Influencers more likely)
- Non-engaging agents handled by rule-based filter (no LLM cost)

**Phase 3: Spread & Discussion (Turns 3-5)**
- Shared content reaches connected personas in the social graph
- "Social proof" modifier: seeing friends engage increases engagement probability
- Debates emerge: Skeptics challenge, Early Adopters defend, Experts weigh in
- Some personas see competitors' responses and react
- Viral threshold: if share rate exceeds threshold, exponential spread begins
- Key inflection moments (viral breakout, pile-on) escalated to **Sonnet** for higher-quality generation

**Phase 4: Settling (Turns 6-7)**
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

## 12. Cost Optimization Strategy

**Decision**: Separate repo (clean, independent product). Name TBD.

### The Problem (Naive Approach)
A 50-agent, 10-turn simulation = ~500 LLM calls. At Claude Sonnet pricing (~$3/M input, $15/M output), a single sim could cost $0.50-$2.00. At $49/mo for 20 sims, that's $10-$40 in LLM costs vs $49 revenue. Thin margins, doesn't scale.

### The Solution (Optimized Approach)

**1. Batched reactions** — Don't make 1 LLM call per agent per turn. Instead, batch 5-10 agents into a single structured-output prompt: "Given these 10 personas, how does each react to this post?" One call returns 10 reactions. Reduces calls by ~8x.

**2. Engagement filtering** — In real social media, ~80% of users scroll past any given post. Use probability-based rules (archetype engagement rates × content relevance score) to determine who engages each turn. Only call LLM for the ~20% who do something interesting. The rest get rule-based "ignored" / "scrolled past" actions. Reduces calls by ~5x.

**3. Tiered model usage** — Use Claude Haiku ($0.25/M input, $1.25/M output) for bulk reaction turns. Reserve Claude Sonnet for:
   - Persona generation (1 call, quality matters)
   - Final analysis + recommendations report (1-2 calls, quality matters)
   - Key inflection moments (when content goes viral or gets dunked on)

**4. Fewer turns** — 7 turns captures the full dynamics (seed → react → spread → settle). 15 is overkill. Phase structure:
   - Turn 0: Seeding (material hits seed agents)
   - Turns 1-2: Initial reactions
   - Turns 3-5: Spread & discussion
   - Turns 6-7: Settling + final actions

**5. Prompt caching** — Persona definitions are static per simulation. Use system prompt caching to avoid re-tokenizing the same persona context on every turn. Saves ~90% on persona token costs for cached hits.

### Optimized Cost Math

```
Standard sim (50 agents, 7 turns):

Persona generation:    1 Sonnet call    ~2K tokens out  = $0.03
Engagement filtering:  Rule-based       ~0 LLM cost     = $0.00
Batched reactions:     ~50-60 Haiku calls (batches of ~8-10 active agents)
                       ~500 tokens avg per call
                       ~30K total tokens                = $0.01-$0.04
Final analysis:        2 Sonnet calls   ~4K tokens out  = $0.06
────────────────────────────────────────────────────────────────
Total per simulation:                                   ≈ $0.05-$0.15

At Starter plan ($49/mo, 20 sims):
  LLM cost: $1.00-$3.00/mo
  Margin: 94-98%

At Pro plan ($149/mo, 100 sims):
  LLM cost: $5.00-$15.00/mo
  Margin: 90-97%
```

### Key Technical Decisions (Resolved)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Where to build | Separate repo | Clean product, independent deploy cycle |
| Reaction model | Batched Haiku | 10-15x cheaper than individual Sonnet calls |
| Engagement model | Hybrid (rules + LLM) | Only pay for interesting reactions |
| Persona consistency | Cached system prompts + trait summaries | Balance cost vs. consistency |
| Turn count | 7 turns (down from 15) | Captures full dynamics without waste |
| Name | TBD | Working name: CrowdTest |

---

## 13. Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM costs too high per sim | Unprofitable unit economics | **Solved**: Batched Haiku calls + engagement filtering = $0.05-$0.15/sim (94%+ margins). See §12. |
| Simulations feel fake/useless | No product-market fit | Heavy prompt engineering investment. Real A/B test validation against actual campaign data. |
| Slow simulation (>5 min) | Poor UX, users bounce | Progressive results (show feed as it generates). Parallel batched calls. 7 turns = faster. |
| Persona quality varies | Inconsistent value | Curated archetype library with tested prompts. Quality scoring on outputs. |
| Haiku quality too low for reactions | Unrealistic social feed | Fallback to Sonnet for key moments. Prompt engineering for Haiku-specific structured outputs. |
| Competition copies the approach | Market share loss | Speed to market. Industry pack depth. Network effects from shared results. |
