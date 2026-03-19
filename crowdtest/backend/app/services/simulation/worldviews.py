"""Worldview dimensions: political, religious, cultural, and values-based modifiers.

These layer ON TOP of psychographic archetypes. A "Skeptic" who is politically
progressive reacts very differently than a "Skeptic" who is libertarian.

Each dimension has:
- modifier_id: unique key
- label: human-readable name
- description: what this worldview means for behavior
- trust_modifiers: how it shifts trust in different message types
- trigger_words: phrases that activate strong positive or negative reactions
- sensitivity_flags: topics where this worldview creates strong opinions
"""

from dataclasses import dataclass, field


@dataclass
class WorldviewModifier:
    id: str
    dimension: str  # which dimension this belongs to
    label: str
    description: str
    trust_modifiers: dict[str, float] = field(default_factory=dict)
    positive_triggers: list[str] = field(default_factory=list)
    negative_triggers: list[str] = field(default_factory=list)
    sensitivity_topics: list[str] = field(default_factory=list)


# =============================================================================
# DIMENSION 1: Political Orientation
# Affects: trust in institutions, reaction to authority/corporate messaging,
#          sensitivity to social issues in marketing
# =============================================================================

POLITICAL: dict[str, WorldviewModifier] = {
    "progressive": WorldviewModifier(
        id="progressive",
        dimension="political",
        label="Progressive",
        description="Values social justice, equity, environmental action. Skeptical of corporate motives unless backed by action.",
        trust_modifiers={
            "corporate_authority": -0.2,
            "social_proof": 0.1,
            "sustainability_claims": 0.3,
            "diversity_messaging": 0.2,
            "luxury_positioning": -0.1,
        },
        positive_triggers=["sustainable", "ethical", "inclusive", "community-driven", "open-source", "fair trade", "carbon neutral"],
        negative_triggers=["disrupt", "hustle culture", "grind", "dominate the market", "crush the competition", "alpha"],
        sensitivity_topics=["environment", "labor practices", "diversity", "data privacy", "wealth inequality"],
    ),
    "moderate_left": WorldviewModifier(
        id="moderate_left",
        dimension="political",
        label="Moderate Left",
        description="Pragmatic progressive. Supports reform but values stability. Open to corporate solutions if well-intentioned.",
        trust_modifiers={
            "corporate_authority": 0.0,
            "social_proof": 0.1,
            "sustainability_claims": 0.15,
            "diversity_messaging": 0.1,
            "expert_endorsement": 0.1,
        },
        positive_triggers=["evidence-based", "responsible", "balanced", "transparent", "accessible"],
        negative_triggers=["move fast and break things", "unregulated", "freedom from oversight"],
        sensitivity_topics=["healthcare", "education", "environment", "worker rights"],
    ),
    "centrist": WorldviewModifier(
        id="centrist",
        dimension="political",
        label="Centrist",
        description="Pragmatic, evaluates on merits. Turned off by strong ideological signals in either direction.",
        trust_modifiers={
            "corporate_authority": 0.05,
            "social_proof": 0.1,
            "data_driven_claims": 0.15,
            "expert_endorsement": 0.1,
            "ideological_messaging": -0.2,
        },
        positive_triggers=["practical", "proven", "balanced approach", "common sense", "results-driven"],
        negative_triggers=["radical", "revolution", "fight the system", "traditional values", "woke"],
        sensitivity_topics=["polarization", "extremism"],
    ),
    "moderate_right": WorldviewModifier(
        id="moderate_right",
        dimension="political",
        label="Moderate Right",
        description="Values free enterprise, personal responsibility, incremental change. Respects tradition but open to innovation.",
        trust_modifiers={
            "corporate_authority": 0.1,
            "entrepreneurial_messaging": 0.2,
            "government_endorsement": -0.1,
            "tradition_appeals": 0.1,
            "self_reliance_messaging": 0.15,
        },
        positive_triggers=["self-made", "earned", "proven track record", "family", "reliable", "American-made"],
        negative_triggers=["privilege", "systemic", "equity mandate", "collective action"],
        sensitivity_topics=["regulation", "taxation", "government overreach"],
    ),
    "conservative": WorldviewModifier(
        id="conservative",
        dimension="political",
        label="Conservative",
        description="Values tradition, authority, stability. Skeptical of progressive framing in marketing. Loyal to trusted brands.",
        trust_modifiers={
            "corporate_authority": 0.1,
            "tradition_appeals": 0.25,
            "authority_endorsement": 0.15,
            "sustainability_claims": -0.1,
            "diversity_messaging": -0.15,
            "patriotic_messaging": 0.2,
        },
        positive_triggers=["trusted", "time-tested", "family values", "patriotic", "secure", "faith-based", "heritage"],
        negative_triggers=["disrupt", "reimagine", "deconstruct", "non-binary", "privilege", "colonialism", "pride", "trans", "woke", "girlhood"],
        sensitivity_topics=["cultural change", "religious freedom", "national identity", "gun rights", "immigration", "gender identity"],
    ),
    "libertarian": WorldviewModifier(
        id="libertarian",
        dimension="political",
        label="Libertarian",
        description="Anti-authority, pro-individual freedom. Hates paternalism in any form. Skeptical of both government and corporate regulation.",
        trust_modifiers={
            "corporate_authority": -0.15,
            "government_endorsement": -0.3,
            "decentralization_claims": 0.3,
            "self_reliance_messaging": 0.25,
            "privacy_focused": 0.2,
        },
        positive_triggers=["decentralized", "permissionless", "sovereign", "opt-in", "no middleman", "privacy-first", "open-source"],
        negative_triggers=["regulated", "compliant", "government-approved", "mandatory", "surveillance", "terms of service"],
        sensitivity_topics=["privacy", "censorship", "regulation", "taxation", "surveillance"],
    ),
    "apolitical": WorldviewModifier(
        id="apolitical",
        dimension="political",
        label="Apolitical",
        description="Disengaged from politics. Turned off by any political signaling in marketing. Just wants the product to work.",
        trust_modifiers={
            "ideological_messaging": -0.3,
            "product_focused": 0.2,
            "social_proof": 0.1,
        },
        positive_triggers=["simple", "just works", "no drama", "straightforward"],
        negative_triggers=["stand with", "fight for", "our values", "take a stand", "movement"],
        sensitivity_topics=[],  # actively avoids all of them
    ),
}

