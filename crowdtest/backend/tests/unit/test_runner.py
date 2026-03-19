"""Unit tests for simulation runner: engagement filtering, action selection,
cringe cascades, meme mutations, worldview collisions."""

import asyncio
import random

import pytest

from app.services.simulation.archetypes import ARCHETYPES
from app.services.simulation.graph import build_social_graph
from app.services.simulation.humor import ContentHumorProfile, HumorTone
from app.services.simulation.personas import build_crowd_distribution, generate_persona_skeleton
from app.services.simulation.runner import (
    ActionType,
    AgentMemory,
    EnvironmentConfig,
    Platform,
    Sentiment,
    SimulationState,
    _check_worldview_collision,
    _pick_action_and_sentiment,
    compute_social_proof,
    compute_controversy,
    initialize_simulation,
    run_simulation,
    should_engage,
)


def _make_persona(**overrides) -> dict:
    """Build a minimal test persona dict."""
    base = {
        "id": "agent_000",
        "primary_archetype": "pragmatist",
        "engagement_rate": 0.5,
        "share_rate": 0.2,
        "influence_weight": 0.5,
        "communication_style": "measured",
        "worldview_ids": {"humor": "dry_wit"},
        "positive_triggers": [],
        "negative_triggers": [],
        "sensitivity_topics": [],
    }
    base.update(overrides)
    return base


def _make_state(
    material: str = "Test product launch",
    humor_profile=None,
    crowd_size: int = 20,
) -> SimulationState:
    """Build a minimal simulation state for testing."""
    personas = [
        generate_persona_skeleton(i, "pragmatist", "saas_b2b")
        for i in range(crowd_size)
    ]
    influence_map = {p["id"]: p["influence_weight"] for p in personas}
    graph = build_social_graph([p["id"] for p in personas], influence_map)
    return initialize_simulation(
        material_content=material,
        personas=personas,
        graph=graph,
        env_config=EnvironmentConfig(crowd_size=crowd_size, max_rounds=10),
        humor_profile=humor_profile,
    )


class TestWorldviewCollision:
    """Test worldview trigger collision detection."""

    def test_no_triggers_returns_zero(self):
        persona = _make_persona()
        score = _check_worldview_collision(persona, "Buy our product today!")
        assert score == 0.0

    def test_negative_triggers_go_negative(self):
        persona = _make_persona(negative_triggers=["pride", "woke", "inclusion"])
        score = _check_worldview_collision(persona, "Celebrating Pride month with inclusion for all!")
        assert score < -0.2, f"Should be negative, got {score}"

    def test_positive_triggers_go_positive(self):
        persona = _make_persona(positive_triggers=["innovation", "data-driven", "ROI"])
        score = _check_worldview_collision(persona, "Data-driven innovation with proven ROI")
        assert score > 0.2, f"Should be positive, got {score}"

    def test_mixed_triggers_polarize(self):
        """When both positive and negative triggers fire, dominant direction wins."""
        persona = _make_persona(
            positive_triggers=["authentic"],
            negative_triggers=["woke", "pride", "inclusion"],
        )
        score = _check_worldview_collision(
            persona, "An authentic celebration of Pride and inclusion"
        )
        # 3 negative triggers vs 1 positive → should be negative
        assert score < 0, f"More negative triggers should win, got {score}"

    def test_sensitivity_topics_amplify(self):
        persona = _make_persona(
            negative_triggers=["woke"],
            sensitivity_topics=["performative activism"],
        )
        score_without = _check_worldview_collision(
            _make_persona(negative_triggers=["woke"]),
            "Join our woke performative activism campaign"
        )
        score_with = _check_worldview_collision(
            persona,
            "Join our woke performative activism campaign"
        )
        assert score_with < score_without, "Sensitivity topics should amplify negative"

    def test_case_insensitive(self):
        persona = _make_persona(negative_triggers=["FOMO", "viral"])
        score = _check_worldview_collision(persona, "Don't miss this fomo-inducing viral moment!")
        assert score < 0


