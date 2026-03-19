"""Tests for the cultural context layer."""

import json
import tempfile
from pathlib import Path

from app.services.simulation.culture import (
    CulturalPulse,
    MemeLifecycle,
    TrendingTopic,
    augment_persona_triggers,
    generate_cultural_pulse_fast,
)


class TestCulturalPulse:
    """Test the CulturalPulse data model."""

    def test_empty_pulse_produces_minimal_prompt(self):
        pulse = CulturalPulse(current_date="2026-03-19")
        block = pulse.to_prompt_block()
        assert "2026-03-19" in block
        assert "Cultural Context" in block

    def test_full_pulse_includes_all_sections(self):
        pulse = CulturalPulse(
            current_date="2026-03-19",
            content_cultural_moment="This lands in a polarized moment.",
            content_sensitivity_flags=["culture war", "brand politics"],
            overall_mood="polarized",
            trending_topics=[
                TrendingTopic(
                    topic="AI replacing jobs",
                    relevance=0.8,
                    sentiment_lean="anxious",
                    context="Major layoff wave in tech",
                ),
            ],
            active_memes=[
                MemeLifecycle(
                    format_name="brain rot",
                    status="peak",
                    audience="gen_z",
                    brand_safety="cringe_if_brand_uses",
                ),
            ],
            dead_memes=["harambe", "planking"],
            current_slang={"delulu": "delusional (positive)", "slay": "doing great"},
            dated_slang=["on fleek", "YOLO"],
            fatigue_topics=["crypto", "metaverse"],
        )
        block = pulse.to_prompt_block()
        assert "polarized moment" in block
        assert "culture war" in block
        assert "AI replacing jobs" in block
        assert "brain rot" in block
        assert "harambe" in block
        assert "delulu" in block
        assert "on fleek" in block
        assert "crypto" in block

    def test_serialize_deserialize_roundtrip(self):
        pulse = CulturalPulse(
            current_date="2026-03-19",
            content_cultural_moment="Test moment",
            trending_topics=[
                TrendingTopic(
                    topic="test",
                    relevance=0.5,
                    sentiment_lean="neutral",
                    trigger_words=["test_trigger"],
                    context="test context",
                ),
            ],
            active_memes=[
                MemeLifecycle(
                    format_name="test_meme",
                    status="rising",
                    audience="mainstream",
                    brand_safety="safe",
                ),
            ],
            additional_triggers={
                "political:conservative": {
                    "negative": ["new_trigger"],
                    "positive": [],
                    "sensitivity": [],
                },
            },
        )
        d = pulse.to_dict()
        restored = CulturalPulse.from_dict(d)
        assert restored.current_date == "2026-03-19"
        assert restored.content_cultural_moment == "Test moment"
        assert len(restored.trending_topics) == 1
        assert restored.trending_topics[0].topic == "test"
        assert len(restored.active_memes) == 1
        assert "political:conservative" in restored.additional_triggers

    def test_save_and_load(self, tmp_path):
        pulse = CulturalPulse(
            current_date="2026-03-19",
            content_cultural_moment="Saved moment",
            dead_memes=["harambe"],
        )
        path = tmp_path / "pulse.json"
        pulse.save(path)
        loaded = CulturalPulse.load(path)
        assert loaded.content_cultural_moment == "Saved moment"
        assert "harambe" in loaded.dead_memes


class TestFastCulturalPulse:
    """Test the rule-based cultural pulse generator."""

    def test_detects_culture_war_content(self):
        pulse = generate_cultural_pulse_fast(
            material="Celebrating Pride month with our trans community #inclusion",
            industry="ecommerce_dtc",
        )
        assert "culture war" in pulse.content_sensitivity_flags[0].lower()
        assert "political:conservative" in pulse.additional_triggers
        assert "political:progressive" in pulse.additional_triggers
        assert pulse.overall_mood == "polarized"

    def test_detects_ai_content(self):
        pulse = generate_cultural_pulse_fast(
            material="Our new AI-powered tool will replace manual work with automation",
            industry="saas_b2b",
        )
        assert any("ai" in f.lower() for f in pulse.content_sensitivity_flags)
        assert pulse.overall_mood == "anxious"

    def test_detects_corporate_cringe(self):
        pulse = generate_cultural_pulse_fast(
            material="No cap bestie, our product is bussin frfr 💅",
            industry="consumer_app",
        )
        assert "humor:meme_native" in pulse.additional_triggers
        assert "generational:gen_z_native" in pulse.additional_triggers

    def test_no_false_positives_on_neutral_content(self):
        pulse = generate_cultural_pulse_fast(
            material="Introducing our new quarterly earnings report for Q1 2026",
            industry="saas_b2b",
        )
        assert len(pulse.content_sensitivity_flags) == 0
        assert len(pulse.additional_triggers) == 0

    def test_always_includes_dead_memes(self):
        pulse = generate_cultural_pulse_fast(
            material="Normal marketing copy here",
            industry="ecommerce_dtc",
        )
        assert len(pulse.dead_memes) > 0
        assert len(pulse.dated_slang) > 0

    def test_includes_current_date(self):
        pulse = generate_cultural_pulse_fast(
            material="Test",
            industry="saas_b2b",
            current_date_override="2026-03-19",
        )
        assert pulse.current_date == "2026-03-19"


