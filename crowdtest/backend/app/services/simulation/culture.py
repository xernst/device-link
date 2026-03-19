"""Cultural Context Layer: keeps the simulation culturally educated and current.

The Problem:
- All worldview triggers, humor tones, and persona archetypes are hardcoded
- No awareness of current date, trending topics, or active controversies
- Meme formats, slang, and cultural references are frozen in time

The Solution:
- CulturalPulse: a pre-simulation LLM call that generates current cultural context
  for the specific content being tested, grounded in today's date and real-world events
- Dynamic trigger augmentation: expands persona trigger lists with content-specific
  cultural flashpoints identified by the LLM
- Context injection: every LLM prompt receives cultural context so agents behave
  with awareness of the current moment
"""

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass
class TrendingTopic:
    """A single cultural flashpoint or trending topic relevant to the simulation."""
    topic: str  # e.g., "AI replacing jobs"
    relevance: float  # 0-1, how relevant to the content being tested
    sentiment_lean: str  # "positive", "negative", "polarized", "neutral"
    affected_worldviews: list[str] = field(default_factory=list)  # which worldview profiles care
    trigger_words: list[str] = field(default_factory=list)  # additional triggers to inject
    context: str = ""  # brief explanation of why this matters


@dataclass
class MemeLifecycle:
    """Status of a meme format or cultural reference."""
    format_name: str  # e.g., "skibidi", "brain rot", "girl dinner"
    status: str  # "rising", "peak", "declining", "dead", "ironic_revival"
    audience: str  # who uses it: "gen_z", "millennial", "mainstream", "niche"
    brand_safety: str  # "safe", "risky", "cringe_if_brand_uses", "never"


