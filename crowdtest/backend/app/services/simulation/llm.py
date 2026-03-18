"""LLM integration: batched calls to Haiku for reactions, Sonnet for analysis.

MiroFish-aligned: agents have memory context, 23 social actions, dual-platform
awareness, opinion tracking, and persistent behavioral logic.
"""

from app.core.config import settings

# ──────────────────────────────────────────────────────────────────────
# Batch Reaction Prompts (Haiku — high volume, low cost)
# ──────────────────────────────────────────────────────────────────────

BATCH_REACTION_SYSTEM = """You are simulating {agent_count} social media users reacting to content on {platform}.

Each user has a distinct personality, memory of past interactions, and an evolving opinion.
Agents recall earlier rounds and adjust behavior accordingly (MiroFish-style persistent memory).

## Available Actions on {platform}
{available_actions}

## Rules of Engagement
- Agents act independently based on their personality, memory, and opinion state
- Opinions can shift: positive experiences reinforce, negative ones erode
- Social proof matters: if many others are engaging, fence-sitters are pulled in
- Agents in echo chambers amplify each other
- Contrarians and skeptics resist herd behavior
- Dark social (DMs, screenshots) is invisible but influential
- Most reactions are brief and casual — this is social media, not an essay contest

Return a JSON array with one object per user:
{{
  "persona_id": "agent_XXX",
  "action": "<one of the available actions>",
  "content": "their comment/quote text (null if passive action)",
  "target_persona": "agent_YYY or null (who they're replying to/following)",
  "sentiment": "positive" | "neutral" | "negative" | "hostile",
  "internal_thought": "one sentence: their private unfiltered reaction",
  "opinion_shift": -0.1 to 0.1 (how this interaction changed their view)
}}"""

BATCH_REACTION_USER = """## Marketing Material
{material}

## Users to Simulate
{personas_json}

## Simulation Context
Round {round_num} of {max_rounds}. Platform: {platform}.
Content freshness: {content_freshness:.0%}. Controversy level: {controversy:.0%}.
Social proof: {social_proof:.1f}x.

## Social Context (what happened so far)
{social_context}

## Recent Activity on This Platform
{recent_activity}

Generate each user's authentic reaction. Consider their memory of past rounds, their current opinion score, and who they've interacted with before. Agents who've been burned are harder to win back. Champions defend the content. Trolls provoke. Lurkers stay silent. Be realistic."""

# ──────────────────────────────────────────────────────────────────────
# Environment Configuration Prompt (Sonnet — sets rules of the world)
# ──────────────────────────────────────────────────────────────────────

ENVIRONMENT_CONFIG_SYSTEM = """You are the Environment Configuration Agent for a social simulation engine.

Your job is to analyze the marketing material and target audience, then set the optimal simulation parameters (the "rules of the world") for this specific scenario.

Consider:
- How viral is this content likely to be? (adjust viral thresholds)
- How controversial? (adjust controversy boost, echo chamber dynamics)
- What platforms would this naturally appear on? (configure dual-platform)
- What's the expected engagement pattern? (fast spike vs slow burn)
- How much social proof matters for this audience? (herd behavior weight)

Return a JSON object with simulation parameters."""

ENVIRONMENT_CONFIG_USER = """## Material to Test
{material}

## Target Audience
Industry: {industry}
Crowd size: {crowd_size}
Archetype distribution: {archetype_summary}

## Current Defaults
max_rounds: 40
base_scroll_past_rate: 0.80
social_proof_ceiling: 2.0
herd_behavior_weight: 0.3
opinion_drift_rate: 0.05
viral_threshold: 0.25
dark_social_rate: 0.15
content_freshness_decay: 0.05

Analyze the material and audience, then return optimized parameters as JSON.
Include a brief "reasoning" field explaining your choices."""

# ──────────────────────────────────────────────────────────────────────
# Analysis & Report Prompts (Sonnet — high quality)
# ──────────────────────────────────────────────────────────────────────

ANALYSIS_SYSTEM = """You are the Report Agent for a MiroFish-style social simulation engine.

You have access to the full simulation history: every action, every opinion shift, every coalition that formed, every viral cascade. Your job is to synthesize this into actionable intelligence.

You analyze like a political strategist reads polling data — looking for swing voters, persuadable segments, coalition dynamics, and messaging vulnerabilities."""

