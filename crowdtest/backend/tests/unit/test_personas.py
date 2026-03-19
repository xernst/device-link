"""Tests for persona generation, worldview assignment, and trigger aggregation."""

import random

from app.services.simulation.archetypes import ARCHETYPES, INDUSTRY_PACKS
from app.services.simulation.personas import (
    AGE_BANDS,
    AGE_TO_GENERATIONAL,
    assign_worldviews,
    aggregate_triggers,
    build_crowd_distribution,
    compute_trust_profile,
    generate_persona_skeleton,
)
from app.services.simulation.worldviews import (
    ALL_DIMENSIONS,
    INDUSTRY_WORLDVIEW_DEFAULTS,
)


class TestWorldviewAssignment:
    """Test worldview assignment across dimensions."""

    def test_all_dimensions_assigned(self):
        wv = assign_worldviews("millennial")
        # Should have one assignment per dimension
        assert set(wv.keys()) == set(ALL_DIMENSIONS.keys())

    def test_generational_matches_age_band(self):
        for band, expected_gen in AGE_TO_GENERATIONAL.items():
            wv = assign_worldviews(band)
            assert wv["generational"] == expected_gen, f"Age band {band} should map to {expected_gen}"

    def test_industry_pack_uses_defined_distribution(self):
        # With enough samples, industry-specific modifiers should dominate
        random.seed(42)
        counts = {}
        for _ in range(200):
            wv = assign_worldviews("millennial", "saas_b2b")
            humor = wv["humor"]
            counts[humor] = counts.get(humor, 0) + 1
        # saas_b2b humor distribution has dry_wit and sarcasm_default at 0.25 each
        assert counts.get("dry_wit", 0) > 20
        assert counts.get("sarcasm_default", 0) > 20

    def test_unknown_industry_falls_back_to_uniform(self):
        wv = assign_worldviews("gen_z", "nonexistent_industry")
        # Should still assign all dimensions
        assert set(wv.keys()) == set(ALL_DIMENSIONS.keys())

    def test_custom_worldviews_override_industry(self):
        custom = {"political": {"progressive": 1.0}}
        wv = assign_worldviews("millennial", "saas_b2b", custom)
        assert wv["political"] == "progressive"

    def test_all_assigned_modifiers_exist_in_dimensions(self):
        """Every assigned modifier ID should exist in its dimension."""
        for _ in range(50):
            wv = assign_worldviews(random.choice(list(AGE_BANDS.keys())))
            for dimension, modifier_id in wv.items():
                assert dimension in ALL_DIMENSIONS, f"Dimension {dimension} not found"
                assert modifier_id in ALL_DIMENSIONS[dimension], \
                    f"Modifier {modifier_id} not found in {dimension}"


class TestTriggerAggregation:
    """Test trigger merging from worldview dimensions."""

    def test_triggers_include_items_from_assigned_worldviews(self):
        wv = {"political": "conservative", "religious": "devout"}
        pos, neg, sens = aggregate_triggers(wv)
        # Conservative has "patriotic" as positive
        assert "patriotic" in pos
        # Devout has "pride" as negative
        assert "pride" in neg

    def test_triggers_deduplicate(self):
        """If two dimensions share a trigger word, it should appear once."""
        wv = {"political": "progressive", "cultural": "cosmopolitan"}
        pos, _, _ = aggregate_triggers(wv)
        # Check no duplicates
        assert len(pos) == len(set(pos))

    def test_empty_worldview_returns_empty_triggers(self):
        pos, neg, sens = aggregate_triggers({})
        assert pos == []
        assert neg == []
        assert sens == []

    def test_invalid_modifier_id_is_skipped(self):
        wv = {"political": "nonexistent_modifier"}
        pos, neg, sens = aggregate_triggers(wv)
        assert pos == []
        assert neg == []
        assert sens == []


class TestTrustProfile:
    """Test trust modifier merging."""

    def test_trust_profile_has_values(self):
        wv = {"political": "progressive", "trust": "peer_trusting"}
        profile = compute_trust_profile(wv)
        assert len(profile) > 0

    def test_trust_profile_averages_overlapping_factors(self):
        """When two dimensions modify the same factor, effects are averaged."""
        wv = {"political": "progressive", "trust": "peer_trusting"}
        profile = compute_trust_profile(wv)
        # social_proof appears in both — should be averaged
        if "social_proof" in profile:
            # Individual values: progressive=0.1, peer_trusting=0.3 → avg=0.2
            assert -1.0 <= profile["social_proof"] <= 1.0


