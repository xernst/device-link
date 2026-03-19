"""Integration tests: validate that real campaigns produce correct directional outcomes.

These tests don't check exact numbers — they check that the engine's emergent
behavior matches what actually happened in the real world.
"""

import asyncio

import pytest

from tests.scenarios.test_real_campaigns import CAMPAIGNS, run_campaign_test


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestPositiveCampaigns:
    """Campaigns that went well should produce positive sentiment."""

    def test_sidney_sweeney_levis_is_positive(self):
        result = _run(run_campaign_test("sidney_sweeney_levis", crowd_size=50))
        sentiments = result["actual"]["sentiment_breakdown"]
        hostile = sentiments.get("hostile", 0)
        negative = sentiments.get("negative", 0)
        positive = sentiments.get("positive", 0)
        assert hostile < positive, "Sidney Sweeney should be more positive than hostile"
        assert result["actual"]["cringe_cascades"] == 0, "No cringe cascades expected"

    def test_wendys_roast_is_positive_viral(self):
        result = _run(run_campaign_test("wendys_twitter_roast", crowd_size=50))
        actual = result["actual"]
        sentiments = actual["sentiment_breakdown"]
        assert sentiments.get("positive", 0) > sentiments.get("negative", 0) + sentiments.get("hostile", 0), \
            "Wendy's should be net positive"
        assert actual["viral_cascades"] > 0, "Should go viral"
        assert actual["meme_mutations"] > 0, "Should produce meme mutations"

    def test_duolingo_is_positive_with_high_dark_social(self):
        result = _run(run_campaign_test("duolingo_unhinged", crowd_size=50))
        actual = result["actual"]
        sentiments = actual["sentiment_breakdown"]
        positive = sentiments.get("positive", 0)
        negative = sentiments.get("negative", 0) + sentiments.get("hostile", 0)
        assert positive > negative * 3, f"Duolingo should be overwhelmingly positive: {positive} vs {negative}"
        assert actual["meme_mutations"] > 0, "Should produce meme mutations"

        # Dark social should be significant
        actions = actual["action_breakdown"]
        dark_social = actions.get("dm", 0) + actions.get("screenshot", 0)
        total_actions = sum(actions.values())
        dark_pct = dark_social / max(total_actions, 1)
        assert dark_pct > 0.1, f"Dark social should be >10%, got {dark_pct:.0%}"

    def test_apple_is_quiet_positive(self):
        result = _run(run_campaign_test("apple_shot_on_iphone", crowd_size=50))
        actual = result["actual"]
        assert actual["cringe_cascades"] == 0
        assert actual["meme_mutations"] == 0
        # Apple should be moderate engagement, not viral
        sentiments = actual["sentiment_breakdown"]
        assert sentiments.get("hostile", 0) == 0 or sentiments.get("hostile", 0) < 5

    def test_scrub_daddy_is_positive_humor(self):
        result = _run(run_campaign_test("scrub_daddy_unhinged", crowd_size=50))
        actual = result["actual"]
        sentiments = actual["sentiment_breakdown"]
        assert sentiments.get("positive", 0) > sentiments.get("negative", 0) + sentiments.get("hostile", 0)
        assert actual["cringe_cascades"] == 0


class TestNegativeCampaigns:
    """Campaigns that went badly should produce negative outcomes."""

    def test_linkedin_cringe_produces_cringe_cascade(self):
        result = _run(run_campaign_test("linkedin_cringe", crowd_size=50))
        actual = result["actual"]
        assert actual["cringe_cascades"] > 0, "LinkedIn cringe must trigger cringe cascades"
        sentiments = actual["sentiment_breakdown"]
        hostile = sentiments.get("hostile", 0)
        negative = sentiments.get("negative", 0)
        positive = sentiments.get("positive", 0)
        assert hostile + negative > positive, \
            f"LinkedIn cringe should be net negative: hostile={hostile} neg={negative} pos={positive}"

    def test_pepsi_kendall_jenner_is_negative(self):
        """Pepsi protest ad should produce negative/hostile sentiment."""
        result = _run(run_campaign_test("pepsi_kendall_jenner", crowd_size=50))
        actual = result["actual"]
        sentiments = actual["sentiment_breakdown"]
        hostile = sentiments.get("hostile", 0)
        negative = sentiments.get("negative", 0)
        positive = sentiments.get("positive", 0)
        assert hostile + negative > positive, \
            f"Pepsi should be net negative: hostile={hostile} neg={negative} pos={positive}"
        # Should also produce lots of screenshots/QTs (mockery)
        actions = actual["action_breakdown"]
        mockery = actions.get("screenshot", 0) + actions.get("quote", 0)
        assert mockery > 0, "Pepsi should produce mockery actions"


class TestPolarizingCampaigns:
    """Campaigns that divided audiences should produce mixed sentiment."""

    def test_bud_light_is_polarized(self):
        """Bud Light/Mulvaney should produce BOTH positive and negative reactions."""
        result = _run(run_campaign_test("bud_light_mulvaney", crowd_size=100))
        actual = result["actual"]
        sentiments = actual["sentiment_breakdown"]
        positive = sentiments.get("positive", 0)
        negative = sentiments.get("negative", 0) + sentiments.get("hostile", 0)
        # Both sides should exist
        assert positive > 0, "Should have positive reactions (supporters)"
        assert negative > 0, "Should have negative reactions (boycotters)"
        # Should be highly engaged
        assert actual["engagement_rate"] > 0.5, "Polarizing content should drive high engagement"


class TestComparativeBehavior:
    """Cross-campaign comparisons that should hold."""

    def test_cringe_gets_more_cringe_cascades_than_good_humor(self):
        linkedin = _run(run_campaign_test("linkedin_cringe", crowd_size=50))
        wendys = _run(run_campaign_test("wendys_twitter_roast", crowd_size=50))
        assert linkedin["actual"]["cringe_cascades"] > wendys["actual"]["cringe_cascades"]

    def test_good_humor_gets_more_positive_sentiment_than_cringe(self):
        duolingo = _run(run_campaign_test("duolingo_unhinged", crowd_size=50))
        linkedin = _run(run_campaign_test("linkedin_cringe", crowd_size=50))
        duo_positive = duolingo["actual"]["sentiment_breakdown"].get("positive", 0)
        link_positive = linkedin["actual"]["sentiment_breakdown"].get("positive", 0)
        assert duo_positive > link_positive, "Good humor should get more positive than cringe"

    def test_unhinged_brands_get_more_dark_social_than_corporate(self):
        duo = _run(run_campaign_test("duolingo_unhinged", crowd_size=50))
        apple = _run(run_campaign_test("apple_shot_on_iphone", crowd_size=50))
        duo_dark = duo["actual"]["action_breakdown"].get("dm", 0) + duo["actual"]["action_breakdown"].get("screenshot", 0)
        apple_dark = apple["actual"]["action_breakdown"].get("dm", 0) + apple["actual"]["action_breakdown"].get("screenshot", 0)
        assert duo_dark > apple_dark, "Unhinged brands should produce more dark social"

    def test_humorous_content_gets_more_meme_mutations(self):
        scrub = _run(run_campaign_test("scrub_daddy_unhinged", crowd_size=50))
        apple = _run(run_campaign_test("apple_shot_on_iphone", crowd_size=50))
        assert scrub["actual"]["meme_mutations"] > apple["actual"]["meme_mutations"]