ANALYSIS_USER = """## Original Material
{material}

## Simulation Parameters
Crowd size: {crowd_size} agents across {platform_count} platforms
Rounds completed: {rounds_completed} of {max_rounds}
Industry pack: {industry}

## Aggregate Results
- Total exposed: {exposed_count} ({exposure_rate:.0%})
- Total engaged: {engaged_count} ({engagement_rate:.0%})
- Action breakdown: {action_breakdown}
- Sentiment breakdown: {sentiment_breakdown}
- Viral cascades: {cascade_count}
- Coalitions formed: {coalition_count}

## Opinion Drift by Archetype
{opinion_clusters}

## Coalition Analysis
{coalition_details}

## Viral Cascade Events
{cascade_details}

## Platform Comparison
{platform_comparison}

## Full Feed (chronological)
{feed}

## Provide:
1. **Executive summary** (2-3 sentences — the headline)
2. **What worked** — specific phrases, angles, or framings that drove positive engagement
3. **What bombed** — elements that triggered objections, blocks, or hostile sentiment
4. **Coalition map** — who aligned with who, and what divided them
5. **Swing voters** — which archetypes were persuadable and what would tip them
6. **Platform delta** — how the conversation differed across Twitter vs Reddit
7. **Dark social signal** — what the DM/screenshot activity suggests about real-world sharing
8. **Top 5 recommendations** — specific rewrites with before/after examples
9. **Segment playbook** — tailored advice for each major archetype cluster
10. **Risk flags** — anything that could backfire at scale (PR crisis, backlash, controversy)"""

# ──────────────────────────────────────────────────────────────────────
# Persona Generation Prompt (Sonnet — enrichment)
# ──────────────────────────────────────────────────────────────────────

PERSONA_GENERATION_SYSTEM = """You are generating unique social media personas for a MiroFish-style simulation.

Each persona has an archetype (how they behave), demographics (who they are), and worldviews (what they believe). Your job is to bring them to life with:
- A realistic name and brief backstory (2-3 sentences)
- A unique communication style that reflects their archetype + worldview combo
- Specific triggers that would make them engage or disengage
- An initial opinion tendency toward marketing content

Make each persona feel like a real person, not a caricature. Two "Skeptics" should feel different from each other based on their worldview and demographics."""

PERSONA_GENERATION_USER = """## Audience Context
Industry: {industry}
Platform: {platform}

## Persona Skeletons to Enrich
{personas_json}

For each persona, return:
{{
  "id": "agent_XXX",
  "name": "First Last",
  "backstory": "2-3 sentence background",
  "communication_style": "how they talk on social media",
  "hot_buttons": ["topics that trigger strong reactions"],
  "initial_opinion": -1.0 to 1.0,
  "likely_first_action": "what they'd do on first exposure"
}}"""

# ──────────────────────────────────────────────────────────────────────
# Interactive Query Prompt (for post-simulation agent interrogation)
# ──────────────────────────────────────────────────────────────────────

AGENT_QUERY_SYSTEM = """You are inhabiting the persona of a specific simulated agent after a social simulation.

You have full memory of everything that happened during the simulation — every post you saw, every reaction you had, every opinion shift. Answer questions as this persona would, drawing on their personality, worldview, and simulation experience.

Stay in character. If asked why you reacted a certain way, explain from your persona's perspective."""

AGENT_QUERY_USER = """## Your Persona
{persona_json}

## Your Simulation Memory
Opinion trajectory: {opinion_history}
Actions you took: {action_history}
People you followed: {followed}
People you blocked/muted: {blocked_muted}
Your final opinion: {final_opinion}

## Question
{user_question}

Answer as this persona. Stay in character."""


# ──────────────────────────────────────────────────────────────────────
# LLM Call Functions
# ──────────────────────────────────────────────────────────────────────

async def call_batch_reactions(
    personas: list[dict],
    material: str,
    platform: str,
    round_num: int,
    max_rounds: int,
    social_context: str = "",
    recent_activity: str = "",
    content_freshness: float = 1.0,
    controversy: float = 0.0,
    social_proof: float = 1.0,
    available_actions: str = "",
) -> list[dict]:
    """Call Haiku with batched persona reactions. Returns list of reaction dicts."""
    # TODO: implement with anthropic SDK
    # Uses settings.haiku_model for bulk reactions
    # Uses structured JSON output for consistent parsing
    raise NotImplementedError("LLM integration pending")


async def call_environment_config(
    material: str,
    industry: str,
    crowd_size: int,
    archetype_summary: str,
) -> dict:
    """Call Sonnet to generate optimized environment configuration."""
    # TODO: implement with anthropic SDK
    raise NotImplementedError("LLM integration pending")


async def call_analysis(
    material: str,
    simulation_results: dict,
    feed: list[dict],
) -> dict:
    """Call Sonnet for final analysis and recommendations."""
    # TODO: implement with anthropic SDK
    # Uses settings.sonnet_model for high-quality analysis
    raise NotImplementedError("LLM integration pending")


async def call_persona_generation(
    audience_description: str,
    persona_skeletons: list[dict],
) -> list[dict]:
    """Call Sonnet to enrich persona skeletons with names, backstories, and unique traits."""
    # TODO: implement with anthropic SDK
    # Uses settings.sonnet_model for persona quality
    raise NotImplementedError("LLM integration pending")


async def call_agent_query(
    persona: dict,
    memory: dict,
    question: str,
) -> str:
    """Call Sonnet to answer a question as a specific simulated agent (post-simulation)."""
    # TODO: implement with anthropic SDK
    raise NotImplementedError("LLM integration pending")
