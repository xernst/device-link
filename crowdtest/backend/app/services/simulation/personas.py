"""Persona generator: archetype x demographics → unique agent."""

import random
from dataclasses import dataclass, field

from app.services.simulation.archetypes import ARCHETYPES, INDUSTRY_PACKS, Archetype


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
    connections: list[str] = field(default_factory=list)  # persona IDs


AGE_BANDS = {
    "gen_z": (18, 26),
    "millennial": (27, 42),
    "gen_x": (43, 58),
    "boomer": (59, 77),
}

ROLES = ["ic", "manager", "exec", "founder", "freelancer", "student"]
TECH_LEVELS = ["digital_native", "competent", "reluctant", "resistant"]
COMPANY_SIZES = ["solo", "startup", "smb", "mid_market", "enterprise"]


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
) -> dict:
    """Generate a persona skeleton (without LLM backstory). Returns dict for LLM enrichment."""
    archetype = ARCHETYPES[archetype_id]
    age_band = random.choice(list(AGE_BANDS.keys()))
    age_min, age_max = AGE_BANDS[age_band]

    return {
        "id": f"agent_{index:03d}",
        "primary_archetype": archetype_id,
        "archetype_name": archetype.name,
        "archetype_description": archetype.description,
        "age": random.randint(age_min, age_max),
        "role": random.choice(ROLES),
        "tech_savviness": random.choice(TECH_LEVELS),
        "company_size": random.choice(COMPANY_SIZES),
        "engagement_rate": archetype.engagement_rate,
        "share_rate": archetype.share_rate,
        "influence_weight": archetype.influence_weight,
        "communication_style": archetype.communication_style,
    }
