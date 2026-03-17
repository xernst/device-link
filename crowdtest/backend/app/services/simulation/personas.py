"""Persona generator: archetype x demographics x worldviews → unique agent.

Each persona is a combination of:
1. Psychographic archetype (Skeptic, Influencer, etc.) — HOW they behave
2. Demographic modifiers (age, role, tech level) — WHO they are
3. Worldview dimensions (political, religious, cultural, economic, media, trust, generational) — WHAT they believe

The worldview dimensions are the key differentiator. Two "Skeptics" with different
political/cultural worldviews will object to completely different things.
"""

import random
from dataclasses import dataclass, field

from app.services.simulation.archetypes import ARCHETYPES, INDUSTRY_PACKS, Archetype
from app.services.simulation.worldviews import (
    ALL_DIMENSIONS,
    INDUSTRY_WORLDVIEW_DEFAULTS,
    WorldviewModifier,
)


@dataclass
class Persona:
    id: str
    name: str
    archetype: Archetype
    archetype_blend: dict[str, float]  # e.g. {"skeptic": 0.6, "expert": 0.3, "pragmatist": 0.1}
    age: int
    role: str
    tech_savviness: str
    company_size: str
    backstory: str  # LLM-generated
    communication_style: str
    influence_score: float  # 1-10
    engagement_rate: float  # computed from archetype blend
    share_rate: float
    worldviews: dict[str, WorldviewModifier] = field(default_factory=dict)  # dimension -> modifier
    positive_triggers: list[str] = field(default_factory=list)  # aggregated from worldviews
    negative_triggers: list[str] = field(default_factory=list)  # aggregated from worldviews
    sensitivity_topics: list[str] = field(default_factory=list)  # aggregated from worldviews
    connections: list[str] = field(default_factory=list)  # persona IDs


AGE_BANDS = {
    "gen_z": (18, 26),
    "millennial": (27, 42),
    "gen_x": (43, 58),
    "boomer": (59, 77),
}

# Map age bands to likely generational worldview for consistency
AGE_TO_GENERATIONAL = {
    "gen_z": "gen_z_native",
    "millennial": "millennial_pragmatist",
    "gen_x": "gen_x_independent",
    "boomer": "boomer_established",
}

ROLES = ["ic", "manager", "exec", "founder", "freelancer", "student"]
TECH_LEVELS = ["digital_native", "competent", "reluctant", "resistant"]
COMPANY_SIZES = ["solo", "startup", "smb", "mid_market", "enterprise"]


def _weighted_pick(options: dict[str, float]) -> str:
    """Pick a random key from a weighted distribution dict."""
    keys = list(options.keys())
    weights = [options[k] for k in keys]
    return random.choices(keys, weights=weights, k=1)[0]


def assign_worldviews(
    age_band: str,
    industry_pack: str | None = None,
    custom_worldviews: dict[str, dict[str, float]] | None = None,
) -> dict[str, str]:
    """Assign one worldview modifier per dimension for a persona.

    Returns dict of {dimension: modifier_id}.
    Uses industry defaults if available, otherwise uniform distribution.
    Generational dimension is linked to age band for consistency.
    """
    assignments: dict[str, str] = {}

    # Get industry-specific worldview distributions if available
    industry_dists = {}
    if industry_pack and industry_pack in INDUSTRY_WORLDVIEW_DEFAULTS:
        industry_dists = INDUSTRY_WORLDVIEW_DEFAULTS[industry_pack]

    for dimension, modifiers in ALL_DIMENSIONS.items():
        # Generational is tied to age band
        if dimension == "generational":
            assignments[dimension] = AGE_TO_GENERATIONAL.get(age_band, "millennial_pragmatist")
            continue

        # Use custom distribution if provided for this dimension
        if custom_worldviews and dimension in custom_worldviews:
            assignments[dimension] = _weighted_pick(custom_worldviews[dimension])
        # Use industry default if available
        elif dimension in industry_dists:
            assignments[dimension] = _weighted_pick(industry_dists[dimension])
        # Otherwise uniform
        else:
            assignments[dimension] = random.choice(list(modifiers.keys()))

    return assignments


