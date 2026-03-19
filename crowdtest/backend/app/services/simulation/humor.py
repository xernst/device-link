"""Content tone & humor analyzer: classifies text AND visual content before simulation.

This runs BEFORE the simulation starts, not during. It produces a HumorProfile for
the content itself, which then modifies how every agent interacts with it throughout
the entire simulation.

Humor is the #1 driver of social media virality. A post's humor tone changes:
- WHO engages (meme natives vs serious professionals)
- HOW they engage (quote-tweet dunk vs heartfelt share vs screenshot-to-groupchat)
- WHETHER it goes viral (and for the right or wrong reasons)
- HOW FAST content freshness decays (funny content has longer shelf life)
- WHAT KIND of cascade occurs (positive viral vs cringe cascade)
"""

from dataclasses import dataclass, field
from enum import Enum

from app.core.config import settings


class HumorTone(str, Enum):
    """Primary humor classification for content."""
    NONE = "none"  # straight, no humor attempt
    MEME = "meme"  # uses recognizable meme format/template
    SATIRE = "satire"  # ironic commentary on industry/culture
    PARODY = "parody"  # mimicking another style for comedic effect
    IRONY = "irony"  # saying the opposite of what's meant
    SARCASM = "sarcasm"  # biting, often self-deprecating
    SHITPOST = "shitpost"  # deliberately low-effort, absurdist, chaotic
    WHOLESOME = "wholesome"  # heartwarming, feel-good humor
    CRINGE_ATTEMPT = "cringe_attempt"  # trying to be funny but missing
    SELF_DEPRECATING = "self_deprecating"  # brand making fun of itself
    ROAST = "roast"  # dunking on competitors or trends
    ABSURDIST = "absurdist"  # surreal, makes no logical sense
    WORDPLAY = "wordplay"  # puns, clever language
    REFERENCE = "reference"  # relies on cultural/pop culture knowledge
    DRY = "dry"  # understated, deadpan delivery


class HumorRisk(str, Enum):
    """What could go wrong with this humor."""
    NONE = "none"
    CRINGE_VIRAL = "cringe_viral"  # goes viral for wrong reasons
    MISREAD_IRONY = "misread_irony"  # literal readers get offended
    ALIENATE_SEGMENT = "alienate_segment"  # humor excludes a demographic
    TONE_DEAF = "tone_deaf"  # humor clashes with current events/context
    TRY_HARD = "try_hard"  # obvious corporate effort to be relatable
    OFFENSIVE = "offensive"  # crosses a line for some audiences
    INSIDE_JOKE = "inside_joke"  # too niche, most people won't get it


@dataclass
class ContentHumorProfile:
    """The humor DNA of a piece of content. Computed once, used every round.

    This is the content's humor fingerprint — it determines how agents with
    different humor worldviews will react throughout the entire simulation.
    """
    # Primary classification
    primary_tone: HumorTone = HumorTone.NONE
    secondary_tones: list[HumorTone] = field(default_factory=list)

    # Execution quality (0-1)
    execution_score: float = 0.0  # how well the humor lands (0=cringe, 1=nailed it)
    originality_score: float = 0.0  # 0=overused format, 1=never seen before
    timing_score: float = 0.0  # 0=stale reference, 1=perfectly timed cultural moment

    # Audience targeting
    target_humor_profiles: list[str] = field(default_factory=list)  # which humor worldviews this appeals to
    repelled_humor_profiles: list[str] = field(default_factory=list)  # which humor worldviews this repels

    # Risk assessment
    primary_risk: HumorRisk = HumorRisk.NONE
    risks: list[dict] = field(default_factory=list)  # [{"risk": HumorRisk, "severity": 0-1, "description": str}]
    cringe_probability: float = 0.0  # 0-1, overall cringe risk
    misread_probability: float = 0.0  # 0-1, chance of audience misunderstanding the tone

    # Meme mechanics
    meme_template: str | None = None  # recognized format name if applicable
    remixability: float = 0.0  # 0-1, how easy it is for agents to remix/mock this
    screenshot_bait: float = 0.0  # 0-1, how likely someone screenshots this for a groupchat or dunk
    quote_tweet_bait: float = 0.0  # 0-1, how likely this gets quote-tweeted with commentary

    # Cultural context
    references: list[str] = field(default_factory=list)  # what cultural knowledge is required
    shelf_life: str = "standard"  # "ephemeral" (hours), "short" (days), "standard" (weeks), "evergreen"
    requires_context: bool = False  # does this need external knowledge to be funny?

    # Engine modifiers — these directly change simulation mechanics
    engagement_multiplier: float = 1.0  # multiplied into base engagement rate
    share_multiplier: float = 1.0  # multiplied into share probability
    comment_multiplier: float = 1.0  # multiplied into comment probability
    freshness_decay_modifier: float = 1.0  # <1 = slower decay (funny stays fresh), >1 = faster
    viral_threshold_modifier: float = 1.0  # <1 = easier to go viral
    dark_social_modifier: float = 1.0  # >1 = more DMs/screenshots