class TestTriggerAugmentation:
    """Test dynamic trigger augmentation from cultural pulse."""

    def test_conservative_gets_culture_war_triggers(self):
        pulse = generate_cultural_pulse_fast(
            material="Stand with trans pride and inclusion",
            industry="ecommerce_dtc",
        )
        persona = {
            "id": "agent_001",
            "worldview_ids": {"political": "conservative"},
            "positive_triggers": ["tradition"],
            "negative_triggers": ["disrupt"],
            "sensitivity_topics": [],
        }
        augmented = augment_persona_triggers(persona, pulse)
        # Should have new triggers added
        assert "pride" in augmented["negative_triggers"]
        assert "trans" in augmented["negative_triggers"]
        assert "inclusion" in augmented["negative_triggers"]
        # Original triggers preserved
        assert "tradition" in augmented["positive_triggers"]
        assert "disrupt" in augmented["negative_triggers"]

    def test_progressive_gets_positive_culture_triggers(self):
        pulse = generate_cultural_pulse_fast(
            material="Stand with trans pride and inclusion",
            industry="ecommerce_dtc",
        )
        persona = {
            "id": "agent_002",
            "worldview_ids": {"political": "progressive"},
            "positive_triggers": ["sustainable"],
            "negative_triggers": [],
            "sensitivity_topics": [],
        }
        augmented = augment_persona_triggers(persona, pulse)
        assert "pride" in augmented["positive_triggers"]
        assert "trans" in augmented["positive_triggers"]

    def test_meme_native_gets_cringe_triggers(self):
        pulse = generate_cultural_pulse_fast(
            material="No cap bestie this is bussin",
            industry="consumer_app",
        )
        persona = {
            "id": "agent_003",
            "worldview_ids": {"humor": "meme_native"},
            "positive_triggers": [],
            "negative_triggers": [],
            "sensitivity_topics": [],
        }
        augmented = augment_persona_triggers(persona, pulse)
        assert "no cap" in augmented["negative_triggers"]
        assert "bestie" in augmented["negative_triggers"]
        assert "bussin" in augmented["negative_triggers"]

    def test_no_duplicate_triggers(self):
        pulse = generate_cultural_pulse_fast(
            material="Pride pride PRIDE",
            industry="ecommerce_dtc",
        )
        persona = {
            "id": "agent_004",
            "worldview_ids": {"political": "conservative"},
            "positive_triggers": [],
            "negative_triggers": ["pride"],  # already has it
            "sensitivity_topics": [],
        }
        augmented = augment_persona_triggers(persona, pulse)
        # Should not duplicate
        count = augmented["negative_triggers"].count("pride")
        assert count == 1

    def test_unaffected_worldview_gets_no_augmentation(self):
        pulse = generate_cultural_pulse_fast(
            material="Stand with trans pride",
            industry="ecommerce_dtc",
        )
        persona = {
            "id": "agent_005",
            "worldview_ids": {"economic": "free_market"},
            "positive_triggers": ["ROI"],
            "negative_triggers": [],
            "sensitivity_topics": [],
        }
        augmented = augment_persona_triggers(persona, pulse)
        # free_market isn't affected by culture war content
        assert augmented["positive_triggers"] == ["ROI"]
        assert augmented["negative_triggers"] == []

    def test_trending_topic_triggers_added_to_sensitivity(self):
        pulse = CulturalPulse(
            current_date="2026-03-19",
            trending_topics=[
                TrendingTopic(
                    topic="AI layoffs",
                    relevance=0.9,
                    sentiment_lean="negative",
                    affected_worldviews=["economic:anti_consumerist"],
                    trigger_words=["layoff", "automated away"],
                    context="Mass tech layoffs",
                ),
            ],
        )
        persona = {
            "id": "agent_006",
            "worldview_ids": {"economic": "anti_consumerist"},
            "positive_triggers": [],
            "negative_triggers": [],
            "sensitivity_topics": [],
        }
        augmented = augment_persona_triggers(persona, pulse)
        assert "layoff" in augmented["sensitivity_topics"]
        assert "automated away" in augmented["sensitivity_topics"]


class TestCulturalPulseIntegration:
    """Test that cultural pulse integrates with the simulation runner."""

    def test_initialize_simulation_with_cultural_pulse(self):
        from app.services.simulation.runner import initialize_simulation, EnvironmentConfig

        pulse = generate_cultural_pulse_fast(
            material="Stand with trans pride",
            industry="ecommerce_dtc",
        )
        personas = [
            {
                "id": "agent_000",
                "primary_archetype": "early_adopter",
                "engagement_rate": 0.5,
                "share_rate": 0.3,
                "influence_weight": 0.5,
                "worldview_ids": {"political": "conservative"},
                "positive_triggers": [],
                "negative_triggers": ["disrupt"],
                "sensitivity_topics": [],
            },
        ]

        from app.services.simulation.graph import build_social_graph
        graph = build_social_graph(["agent_000"], {"agent_000": 0.5})

        state = initialize_simulation(
            material_content="Stand with trans pride",
            personas=personas,
            graph=graph,
            cultural_pulse=pulse,
        )

        # Persona triggers should be augmented
        persona = state.personas[0]
        assert "pride" in persona["negative_triggers"]
        assert "trans" in persona["negative_triggers"]
        # Cultural pulse should be stored in state
        assert state.cultural_pulse is not None
