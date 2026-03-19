"""Edge case and stress tests for the simulation engine."""

import asyncio
import random

from app.services.simulation.graph import build_social_graph
from app.services.simulation.humor import ContentHumorProfile, HumorTone
from app.services.simulation.personas import build_crowd_distribution, generate_persona_skeleton
from app.services.simulation.runner import (
    ActionType,
    EnvironmentConfig,
    Platform,
    Sentiment,
    SimulationState,
    _check_worldview_collision,
    _pick_action_and_sentiment,
    _sentiment_to_opinion_delta,
    compute_controversy,
    compute_social_proof,
    detect_coalitions,
    get_available_actions,
    initialize_simulation,
    propagate_influence,
    run_simulation,
    select_seeds,
    should_engage,
)


_run = asyncio.get_event_loop().run_until_complete


# ──────────────────────────────────────────────────────────────────────
# Edge Cases: Empty / Minimal Inputs
# ──────────────────────────────────────────────────────────────────────

class TestEmptyInputs:
    """Test behavior with empty or minimal inputs."""

    def test_simulation_with_single_persona(self):
        persona = generate_persona_skeleton(0, "skeptic")
        graph = build_social_graph([persona["id"]], {persona["id"]: 0.5})
        state = initialize_simulation("Test content", [persona], graph)
        final = _run(run_simulation(state))
        assert final.current_round > 0

    def test_simulation_with_zero_rounds(self):
        persona = generate_persona_skeleton(0, "skeptic")
        graph = build_social_graph([persona["id"]], {persona["id"]: 0.5})
        config = EnvironmentConfig(max_rounds=0)
        state = initialize_simulation("Test content", [persona], graph, config)
        final = _run(run_simulation(state))
        assert final.current_round == 0
        assert len(final.all_actions) == 0

    def test_empty_content_string(self):
        persona = generate_persona_skeleton(0, "skeptic")
        graph = build_social_graph([persona["id"]], {persona["id"]: 0.5})
        state = initialize_simulation("", [persona], graph)
        final = _run(run_simulation(state))
        # Should complete without error
        assert isinstance(final, SimulationState)

    def test_worldview_collision_with_empty_content(self):
        persona = {"positive_triggers": ["test"], "negative_triggers": ["bad"]}
        score = _check_worldview_collision(persona, "")
        assert score == 0.0

    def test_worldview_collision_with_empty_triggers(self):
        persona = {}
        score = _check_worldview_collision(persona, "This content has words")
        assert score == 0.0

    def test_social_proof_with_no_exposure(self):
        state = SimulationState(material_content="test")
        proof = compute_social_proof(state)
        assert proof == 1.0

    def test_controversy_with_no_actions(self):
        state = SimulationState(material_content="test")
        score = compute_controversy(state)
        assert score == 0.0

    def test_select_seeds_when_seed_count_exceeds_crowd(self):
        persona = generate_persona_skeleton(0, "skeptic")
        config = EnvironmentConfig(seed_count=100)
        state = initialize_simulation("Test", [persona], None, config)
        seeds = select_seeds(state)
        assert len(seeds) == 1  # can't seed more than crowd size


# ──────────────────────────────────────────────────────────────────────
# Sentiment to Opinion Delta
# ──────────────────────────────────────────────────────────────────────

class TestSentimentToOpinionDelta:
    """Test sentiment-to-opinion conversion."""

    def test_positive_gives_positive_delta(self):
        config = EnvironmentConfig()
        delta = _sentiment_to_opinion_delta(Sentiment.POSITIVE, config)
        assert delta > 0

    def test_negative_gives_negative_delta(self):
        config = EnvironmentConfig()
        delta = _sentiment_to_opinion_delta(Sentiment.NEGATIVE, config)
        assert delta < 0

    def test_hostile_more_negative_than_negative(self):
        config = EnvironmentConfig()
        neg = _sentiment_to_opinion_delta(Sentiment.NEGATIVE, config)
        hostile = _sentiment_to_opinion_delta(Sentiment.HOSTILE, config)
        assert hostile < neg

    def test_neutral_near_zero(self):
        config = EnvironmentConfig()
        delta = _sentiment_to_opinion_delta(Sentiment.NEUTRAL, config)
        assert abs(delta) < 0.02