# ──────────────────────────────────────────────────────────────────────
# Humor-Persona Compatibility Matrix
# ──────────────────────────────────────────────────────────────────────

# How each humor worldview reacts to each content humor tone.
# Values: engagement modifier (1.0 = neutral, >1 = more engaged, <1 = less engaged)
# Negative values mean active hostility (dunking, roasting, reporting)
HUMOR_COMPATIBILITY: dict[str, dict[str, float]] = {
    "meme_native": {
        "meme": 1.8, "shitpost": 2.0, "absurdist": 1.7, "roast": 1.6,
        "irony": 1.5, "sarcasm": 1.4, "satire": 1.3, "reference": 1.5,
        "self_deprecating": 1.4, "parody": 1.3, "dry": 1.2, "wordplay": 0.8,
        "wholesome": 0.7, "cringe_attempt": -1.5,  # will actively dunk
        "none": 0.6,
    },
    "dry_wit": {
        "dry": 1.8, "irony": 1.6, "sarcasm": 1.5, "satire": 1.5,
        "self_deprecating": 1.3, "wordplay": 1.3, "roast": 1.1,
        "parody": 1.1, "reference": 1.2, "absurdist": 0.8,
        "meme": 0.9, "shitpost": 0.7, "wholesome": 0.6,
        "cringe_attempt": -1.2, "none": 0.9,
    },
    "wholesome_humor": {
        "wholesome": 2.0, "self_deprecating": 1.3, "wordplay": 1.2,
        "dry": 0.9, "reference": 0.9, "parody": 0.8,
        "meme": 0.8, "irony": 0.7, "sarcasm": 0.5, "satire": 0.6,
        "roast": 0.3, "shitpost": 0.3, "absurdist": 0.5,
        "cringe_attempt": 0.6,  # wholesome people are forgiving
        "none": 1.0,
    },
    "edgy_humor": {
        "roast": 2.0, "shitpost": 1.7, "sarcasm": 1.6, "satire": 1.5,
        "irony": 1.4, "absurdist": 1.3, "meme": 1.3, "parody": 1.3,
        "self_deprecating": 1.2, "dry": 1.0, "reference": 1.0,
        "wordplay": 0.7, "wholesome": 0.4,
        "cringe_attempt": -1.0,  # will mock but less aggressively
        "none": 0.5,
    },
    "no_humor": {
        "none": 1.5,  # prefers serious content
        "dry": 0.9, "satire": 0.7, "wordplay": 0.7,
        "self_deprecating": 0.6, "irony": 0.5, "sarcasm": 0.5,
        "roast": 0.4, "reference": 0.5, "parody": 0.4,
        "meme": 0.3, "shitpost": 0.2, "absurdist": 0.2,
        "wholesome": 0.7,
        "cringe_attempt": 0.3,  # just disengages, doesn't dunk
    },
    "sarcasm_default": {
        "sarcasm": 1.8, "irony": 1.7, "dry": 1.6, "roast": 1.5,
        "satire": 1.4, "self_deprecating": 1.5, "shitpost": 1.2,
        "meme": 1.1, "parody": 1.2, "reference": 1.1, "absurdist": 1.0,
        "wordplay": 0.8, "wholesome": 0.5,
        "cringe_attempt": -1.8,  # sarcasm defaults LIVE for dunking on cringe
        "none": 0.6,  # will add sarcasm to earnest content anyway
    },
    "absurdist": {
        "absurdist": 2.0, "shitpost": 1.8, "meme": 1.4, "parody": 1.3,
        "irony": 1.2, "sarcasm": 1.0, "roast": 1.0, "satire": 1.0,
        "self_deprecating": 1.1, "reference": 1.1, "dry": 0.9,
        "wordplay": 0.8, "wholesome": 0.6,
        "cringe_attempt": -0.8,  # finds cringe almost entertaining
        "none": 0.4,
    },
    "cultural_humor": {
        "reference": 2.0, "satire": 1.5, "parody": 1.5, "meme": 1.4,
        "irony": 1.3, "dry": 1.2, "sarcasm": 1.1, "roast": 1.1,
        "self_deprecating": 1.0, "absurdist": 0.9, "shitpost": 0.8,
        "wordplay": 1.2, "wholesome": 0.7,
        "cringe_attempt": -1.0,
        "none": 0.7,
    },
}