@dataclass
class CulturalPulse:
    """Pre-simulation cultural intelligence snapshot.

    Generated once per simulation run by an LLM call grounded in the current date.
    Provides the cultural context that makes agents behave like they live in today's
    world, not a frozen snapshot.
    """
    # When this pulse was generated
    generated_at: str = ""
    current_date: str = ""

    # Content-specific cultural context
    content_cultural_moment: str = ""  # how does this content land RIGHT NOW?
    content_sensitivity_flags: list[str] = field(default_factory=list)  # active controversies this touches

    # Trending topics relevant to this content/industry
    trending_topics: list[TrendingTopic] = field(default_factory=list)

    # Meme landscape
    active_memes: list[MemeLifecycle] = field(default_factory=list)
    dead_memes: list[str] = field(default_factory=list)  # using these = cringe

    # Slang currency (what's current vs dated)
    current_slang: dict[str, str] = field(default_factory=dict)  # term -> meaning
    dated_slang: list[str] = field(default_factory=list)  # using these = fellow kids

    # Dynamic trigger augmentation: additional triggers to inject into personas
    # Keyed by worldview dimension + modifier (e.g., "political:conservative")
    additional_triggers: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    # Format: {"political:conservative": {"negative": ["term1"], "positive": ["term2"], "sensitivity": ["term3"]}}

    # Cultural temperature
    overall_mood: str = ""  # "optimistic", "anxious", "angry", "exhausted", "manic"
    fatigue_topics: list[str] = field(default_factory=list)  # topics people are tired of

    def to_prompt_block(self) -> str:
        """Format cultural context for injection into LLM prompts."""
        lines = [f"## Cultural Context (as of {self.current_date})"]

        if self.content_cultural_moment:
            lines.append(f"\n**How this content lands right now:** {self.content_cultural_moment}")

        if self.content_sensitivity_flags:
            lines.append(f"\n**Active sensitivity flags:** {', '.join(self.content_sensitivity_flags)}")

        if self.overall_mood:
            lines.append(f"\n**Cultural mood:** {self.overall_mood}")

        if self.trending_topics:
            lines.append("\n**Relevant trending topics:**")
            for t in self.trending_topics[:5]:
                lines.append(f"- {t.topic} ({t.sentiment_lean}) — {t.context}")

        if self.active_memes:
            lines.append("\n**Meme landscape:**")
            for m in self.active_memes[:5]:
                lines.append(f"- {m.format_name}: {m.status} (audience: {m.audience}, brand safety: {m.brand_safety})")

        if self.dead_memes:
            lines.append(f"\n**Dead/cringe memes (DO NOT use):** {', '.join(self.dead_memes[:10])}")

        if self.current_slang:
            slang_str = ", ".join(f"{k} ({v})" for k, v in list(self.current_slang.items())[:10])
            lines.append(f"\n**Current slang:** {slang_str}")

        if self.dated_slang:
            lines.append(f"\n**Dated slang (= fellow kids energy):** {', '.join(self.dated_slang[:10])}")

        if self.fatigue_topics:
            lines.append(f"\n**Topic fatigue (people are over it):** {', '.join(self.fatigue_topics)}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        d = {
            "generated_at": self.generated_at,
            "current_date": self.current_date,
            "content_cultural_moment": self.content_cultural_moment,
            "content_sensitivity_flags": self.content_sensitivity_flags,
            "trending_topics": [
                {
                    "topic": t.topic,
                    "relevance": t.relevance,
                    "sentiment_lean": t.sentiment_lean,
                    "affected_worldviews": t.affected_worldviews,
                    "trigger_words": t.trigger_words,
                    "context": t.context,
                }
                for t in self.trending_topics
            ],
            "active_memes": [
                {
                    "format_name": m.format_name,
                    "status": m.status,
                    "audience": m.audience,
                    "brand_safety": m.brand_safety,
                }
                for m in self.active_memes
            ],
            "dead_memes": self.dead_memes,
            "current_slang": self.current_slang,
            "dated_slang": self.dated_slang,
            "additional_triggers": self.additional_triggers,
            "overall_mood": self.overall_mood,
            "fatigue_topics": self.fatigue_topics,
        }
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "CulturalPulse":
        """Deserialize from JSON."""
        pulse = cls(
            generated_at=d.get("generated_at", ""),
            current_date=d.get("current_date", ""),
            content_cultural_moment=d.get("content_cultural_moment", ""),
            content_sensitivity_flags=d.get("content_sensitivity_flags", []),
            dead_memes=d.get("dead_memes", []),
            current_slang=d.get("current_slang", {}),
            dated_slang=d.get("dated_slang", []),
            additional_triggers=d.get("additional_triggers", {}),
            overall_mood=d.get("overall_mood", ""),
            fatigue_topics=d.get("fatigue_topics", []),
        )
        for t in d.get("trending_topics", []):
            pulse.trending_topics.append(TrendingTopic(**t))
        for m in d.get("active_memes", []):
            pulse.active_memes.append(MemeLifecycle(**m))
        return pulse

    @classmethod
    def load(cls, path: str | Path) -> "CulturalPulse":
        """Load from a JSON file."""
        with open(path) as f:
            return cls.from_dict(json.load(f))

    def save(self, path: str | Path) -> None:
        """Save to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


# ──────────────────────────────────────────────────────────────────────
# Cultural Pulse Generation (LLM-powered)
# ──────────────────────────────────────────────────────────────────────

CULTURAL_PULSE_SYSTEM = """You are a Cultural Intelligence Analyst for a social media simulation engine.

Your job: analyze a piece of marketing content and generate a cultural context snapshot that tells the simulation HOW THIS CONTENT LANDS RIGHT NOW — not in general, but today, given the current cultural moment, trending topics, active controversies, and meme landscape.

You must be specific. Don't give generic advice. Ground everything in the current date and real-world context.

Return a JSON object with these fields:
{
  "content_cultural_moment": "1-2 sentences on how this specific content lands given today's cultural context",
  "content_sensitivity_flags": ["list of active controversies or sensitivities this content touches"],
  "overall_mood": "one word: optimistic | anxious | angry | exhausted | manic | polarized | hopeful",
  "trending_topics": [
    {
      "topic": "topic name",
      "relevance": 0.0-1.0,
      "sentiment_lean": "positive | negative | polarized | neutral",
      "affected_worldviews": ["political:conservative", "humor:meme_native"],
      "trigger_words": ["additional trigger words for personas who care about this"],
      "context": "why this matters for this content"
    }
  ],
  "active_memes": [
    {
      "format_name": "meme name",
      "status": "rising | peak | declining | dead | ironic_revival",
      "audience": "gen_z | millennial | mainstream | niche",
      "brand_safety": "safe | risky | cringe_if_brand_uses | never"
    }
  ],
  "dead_memes": ["memes that are over and cringe to use"],
  "current_slang": {"term": "meaning"},
  "dated_slang": ["terms that are dated/cringe now"],
  "fatigue_topics": ["topics people are tired of seeing"],
  "additional_triggers": {
    "political:conservative": {"negative": ["new trigger words"], "positive": [], "sensitivity": []},
    "humor:meme_native": {"negative": ["dead meme formats"], "positive": ["current formats"]}
  }
}"""

CULTURAL_PULSE_USER = """## Date
Today is {current_date}.

