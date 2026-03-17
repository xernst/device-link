"""Simulation runner: the turn-based engine with batched LLM calls + engagement filtering."""

import random
from dataclasses import dataclass, field
from enum import Enum

from app.core.config import settings


class ActionType(str, Enum):
    IGNORE = "ignore"
    READ = "read"
    REACT = "react"  # like/emoji
    COMMENT = "comment"
    SHARE = "share"


@dataclass
class TurnAction:
    persona_id: str
    turn: int
    action: ActionType
    content: str | None = None  # comment text, if applicable
    triggered_by: str | None = None  # persona_id that caused exposure


@dataclass
class SimulationState:
    material_content: str
    platform: str  # twitter, linkedin, instagram, reddit
    personas: list[dict]  # enriched persona dicts
    graph: object  # SocialGraph
    turn: int = 0
    max_turns: int = 7
    exposed: set[str] = field(default_factory=set)  # persona IDs who've seen the material
    engaged: set[str] = field(default_factory=set)  # persona IDs who've engaged
    actions: list[TurnAction] = field(default_factory=list)
    social_proof_modifier: float = 1.0  # increases as more people engage


def should_engage(persona: dict, social_proof: float) -> bool:
    """Rule-based engagement filter. Returns True if this persona should get an LLM call."""
    base_rate = persona["engagement_rate"]
    adjusted = min(base_rate * social_proof, 0.95)  # cap at 95%
    return random.random() < adjusted


def compute_social_proof(state: SimulationState) -> float:
    """Social proof increases engagement probability as more agents engage."""
    if not state.exposed:
        return 1.0
    engagement_ratio = len(state.engaged) / max(len(state.exposed), 1)
    return 1.0 + (engagement_ratio * 0.5)  # up to 1.5x boost


def select_seeds(state: SimulationState, seed_count: int = 10) -> list[str]:
    """Pick initial seed personas (high-influence agents see the material first)."""
    sorted_personas = sorted(
        state.personas,
        key=lambda p: p["influence_weight"],
        reverse=True,
    )
    seeds = [p["id"] for p in sorted_personas[:seed_count]]
    return seeds


def batch_personas_for_llm(
    persona_ids: list[str],
    personas_map: dict[str, dict],
    batch_size: int | None = None,
) -> list[list[dict]]:
    """Group personas into batches for batched LLM calls."""
    if batch_size is None:
        batch_size = settings.batch_size
    personas = [personas_map[pid] for pid in persona_ids]
    return [personas[i:i + batch_size] for i in range(0, len(personas), batch_size)]


async def run_turn(state: SimulationState) -> list[TurnAction]:
    """Execute one simulation turn.

    1. Determine which exposed personas engage (rule-based filter)
    2. Batch engaging personas into groups
    3. Call LLM for each batch (batched Haiku calls)
    4. Process actions: shares expose new personas via social graph
    5. Update state

    Returns list of actions taken this turn.
    """
    turn_actions: list[TurnAction] = []

    # Build persona lookup
    personas_map = {p["id"]: p for p in state.personas}

    # Update social proof
    state.social_proof_modifier = compute_social_proof(state)

    # Filter: which exposed personas engage this turn?
    engaging = []
    for pid in state.exposed:
        if pid not in state.engaged:  # haven't engaged yet
            persona = personas_map[pid]
            if should_engage(persona, state.social_proof_modifier):
                engaging.append(pid)

    # Non-engaging personas get IGNORE actions (no LLM cost)
    for pid in state.exposed - state.engaged - set(engaging):
        turn_actions.append(TurnAction(
            persona_id=pid,
            turn=state.turn,
            action=ActionType.IGNORE,
        ))

    # Batch engaging personas for LLM calls
    batches = batch_personas_for_llm(engaging, personas_map)

    for batch in batches:
        # TODO: call batched Haiku here
        # For now, generate placeholder actions
        for persona in batch:
            action_type = _pick_action(persona)
            turn_actions.append(TurnAction(
                persona_id=persona["id"],
                turn=state.turn,
                action=action_type,
                content=None,  # LLM will generate this
            ))
            state.engaged.add(persona["id"])

            # Shares expose connected personas
            if action_type == ActionType.SHARE:
                # TODO: use graph.get_neighbors() to expose new personas
                pass

    state.actions.extend(turn_actions)
    state.turn += 1
    return turn_actions


def _pick_action(persona: dict) -> ActionType:
    """Temporary: rule-based action selection. Will be replaced by LLM."""
    r = random.random()
    if r < persona.get("share_rate", 0.2):
        return ActionType.SHARE
    elif r < 0.5:
        return ActionType.COMMENT
    elif r < 0.8:
        return ActionType.REACT
    else:
        return ActionType.READ