def get_humor_compatibility(humor_profile: str, content_tone: str) -> float:
    """Get the engagement modifier for a humor profile + content tone combo.

    Returns a multiplier: >1 means more engaged, <1 means less, negative means hostile.
    """
    profile_map = HUMOR_COMPATIBILITY.get(humor_profile, {})
    return profile_map.get(content_tone, 1.0)


# ──────────────────────────────────────────────────────────────────────
# Content Analysis Prompts
# ──────────────────────────────────────────────────────────────────────

HUMOR_ANALYSIS_SYSTEM = """You are an expert social media humor analyst. Your job is to dissect the humor DNA of marketing content — not just "is it funny?" but HOW it's trying to be funny, WHO it's funny to, what could go WRONG, and how it will spread.

You understand:
- Every meme format and its lifecycle (rising, peak, dead, ironic revival)
- The difference between brands that "get it" (Wendy's, Duolingo, Scrub Daddy) and brands that don't (corporate "fellow kids" attempts)
- How humor fragments audiences: the same post can be genuinely funny, offensively unfunny, and completely mystifying to three different people
- Dark social dynamics: the funniest content often spreads through screenshots in group chats, not public shares
- Cringe cascades: how bad humor attempts become the content themselves (getting roasted IS the engagement)
- Platform humor cultures: Twitter rewards wit and dunks, Reddit rewards reference depth and absurdist threads, TikTok rewards timing and format mastery

Return structured JSON. Be brutally honest about execution quality."""

HUMOR_ANALYSIS_USER = """Analyze the humor DNA of this marketing content.

## Content
{content}

{visual_context}

## Context
Platform: {platform}
Industry: {industry}
Brand voice: {brand_voice}

## Return JSON:
{{
  "primary_tone": "none/meme/satire/parody/irony/sarcasm/shitpost/wholesome/cringe_attempt/self_deprecating/roast/absurdist/wordplay/reference/dry",
  "secondary_tones": ["list of secondary humor tones present"],
  "execution_score": 0.0-1.0,
  "originality_score": 0.0-1.0,
  "timing_score": 0.0-1.0,
  "target_humor_profiles": ["which humor worldviews will love this"],
  "repelled_humor_profiles": ["which humor worldviews will hate this"],
  "primary_risk": "none/cringe_viral/misread_irony/alienate_segment/tone_deaf/try_hard/offensive/inside_joke",
  "risks": [
    {{"risk": "risk_type", "severity": 0.0-1.0, "description": "why this is a risk"}}
  ],
  "cringe_probability": 0.0-1.0,
  "misread_probability": 0.0-1.0,
  "meme_template": "recognized meme format name or null",
  "remixability": 0.0-1.0,
  "screenshot_bait": 0.0-1.0,
  "quote_tweet_bait": 0.0-1.0,
  "references": ["cultural references required to understand this"],
  "shelf_life": "ephemeral/short/standard/evergreen",
  "requires_context": true/false,
  "reasoning": "2-3 sentences explaining your assessment"
}}"""


# ──────────────────────────────────────────────────────────────────────
# Content Analysis Function
# ──────────────────────────────────────────────────────────────────────