# =============================================================================
# DIMENSION 2: Religious / Spiritual Orientation
# Affects: reaction to values-based messaging, trust in certain institutions,
#          sensitivity to moral framing
# =============================================================================

RELIGIOUS: dict[str, WorldviewModifier] = {
    "secular": WorldviewModifier(
        id="secular",
        dimension="religious",
        label="Secular",
        description="No religious affiliation. Evaluates based on logic and evidence. May be put off by religious undertones.",
        trust_modifiers={
            "scientific_claims": 0.2,
            "data_driven_claims": 0.15,
            "faith_based_messaging": -0.2,
            "moral_authority": -0.1,
        },
        positive_triggers=["evidence-based", "scientific", "rational", "data-driven", "peer-reviewed"],
        negative_triggers=["blessed", "faith", "prayer", "God's plan", "spiritual journey", "divine"],
        sensitivity_topics=["religious exemptions", "faith-based policy"],
    ),
    "spiritual_not_religious": WorldviewModifier(
        id="spiritual_not_religious",
        dimension="religious",
        label="Spiritual, Not Religious",
        description="Personal spirituality without institutional religion. Open to mindfulness, wellness, holistic messaging.",
        trust_modifiers={
            "wellness_messaging": 0.25,
            "holistic_claims": 0.2,
            "institutional_religion": -0.1,
            "mindfulness_framing": 0.2,
        },
        positive_triggers=["mindful", "holistic", "intentional", "energy", "alignment", "manifest", "universe", "journey"],
        negative_triggers=["dogma", "scripture", "sin", "orthodox", "commandment"],
        sensitivity_topics=["institutional religion", "materialism vs. meaning"],
    ),
    "mainstream_religious": WorldviewModifier(
        id="mainstream_religious",
        dimension="religious",
        label="Mainstream Religious",
        description="Identifies with a major religion but moderate in practice. Values community, family, moral grounding.",
        trust_modifiers={
            "community_messaging": 0.15,
            "family_values": 0.15,
            "moral_framing": 0.1,
            "hedonistic_messaging": -0.1,
        },
        positive_triggers=["community", "family", "values", "purpose", "service", "grateful", "blessing"],
        negative_triggers=["hedonistic", "sinful pleasure", "godless", "anti-religious"],
        sensitivity_topics=["religious mockery", "moral relativism"],
    ),
    "devout": WorldviewModifier(
        id="devout",
        dimension="religious",
        label="Devout",
        description="Deeply religious, faith central to identity. Strong moral framework. Evaluates products through values lens.",
        trust_modifiers={
            "faith_based_messaging": 0.3,
            "moral_framing": 0.25,
            "family_values": 0.2,
            "secular_progressive_messaging": -0.2,
            "hedonistic_messaging": -0.3,
        },
        positive_triggers=["faith", "family", "purpose-driven", "God", "blessing", "service", "stewardship", "moral"],
        negative_triggers=["pride month", "pride", "your truth", "pleasure-first", "no rules", "liberation from tradition"],
        sensitivity_topics=["sexuality in marketing", "religious freedom", "traditional family", "modesty"],
    ),
}

# =============================================================================
# DIMENSION 3: Cultural Orientation
# Affects: response to individualism vs. collectivism in messaging,
#          attitude toward tradition vs. disruption
# =============================================================================

