"""Pre-designed persona archetypes. The foundation of every simulation."""

from dataclasses import dataclass


@dataclass
class Archetype:
    id: str
    name: str
    description: str
    engagement_rate: float  # base probability of engaging with content (0-1)
    share_rate: float  # probability of sharing if engaged (0-1)
    objection_tendency: float  # how likely to raise objections (0-1)
    influence_weight: float  # how much their actions affect others (0-1)
    communication_style: str  # how they express themselves


ARCHETYPES: dict[str, Archetype] = {
    "skeptic": Archetype(
        id="skeptic",
        name="The Skeptic",
        description="Needs proof, asks hard questions, resistant to hype",
        engagement_rate=0.35,
        share_rate=0.10,
        objection_tendency=0.85,
        influence_weight=0.6,
        communication_style="direct, questioning, demands evidence",
    ),
    "early_adopter": Archetype(
        id="early_adopter",
        name="The Early Adopter",
        description="Excited by novelty, forgives rough edges, shares discoveries",
        engagement_rate=0.70,
        share_rate=0.60,
        objection_tendency=0.15,
        influence_weight=0.7,
        communication_style="enthusiastic, forward-looking, uses superlatives",
    ),
    "pragmatist": Archetype(
        id="pragmatist",
        name="The Pragmatist",
        description="Does it solve my problem? ROI-focused, comparison shopper",
        engagement_rate=0.40,
        share_rate=0.20,
        objection_tendency=0.50,
        influence_weight=0.5,
        communication_style="measured, practical, asks about specifics",
    ),
    "loyalist": Archetype(
        id="loyalist",
        name="The Loyalist",
        description="Brand-attached, defensive of current tools, high switching cost",
        engagement_rate=0.25,
        share_rate=0.15,
        objection_tendency=0.70,
        influence_weight=0.4,
        communication_style="comparative, defensive, mentions incumbent tools",
    ),
    "influencer": Archetype(
        id="influencer",
        name="The Influencer",
        description="Shares opinions publicly, shapes others' views, status-driven",
        engagement_rate=0.80,
        share_rate=0.75,
        objection_tendency=0.25,
        influence_weight=0.9,
        communication_style="opinionated, public-facing, creates threads",
    ),
    "lurker": Archetype(
        id="lurker",
        name="The Lurker",
        description="Reads everything, shares nothing, decides privately",
        engagement_rate=0.10,
        share_rate=0.02,
        objection_tendency=0.05,
        influence_weight=0.1,
        communication_style="silent, occasional like, rarely comments",
    ),
    "budget_conscious": Archetype(
        id="budget_conscious",
        name="The Budget-Conscious",
        description="Price-sensitive, hunts deals, needs justification",
        engagement_rate=0.35,
        share_rate=0.25,
        objection_tendency=0.60,
        influence_weight=0.4,
        communication_style="asks about pricing, compares value, mentions alternatives",
    ),
    "expert": Archetype(
        id="expert",
        name="The Expert",
        description="Deep domain knowledge, detects BS instantly, values precision",
        engagement_rate=0.45,
        share_rate=0.30,
        objection_tendency=0.75,
        influence_weight=0.8,
        communication_style="technical, precise, corrects inaccuracies",
    ),
    "overwhelmed": Archetype(
        id="overwhelmed",
        name="The Overwhelmed",
        description="Too many options, decision fatigue, wants simplicity",
        engagement_rate=0.15,
        share_rate=0.05,
        objection_tendency=0.20,
        influence_weight=0.2,
        communication_style="confused, asks basic questions, wants summaries",
    ),
    "aspirational": Archetype(
        id="aspirational",
        name="The Aspirational",
        description="Wants to level up, motivated by success stories",
        engagement_rate=0.55,
        share_rate=0.45,
        objection_tendency=0.15,
        influence_weight=0.5,
        communication_style="optimistic, references goals, inspired by results",
    ),
}

# Pre-configured industry crowd compositions
INDUSTRY_PACKS: dict[str, dict[str, float]] = {
    "saas_b2b": {
        "pragmatist": 0.25,
        "expert": 0.20,
        "budget_conscious": 0.15,
        "skeptic": 0.15,
        "loyalist": 0.10,
        "lurker": 0.10,
        "early_adopter": 0.05,
    },
    "ecommerce_dtc": {
        "early_adopter": 0.20,
        "aspirational": 0.20,
        "budget_conscious": 0.20,
        "influencer": 0.15,
        "lurker": 0.10,
        "overwhelmed": 0.10,
        "pragmatist": 0.05,
    },
    "consumer_app": {
        "early_adopter": 0.25,
        "lurker": 0.20,
        "influencer": 0.20,
        "aspirational": 0.15,
        "overwhelmed": 0.10,
        "skeptic": 0.05,
        "pragmatist": 0.05,
    },
}