async def analyze_content_humor(
    content: str,
    platform: str = "twitter",
    industry: str = "",
    brand_voice: str = "",
    visual_context: str = "",
) -> ContentHumorProfile:
    """Analyze content humor using Claude and return a ContentHumorProfile.

    This is called ONCE before simulation starts. The resulting profile
    modifies engine behavior for every round.
    """
    import anthropic
    import json

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model=settings.sonnet_model,
        max_tokens=1024,
        system=HUMOR_ANALYSIS_SYSTEM,
        messages=[{
            "role": "user",
            "content": HUMOR_ANALYSIS_USER.format(
                content=content,
                platform=platform,
                industry=industry or "general",
                brand_voice=brand_voice or "unknown",
                visual_context=visual_context or "(no visual content)",
            ),
        }],
    )

    raw = response.content[0].text
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    data = json.loads(raw)

    # Build the profile
    primary = HumorTone(data.get("primary_tone", "none"))
    profile = ContentHumorProfile(
        primary_tone=primary,
        secondary_tones=[HumorTone(t) for t in data.get("secondary_tones", []) if t in HumorTone.__members__.values()],
        execution_score=data.get("execution_score", 0.0),
        originality_score=data.get("originality_score", 0.0),
        timing_score=data.get("timing_score", 0.0),
        target_humor_profiles=data.get("target_humor_profiles", []),
        repelled_humor_profiles=data.get("repelled_humor_profiles", []),
        primary_risk=HumorRisk(data.get("primary_risk", "none")),
        risks=data.get("risks", []),
        cringe_probability=data.get("cringe_probability", 0.0),
        misread_probability=data.get("misread_probability", 0.0),
        meme_template=data.get("meme_template"),
        remixability=data.get("remixability", 0.0),
        screenshot_bait=data.get("screenshot_bait", 0.0),
        quote_tweet_bait=data.get("quote_tweet_bait", 0.0),
        references=data.get("references", []),
        shelf_life=data.get("shelf_life", "standard"),
        requires_context=data.get("requires_context", False),
    )

    # Compute engine modifiers from the analysis
    profile.engagement_multiplier = _compute_engagement_multiplier(profile)
    profile.share_multiplier = _compute_share_multiplier(profile)
    profile.comment_multiplier = _compute_comment_multiplier(profile)
    profile.freshness_decay_modifier = _compute_freshness_modifier(profile)
    profile.viral_threshold_modifier = _compute_viral_modifier(profile)
    profile.dark_social_modifier = _compute_dark_social_modifier(profile)

    return profile


def _compute_engagement_multiplier(profile: ContentHumorProfile) -> float:
    """Funny content gets more engagement. Bad funny gets even more (for wrong reasons)."""
    if profile.primary_tone == HumorTone.NONE:
        return 1.0

    # Good humor boosts engagement
    base = 1.0 + (profile.execution_score * 0.5)

    # Cringe ALSO boosts engagement (people engage to dunk)
    if profile.cringe_probability > 0.5:
        base += profile.cringe_probability * 0.4

    # Originality bonus
    base += profile.originality_score * 0.2

    return base


def _compute_share_multiplier(profile: ContentHumorProfile) -> float:
    """Funny content gets shared more. Screenshot-bait and quote-tweet-bait multiply this."""
    if profile.primary_tone == HumorTone.NONE:
        return 1.0

    base = 1.0 + (profile.execution_score * 0.6)
    base += profile.screenshot_bait * 0.3
    base += profile.quote_tweet_bait * 0.3

    # Cringe gets shared too (as a warning or to mock)
    if profile.cringe_probability > 0.4:
        base += profile.cringe_probability * 0.3

    return base


def _compute_comment_multiplier(profile: ContentHumorProfile) -> float:
    """Humor drives comments. Bad humor drives even more (roasting). Irony drives confusion."""
    if profile.primary_tone == HumorTone.NONE:
        return 1.0

    base = 1.0 + (profile.execution_score * 0.3)

    # Cringe drives comment storms (roasting)
    if profile.cringe_probability > 0.3:
        base += profile.cringe_probability * 0.6

    # Irony/sarcasm drives "wait is this serious?" comments
    if profile.misread_probability > 0.3:
        base += profile.misread_probability * 0.4

    # Remixable content drives "I can do better" comments
    base += profile.remixability * 0.3

    return base


def _compute_freshness_modifier(profile: ContentHumorProfile) -> float:
    """Funny content stays fresh longer. Except ephemeral references."""
    shelf_life_map = {
        "ephemeral": 1.5,  # decays faster
        "short": 1.2,
        "standard": 1.0,
        "evergreen": 0.5,  # decays much slower
    }
    base = shelf_life_map.get(profile.shelf_life, 1.0)

    # Good humor has longer shelf life
    if profile.execution_score > 0.7:
        base *= 0.8  # slower decay

    return base


def _compute_viral_modifier(profile: ContentHumorProfile) -> float:
    """Funny content goes viral easier. Cringe content goes viral even easier."""
    if profile.primary_tone == HumorTone.NONE:
        return 1.0

    # Lower = easier to go viral
    base = 1.0 - (profile.execution_score * 0.3)

    # Cringe has the lowest viral threshold (easiest to go viral)
    if profile.cringe_probability > 0.5:
        base *= 0.6

    # Screenshot bait lowers threshold
    base *= (1.0 - profile.screenshot_bait * 0.2)

    return max(0.3, base)  # floor at 0.3