CULTURAL: dict[str, WorldviewModifier] = {
    "individualist": WorldviewModifier(
        id="individualist",
        dimension="cultural",
        label="Individualist",
        description="Self-expression, personal achievement, standing out. Responds to 'be unique' messaging.",
        trust_modifiers={
            "personal_achievement": 0.25,
            "uniqueness_claims": 0.2,
            "conformity_messaging": -0.15,
            "self_expression": 0.2,
        },
        positive_triggers=["stand out", "be yourself", "unique", "personal", "customize", "your way", "independent"],
        negative_triggers=["everyone's doing it", "join the crowd", "collective", "conform", "standardized"],
        sensitivity_topics=["conformity pressure", "groupthink"],
    ),
    "collectivist": WorldviewModifier(
        id="collectivist",
        dimension="cultural",
        label="Collectivist",
        description="Community-oriented, values harmony and group benefit. Responds to social proof and shared success.",
        trust_modifiers={
            "social_proof": 0.25,
            "community_messaging": 0.2,
            "family_values": 0.15,
            "rugged_individualism": -0.15,
        },
        positive_triggers=["together", "community", "shared", "our team", "family", "we", "belonging", "harmony"],
        negative_triggers=["lone wolf", "against the grain", "disrupt", "only you", "leave them behind"],
        sensitivity_topics=["social isolation", "community breakdown"],
    ),
    "traditionalist": WorldviewModifier(
        id="traditionalist",
        dimension="cultural",
        label="Traditionalist",
        description="Values heritage, proven methods, cultural continuity. Skeptical of rapid change.",
        trust_modifiers={
            "heritage_claims": 0.25,
            "tradition_appeals": 0.2,
            "disruption_messaging": -0.2,
            "authority_endorsement": 0.15,
        },
        positive_triggers=["heritage", "time-tested", "tradition", "legacy", "craftsmanship", "authentic", "classic"],
        negative_triggers=["disrupt", "reinvent", "old way is dead", "move on", "outdated", "legacy system"],
        sensitivity_topics=["cultural erosion", "rapid change", "loss of identity"],
    ),
    "cosmopolitan": WorldviewModifier(
        id="cosmopolitan",
        dimension="cultural",
        label="Cosmopolitan",
        description="Global perspective, embraces diversity and cross-cultural exchange. Values sophistication and openness.",
        trust_modifiers={
            "global_messaging": 0.2,
            "diversity_messaging": 0.15,
            "sophistication_claims": 0.15,
            "parochial_messaging": -0.15,
        },
        positive_triggers=["global", "diverse", "worldly", "cross-cultural", "international", "sophisticated", "inclusive"],
        negative_triggers=["local only", "our people", "outsiders", "foreign", "keep it simple"],
        sensitivity_topics=["xenophobia", "cultural isolationism"],
    ),
    "multicultural": WorldviewModifier(
        id="multicultural",
        dimension="cultural",
        label="Multicultural",
        description="Navigates multiple cultural identities. Notices representation (or lack of it). Values authenticity over tokenism.",
        trust_modifiers={
            "authentic_representation": 0.25,
            "tokenism": -0.3,
            "diversity_messaging": 0.1,  # cautious — wants authenticity not performance
            "cultural_specificity": 0.2,
        },
        positive_triggers=["representation", "authentic", "our story", "cultural", "diaspora", "multilingual", "heritage"],
        negative_triggers=["colorblind", "we don't see race", "exotic", "urban", "ethnic"],
        sensitivity_topics=["tokenism", "cultural appropriation", "representation"],
    ),
}

# =============================================================================
# DIMENSION 4: Economic Worldview
# Affects: reaction to pricing, value props, brand positioning
# =============================================================================