def aggregate_triggers(worldview_ids: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    """Aggregate positive triggers, negative triggers, and sensitivity topics from all worldview dimensions."""
    positive = []
    negative = []
    sensitivity = []

    for dimension, modifier_id in worldview_ids.items():
        if dimension in ALL_DIMENSIONS and modifier_id in ALL_DIMENSIONS[dimension]:
            mod = ALL_DIMENSIONS[dimension][modifier_id]
            positive.extend(mod.positive_triggers)
            negative.extend(mod.negative_triggers)
            sensitivity.extend(mod.sensitivity_topics)

    # Deduplicate while preserving order
    return (
        list(dict.fromkeys(positive)),
        list(dict.fromkeys(negative)),
        list(dict.fromkeys(sensitivity)),
    )


def compute_trust_profile(worldview_ids: dict[str, str]) -> dict[str, float]:
    """Merge trust modifiers from all worldview dimensions into a single trust profile.

    When multiple dimensions modify the same trust factor, effects are averaged.
    This becomes part of the persona's prompt context for LLM calls.
    """
    trust_sums: dict[str, float] = {}
    trust_counts: dict[str, int] = {}

    for dimension, modifier_id in worldview_ids.items():
        if dimension in ALL_DIMENSIONS and modifier_id in ALL_DIMENSIONS[dimension]:
            mod = ALL_DIMENSIONS[dimension][modifier_id]
            for factor, value in mod.trust_modifiers.items():
                trust_sums[factor] = trust_sums.get(factor, 0.0) + value
                trust_counts[factor] = trust_counts.get(factor, 0) + 1

    return {k: trust_sums[k] / trust_counts[k] for k in trust_sums}


def build_crowd_distribution(
    crowd_size: int,
    industry_pack: str | None = None,
    custom_distribution: dict[str, float] | None = None,
) -> list[str]:
    """Return a list of archetype IDs for the crowd, based on distribution weights."""
    if custom_distribution:
        dist = custom_distribution
    elif industry_pack and industry_pack in INDUSTRY_PACKS:
        dist = INDUSTRY_PACKS[industry_pack]
    else:
        # Default even distribution
        all_ids = list(ARCHETYPES.keys())
        dist = {k: 1.0 / len(all_ids) for k in all_ids}

    # Normalize
    total = sum(dist.values())
    normalized = {k: v / total for k, v in dist.items()}

    # Allocate
    assignments = []
    for archetype_id, weight in normalized.items():
        count = round(crowd_size * weight)
        assignments.extend([archetype_id] * count)

    # Fix rounding (trim or pad)
    while len(assignments) > crowd_size:
        assignments.pop()
    while len(assignments) < crowd_size:
        assignments.append(random.choice(list(normalized.keys())))

    random.shuffle(assignments)
    return assignments


def generate_persona_skeleton(
    index: int,
    archetype_id: str,
    industry_pack: str | None = None,
    custom_worldviews: dict[str, dict[str, float]] | None = None,
) -> dict:
    """Generate a persona skeleton with archetype + demographics + worldviews.

    Returns dict for LLM enrichment (backstory, name, unique traits).
    """
    archetype = ARCHETYPES[archetype_id]
    age_band = random.choice(list(AGE_BANDS.keys()))
    age_min, age_max = AGE_BANDS[age_band]

    # Assign worldview modifiers
    worldview_ids = assign_worldviews(age_band, industry_pack, custom_worldviews)
    positive, negative, sensitivity = aggregate_triggers(worldview_ids)
    trust_profile = compute_trust_profile(worldview_ids)

    # Build worldview summary for LLM context
    worldview_summary = {}
    for dimension, modifier_id in worldview_ids.items():
        if dimension in ALL_DIMENSIONS and modifier_id in ALL_DIMENSIONS[dimension]:
            mod = ALL_DIMENSIONS[dimension][modifier_id]
            worldview_summary[dimension] = {
                "id": modifier_id,
                "label": mod.label,
                "description": mod.description,
            }

    return {
        "id": f"agent_{index:03d}",
        # Archetype
        "primary_archetype": archetype_id,
        "archetype_name": archetype.name,
        "archetype_description": archetype.description,
        # Demographics
        "age": random.randint(age_min, age_max),
        "age_band": age_band,
        "role": random.choice(ROLES),
        "tech_savviness": random.choice(TECH_LEVELS),
        "company_size": random.choice(COMPANY_SIZES),
        # Behavioral rates
        "engagement_rate": archetype.engagement_rate,
        "share_rate": archetype.share_rate,
        "influence_weight": archetype.influence_weight,
        "communication_style": archetype.communication_style,
        # Worldviews
        "worldview_ids": worldview_ids,
        "worldview_summary": worldview_summary,
        "trust_profile": trust_profile,
        "positive_triggers": positive,
        "negative_triggers": negative,
        "sensitivity_topics": sensitivity,
    }