class TestShouldEngage:
    """Test the engagement filter."""

    def test_high_engagement_rate_engages_more(self):
        """Run 100 trials; high engagement rate should produce more True."""
        state = _make_state()
        high = _make_persona(id="high", engagement_rate=0.9)
        low = _make_persona(id="low", engagement_rate=0.1)
        mem = AgentMemory(persona_id="test")

        random.seed(42)
        high_count = sum(should_engage(high, mem, state) for _ in range(200))
        random.seed(42)
        low_count = sum(should_engage(low, mem, state) for _ in range(200))
        assert high_count > low_count * 2, f"High ({high_count}) should be >> Low ({low_count})"

    def test_humor_compatibility_modifies_engagement(self):
        """Meme natives engage more with meme content than no-humor personas."""
        meme_profile = ContentHumorProfile(
            primary_tone=HumorTone.MEME,
            execution_score=0.8,
            engagement_multiplier=1.5,
        )
        state = _make_state(humor_profile=meme_profile)

        meme_native = _make_persona(
            id="meme", engagement_rate=0.5,
            worldview_ids={"humor": "meme_native"},
        )
        no_humor = _make_persona(
            id="nohum", engagement_rate=0.5,
            worldview_ids={"humor": "no_humor"},
        )
        mem = AgentMemory(persona_id="test")

        random.seed(42)
        meme_count = sum(should_engage(meme_native, mem, state) for _ in range(200))
        random.seed(42)
        nohum_count = sum(should_engage(no_humor, mem, state) for _ in range(200))
        assert meme_count > nohum_count, f"Meme native ({meme_count}) should engage more than no-humor ({nohum_count})"

    def test_worldview_collision_drives_engagement(self):
        """Outraged personas engage MORE (to express outrage)."""
        state = _make_state(material="Celebrate pride and inclusion this month!")
        triggered = _make_persona(
            id="trig", engagement_rate=0.3,
            negative_triggers=["pride", "inclusion"],
        )
        neutral = _make_persona(
            id="neut", engagement_rate=0.3,
        )
        mem = AgentMemory(persona_id="test")

        random.seed(42)
        trig_count = sum(should_engage(triggered, mem, state) for _ in range(200))
        random.seed(42)
        neut_count = sum(should_engage(neutral, mem, state) for _ in range(200))
        assert trig_count > neut_count, f"Triggered ({trig_count}) should engage more than neutral ({neut_count})"


class TestActionSelection:
    """Test humor-aware and worldview-aware action selection."""

    def test_cringe_dunk_path(self):
        """Meme natives facing cringe should screenshot/QT dunk."""
        cringe_profile = ContentHumorProfile(
            primary_tone=HumorTone.CRINGE_ATTEMPT,
            cringe_probability=0.8,
            engagement_multiplier=1.5,
            share_multiplier=1.5,
        )
        state = _make_state(humor_profile=cringe_profile)
        state.exposed.update(p["id"] for p in state.personas)

        meme_persona = _make_persona(
            worldview_ids={"humor": "meme_native"},
        )

        dunk_actions = set()
        for _ in range(100):
            action, sentiment = _pick_action_and_sentiment(meme_persona, Platform.TWITTER, state)
            dunk_actions.add(action)

        # Should see dunking actions
        expected_dunks = {ActionType.QUOTE, ActionType.SCREENSHOT, ActionType.COMMENT, ActionType.DM}
        assert dunk_actions & expected_dunks, f"Should produce dunk actions, got {dunk_actions}"

    def test_tone_deaf_path(self):
        """Tone-deaf content (not humorous but cringey) should trigger negative reactions."""
        tone_deaf_profile = ContentHumorProfile(
            primary_tone=HumorTone.NONE,  # not trying to be funny
            cringe_probability=0.85,  # but wildly out of touch
            screenshot_bait=0.9,
            engagement_multiplier=2.0,
            share_multiplier=2.0,
        )
        state = _make_state(humor_profile=tone_deaf_profile)
        state.exposed.update(p["id"] for p in state.personas)

        persona = _make_persona()
        sentiments = []
        for _ in range(100):
            _, sentiment = _pick_action_and_sentiment(persona, Platform.TWITTER, state)
            sentiments.append(sentiment)

        negative_count = sum(1 for s in sentiments if s in (Sentiment.NEGATIVE, Sentiment.HOSTILE))
        assert negative_count > 40, f"Tone-deaf should get >40% negative, got {negative_count}%"

    def test_worldview_outrage_path(self):
        """Content triggering worldview collision should produce outrage actions."""
        state = _make_state(material="Celebrate pride and inclusion! Stand with the movement!")
        persona = _make_persona(
            negative_triggers=["pride", "inclusion", "movement", "stand with"],
        )

        outrage_actions = set()
        for _ in range(100):
            action, sentiment = _pick_action_and_sentiment(persona, Platform.TWITTER, state)
            outrage_actions.add(action)

        expected_outrage = {ActionType.QUOTE, ActionType.COMMENT, ActionType.SCREENSHOT,
                          ActionType.DM, ActionType.BLOCK, ActionType.REPORT, ActionType.SHARE}
        overlap = outrage_actions & expected_outrage
        assert len(overlap) >= 3, f"Should produce diverse outrage actions, got {outrage_actions}"

    def test_good_meme_drives_dark_social(self):
        """Good meme content should produce DM/screenshot actions."""
        meme_profile = ContentHumorProfile(
            primary_tone=HumorTone.MEME,
            execution_score=0.9,
            screenshot_bait=0.8,
            engagement_multiplier=2.0,
            share_multiplier=2.0,
            dark_social_modifier=2.0,
        )
        state = _make_state(humor_profile=meme_profile)

        persona = _make_persona(worldview_ids={"humor": "meme_native"})
        actions = []
        for _ in range(200):
            action, _ = _pick_action_and_sentiment(persona, Platform.TWITTER, state)
            actions.append(action)

        dark_social = sum(1 for a in actions if a in (ActionType.DM, ActionType.SCREENSHOT))
        assert dark_social > 10, f"Good memes should drive dark social, got {dark_social}/200"