ECONOMIC: dict[str, WorldviewModifier] = {
    "free_market": WorldviewModifier(
        id="free_market",
        dimension="economic",
        label="Free Market",
        description="Believes competition drives quality. Respects successful businesses. Price = value signal.",
        trust_modifiers={
            "premium_positioning": 0.15,
            "entrepreneurial_messaging": 0.2,
            "competition_framing": 0.15,
            "anti_corporate_messaging": -0.2,
        },
        positive_triggers=["competitive edge", "market leader", "premium", "investment", "ROI", "scale", "growth"],
        negative_triggers=["anti-capitalist", "exploitation", "eat the rich", "degrowth", "profit is theft"],
        sensitivity_topics=["regulation", "wealth redistribution"],
    ),
    "conscious_capitalism": WorldviewModifier(
        id="conscious_capitalism",
        dimension="economic",
        label="Conscious Capitalist",
        description="Business should do well AND do good. Values B-corps, ethical supply chains, stakeholder capitalism.",
        trust_modifiers={
            "social_impact_claims": 0.25,
            "ethical_sourcing": 0.2,
            "b_corp_certification": 0.2,
            "pure_profit_messaging": -0.1,
        },
        positive_triggers=["B-corp", "1% for the planet", "ethical", "stakeholder", "triple bottom line", "purpose-driven"],
        negative_triggers=["shareholder value", "maximize returns", "cost-cutting", "offshore"],
        sensitivity_topics=["greenwashing", "corporate social responsibility authenticity"],
    ),
    "anti_consumerist": WorldviewModifier(
        id="anti_consumerist",
        dimension="economic",
        label="Anti-Consumerist",
        description="Skeptical of marketing itself. Values minimalism, sustainability, anti-waste. Hard to sell to but influential.",
        trust_modifiers={
            "sustainability_claims": 0.15,
            "minimalism_messaging": 0.2,
            "conspicuous_consumption": -0.3,
            "marketing_hype": -0.3,
            "longevity_claims": 0.2,
        },
        positive_triggers=["buy less", "built to last", "repair", "minimal", "no waste", "buy once", "open source"],
        negative_triggers=["upgrade now", "limited edition", "exclusive", "luxury", "new collection", "flash sale", "FOMO"],
        sensitivity_topics=["planned obsolescence", "fast fashion", "overconsumption"],
    ),
    "aspiring_affluent": WorldviewModifier(
        id="aspiring_affluent",
        dimension="economic",
        label="Aspiring Affluent",
        description="Upwardly mobile, motivated by status symbols and lifestyle upgrades. Responsive to aspiration marketing.",
        trust_modifiers={
            "luxury_positioning": 0.25,
            "status_signaling": 0.2,
            "success_stories": 0.2,
            "budget_messaging": -0.1,
        },
        positive_triggers=["exclusive", "premium", "luxury", "elite", "upgrade", "level up", "first class", "VIP"],
        negative_triggers=["budget", "cheap", "basic", "good enough", "frugal", "discount"],
        sensitivity_topics=["income inequality framing", "privilege discourse"],
    ),
}

# =============================================================================
# DIMENSION 5: Media Diet / Information Ecosystem
# Affects: what sources they trust, how they verify claims, susceptibility
#          to different persuasion techniques
# =============================================================================

MEDIA_DIET: dict[str, WorldviewModifier] = {
    "mainstream": WorldviewModifier(
        id="mainstream",
        dimension="media_diet",
        label="Mainstream Media Consumer",
        description="Gets news from major outlets. Trusts established institutions and expert consensus.",
        trust_modifiers={
            "expert_endorsement": 0.2,
            "press_coverage": 0.2,
            "institutional_backing": 0.15,
            "grassroots_claims": -0.05,
        },
        positive_triggers=["as seen in", "award-winning", "recommended by experts", "FDA approved", "peer-reviewed"],
        negative_triggers=["the media won't tell you", "banned", "censored", "what they don't want you to know"],
        sensitivity_topics=["misinformation", "conspiracy theories"],
    ),
    "alternative_media": WorldviewModifier(
        id="alternative_media",
        dimension="media_diet",
        label="Alternative Media Consumer",
        description="Skeptical of mainstream narratives. Gets info from independent creators, podcasts, substacks.",
        trust_modifiers={
            "institutional_backing": -0.2,
            "press_coverage": -0.1,
            "independent_creator_endorsement": 0.25,
            "grassroots_claims": 0.2,
            "anti_establishment_framing": 0.15,
        },
        positive_triggers=["independent", "uncensored", "truth", "real talk", "no sponsors", "grassroots"],
        negative_triggers=["mainstream", "establishment", "approved", "official", "institutional"],
        sensitivity_topics=["media censorship", "narrative control", "big tech"],
    ),
    "academic": WorldviewModifier(
        id="academic",
        dimension="media_diet",
        label="Academic / Research-Oriented",
        description="Wants primary sources, citations, methodology. Extremely skeptical of unsourced claims.",
        trust_modifiers={
            "scientific_claims": 0.25,
            "data_driven_claims": 0.25,
            "anecdotal_evidence": -0.2,
            "hype_language": -0.25,
        },
        positive_triggers=["peer-reviewed", "study shows", "meta-analysis", "n=", "statistically significant", "methodology"],
        negative_triggers=["game-changer", "revolutionary", "miracle", "secret", "hack", "10x"],
        sensitivity_topics=["p-hacking", "misleading statistics", "cherry-picked data"],
    ),
    "social_native": WorldviewModifier(
        id="social_native",
        dimension="media_diet",
        label="Social Media Native",
        description="Lives on social platforms. Trusts creators and peers over institutions. Meme-literate. Short attention span.",
        trust_modifiers={
            "influencer_endorsement": 0.25,
            "social_proof": 0.2,
            "viral_content": 0.15,
            "long_form_content": -0.15,
            "institutional_backing": -0.05,
        },
        positive_triggers=["viral", "trending", "creator", "collab", "drop", "link in bio", "no cap"],
        negative_triggers=["whitepaper", "comprehensive report", "detailed analysis", "terms and conditions"],
        sensitivity_topics=["authenticity vs. sponsorship", "sellout culture"],
    ),
    "news_avoidant": WorldviewModifier(
        id="news_avoidant",
        dimension="media_diet",
        label="News Avoidant",
        description="Actively avoids news and current events. Gets info through personal networks and word of mouth.",
        trust_modifiers={
            "personal_recommendation": 0.25,
            "word_of_mouth": 0.2,
            "news_references": -0.15,
            "urgency_messaging": -0.2,
        },
        positive_triggers=["friend recommended", "my neighbor uses", "simple", "no drama", "peaceful"],
        negative_triggers=["breaking", "urgent", "crisis", "you need to know", "the world is changing"],
        sensitivity_topics=[],  # avoids all sensitivity
    ),
}

