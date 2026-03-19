"""Test harness: simulate real-world ad campaigns through the engine.

Tests the engine against known outcomes — campaigns that went viral (good or bad),
campaigns that flopped, campaigns that split audiences. If the engine can't predict
what actually happened, the engine is wrong.

Each test case:
1. Feeds real campaign content into the humor analyzer + simulation
2. Runs the full simulation (rule-based, no LLM — fast)
3. Checks that emergent behavior matches real-world outcomes
"""

import asyncio

from app.services.simulation.archetypes import INDUSTRY_PACKS
from app.services.simulation.graph import build_social_graph
from app.services.simulation.humor import ContentHumorProfile, HumorRisk, HumorTone, analyze_content_humor_fast
from app.services.simulation.personas import build_crowd_distribution, generate_persona_skeleton
from app.services.simulation.runner import (
    EnvironmentConfig,
    Platform,
    initialize_simulation,
    run_simulation,
)


# ──────────────────────────────────────────────────────────────────────
# Campaign Library: Real campaigns with known outcomes
# ──────────────────────────────────────────────────────────────────────

CAMPAIGNS = {
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. Sidney Sweeney x Levi's — Successful celebrity endorsement
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "sidney_sweeney_levis": {
        "name": "Sidney Sweeney x Levi's 501 Jeans",
        "content": (
            "Some things never go out of style. @SidneySweeney in the 501® Original. "
            "The jean that started it all — now starting conversations all over again. "
            "#LiveInLevis #501Original"
        ),
        "visual_description": (
            "Sidney Sweeney in a cinematic lifestyle shot wearing Levi's 501 jeans. "
            "Golden hour lighting, casual confidence, authentic styling. Mix of vintage "
            "Americana aesthetic with modern celebrity appeal. High production value but "
            "feels effortless, not forced. Classic denim brand + Gen Z/millennial star."
        ),
        "platform": "instagram",
        "industry": "ecommerce_dtc",
        "humor_profile_override": ContentHumorProfile(
            primary_tone=HumorTone.NONE,
            execution_score=0.0,
            engagement_multiplier=1.0,
            share_multiplier=1.0,
            freshness_decay_modifier=1.0,
            viral_threshold_modifier=1.0,
            dark_social_modifier=1.0,
        ),
        "expected_outcomes": {
            "overall_sentiment": "positive",  # broadly well-received
            "engagement_level": "high",  # celebrity drives engagement
            "viral_type": "positive",  # shared for aspirational reasons
            "controversy": "low",  # minimal backlash
            "dark_social": "moderate",  # screenshotted/shared in DMs (thirst posts)
            "key_insight": "Celebrity-product fit is strong. Sidney Sweeney's audience overlaps with Levi's target demo.",
        },
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. Bud Light x Dylan Mulvaney — Culture war flashpoint
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "bud_light_mulvaney": {
        "name": "Bud Light x Dylan Mulvaney Pride Campaign",
        "content": (
            "Cheers to 365 days of girlhood 🎉 @DylanMulvaney celebrates with Bud Light. "
            "Here's to the moments that make us who we are. Trans pride is beautiful. "
            "Stand with inclusion. #BudLight #Pride"
        ),
        "visual_description": (
            "Dylan Mulvaney holding a custom Bud Light can with her face on it, "
            "celebrating in a bathtub with bubbles. Playful, celebratory mood. "
            "The personalized can is the focal point — it reads as special/exclusive. "
            "Pastel aesthetic, feel-good energy. Influencer partnership format."
        ),
        "platform": "instagram",
        "industry": "ecommerce_dtc",
        "humor_profile_override": ContentHumorProfile(
            primary_tone=HumorTone.WHOLESOME,
            execution_score=0.5,
            cringe_probability=0.2,
            misread_probability=0.3,  # different audiences read it very differently
            screenshot_bait=0.7,  # highly screenshotted (by both sides)
            quote_tweet_bait=0.8,  # massive quote-tweet activity
            remixability=0.6,  # the can image was remixed heavily
            engagement_multiplier=1.8,
            share_multiplier=2.0,
            comment_multiplier=2.5,
            freshness_decay_modifier=0.3,  # this stayed in the news cycle for MONTHS
            viral_threshold_modifier=0.3,  # went massively viral
            dark_social_modifier=2.0,
        ),
        "env_override": {
            "max_rounds": 50,  # this played out over a long time
        },
        "expected_outcomes": {
            "overall_sentiment": "deeply_polarized",  # 50/50 split
            "engagement_level": "extreme",  # massive engagement on both sides
            "viral_type": "controversy_cascade",  # viral for culture war reasons
            "controversy": "extreme",  # one of the most controversial campaigns in recent memory
            "dark_social": "extreme",  # screenshotted millions of times
            "coalitions": ["progressive_supporters", "conservative_boycotters"],
            "key_insight": "Brand identity crisis. Core blue-collar audience clashed with progressive influencer partnership. Neither side felt the brand was 'theirs' anymore.",
        },
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. Wendy's Twitter Roasts — Brand humor done right
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "wendys_twitter_roast": {
        "name": "Wendy's Twitter Roast Era",
        "content": (
            "@McDonaldsCorp Your ice cream machine is broken again? "
            "Ours works. Just saying. 🍦 "
            "Maybe try serving fresh beef that was never frozen while you're at it."
        ),
        "visual_description": None,  # text-only tweet
        "platform": "twitter",
        "industry": "ecommerce_dtc",
        "humor_profile_override": ContentHumorProfile(
            primary_tone=HumorTone.ROAST,
            secondary_tones=[HumorTone.SARCASM, HumorTone.REFERENCE],
            execution_score=0.85,
            originality_score=0.7,
            timing_score=0.9,
            target_humor_profiles=["meme_native", "edgy_humor", "sarcasm_default"],
            repelled_humor_profiles=["no_humor", "wholesome_humor"],
            cringe_probability=0.05,
            screenshot_bait=0.8,
            quote_tweet_bait=0.7,
            remixability=0.5,
            engagement_multiplier=2.0,
            share_multiplier=2.2,
            comment_multiplier=1.8,
            freshness_decay_modifier=0.6,
            viral_threshold_modifier=0.4,
            dark_social_modifier=1.8,
        ),
        "expected_outcomes": {
            "overall_sentiment": "positive",
            "engagement_level": "viral",
            "viral_type": "positive_humor",
            "controversy": "low",
            "dark_social": "high",  # screenshotted constantly
            "key_insight": "Brand roasts work when: (1) you're punching at a bigger target, (2) the humor is genuinely sharp, (3) your actual product backs up the trash talk.",
        },
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. Pepsi x Kendall Jenner — Cringe cascade case study
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "pepsi_kendall_jenner": {
        "name": "Pepsi x Kendall Jenner Protest Ad",
        "content": (
            "Live for now. Join the conversation. 🌍✊ "
            "Pepsi brings people together — because nothing says unity "
            "like handing a cop a Pepsi. #LiveForNow #PepsiMoment"
        ),
        "visual_description": (
            "Kendall Jenner leaves a photoshoot to join a protest march. "
            "She hands a Pepsi to a police officer. The officer smiles, the crowd cheers. "
            "Diverse cast of young, attractive protesters carrying generic signs. "
            "The protest looks like a music festival — no specific cause, no real tension. "
            "Studio-perfect lighting on what should be gritty street activism."
        ),
        "platform": "twitter",
        "industry": "ecommerce_dtc",
        "humor_profile_override": ContentHumorProfile(
            primary_tone=HumorTone.NONE,  # not trying to be funny
            execution_score=0.0,
            cringe_probability=0.85,  # massively cringe
            misread_probability=0.1,  # everyone understood it — and hated it
            screenshot_bait=0.9,
            quote_tweet_bait=0.95,
            remixability=0.9,  # heavily parodied
            primary_risk=HumorRisk.TONE_DEAF,
            risks=[
                {"risk": "tone_deaf", "severity": 0.95, "description": "Trivializes protest movements"},
                {"risk": "cringe_viral", "severity": 0.9, "description": "Will be mocked relentlessly"},
            ],
            engagement_multiplier=2.5,
            share_multiplier=2.5,
            comment_multiplier=3.0,
            freshness_decay_modifier=0.4,
            viral_threshold_modifier=0.2,
            dark_social_modifier=2.5,
        ),
        "expected_outcomes": {
            "overall_sentiment": "hostile",
            "engagement_level": "extreme",
            "viral_type": "cringe_cascade",
            "controversy": "extreme",
            "dark_social": "extreme",
            "meme_mutations": "high",  # massively parodied
            "key_insight": "Tone-deaf co-option of social movements. The protest aesthetic without protest substance. Parodies wrote themselves.",
        },
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5. Duolingo TikTok — Unhinged brand account done right
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "duolingo_unhinged": {
        "name": "Duolingo Unhinged TikTok/Twitter Era",
        "content": (
            "me watching you open Instagram instead of doing your Spanish lesson "
            "👁️👄👁️ i see everything. your streak is in danger. this is not a threat "
            "it's a promise. 🦉 #Duolingo #LearnOnDuolingo"
        ),
        "visual_description": (
            "The Duolingo owl mascot (Duo) with an unhinged expression, "
            "peering through a window menacingly. Low-effort edit style — intentionally "
            "rough, like a shitpost. The owl's eyes are slightly too wide. "
            "Meme format: threatening bird + relatable tech anxiety."
        ),
        "platform": "twitter",
        "industry": "consumer_app",
        "humor_profile_override": ContentHumorProfile(
            primary_tone=HumorTone.SHITPOST,
            secondary_tones=[HumorTone.ABSURDIST, HumorTone.IRONY, HumorTone.REFERENCE],
            execution_score=0.9,
            originality_score=0.85,
            timing_score=0.8,
            target_humor_profiles=["meme_native", "absurdist", "edgy_humor", "sarcasm_default"],
            repelled_humor_profiles=["no_humor"],
            cringe_probability=0.05,
            screenshot_bait=0.85,
            quote_tweet_bait=0.6,
            remixability=0.7,
            engagement_multiplier=2.2,
            share_multiplier=2.0,
            comment_multiplier=1.5,
            freshness_decay_modifier=0.5,
            viral_threshold_modifier=0.3,
            dark_social_modifier=2.0,
        ),
        "expected_outcomes": {
            "overall_sentiment": "positive",
            "engagement_level": "viral",
            "viral_type": "positive_humor",
            "controversy": "minimal",
            "dark_social": "very_high",
            "meme_mutations": "moderate",  # people remix the owl
            "key_insight": "Unhinged brand accounts work when the humor matches the product experience. Everyone has Duolingo guilt. The owl being 'threatening' is funny BECAUSE it's relatable.",
        },
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 6. LinkedIn Cringe — Corporate humor that misses
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "linkedin_cringe": {
        "name": "Generic SaaS LinkedIn 'Relatable' Post",
        "content": (
            "POV: You just told your team you're switching to our platform 😂🚀\n\n"
            "[image of The Office characters celebrating]\n\n"
            "Who else has been there? 👇 Drop a 🔥 if you love productivity tools!\n\n"
            "#SaaS #Productivity #TeamWork #Innovation #WeAreHiring"
        ),
        "visual_description": (
            "Screenshot from The Office (Michael Scott celebrating) with text overlay. "
            "Low-effort meme format. The image is slightly pixelated from being "
            "screenshotted and re-uploaded multiple times. Corporate LinkedIn aesthetic "
            "mixed with stale meme format."
        ),
        "platform": "twitter",  # imagine this leaked from LinkedIn to Twitter
        "industry": "saas_b2b",
        "humor_profile_override": ContentHumorProfile(
            primary_tone=HumorTone.CRINGE_ATTEMPT,
            secondary_tones=[HumorTone.REFERENCE],
            execution_score=0.15,
            originality_score=0.05,  # extremely stale format
            timing_score=0.1,
            target_humor_profiles=[],  # nobody loves this
            repelled_humor_profiles=["meme_native", "dry_wit", "sarcasm_default", "edgy_humor"],
            cringe_probability=0.8,
            misread_probability=0.1,
            screenshot_bait=0.7,  # screenshotted to mock
            quote_tweet_bait=0.85,  # QT dunks galore
            remixability=0.6,
            primary_risk=HumorRisk.CRINGE_VIRAL,
            risks=[
                {"risk": "cringe_viral", "severity": 0.7, "description": "Will be screenshotted and mocked"},
                {"risk": "try_hard", "severity": 0.8, "description": "Obviously trying to be relatable and failing"},
            ],
            engagement_multiplier=1.5,  # engagement from mockery
            share_multiplier=1.5,
            comment_multiplier=2.0,  # lots of roast comments
            freshness_decay_modifier=1.5,  # stale fast
            viral_threshold_modifier=0.5,  # could go cringe-viral
            dark_social_modifier=2.0,
        ),
        "expected_outcomes": {
            "overall_sentiment": "negative",
            "engagement_level": "moderate_negative",
            "viral_type": "cringe_cascade",
            "controversy": "low",  # not controversial, just cringe
            "dark_social": "high",  # screenshotted to groupchats
            "meme_mutations": "moderate",  # becomes the butt of jokes
            "key_insight": "Stale meme formats + hashtag spam + 'drop a 🔥' engagement bait = peak LinkedIn cringe. Meme natives will screenshot this to their groupchats.",
        },
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 7. Apple "Shot on iPhone" — Understated excellence
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "apple_shot_on_iphone": {
        "name": "Apple Shot on iPhone Billboard Campaign",
        "content": (
            "Shot on iPhone."
        ),
        "visual_description": (
            "Stunning landscape photo taken by a real iPhone user. No filters obvious. "
            "Professional-grade quality from a consumer device. Minimal branding — just "
            "the small 'Shot on iPhone' text. No celebrity, no model. Just the photo. "
            "Billboard format: the image IS the ad."
        ),
        "platform": "twitter",
        "industry": "consumer_app",
        "humor_profile_override": ContentHumorProfile(
            primary_tone=HumorTone.NONE,
            execution_score=0.0,
            engagement_multiplier=1.0,
            share_multiplier=1.3,  # UGC element drives sharing
            freshness_decay_modifier=0.7,  # evergreen concept
            viral_threshold_modifier=1.0,
            dark_social_modifier=0.8,
        ),
        "expected_outcomes": {
            "overall_sentiment": "positive",
            "engagement_level": "moderate",
            "viral_type": "none",  # not viral, just consistently good
            "controversy": "none",
            "key_insight": "Confidence is letting the product speak for itself. Three words. No humor needed when quality is undeniable.",
        },
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 8. Scrub Daddy x Grimace — Unhinged brand collab
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "scrub_daddy_unhinged": {
        "name": "Scrub Daddy Unhinged Social Media",
        "content": (
            "some of you have never had a scrub daddy experience and it shows 💅 "
            "we're not just a sponge we're a lifestyle. "
            "our enemies (other sponges) could never. "
            "this tweet was written by the sponge. i am sentient. help."
        ),
        "visual_description": None,  # text-only
        "platform": "twitter",
        "industry": "ecommerce_dtc",
        "humor_profile_override": ContentHumorProfile(
            primary_tone=HumorTone.SHITPOST,
            secondary_tones=[HumorTone.ABSURDIST, HumorTone.SELF_DEPRECATING],
            execution_score=0.8,
            originality_score=0.75,
            target_humor_profiles=["meme_native", "absurdist", "sarcasm_default"],
            cringe_probability=0.1,
            screenshot_bait=0.75,
            quote_tweet_bait=0.5,
            remixability=0.5,
            engagement_multiplier=1.8,
            share_multiplier=1.7,
            comment_multiplier=1.4,
            freshness_decay_modifier=0.6,
            viral_threshold_modifier=0.5,
            dark_social_modifier=1.7,
        ),
        "expected_outcomes": {
            "overall_sentiment": "positive",
            "engagement_level": "high",
            "viral_type": "positive_humor",
            "controversy": "none",
            "key_insight": "A cleaning sponge shouldn't be this funny. The absurdity of a sponge brand having an unhinged social presence IS the humor. Works because it's committed to the bit.",
        },
    },
}


# ──────────────────────────────────────────────────────────────────────
# Test Runner
# ──────────────────────────────────────────────────────────────────────

def _build_test_crowd(industry: str, crowd_size: int = 100) -> tuple[list[dict], object]:
    """Build a test crowd with personas and social graph."""
    archetype_ids = build_crowd_distribution(crowd_size, industry)
    personas = [
        generate_persona_skeleton(i, aid, industry)
        for i, aid in enumerate(archetype_ids)
    ]
    influence_map = {p["id"]: p["influence_weight"] for p in personas}
    graph = build_social_graph([p["id"] for p in personas], influence_map)
    return personas, graph


async def run_campaign_test(campaign_key: str, crowd_size: int = 100) -> dict:
    """Run a single campaign through the simulation and return results."""
    campaign = CAMPAIGNS[campaign_key]

    # Build crowd
    personas, graph = _build_test_crowd(campaign["industry"], crowd_size)

    # Build env config
    env_kwargs = {"crowd_size": crowd_size, "max_rounds": 30}
    if "env_override" in campaign:
        env_kwargs.update(campaign["env_override"])
    env_config = EnvironmentConfig(**env_kwargs)

    # Get humor profile
    humor_profile = campaign.get("humor_profile_override")

    # Initialize and run
    state = initialize_simulation(
        material_content=campaign["content"],
        personas=personas,
        graph=graph,
        env_config=env_config,
        visual_context=campaign.get("visual_description"),
        humor_profile=humor_profile,
    )
    final_state = await run_simulation(state)

    # Compute results
    total = len(final_state.personas)
    exposed = len(final_state.exposed)
    engaged = len(final_state.engaged)

    # Sentiment breakdown
    sentiments = {}
    for a in final_state.all_actions:
        s = a.sentiment.value
        sentiments[s] = sentiments.get(s, 0) + 1

    # Action breakdown
    actions = {}
    for a in final_state.all_actions:
        act = a.action.value
        actions[act] = actions.get(act, 0) + 1

    # Platform breakdown
    platform_results = {}
    for platform, ps in final_state.platform_states.items():
        platform_results[platform.value] = {
            "engagement_count": ps.engagement_count,
            "share_count": ps.share_count,
            "trending_score": ps.trending_score,
        }

    return {
        "campaign": campaign["name"],
        "expected": campaign["expected_outcomes"],
        "actual": {
            "total_agents": total,
            "exposed": exposed,
            "engaged": engaged,
            "exposure_rate": exposed / total if total else 0,
            "engagement_rate": engaged / total if total else 0,
            "sentiment_breakdown": sentiments,
            "action_breakdown": actions,
            "rounds_completed": final_state.current_round,
            "viral_cascades": len(final_state.viral_cascades),
            "cringe_cascades": len(final_state.cringe_cascades),
            "meme_mutations": len(final_state.meme_mutations),
            "coalitions": len(final_state.coalitions),
            "opinion_clusters": final_state.opinion_clusters,
            "platform_results": platform_results,
        },
    }


async def run_all_campaign_tests(crowd_size: int = 100) -> list[dict]:
    """Run all campaign tests and return comparative results."""
    results = []
    for key in CAMPAIGNS:
        result = await run_campaign_test(key, crowd_size)
        results.append(result)
    return results


def print_campaign_report(result: dict):
    """Print a human-readable report for a campaign test."""
    actual = result["actual"]
    expected = result["expected"]

    print(f"\n{'='*70}")
    print(f"CAMPAIGN: {result['campaign']}")
    print(f"{'='*70}")
    print(f"Rounds completed: {actual['rounds_completed']}")
    print(f"Exposure: {actual['exposed']}/{actual['total_agents']} ({actual['exposure_rate']:.0%})")
    print(f"Engagement: {actual['engaged']}/{actual['total_agents']} ({actual['engagement_rate']:.0%})")
    print(f"Viral cascades: {actual['viral_cascades']}")
    print(f"Cringe cascades: {actual['cringe_cascades']}")
    print(f"Meme mutations: {actual['meme_mutations']}")
    print(f"Coalitions: {actual['coalitions']}")
    print(f"\nSentiment: {actual['sentiment_breakdown']}")
    print(f"\nTop actions: {dict(sorted(actual['action_breakdown'].items(), key=lambda x: x[1], reverse=True)[:8])}")
    print(f"\nPlatforms: {actual['platform_results']}")
    print(f"\nOpinion by archetype:")
    for arch, score in sorted(actual['opinion_clusters'].items(), key=lambda x: x[1]):
        bar = "█" * int(abs(score) * 20)
        direction = "+" if score > 0 else "-"
        print(f"  {arch:25s} {direction}{bar} ({score:+.2f})")
    print(f"\nExpected: {expected.get('overall_sentiment', '?')} | {expected.get('viral_type', '?')} | controversy={expected.get('controversy', '?')}")
    print(f"Key insight: {expected.get('key_insight', 'N/A')}")


# ──────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    async def main():
        if len(sys.argv) > 1:
            key = sys.argv[1]
            if key == "all":
                results = await run_all_campaign_tests()
                for r in results:
                    print_campaign_report(r)
            elif key in CAMPAIGNS:
                result = await run_campaign_test(key)
                print_campaign_report(result)
            else:
                print(f"Unknown campaign: {key}")
                print(f"Available: {', '.join(CAMPAIGNS.keys())}")
        else:
            print("Usage: python -m tests.scenarios.test_real_campaigns <campaign_key|all>")
            print(f"\nAvailable campaigns:")
            for key, camp in CAMPAIGNS.items():
                print(f"  {key:30s} {camp['name']}")

    asyncio.run(main())