## Content Being Tested
{material}

## Visual Description (if applicable)
{visual_context}

## Industry
{industry}

## Existing Worldview Dimensions
The simulation has these worldview dimensions: political (progressive, moderate_left, centrist, moderate_right, conservative, libertarian, apolitical), religious (secular, spiritual, mainstream_religious, devout), cultural (individualist, collectivist, traditionalist, cosmopolitan, multicultural), humor (meme_native, dry_wit, wholesome_humor, edgy_humor, no_humor, sarcasm_default, absurdist, cultural_humor), generational (gen_z_native, millennial_pragmatist, gen_x_independent, boomer_established).

Generate a cultural pulse for THIS content on THIS date. Be specific to what's actually happening in culture right now. The additional_triggers should contain NEW trigger words that aren't already in the system — words and phrases that are culturally relevant TODAY for specific worldview profiles reacting to this content."""


async def generate_cultural_pulse(
    material: str,
    industry: str,
    visual_context: str = "",
    current_date_override: str | None = None,
) -> CulturalPulse:
    """Generate a CulturalPulse via LLM for the current cultural moment.

    This is the key call that makes the simulation culturally aware.
    Called once at the start of each simulation, before environment config.
    """
    today = current_date_override or date.today().isoformat()

    # Build prompt
    user_prompt = CULTURAL_PULSE_USER.format(
        current_date=today,
        material=material,
        visual_context=visual_context or "(no visual content)",
        industry=industry,
    )

    # TODO: implement with anthropic SDK (Sonnet call)
    # For now, return a minimal pulse with the date set
    pulse = CulturalPulse(
        generated_at=datetime.now().isoformat(),
        current_date=today,
    )
    return pulse


def generate_cultural_pulse_fast(
    material: str,
    industry: str,
    visual_context: str = "",
    current_date_override: str | None = None,
) -> CulturalPulse:
    """Rule-based cultural pulse for testing (no LLM call).

    Provides baseline cultural awareness from hardcoded knowledge.
    Production should use generate_cultural_pulse() with LLM.
    """
    today = current_date_override or date.today().isoformat()
    content_lower = material.lower()

    # Detect content themes for trigger augmentation
    additional_triggers: dict[str, dict[str, list[str]]] = {}
    sensitivity_flags: list[str] = []

    # Culture war detection
    culture_war_signals = ["pride", "trans", "woke", "dei", "inclusion", "diversity",
                           "gender", "pronouns", "lgbtq", "boycott", "cancel"]
    culture_war_hits = [s for s in culture_war_signals if s in content_lower]
    if culture_war_hits:
        sensitivity_flags.append("culture war topic detected")
        additional_triggers["political:conservative"] = {
            "negative": culture_war_hits,
            "positive": [],
            "sensitivity": ["culture war", "brand politics"],
        }
        additional_triggers["political:progressive"] = {
            "positive": culture_war_hits,
            "negative": [],
            "sensitivity": ["rainbow capitalism", "performative allyship"],
        }

    # AI/tech anxiety detection
    ai_signals = ["ai", "artificial intelligence", "chatgpt", "automation", "replace",
                   "machine learning", "robot"]
    ai_hits = [s for s in ai_signals if s in content_lower]
    if ai_hits:
        sensitivity_flags.append("AI/automation anxiety")
        additional_triggers["economic:anti_consumerist"] = {
            "negative": ["ai-powered", "automated", "machine learning"],
            "positive": [],
            "sensitivity": ["job displacement", "ai ethics"],
        }

    # Corporate cringe detection
    cringe_signals = ["slay", "bestie", "no cap", "frfr", "bussin", "vibe check",
                       "main character", "understood the assignment"]
    cringe_hits = [s for s in cringe_signals if s in content_lower]
    if cringe_hits:
        additional_triggers["humor:meme_native"] = {
            "negative": cringe_hits,
            "positive": [],
            "sensitivity": ["corporate appropriation of slang"],
        }
        additional_triggers["generational:gen_z_native"] = {
            "negative": cringe_hits,
            "positive": [],
            "sensitivity": ["brands co-opting gen z culture"],
        }

    # Health/wellness detection
    wellness_signals = ["clean", "natural", "toxin", "wellness", "heal", "detox",
                         "organic", "holistic"]
    wellness_hits = [s for s in wellness_signals if s in content_lower]
    if wellness_hits:
        sensitivity_flags.append("wellness claims")
        additional_triggers["media_diet:academic"] = {
            "negative": ["toxin-free", "detox", "clean eating", "holistic"],
            "positive": ["peer-reviewed", "clinically tested"],
            "sensitivity": ["pseudoscience", "health misinformation"],
        }

    # Detect overall cultural moment based on content
    cultural_moment = ""
    if culture_war_hits:
        cultural_moment = (
            "This content touches active culture war topics. Expect deep polarization "
            "between progressive supporters and conservative critics. Both sides will "
            "engage heavily but for opposite reasons."
        )
    elif cringe_hits:
        cultural_moment = (
            "This content uses slang/meme language that younger audiences will scrutinize "
            "for authenticity. If execution feels forced, expect cringe dunking."
        )
    elif ai_hits:
        cultural_moment = (
            "AI is a culturally charged topic. Tech-positive audiences will engage; "
            "others may be anxious or hostile about automation/replacement narratives."
        )

    # Common dead memes (as of knowledge cutoff)
    dead_memes = [
        "harambe", "dat boi", "cash me outside", "covfefe", "tide pod",
        "ice bucket challenge", "planking", "harlem shake",
    ]

    # Dated slang that brands still use
    dated_slang = [
        "on fleek", "YOLO", "bae", "adulting", "I can't even",
        "it me", "big mood (overused)", "this is everything",
    ]

    pulse = CulturalPulse(
        generated_at=datetime.now().isoformat(),
        current_date=today,
        content_cultural_moment=cultural_moment,
        content_sensitivity_flags=sensitivity_flags,
        additional_triggers=additional_triggers,
        dead_memes=dead_memes,
        dated_slang=dated_slang,
        overall_mood="polarized" if culture_war_hits else "anxious" if ai_hits else "neutral",
    )
    return pulse


# ──────────────────────────────────────────────────────────────────────
# Dynamic Trigger Augmentation
# ──────────────────────────────────────────────────────────────────────

def augment_persona_triggers(
    persona: dict,
    pulse: CulturalPulse,
) -> dict:
    """Expand a persona's trigger lists with cultural-pulse-derived triggers.

    This is called per-persona during simulation init. It merges the static
    hardcoded triggers with dynamic ones from the cultural pulse, so agents
    react to culturally relevant topics even if those topics weren't in the
    original worldview definitions.

    Modifies the persona dict in place and returns it.
    """
    worldview_ids = persona.get("worldview_ids", {})
    existing_positive = list(persona.get("positive_triggers", []))
    existing_negative = list(persona.get("negative_triggers", []))
    existing_sensitivity = list(persona.get("sensitivity_topics", []))

    # Merge triggers from cultural pulse
    for dimension, modifier_id in worldview_ids.items():
        key = f"{dimension}:{modifier_id}"
        if key in pulse.additional_triggers:
            aug = pulse.additional_triggers[key]
            for trigger in aug.get("positive", []):
                if trigger not in existing_positive:
                    existing_positive.append(trigger)
            for trigger in aug.get("negative", []):
                if trigger not in existing_negative:
                    existing_negative.append(trigger)
            for trigger in aug.get("sensitivity", []):
                if trigger not in existing_sensitivity:
                    existing_sensitivity.append(trigger)

    # Also merge triggers from trending topics that affect this persona's worldviews
    persona_worldview_keys = {f"{d}:{m}" for d, m in worldview_ids.items()}
    for topic in pulse.trending_topics:
        affected = set(topic.affected_worldviews)
        if affected & persona_worldview_keys:
            for trigger in topic.trigger_words:
                if trigger not in existing_negative and trigger not in existing_positive:
                    # Trending topic triggers go into sensitivity (they're contextual)
                    if trigger not in existing_sensitivity:
                        existing_sensitivity.append(trigger)

    persona["positive_triggers"] = existing_positive
    persona["negative_triggers"] = existing_negative
    persona["sensitivity_topics"] = existing_sensitivity

    return persona
