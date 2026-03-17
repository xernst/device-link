"""LLM integration: batched calls to Haiku for reactions, Sonnet for analysis."""

from app.core.config import settings

# Prompt templates for batched persona reactions
BATCH_REACTION_SYSTEM = """You are simulating {agent_count} social media users reacting to a marketing post on {platform}.

Each user has a distinct personality. For each user, decide their reaction and generate their response.

Return a JSON array with one object per user:
{{
  "persona_id": "agent_XXX",
  "action": "ignore" | "read" | "react" | "comment" | "share",
  "content": "their comment or share text (null if ignore/read/react)",
  "sentiment": "positive" | "neutral" | "negative" | "hostile",
  "internal_thought": "one sentence explaining their private reaction"
}}"""

BATCH_REACTION_USER = """## Marketing Material
{material}

## Users to Simulate
{personas_json}

## Context
Turn {turn} of simulation. Platform: {platform}.
{social_context}

Generate each user's authentic reaction based on their personality. Be realistic — most people's reactions are brief and casual."""

ANALYSIS_SYSTEM = """You are an expert marketing analyst reviewing the results of a social simulation. Analyze the engagement patterns, identify what worked and what didn't, and provide actionable recommendations."""

ANALYSIS_USER = """## Original Material
{material}

## Simulation Results
- Total agents: {total_agents}
- Engaged: {engaged_count} ({engagement_rate}%)
- Actions: {action_breakdown}
- Sentiment: {sentiment_breakdown}

## Full Feed
{feed}

Provide:
1. Executive summary (2-3 sentences)
2. What worked (specific phrases/angles that drove engagement)
3. What didn't (elements that triggered objections)
4. Top 3 recommendations with suggested rewrites
5. Segment-specific advice (which archetypes loved/hated it and why)"""


async def call_batch_reactions(
    personas: list[dict],
    material: str,
    platform: str,
    turn: int,
    social_context: str = "",
) -> list[dict]:
    """Call Haiku with batched persona reactions. Returns list of reaction dicts."""
    # TODO: implement with anthropic SDK
    # Uses settings.haiku_model for bulk reactions
    # Uses structured JSON output for consistent parsing
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