# =============================================================================
# DIMENSION 6: Trust Orientation
# Affects: who they believe, what evidence they need, how they make decisions
# =============================================================================

TRUST: dict[str, WorldviewModifier] = {
    "institution_trusting": WorldviewModifier(
        id="institution_trusting",
        dimension="trust",
        label="Institution-Trusting",
        description="Trusts established brands, certifications, credentials. 'If it's big, it must be good.'",
        trust_modifiers={
            "brand_recognition": 0.25,
            "certifications": 0.2,
            "expert_endorsement": 0.2,
            "startup_claims": -0.1,
        },
        positive_triggers=["Fortune 500", "certified", "accredited", "established", "trusted by thousands"],
        negative_triggers=["underground", "indie", "bootstrap", "no credentials needed", "unproven"],
        sensitivity_topics=["institutional failure", "corporate scandals"],
    ),
    "peer_trusting": WorldviewModifier(
        id="peer_trusting",
        dimension="trust",
        label="Peer-Trusting",
        description="Trusts friends, communities, reviews. Social proof is the primary decision driver.",
        trust_modifiers={
            "social_proof": 0.3,
            "user_reviews": 0.25,
            "community_endorsement": 0.2,
            "corporate_messaging": -0.1,
        },
        positive_triggers=["rated 5 stars", "community favorite", "recommended by friends", "user reviews", "real people"],
        negative_triggers=["take our word for it", "trust us", "proprietary", "no reviews yet"],
        sensitivity_topics=["fake reviews", "astroturfing"],
    ),
    "self_reliant": WorldviewModifier(
        id="self_reliant",
        dimension="trust",
        label="Self-Reliant",
        description="Does own research. Doesn't trust anyone's word — needs to verify independently.",
        trust_modifiers={
            "transparency": 0.25,
            "open_source": 0.2,
            "try_before_buy": 0.2,
            "marketing_claims": -0.2,
            "authority_claims": -0.15,
        },
        positive_triggers=["open source", "free trial", "see for yourself", "transparent", "no lock-in", "DIY"],
        negative_triggers=["just trust us", "experts agree", "everyone knows", "don't question", "proprietary"],
        sensitivity_topics=["lock-in", "hidden terms", "lack of transparency"],
    ),
    "authority_skeptical": WorldviewModifier(
        id="authority_skeptical",
        dimension="trust",
        label="Authority-Skeptical",
        description="Actively distrusts authority figures, corporations, and governments. Contrarian by nature.",
        trust_modifiers={
            "corporate_authority": -0.3,
            "government_endorsement": -0.3,
            "grassroots_claims": 0.2,
            "underdog_narrative": 0.25,
            "anti_establishment_framing": 0.2,
        },
        positive_triggers=["underdog", "fighting the system", "independent", "people-powered", "no corporate backing"],
        negative_triggers=["industry leader", "government approved", "backed by", "partnered with", "endorsed by"],
        sensitivity_topics=["corporate influence", "regulatory capture", "surveillance capitalism"],
    ),
}

# =============================================================================
# DIMENSION 7: Generational Identity (beyond just age — the cultural imprint)
# =============================================================================

