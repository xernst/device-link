"""Unit tests for the humor compatibility matrix and content humor analysis."""

import pytest
from app.services.simulation.humor import (
    ContentHumorProfile,
    HumorRisk,
    HumorTone,
    HUMOR_COMPATIBILITY,
    analyze_content_humor_fast,
    get_humor_compatibility,
    _compute_engagement_multiplier,
    _compute_share_multiplier,
    _compute_comment_multiplier,
    _compute_freshness_modifier,
    _compute_viral_modifier,
    _compute_dark_social_modifier,
)


class TestHumorCompatibilityMatrix:
    """Test that the humor compatibility matrix produces expected interactions."""

    def test_meme_native_loves_memes(self):
        score = get_humor_compatibility("meme_native", "meme")
        assert score > 1.5, f"Meme natives should love meme content, got {score}"

    def test_meme_native_hates_cringe(self):
        score = get_humor_compatibility("meme_native", "cringe_attempt")
        assert score < 0, f"Meme natives should hate cringe, got {score}"

    def test_sarcasm_default_lives_for_cringe_dunking(self):
        score = get_humor_compatibility("sarcasm_default", "cringe_attempt")
        assert score < -1.5, f"Sarcasm defaults should dunk hardest on cringe, got {score}"

    def test_wholesome_is_forgiving_of_cringe(self):
        score = get_humor_compatibility("wholesome_humor", "cringe_attempt")
        assert score > 0, f"Wholesome people should be forgiving, got {score}"

    def test_no_humor_prefers_serious(self):
        score = get_humor_compatibility("no_humor", "none")
        assert score > 1.0, f"No-humor should prefer serious content, got {score}"

    def test_no_humor_dislikes_shitposts(self):
        score = get_humor_compatibility("no_humor", "shitpost")
        assert score < 0.5, f"No-humor should dislike shitposts, got {score}"

    def test_edgy_loves_roasts(self):
        score = get_humor_compatibility("edgy_humor", "roast")
        assert score >= 2.0, f"Edgy should love roasts, got {score}"

    def test_absurdist_loves_absurdism(self):
        score = get_humor_compatibility("absurdist", "absurdist")
        assert score >= 2.0, f"Absurdist should love absurdist content, got {score}"

    def test_dry_wit_loves_dry_humor(self):
        score = get_humor_compatibility("dry_wit", "dry")
        assert score > 1.5, f"Dry wit should love dry humor, got {score}"

    def test_cultural_loves_references(self):
        score = get_humor_compatibility("cultural_humor", "reference")
        assert score >= 2.0, f"Cultural humor should love references, got {score}"

    def test_unknown_profile_returns_neutral(self):
        score = get_humor_compatibility("nonexistent_profile", "meme")
        assert score == 1.0, f"Unknown profile should return 1.0, got {score}"

    def test_unknown_tone_returns_neutral(self):
        score = get_humor_compatibility("meme_native", "nonexistent_tone")
        assert score == 1.0, f"Unknown tone should return 1.0, got {score}"

    def test_all_profiles_have_cringe_entry(self):
        """Every humor profile must have an opinion on cringe_attempt."""
        for profile_id, profile_map in HUMOR_COMPATIBILITY.items():
            assert "cringe_attempt" in profile_map, f"Profile {profile_id} missing cringe_attempt entry"

    def test_all_profiles_have_none_entry(self):
        """Every humor profile must handle no-humor content."""
        for profile_id, profile_map in HUMOR_COMPATIBILITY.items():
            assert "none" in profile_map, f"Profile {profile_id} missing none entry"

    def test_cringe_divides_audiences(self):
        """Cringe should produce a wide range of reactions across profiles."""
        cringe_scores = [
            get_humor_compatibility(p, "cringe_attempt")
            for p in HUMOR_COMPATIBILITY
        ]
        min_score = min(cringe_scores)
        max_score = max(cringe_scores)
        spread = max_score - min_score
        assert spread > 2.0, f"Cringe should divide audiences widely, spread={spread}"