def _compute_dark_social_modifier(profile: ContentHumorProfile) -> float:
    """Funny content drives more dark social (DMs, screenshots, groupchats)."""
    if profile.primary_tone == HumorTone.NONE:
        return 1.0

    base = 1.0 + (profile.screenshot_bait * 0.5)

    # Cringe gets screenshotted and sent to friends ("you gotta see this")
    if profile.cringe_probability > 0.3:
        base += profile.cringe_probability * 0.6

    # Inside jokes get DM'd to the in-group
    if profile.requires_context:
        base += 0.3

    return base


# ──────────────────────────────────────────────────────────────────────
# Rule-based fallback (when LLM is not available)
# ──────────────────────────────────────────────────────────────────────

def analyze_content_humor_fast(content: str) -> ContentHumorProfile:
    """Fast, rule-based humor detection fallback. No LLM call.

    Checks for humor signals in text content. Less accurate but instant.
    Used for development/testing or when LLM budget is exhausted.
    """
    content_lower = content.lower()

    # Meme/humor signal detection
    meme_signals = ["meme", "shitpost", "lmao", "lol", "bruh", "no cap", "fr fr", "ong",
                    "based", "ratio", "cope", "seethe", "chad", "sigma", "npc",
                    "living rent free", "touch grass", "skill issue"]
    sarcasm_signals = ["sure jan", "totally", "wow such", "oh great another",
                       "revolutionary", "groundbreaking", "game-changing",
                       "/s", "imagine thinking", "tell me without telling me"]
    wholesome_signals = ["wholesome", "faith in humanity", "made my day",
                         "crying", "protect this", "we don't deserve"]
    roast_signals = ["shots fired", "no chill", "chose violence", "savage",
                     "destroyed", "murdered by words", "boom roasted"]
    cringe_signals = ["fellow kids", "how do you do", "lit fam", "on fleek",
                      "yolo", "adulting", "it's giving", "slay queen"]

    # Count signals
    meme_count = sum(1 for s in meme_signals if s in content_lower)
    sarcasm_count = sum(1 for s in sarcasm_signals if s in content_lower)
    wholesome_count = sum(1 for s in wholesome_signals if s in content_lower)
    roast_count = sum(1 for s in roast_signals if s in content_lower)
    cringe_count = sum(1 for s in cringe_signals if s in content_lower)

    # Emoji humor signals
    humor_emoji = ["😂", "💀", "🤣", "😭", "🫡", "🗿", "😤", "🤡", "🔥"]
    emoji_count = sum(content.count(e) for e in humor_emoji)

    # Classify
    if cringe_count >= 2:
        tone = HumorTone.CRINGE_ATTEMPT
    elif meme_count >= 2 or emoji_count >= 3:
        tone = HumorTone.MEME
    elif sarcasm_count >= 2:
        tone = HumorTone.SARCASM
    elif roast_count >= 1:
        tone = HumorTone.ROAST
    elif wholesome_count >= 1:
        tone = HumorTone.WHOLESOME
    elif emoji_count >= 1 and (meme_count >= 1 or sarcasm_count >= 1):
        tone = HumorTone.IRONY
    else:
        tone = HumorTone.NONE

    profile = ContentHumorProfile(primary_tone=tone)

    if tone != HumorTone.NONE:
        # Rough estimates
        profile.execution_score = 0.5 if tone != HumorTone.CRINGE_ATTEMPT else 0.2
        profile.cringe_probability = 0.7 if tone == HumorTone.CRINGE_ATTEMPT else 0.2
        profile.screenshot_bait = 0.5 if tone in (HumorTone.CRINGE_ATTEMPT, HumorTone.ROAST) else 0.3
        profile.remixability = 0.6 if tone == HumorTone.MEME else 0.3
        profile.quote_tweet_bait = 0.6 if tone in (HumorTone.SARCASM, HumorTone.ROAST) else 0.3

        # Compute engine modifiers
        profile.engagement_multiplier = _compute_engagement_multiplier(profile)
        profile.share_multiplier = _compute_share_multiplier(profile)
        profile.comment_multiplier = _compute_comment_multiplier(profile)
        profile.freshness_decay_modifier = _compute_freshness_modifier(profile)
        profile.viral_threshold_modifier = _compute_viral_modifier(profile)
        profile.dark_social_modifier = _compute_dark_social_modifier(profile)

    return profile