GENERATIONAL: dict[str, WorldviewModifier] = {
    "gen_z_native": WorldviewModifier(
        id="gen_z_native",
        dimension="generational",
        label="Gen Z (Digital Native)",
        description="Born into social media. Values authenticity, mental health, social justice. Detects corporate cringe instantly.",
        trust_modifiers={
            "authenticity": 0.25,
            "mental_health_awareness": 0.2,
            "corporate_cringe": -0.3,
            "influencer_endorsement": 0.15,
        },
        positive_triggers=["real talk", "no filter", "mental health", "safe space", "vibe", "slay", "understood"],
        negative_triggers=["fellow kids", "millennial humor", "adulting", "synergy", "leverage", "circle back"],
        sensitivity_topics=["performative activism", "climate anxiety", "mental health stigma"],
    ),
    "millennial_pragmatist": WorldviewModifier(
        id="millennial_pragmatist",
        dimension="generational",
        label="Millennial (Pragmatic Idealist)",
        description="Idealistic but burned. Values experiences over things. Wants ethical but also needs it to work.",
        trust_modifiers={
            "experience_over_things": 0.2,
            "ethical_claims": 0.15,
            "subscription_fatigue": -0.15,
            "nostalgia": 0.1,
        },
        positive_triggers=["experience", "authentic", "curated", "sustainable", "side hustle", "work-life balance"],
        negative_triggers=["another subscription", "hustle harder", "pull yourself up", "stop buying avocado toast"],
        sensitivity_topics=["housing crisis", "student debt", "subscription fatigue"],
    ),
    "gen_x_independent": WorldviewModifier(
        id="gen_x_independent",
        dimension="generational",
        label="Gen X (Independent Skeptic)",
        description="Self-reliant, skeptical of hype, values quality and durability. The forgotten generation — and fine with it.",
        trust_modifiers={
            "no_hype": 0.2,
            "durability_claims": 0.2,
            "trend_chasing": -0.2,
            "straight_talk": 0.15,
        },
        positive_triggers=["built to last", "no BS", "straightforward", "reliable", "quality", "just works"],
        negative_triggers=["trending", "viral", "FOMO", "limited time", "join the movement", "disruptive"],
        sensitivity_topics=["being marketed to", "ageism", "trend obsession"],
    ),
    "boomer_established": WorldviewModifier(
        id="boomer_established",
        dimension="generational",
        label="Boomer (Established)",
        description="Values reputation, stability, customer service. Brand loyal. Prefers phone/email over chat.",
        trust_modifiers={
            "brand_reputation": 0.25,
            "customer_service": 0.2,
            "stability_messaging": 0.15,
            "trendy_language": -0.2,
        },
        positive_triggers=["trusted since", "award-winning service", "call us anytime", "reputation", "guaranteed"],
        negative_triggers=["ok boomer", "legacy", "outdated", "your parents'", "old school"],
        sensitivity_topics=["ageism", "digital exclusion", "dismissal of experience"],
    ),
}


# =============================================================================
# Registry: all dimensions in one place
# =============================================================================

# =============================================================================
# DIMENSION 8: Humor & Tone Literacy (how agents process social media humor)
# =============================================================================