class TestEngineModifiers:
    """Test that humor profiles produce correct engine modifiers."""

    def test_no_humor_neutral_multipliers(self):
        profile = ContentHumorProfile(primary_tone=HumorTone.NONE)
        assert _compute_engagement_multiplier(profile) == 1.0
        assert _compute_share_multiplier(profile) == 1.0
        assert _compute_viral_modifier(profile) == 1.0

    def test_good_humor_boosts_engagement(self):
        profile = ContentHumorProfile(
            primary_tone=HumorTone.MEME,
            execution_score=0.9,
        )
        mult = _compute_engagement_multiplier(profile)
        assert mult > 1.3, f"Good humor should boost engagement, got {mult}"

    def test_cringe_also_boosts_engagement(self):
        """Cringe gets high engagement (people engage to dunk)."""
        profile = ContentHumorProfile(
            primary_tone=HumorTone.CRINGE_ATTEMPT,
            execution_score=0.1,
            cringe_probability=0.8,
        )
        mult = _compute_engagement_multiplier(profile)
        assert mult > 1.2, f"Cringe should boost engagement (dunking), got {mult}"

    def test_cringe_drives_comments(self):
        profile = ContentHumorProfile(
            primary_tone=HumorTone.CRINGE_ATTEMPT,
            cringe_probability=0.8,
            misread_probability=0.5,
            remixability=0.6,
        )
        mult = _compute_comment_multiplier(profile)
        assert mult > 1.5, f"Cringe should drive comments (roasting), got {mult}"

    def test_evergreen_humor_decays_slower(self):
        profile = ContentHumorProfile(
            primary_tone=HumorTone.MEME,
            shelf_life="evergreen",
            execution_score=0.8,
        )
        mod = _compute_freshness_modifier(profile)
        assert mod < 0.5, f"Evergreen humor should decay very slowly, got {mod}"

    def test_ephemeral_humor_decays_faster(self):
        profile = ContentHumorProfile(
            primary_tone=HumorTone.REFERENCE,
            shelf_life="ephemeral",
        )
        mod = _compute_freshness_modifier(profile)
        assert mod > 1.0, f"Ephemeral humor should decay faster, got {mod}"

    def test_cringe_lowers_viral_threshold(self):
        profile = ContentHumorProfile(
            primary_tone=HumorTone.CRINGE_ATTEMPT,
            execution_score=0.1,
            cringe_probability=0.8,
            screenshot_bait=0.7,
        )
        mod = _compute_viral_modifier(profile)
        assert mod < 0.6, f"Cringe should lower viral threshold, got {mod}"

    def test_screenshot_bait_drives_dark_social(self):
        profile = ContentHumorProfile(
            primary_tone=HumorTone.ROAST,
            screenshot_bait=0.8,
            cringe_probability=0.6,
        )
        mod = _compute_dark_social_modifier(profile)
        assert mod > 1.5, f"High screenshot bait should drive dark social, got {mod}"


class TestFastHumorDetection:
    """Test the rule-based fast humor analysis (no LLM)."""

    def test_detects_meme_signals(self):
        content = "bruh this is so based lmao no cap 💀"
        profile = analyze_content_humor_fast(content)
        assert profile.primary_tone == HumorTone.MEME

    def test_detects_sarcasm(self):
        content = "Oh great another revolutionary game-changing AI tool. Totally groundbreaking."
        profile = analyze_content_humor_fast(content)
        assert profile.primary_tone == HumorTone.SARCASM

    def test_detects_cringe(self):
        content = "Hey fellow kids! This product is lit fam, totally on fleek! YOLO am I right?"
        profile = analyze_content_humor_fast(content)
        assert profile.primary_tone == HumorTone.CRINGE_ATTEMPT

    def test_detects_roast(self):
        content = "Shots fired! No chill today. We chose violence against the competition."
        profile = analyze_content_humor_fast(content)
        assert profile.primary_tone == HumorTone.ROAST

    def test_detects_wholesome(self):
        content = "This wholesome moment restored my faith in humanity. Made my day! 😊"
        profile = analyze_content_humor_fast(content)
        assert profile.primary_tone == HumorTone.WHOLESOME

    def test_detects_no_humor(self):
        content = "Our Q3 results demonstrate 15% YoY growth in enterprise segments."
        profile = analyze_content_humor_fast(content)
        assert profile.primary_tone == HumorTone.NONE

    def test_cringe_has_high_cringe_probability(self):
        content = "Hey fellow kids! This is lit fam, on fleek!"
        profile = analyze_content_humor_fast(content)
        assert profile.cringe_probability > 0.5

    def test_modifiers_computed_for_humor(self):
        content = "bruh lmao no cap 💀😂"
        profile = analyze_content_humor_fast(content)
        assert profile.engagement_multiplier > 1.0
        assert profile.share_multiplier > 1.0