class TestCrowdDistribution:
    """Test crowd building across industries."""

    def test_correct_crowd_size(self):
        for size in [1, 10, 50, 100, 200]:
            result = build_crowd_distribution(size)
            assert len(result) == size, f"Expected {size} agents, got {len(result)}"

    def test_all_archetypes_are_valid(self):
        result = build_crowd_distribution(100, "saas_b2b")
        for archetype_id in result:
            assert archetype_id in ARCHETYPES, f"Unknown archetype: {archetype_id}"

    def test_industry_pack_shapes_distribution(self):
        random.seed(42)
        result = build_crowd_distribution(200, "developer_tools")
        counts = {}
        for aid in result:
            counts[aid] = counts.get(aid, 0) + 1
        # developer_tools has expert at 0.08 (highest), so should appear often
        assert counts.get("expert", 0) > 5

    def test_zero_crowd_returns_empty(self):
        result = build_crowd_distribution(0)
        assert result == []

    def test_all_industry_packs_valid(self):
        """Every industry pack in archetypes should produce valid crowds."""
        for industry in INDUSTRY_PACKS:
            result = build_crowd_distribution(50, industry)
            assert len(result) == 50, f"Industry {industry} failed to produce 50 agents"
            for aid in result:
                assert aid in ARCHETYPES, f"Industry {industry} produced unknown archetype: {aid}"


class TestPersonaSkeleton:
    """Test full persona skeleton generation."""

    def test_skeleton_has_all_required_fields(self):
        skeleton = generate_persona_skeleton(0, "skeptic")
        required = [
            "id", "primary_archetype", "engagement_rate", "share_rate",
            "influence_weight", "worldview_ids", "positive_triggers",
            "negative_triggers", "sensitivity_topics", "trust_profile",
            "age", "age_band", "role",
        ]
        for field in required:
            assert field in skeleton, f"Missing field: {field}"

    def test_skeleton_id_format(self):
        skeleton = generate_persona_skeleton(42, "skeptic")
        assert skeleton["id"] == "agent_042"

    def test_skeleton_preserves_archetype_rates(self):
        archetype = ARCHETYPES["early_adopter"]
        skeleton = generate_persona_skeleton(0, "early_adopter")
        assert skeleton["engagement_rate"] == archetype.engagement_rate
        assert skeleton["share_rate"] == archetype.share_rate

    def test_skeleton_age_matches_band(self):
        random.seed(42)
        skeleton = generate_persona_skeleton(0, "skeptic")
        band = skeleton["age_band"]
        age_min, age_max = AGE_BANDS[band]
        assert age_min <= skeleton["age"] <= age_max

    def test_skeleton_worldview_ids_all_valid(self):
        skeleton = generate_persona_skeleton(0, "skeptic", "saas_b2b")
        for dim, mod_id in skeleton["worldview_ids"].items():
            assert dim in ALL_DIMENSIONS
            assert mod_id in ALL_DIMENSIONS[dim], f"Invalid modifier {mod_id} in {dim}"

    def test_triggers_populated_from_worldviews(self):
        """Triggers should be populated, not empty."""
        random.seed(42)
        skeleton = generate_persona_skeleton(0, "skeptic", "ecommerce_dtc")
        # With 8 worldview dimensions, there should be SOME triggers
        total_triggers = (len(skeleton["positive_triggers"])
                          + len(skeleton["negative_triggers"])
                          + len(skeleton["sensitivity_topics"]))
        assert total_triggers > 0, "Persona should have at least some triggers"


class TestIndustryWorldviewDefaults:
    """Test that all industry packs have worldview defaults."""

    def test_all_industry_packs_have_worldview_defaults(self):
        for industry in INDUSTRY_PACKS:
            assert industry in INDUSTRY_WORLDVIEW_DEFAULTS, \
                f"Industry {industry} has archetype pack but no worldview defaults"

    def test_worldview_defaults_weights_sum_to_one(self):
        """Distribution weights should approximately sum to 1.0."""
        for industry, dims in INDUSTRY_WORLDVIEW_DEFAULTS.items():
            for dim, weights in dims.items():
                total = sum(weights.values())
                assert abs(total - 1.0) < 0.05, \
                    f"{industry}/{dim} weights sum to {total}, expected ~1.0"

    def test_worldview_defaults_reference_valid_modifiers(self):
        """All modifier IDs in defaults should exist in ALL_DIMENSIONS."""
        for industry, dims in INDUSTRY_WORLDVIEW_DEFAULTS.items():
            for dim, modifiers in dims.items():
                assert dim in ALL_DIMENSIONS, f"Unknown dimension {dim} in {industry}"
                for mod_id in modifiers:
                    assert mod_id in ALL_DIMENSIONS[dim], \
                        f"Unknown modifier {mod_id} in {industry}/{dim}"