class TestCascadeMechanics:
    """Test viral and cringe cascades."""

    def test_cringe_cascade_spreads_negative_opinion(self):
        """Cringe cascade should shift exposed agents' opinion negative."""
        cringe_profile = ContentHumorProfile(
            primary_tone=HumorTone.CRINGE_ATTEMPT,
            cringe_probability=0.8,
            engagement_multiplier=1.5,
            share_multiplier=1.5,
        )
        state = _make_state(humor_profile=cringe_profile, crowd_size=30)

        # Record starting opinions
        start_opinions = {pid: m.opinion_score for pid, m in state.memories.items()}

        # Run simulation
        final = asyncio.get_event_loop().run_until_complete(run_simulation(state))

        # Check that cringe cascades occurred
        assert len(final.cringe_cascades) > 0, "Should have cringe cascades"

        # Check that opinions drifted negative
        end_opinions = {pid: m.opinion_score for pid, m in final.memories.items()}
        negative_drift_count = sum(
            1 for pid in start_opinions
            if end_opinions.get(pid, 0) < start_opinions[pid]
        )
        assert negative_drift_count > 5, f"Cringe should push opinions negative, only {negative_drift_count} drifted"

    def test_meme_mutations_from_remixable_content(self):
        """Remixable content should produce meme mutations."""
        meme_profile = ContentHumorProfile(
            primary_tone=HumorTone.SHITPOST,
            execution_score=0.8,
            remixability=0.8,
            engagement_multiplier=2.0,
            share_multiplier=2.0,
        )
        state = _make_state(humor_profile=meme_profile, crowd_size=50)
        final = asyncio.get_event_loop().run_until_complete(run_simulation(state))

        assert len(final.meme_mutations) > 0, "Remixable content should produce mutations"

    def test_no_mutations_from_low_remixability(self):
        """Low remixability content should produce few/no mutations."""
        profile = ContentHumorProfile(
            primary_tone=HumorTone.NONE,
            remixability=0.0,
            engagement_multiplier=1.0,
            share_multiplier=1.0,
        )
        state = _make_state(humor_profile=profile, crowd_size=30)
        final = asyncio.get_event_loop().run_until_complete(run_simulation(state))

        assert len(final.meme_mutations) == 0, f"Should have 0 mutations, got {len(final.meme_mutations)}"


class TestFullSimulation:
    """End-to-end simulation tests."""

    def test_simulation_completes(self):
        """Simulation should run to completion without errors."""
        state = _make_state(crowd_size=20)
        final = asyncio.get_event_loop().run_until_complete(run_simulation(state))
        assert final.current_round > 0
        assert len(final.all_actions) > 0
        assert len(final.exposed) > 0

    def test_humor_content_gets_more_engagement(self):
        """Content with humor should produce more engagement than without."""
        random.seed(42)
        boring_state = _make_state(crowd_size=30)
        boring_final = asyncio.get_event_loop().run_until_complete(run_simulation(boring_state))

        random.seed(42)
        funny_profile = ContentHumorProfile(
            primary_tone=HumorTone.MEME,
            execution_score=0.9,
            engagement_multiplier=2.0,
            share_multiplier=2.0,
            viral_threshold_modifier=0.5,
        )
        funny_state = _make_state(crowd_size=30, humor_profile=funny_profile)
        funny_final = asyncio.get_event_loop().run_until_complete(run_simulation(funny_state))

        boring_engaged = len(boring_final.engaged)
        funny_engaged = len(funny_final.engaged)
        assert funny_engaged >= boring_engaged, f"Funny ({funny_engaged}) should engage >= boring ({boring_engaged})"

    def test_linkedin_cringe_produces_cringe_cascades(self):
        """LinkedIn cringe scenario should produce cringe cascades."""
        cringe_profile = ContentHumorProfile(
            primary_tone=HumorTone.CRINGE_ATTEMPT,
            execution_score=0.15,
            cringe_probability=0.8,
            screenshot_bait=0.7,
            quote_tweet_bait=0.85,
            engagement_multiplier=1.5,
            share_multiplier=1.5,
            comment_multiplier=2.0,
            viral_threshold_modifier=0.5,
            dark_social_modifier=2.0,
        )
        state = _make_state(
            material="POV: You just told your team 😂🚀 Drop a 🔥! #SaaS #Innovation",
            humor_profile=cringe_profile,
            crowd_size=50,
        )
        final = asyncio.get_event_loop().run_until_complete(run_simulation(state))

        assert len(final.cringe_cascades) > 0, "LinkedIn cringe should produce cringe cascades"

        # Check hostile/negative sentiment exists
        hostile_actions = [
            a for a in final.all_actions
            if a.sentiment in (Sentiment.HOSTILE, Sentiment.NEGATIVE)
        ]
        assert len(hostile_actions) > 10, f"Should have hostile reactions, got {len(hostile_actions)}"

    def test_opinion_clusters_form(self):
        """Simulation should produce opinion clusters by archetype."""
        state = _make_state(crowd_size=30)
        final = asyncio.get_event_loop().run_until_complete(run_simulation(state))
        assert len(final.opinion_clusters) > 0, "Should produce opinion clusters"