# ──────────────────────────────────────────────────────────────────────
# Platform-Specific Actions
# ──────────────────────────────────────────────────────────────────────

class TestPlatformActions:
    """Test platform-specific action availability."""

    def test_twitter_has_quote(self):
        actions = get_available_actions(Platform.TWITTER)
        assert ActionType.QUOTE in actions

    def test_reddit_has_upvote_downvote(self):
        actions = get_available_actions(Platform.REDDIT)
        assert ActionType.UPVOTE in actions
        assert ActionType.DOWNVOTE in actions

    def test_twitter_no_upvote(self):
        actions = get_available_actions(Platform.TWITTER)
        assert ActionType.UPVOTE not in actions

    def test_common_actions_on_both_platforms(self):
        twitter = set(get_available_actions(Platform.TWITTER))
        reddit = set(get_available_actions(Platform.REDDIT))
        common = {ActionType.LIKE, ActionType.COMMENT, ActionType.SHARE,
                  ActionType.DM, ActionType.SCREENSHOT, ActionType.FOLLOW}
        assert common <= twitter
        assert common <= reddit


# ──────────────────────────────────────────────────────────────────────
# Opinion Bounds
# ──────────────────────────────────────────────────────────────────────

class TestOpinionBounds:
    """Test that opinions stay within [-1, 1] bounds."""

    def test_opinion_clamped_to_bounds(self):
        from app.services.simulation.runner import AgentMemory
        mem = AgentMemory(persona_id="test")
        # Push way positive
        for _ in range(100):
            mem.update_opinion(0, 0.5)
        assert mem.opinion_score <= 1.0
        # Push way negative
        for _ in range(200):
            mem.update_opinion(0, -0.5)
        assert mem.opinion_score >= -1.0

    def test_worldview_collision_clamped(self):
        # Many negative triggers should clamp to -1.0
        persona = {"negative_triggers": [f"word{i}" for i in range(50)]}
        content = " ".join(f"word{i}" for i in range(50))
        score = _check_worldview_collision(persona, content)
        assert score >= -1.0
        assert score <= 1.0


# ──────────────────────────────────────────────────────────────────────
# Coalition Detection
# ──────────────────────────────────────────────────────────────────────

class TestCoalitionDetection:
    """Test coalition detection edge cases."""

    def test_no_coalitions_with_no_engagement(self):
        personas = [generate_persona_skeleton(i, "lurker") for i in range(10)]
        graph = build_social_graph(
            [p["id"] for p in personas],
            {p["id"]: p["influence_weight"] for p in personas},
        )
        state = initialize_simulation("Test", personas, graph)
        coalitions = detect_coalitions(state)
        assert coalitions == []

    def test_coalition_requires_minimum_size(self):
        """Coalitions need at least 3 members."""
        personas = [generate_persona_skeleton(i, "champion") for i in range(2)]
        graph = build_social_graph(
            [p["id"] for p in personas],
            {p["id"]: p["influence_weight"] for p in personas},
        )
        state = initialize_simulation("Test", personas, graph)
        # Mark both as engaged with aligned opinions
        for p in personas:
            state.memories[p["id"]].update_opinion(0, 0.5)
            state.memories[p["id"]].record_interaction(
                0, ActionType.LIKE, None, Sentiment.POSITIVE,
            )
        coalitions = detect_coalitions(state)
        # Only 2 agents, so no coalitions (minimum is 3)
        assert len(coalitions) == 0


# ──────────────────────────────────────────────────────────────────────
# Influence Propagation
# ──────────────────────────────────────────────────────────────────────