HUMOR: dict[str, WorldviewModifier] = {
    "meme_native": WorldviewModifier(
        id="meme_native",
        dimension="humor",
        label="Meme Native",
        description="Fluent in internet humor. Recognizes meme formats instantly. Judges brands by meme quality. Will roast cringe attempts. Communicates primarily through references and irony.",
        trust_modifiers={
            "meme_marketing": 0.3,
            "self_aware_humor": 0.25,
            "corporate_cringe": -0.35,
            "deadpan_delivery": 0.2,
            "try_hard_humor": -0.3,
        },
        positive_triggers=["self-aware", "shitpost", "based", "unhinged brand account", "ratio", "W take"],
        negative_triggers=["fellow kids", "we're all about the vibes", "it's giving", "slay queen", "yasss"],
        sensitivity_topics=["forced relatability", "brands using tragedy for engagement", "performative humor"],
    ),
    "dry_wit": WorldviewModifier(
        id="dry_wit",
        dimension="humor",
        label="Dry Wit / Deadpan",
        description="Appreciates understated, clever humor. Sarcasm is their first language. Eye-rolls at obvious jokes. Values wit over spectacle.",
        trust_modifiers={
            "subtle_humor": 0.25,
            "intellectual_wit": 0.2,
            "slapstick": -0.15,
            "pun_heavy": -0.1,
            "clever_wordplay": 0.2,
        },
        positive_triggers=["actually clever", "understatement", "dry", "subtle", "deadpan"],
        negative_triggers=["LMAO SO RANDOM", "wait for it...", "😂😂😂", "I can't even", "who did this"],
        sensitivity_topics=["lowest common denominator humor", "explaining the joke"],
    ),
    "wholesome_humor": WorldviewModifier(
        id="wholesome_humor",
        dimension="humor",
        label="Wholesome / Feel-Good",
        description="Enjoys positive, uplifting humor. Shares heartwarming content. Avoids edgy or mean-spirited comedy. The 'this made my day' crowd.",
        trust_modifiers={
            "heartwarming_content": 0.3,
            "uplifting_humor": 0.25,
            "edgy_comedy": -0.25,
            "mean_spirited": -0.35,
            "cute_factor": 0.2,
        },
        positive_triggers=["wholesome", "faith in humanity", "made my day", "crying happy tears", "protect this"],
        negative_triggers=["dark humor", "savage", "destroyed", "brutal", "roasted"],
        sensitivity_topics=["bullying disguised as humor", "punching down", "shock value"],
    ),
    "edgy_humor": WorldviewModifier(
        id="edgy_humor",
        dimension="humor",
        label="Edgy / Dark Comedy",
        description="Pushes boundaries. Appreciates taboo-breaking, shock humor, and brands that aren't afraid to offend. The Wendy's Twitter energy.",
        trust_modifiers={
            "edgy_brand_voice": 0.3,
            "roast_culture": 0.25,
            "corporate_safe": -0.2,
            "pushing_boundaries": 0.2,
            "sanitized_humor": -0.15,
        },
        positive_triggers=["savage", "no chill", "unhinged", "chose violence", "shots fired", "brand beef"],
        negative_triggers=["family friendly", "appropriate", "tasteful", "respectful humor", "clean fun"],
        sensitivity_topics=["punching down vs punching up", "crossing the line into cruelty"],
    ),
    "no_humor": WorldviewModifier(
        id="no_humor",
        dimension="humor",
        label="Humor-Resistant / Serious",
        description="Doesn't engage with humor in professional/brand context. Finds brand humor unprofessional. Wants substance, not laughs.",
        trust_modifiers={
            "professional_tone": 0.25,
            "data_driven": 0.2,
            "humor_in_marketing": -0.2,
            "meme_marketing": -0.25,
            "serious_messaging": 0.2,
        },
        positive_triggers=["professional", "data shows", "research-backed", "industry-leading"],
        negative_triggers=["lol", "relatable content", "we don't take ourselves seriously", "fun brand"],
        sensitivity_topics=["trivialization of serious topics", "humor masking lack of substance"],
    ),
    "sarcasm_default": WorldviewModifier(
        id="sarcasm_default",
        dimension="humor",
        label="Sarcasm as Default Mode",
        description="Everything is met with sarcasm first. Quote-tweets with eye rolls. Will dunk on brands that set themselves up. The 'oh wow another AI tool' energy.",
        trust_modifiers={
            "self_deprecating_brand": 0.2,
            "earnest_marketing": -0.15,
            "overconfident_claims": -0.25,
            "acknowledging_competition": 0.15,
            "corporate_speak": -0.3,
        },
        positive_triggers=["at least they're honest", "okay that's actually good", "I'll give them this one"],
        negative_triggers=["revolutionary", "game-changing", "disrupting", "reimagining", "the future of"],
        sensitivity_topics=["brands being earnest about mediocre products", "tech hype cycles"],
    ),
    "absurdist": WorldviewModifier(
        id="absurdist",
        dimension="humor",
        label="Absurdist / Surreal",
        description="Appreciates bizarre, nonsensical humor. The weirder the better. Loves brands that embrace chaos. Duolingo owl energy.",
        trust_modifiers={
            "weird_brand_voice": 0.3,
            "surreal_content": 0.25,
            "conventional_marketing": -0.2,
            "predictable_format": -0.15,
            "unhinged_social": 0.2,
        },
        positive_triggers=["chaotic", "unhinged", "cursed", "why does this exist", "fever dream", "absurd"],
        negative_triggers=["straightforward", "clear messaging", "professional", "on-brand"],
        sensitivity_topics=["brands trying to be random without commitment", "forced randomness"],
    ),
    "cultural_humor": WorldviewModifier(
        id="cultural_humor",
        dimension="humor",
        label="Cultural / Reference-Heavy",
        description="Humor rooted in specific cultural references — TV shows, music, historical events, niche communities. Gets in-jokes. Loves easter eggs.",
        trust_modifiers={
            "cultural_references": 0.25,
            "in_jokes": 0.2,
            "niche_humor": 0.2,
            "generic_humor": -0.15,
            "easter_eggs": 0.15,
        },
        positive_triggers=["IYKYK", "understood the assignment", "main character energy", "deep cut", "reference"],
        negative_triggers=["broad appeal", "everyone will love", "universal humor", "inoffensive"],
        sensitivity_topics=["misusing cultural references", "appropriating niche humor for mass appeal"],
    ),
}


ALL_DIMENSIONS: dict[str, dict[str, WorldviewModifier]] = {
    "political": POLITICAL,
    "religious": RELIGIOUS,
    "cultural": CULTURAL,
    "economic": ECONOMIC,
    "media_diet": MEDIA_DIET,
    "trust": TRUST,
    "generational": GENERATIONAL,
    "humor": HUMOR,
}