class TestInfluencePropagation:
    """Test opinion influence spreading through graph."""

    def test_blocked_agents_dont_receive_influence(self):
        personas = [generate_persona_skeleton(i, "skeptic") for i in range(5)]
        graph = build_social_graph(
            [p["id"] for p in personas],
            {p["id"]: p["influence_weight"] for p in personas},
        )
        state = initialize_simulation("Test", personas, graph)
        # Make agent_000 positive and block them from agent_001
        state.memories["agent_000"].update_opinion(0, 0.8)
        state.memories["agent_001"].blocked.append("agent_000")
        initial_opinion = state.memories["agent_001"].opinion_score
        propagate_influence("agent_000", state, graph)
        # Agent_001 should not be influenced
        assert state.memories["agent_001"].opinion_score == initial_opinion

    def test_muted_agents_dont_receive_influence(self):
        personas = [generate_persona_skeleton(i, "skeptic") for i in range(5)]
        graph = build_social_graph(
            [p["id"] for p in personas],
            {p["id"]: p["influence_weight"] for p in personas},
        )
        state = initialize_simulation("Test", personas, graph)
        state.memories["agent_000"].update_opinion(0, 0.8)
        state.memories["agent_001"].muted.append("agent_000")
        initial_opinion = state.memories["agent_001"].opinion_score
        propagate_influence("agent_000", state, graph)
        assert state.memories["agent_001"].opinion_score == initial_opinion


# ──────────────────────────────────────────────────────────────────────
# Action Selection Path Coverage
# ──────────────────────────────────────────────────────────────────────

class TestActionSelectionPaths:
    """Test that all action selection paths produce valid results."""

    def _make_state(self, humor_profile=None, content="test"):
        persona = generate_persona_skeleton(0, "skeptic")
        graph = build_social_graph([persona["id"]], {persona["id"]: 0.5})
        return initialize_simulation(
            content, [persona], graph, humor_profile=humor_profile,
        )

    def test_meme_remix_path(self):
        """Meme-native agents with remixable content should produce remix actions."""
        random.seed(42)
        hp = ContentHumorProfile(
            primary_tone=HumorTone.MEME,
            execution_score=0.9,
            cringe_probability=0.1,
            remixability=0.9,
            engagement_multiplier=2.0,
            share_multiplier=1.5,
        )
        state = self._make_state(humor_profile=hp)
        persona = {
            "id": "agent_000",
            "worldview_ids": {"humor": "meme_native"},
            "engagement_rate": 0.5,
            "share_rate": 0.3,
            "positive_triggers": [],
            "negative_triggers": [],
            "sensitivity_topics": [],
        }
        remix_count = 0
        for _ in range(200):
            action, sentiment = _pick_action_and_sentiment(
                persona, Platform.TWITTER, state,
            )
            if action in (ActionType.QUOTE, ActionType.COMMENT) and sentiment == Sentiment.POSITIVE:
                remix_count += 1
        # Meme native with high remixability should hit remix path sometimes
        assert remix_count > 0

    def test_standard_path_produces_diverse_actions(self):
        """Standard path should produce a variety of actions."""
        state = self._make_state()
        persona = {
            "id": "agent_000",
            "worldview_ids": {},
            "engagement_rate": 0.5,
            "share_rate": 0.3,
            "positive_triggers": [],
            "negative_triggers": [],
            "sensitivity_topics": [],
        }
        actions_seen = set()
        for _ in range(500):
            action, _ = _pick_action_and_sentiment(persona, Platform.TWITTER, state)
            actions_seen.add(action)
        # Should see at least several different action types
        assert len(actions_seen) >= 5

    def test_worldview_outrage_can_trigger_block_or_report(self):
        """Worldview outrage path includes block and report actions."""
        random.seed(42)
        # Content with many negative triggers for conservative persona
        state = self._make_state(content="pride trans woke girlhood inclusion non-binary reimagine deconstruct")
        persona = {
            "id": "agent_000",
            "worldview_ids": {"humor": "no_humor", "political": "conservative"},
            "engagement_rate": 0.5,
            "share_rate": 0.3,
            "positive_triggers": [],
            "negative_triggers": ["pride", "trans", "woke", "girlhood", "inclusion", "non-binary", "reimagine", "deconstruct"],
            "sensitivity_topics": ["gender identity", "cultural change"],
        }
        block_report_count = 0
        for _ in range(500):
            action, sentiment = _pick_action_and_sentiment(
                persona, Platform.TWITTER, state,
            )
            if action in (ActionType.BLOCK, ActionType.REPORT):
                block_report_count += 1
        # Worldview outrage path has 10% block and 10% report probability
        assert block_report_count > 0


# ──────────────────────────────────────────────────────────────────────
# Social Target Selection
# ──────────────────────────────────────────────────────────────────────

class TestSocialTargetSelection:
    """Test that follow/block/mute pick real targets."""

    def test_follow_picks_real_persona(self):
        random.seed(42)
        personas = [generate_persona_skeleton(i, "champion") for i in range(10)]
        graph = build_social_graph(
            [p["id"] for p in personas],
            {p["id"]: p["influence_weight"] for p in personas},
        )
        hp = ContentHumorProfile(
            primary_tone=HumorTone.WHOLESOME,
            execution_score=0.8,
            engagement_multiplier=2.0,
            share_multiplier=1.5,
        )
        state = initialize_simulation("Wholesome content", personas, graph, humor_profile=hp)
        final = _run(run_simulation(state))
        # Check all followed entries are real persona IDs or brand_account
        valid_ids = {p["id"] for p in personas} | {"brand_account"}
        for pid, memory in final.memories.items():
            for followed_id in memory.followed:
                assert followed_id in valid_ids, \
                    f"{pid} followed '{followed_id}' which is not a valid persona"

    def test_block_picks_real_persona(self):
        random.seed(42)
        personas = [generate_persona_skeleton(i, "skeptic") for i in range(20)]
        graph = build_social_graph(
            [p["id"] for p in personas],
            {p["id"]: p["influence_weight"] for p in personas},
        )
        hp = ContentHumorProfile(
            primary_tone=HumorTone.CRINGE_ATTEMPT,
            execution_score=0.1,
            cringe_probability=0.8,
            engagement_multiplier=1.5,
        )
        state = initialize_simulation("Cringe content bro slay queen", personas, graph, humor_profile=hp)
        final = _run(run_simulation(state))
        valid_ids = {p["id"] for p in personas} | {"brand_account"}
        for pid, memory in final.memories.items():
            for blocked_id in memory.blocked:
                assert blocked_id in valid_ids, \
                    f"{pid} blocked '{blocked_id}' which is not a valid persona"


# ──────────────────────────────────────────────────────────────────────
# Stress Tests
# ──────────────────────────────────────────────────────────────────────

class TestStress:
    """Test with larger crowds and longer simulations."""

    def test_large_crowd_completes(self):
        """200 agents across 40 rounds should complete without error."""
        random.seed(42)
        ids = build_crowd_distribution(200, "ecommerce_dtc")
        personas = [generate_persona_skeleton(i, aid) for i, aid in enumerate(ids)]
        influence_map = {p["id"]: p["influence_weight"] for p in personas}
        graph = build_social_graph([p["id"] for p in personas], influence_map)
        hp = ContentHumorProfile(
            primary_tone=HumorTone.MEME,
            execution_score=0.8,
            cringe_probability=0.1,
            remixability=0.7,
            engagement_multiplier=1.5,
            share_multiplier=1.3,
        )
        config = EnvironmentConfig(crowd_size=200, max_rounds=40)
        state = initialize_simulation(
            "Test content for large crowd simulation",
            personas, graph, config, humor_profile=hp,
        )
        final = _run(run_simulation(state))
        assert final.current_round > 0
        assert len(final.all_actions) > 0
        assert len(final.exposed) > 0