# Default distributions per industry pack (which worldviews are most common)
INDUSTRY_WORLDVIEW_DEFAULTS: dict[str, dict[str, dict[str, float]]] = {
    "saas_b2b": {
        "political": {"centrist": 0.3, "moderate_left": 0.2, "moderate_right": 0.2, "libertarian": 0.15, "apolitical": 0.15},
        "economic": {"free_market": 0.4, "conscious_capitalism": 0.3, "aspiring_affluent": 0.2, "anti_consumerist": 0.1},
        "media_diet": {"mainstream": 0.3, "academic": 0.25, "social_native": 0.2, "alternative_media": 0.15, "news_avoidant": 0.1},
        "trust": {"institution_trusting": 0.3, "peer_trusting": 0.3, "self_reliant": 0.25, "authority_skeptical": 0.15},
        "humor": {"dry_wit": 0.25, "sarcasm_default": 0.25, "no_humor": 0.2, "meme_native": 0.15, "cultural_humor": 0.15},
    },
    "ecommerce_dtc": {
        "political": {"moderate_left": 0.2, "progressive": 0.15, "centrist": 0.2, "apolitical": 0.15, "moderate_right": 0.15, "conservative": 0.1, "libertarian": 0.05},
        "economic": {"aspiring_affluent": 0.3, "conscious_capitalism": 0.25, "free_market": 0.25, "anti_consumerist": 0.2},
        "media_diet": {"social_native": 0.4, "mainstream": 0.25, "alternative_media": 0.2, "news_avoidant": 0.15},
        "trust": {"peer_trusting": 0.4, "self_reliant": 0.25, "institution_trusting": 0.2, "authority_skeptical": 0.15},
        "humor": {"meme_native": 0.3, "wholesome_humor": 0.25, "cultural_humor": 0.2, "sarcasm_default": 0.15, "absurdist": 0.1},
    },
    "consumer_app": {
        "political": {"apolitical": 0.3, "moderate_left": 0.2, "progressive": 0.2, "centrist": 0.2, "libertarian": 0.1},
        "economic": {"aspiring_affluent": 0.3, "free_market": 0.25, "conscious_capitalism": 0.25, "anti_consumerist": 0.2},
        "media_diet": {"social_native": 0.45, "mainstream": 0.2, "alternative_media": 0.2, "news_avoidant": 0.15},
        "trust": {"peer_trusting": 0.35, "self_reliant": 0.25, "institution_trusting": 0.2, "authority_skeptical": 0.2},
        "humor": {"meme_native": 0.3, "absurdist": 0.2, "edgy_humor": 0.15, "sarcasm_default": 0.15, "cultural_humor": 0.2},
    },
    "developer_tools": {
        "political": {"libertarian": 0.25, "apolitical": 0.2, "centrist": 0.2, "progressive": 0.15, "moderate_left": 0.1, "moderate_right": 0.1},
        "economic": {"free_market": 0.35, "conscious_capitalism": 0.2, "anti_consumerist": 0.25, "aspiring_affluent": 0.2},
        "media_diet": {"social_native": 0.3, "alternative_media": 0.25, "academic": 0.2, "news_avoidant": 0.15, "mainstream": 0.1},
        "trust": {"self_reliant": 0.35, "authority_skeptical": 0.25, "peer_trusting": 0.25, "institution_trusting": 0.15},
        "humor": {"sarcasm_default": 0.25, "dry_wit": 0.25, "meme_native": 0.2, "no_humor": 0.15, "absurdist": 0.15},
    },
    "fintech": {
        "political": {"centrist": 0.25, "moderate_right": 0.2, "libertarian": 0.2, "moderate_left": 0.15, "apolitical": 0.1, "conservative": 0.1},
        "economic": {"free_market": 0.35, "aspiring_affluent": 0.3, "conscious_capitalism": 0.2, "anti_consumerist": 0.15},
        "media_diet": {"mainstream": 0.3, "social_native": 0.25, "academic": 0.2, "alternative_media": 0.15, "news_avoidant": 0.1},
        "trust": {"institution_trusting": 0.3, "self_reliant": 0.25, "peer_trusting": 0.25, "authority_skeptical": 0.2},
        "humor": {"no_humor": 0.3, "dry_wit": 0.25, "sarcasm_default": 0.2, "meme_native": 0.15, "cultural_humor": 0.1},
    },
    "health_wellness": {
        "political": {"moderate_left": 0.25, "progressive": 0.2, "centrist": 0.2, "apolitical": 0.15, "moderate_right": 0.1, "conservative": 0.1},
        "economic": {"conscious_capitalism": 0.35, "aspiring_affluent": 0.25, "anti_consumerist": 0.2, "free_market": 0.2},
        "media_diet": {"social_native": 0.3, "alternative_media": 0.25, "mainstream": 0.2, "academic": 0.15, "news_avoidant": 0.1},
        "trust": {"peer_trusting": 0.3, "self_reliant": 0.3, "authority_skeptical": 0.2, "institution_trusting": 0.2},
        "humor": {"wholesome_humor": 0.3, "cultural_humor": 0.2, "no_humor": 0.2, "dry_wit": 0.15, "meme_native": 0.15},
    },
    "education": {
        "political": {"progressive": 0.25, "moderate_left": 0.25, "centrist": 0.2, "apolitical": 0.15, "moderate_right": 0.1, "libertarian": 0.05},
        "economic": {"conscious_capitalism": 0.3, "anti_consumerist": 0.25, "free_market": 0.25, "aspiring_affluent": 0.2},
        "media_diet": {"academic": 0.35, "mainstream": 0.25, "social_native": 0.2, "alternative_media": 0.1, "news_avoidant": 0.1},
        "trust": {"institution_trusting": 0.3, "peer_trusting": 0.3, "self_reliant": 0.2, "authority_skeptical": 0.2},
        "humor": {"dry_wit": 0.25, "wholesome_humor": 0.2, "sarcasm_default": 0.2, "cultural_humor": 0.2, "no_humor": 0.15},
    },
}
