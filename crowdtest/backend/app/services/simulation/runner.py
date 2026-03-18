"""Simulation runner: MiroFish-aligned dual-platform engine with persistent memory,
opinion drift, and social actions modeled after OASIS (23 social actions).

Key MiroFish rules of engagement:
1. Dual-platform simulation (Twitter-like + Reddit-like) running in parallel
2. Agents have persistent memory across rounds (recall earlier interactions)
3. Environment Configuration Agent sets the rules of the world
4. 23 social actions (not just read/react/comment/share)
5. Opinion drift: agents change minds based on exposure and influence
6. Emergent coalitions: agents cluster around shared positions
7. 30-50 rounds (not 7) for realistic social evolution
8. Social proof cascades and herd behavior dynamics
"""

import random
from dataclasses import dataclass, field
from enum import Enum

from app.core.config import settings


# ──────────────────────────────────────────────────────────────────────
# Social Actions — modeled after OASIS (23 actions for Twitter + Reddit)
# ──────────────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    """Full social action set, adapted from OASIS platform simulation."""
    # Passive
    IGNORE = "ignore"  # scrolled past
    READ = "read"  # read but no visible action

    # Reactions (low-effort engagement)
    LIKE = "like"
    DISLIKE = "dislike"
    EMOJI_REACT = "emoji_react"  # platform-specific reactions

    # Content engagement
    COMMENT = "comment"
    REPLY = "reply"  # reply to another agent's comment
    QUOTE = "quote"  # quote-repost with commentary

    # Amplification
    SHARE = "share"  # repost / retweet
    CROSSPOST = "crosspost"  # share to the other platform
    BOOKMARK = "bookmark"  # save for later (private signal)

    # Social graph actions
    FOLLOW = "follow"  # follow the poster or another commenter
    UNFOLLOW = "unfollow"  # unfollow after negative experience
    MUTE = "mute"  # mute without unfollowing
    BLOCK = "block"  # block (strong negative signal)

    # Discovery actions
    SEARCH = "search"  # searched for more info after seeing content
    CLICK_PROFILE = "click_profile"  # checked out the poster's profile
    CLICK_LINK = "click_link"  # clicked an external link in the content

    # Reddit-specific
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"
    AWARD = "award"  # reddit award / super-like

    # Meta actions
    REPORT = "report"  # flagged as spam/inappropriate
    DM = "dm"  # sent a direct message (dark social)
    SCREENSHOT = "screenshot"  # screenshotted to share elsewhere (dark social)


class Platform(str, Enum):
    """Dual-platform simulation environments."""
    TWITTER = "twitter"
    REDDIT = "reddit"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    HOSTILE = "hostile"


# ──────────────────────────────────────────────────────────────────────
# Agent Memory — persistent across rounds, MiroFish-style
# ──────────────────────────────────────────────────────────────────────

@dataclass
class AgentMemory:
    """Per-agent memory that persists across simulation rounds.

    MiroFish rule: agents recall earlier rounds and tweak their behavior accordingly.
    """
    persona_id: str
    # What they've seen and done
    seen_content: list[str] = field(default_factory=list)  # content hashes
    interactions: list[dict] = field(default_factory=list)  # {round, action, target, sentiment}
    # Opinion state (drifts over time)
    opinion_score: float = 0.0  # -1.0 (hostile) to 1.0 (champion) toward the material
    opinion_history: list[tuple[int, float]] = field(default_factory=list)  # (round, score)
    # Social state
    followed: list[str] = field(default_factory=list)  # persona IDs they follow
    muted: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    # Influence received
    influence_log: list[dict] = field(default_factory=list)  # {from, round, delta}

    def record_interaction(self, round_num: int, action: ActionType, target: str | None, sentiment: Sentiment):
        self.interactions.append({
            "round": round_num,
            "action": action.value,
            "target": target,
            "sentiment": sentiment.value,
        })

    def update_opinion(self, round_num: int, delta: float, source: str | None = None):
        """Shift opinion based on exposure. Clamped to [-1, 1]."""
        self.opinion_score = max(-1.0, min(1.0, self.opinion_score + delta))
        self.opinion_history.append((round_num, self.opinion_score))
        if source:
            self.influence_log.append({"from": source, "round": round_num, "delta": delta})

    @property
    def interaction_count(self) -> int:
        return len(self.interactions)

    @property
    def has_engaged(self) -> bool:
        return any(
            i["action"] not in (ActionType.IGNORE.value, ActionType.READ.value)
            for i in self.interactions
        )


# ──────────────────────────────────────────────────────────────────────
# Environment Configuration — MiroFish's "rules of the world"
# ──────────────────────────────────────────────────────────────────────

@dataclass
class EnvironmentConfig:
    """Environment Configuration Agent output.

    MiroFish rule: a meta-agent sets the simulation parameters and rules of engagement
    for the world these agents will inhabit.
    """
    # Simulation scale
    crowd_size: int = 100  # mock senate size
    max_rounds: int = 40  # MiroFish typical: 30-50 rounds
    seed_count: int = 15  # initial agents who see the content

    # Platform config
    platforms: list[Platform] = field(default_factory=lambda: [Platform.TWITTER, Platform.REDDIT])

    # Engagement dynamics
    base_scroll_past_rate: float = 0.80  # 80% scroll past on first exposure
    social_proof_ceiling: float = 2.0  # max social proof multiplier
    social_proof_growth: float = 0.5  # how fast social proof builds
    herd_behavior_weight: float = 0.3  # MiroFish finding: LLM agents susceptible to herd behavior

    # Opinion dynamics
    opinion_drift_rate: float = 0.05  # base drift per round from exposure
    influence_decay: float = 0.8  # influence weakens over graph distance
    echo_chamber_bonus: float = 0.15  # opinion reinforcement within clusters
    contrarian_resistance: float = 0.7  # how much contrarians resist herd drift

    # Virality thresholds
    viral_threshold: float = 0.25  # engagement ratio that triggers viral cascade
    cascade_probability: float = 0.6  # probability of cascade spreading per hop
    dark_social_rate: float = 0.15  # % of shares that happen in DMs/private

    # Content decay
    content_freshness_decay: float = 0.05  # content becomes less engaging per round
    controversy_boost: float = 1.3  # controversial content decays slower

    # Platform-specific modifiers
    twitter_virality_modifier: float = 1.3  # Twitter spreads faster
    reddit_depth_modifier: float = 1.5  # Reddit discussions go deeper
    twitter_character_limit: int = 280
    reddit_allows_long_form: bool = True


# ──────────────────────────────────────────────────────────────────────
# Turn Actions & State
# ──────────────────────────────────────────────────────────────────────

@dataclass
class TurnAction:
    persona_id: str
    round_num: int
    platform: Platform
    action: ActionType
    content: str | None = None  # comment/quote text
    target_persona: str | None = None  # who they're replying to / following
    sentiment: Sentiment = Sentiment.NEUTRAL
    internal_thought: str | None = None  # private reaction (not visible to others)
    opinion_delta: float = 0.0  # how this action shifted their opinion
    triggered_by: str | None = None  # persona_id that caused exposure


@dataclass
class PlatformState:
    """Per-platform simulation state (MiroFish runs Twitter + Reddit in parallel)."""
    platform: Platform
    posts: list[TurnAction] = field(default_factory=list)  # top-level posts
    comments: list[TurnAction] = field(default_factory=list)  # replies and comments
    trending_score: float = 0.0  # how much traction this has on this platform
    engagement_count: int = 0
    share_count: int = 0


@dataclass
class SimulationState:
    """Full simulation state across both platforms."""
    material_content: str
    material_metadata: dict = field(default_factory=dict)  # extracted entities, tone, etc.
    env_config: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    personas: list[dict] = field(default_factory=list)
    graph: object = None  # SocialGraph
    memories: dict[str, AgentMemory] = field(default_factory=dict)  # persona_id -> memory

    # Platform states
    platform_states: dict[Platform, PlatformState] = field(default_factory=dict)

    # Simulation progress
    current_round: int = 0
    exposed: set[str] = field(default_factory=set)
    engaged: set[str] = field(default_factory=set)
    all_actions: list[TurnAction] = field(default_factory=list)

    # Emergent dynamics tracking
    coalitions: list[set[str]] = field(default_factory=list)  # groups of aligned agents
    opinion_clusters: dict[str, float] = field(default_factory=dict)  # archetype -> avg opinion
    viral_cascades: list[dict] = field(default_factory=list)  # cascade events

    # Global metrics
    social_proof_modifier: float = 1.0
    content_freshness: float = 1.0  # decays each round
    controversy_score: float = 0.0  # rises with mixed sentiment


def initialize_simulation(
    material_content: str,
    personas: list[dict],
    graph: object,
    env_config: EnvironmentConfig | None = None,
) -> SimulationState:
    """Initialize simulation state with MiroFish-aligned defaults."""
    config = env_config or EnvironmentConfig()

    # Initialize per-agent memory
    memories = {}
    for p in personas:
        pid = p["id"]
        # Initial opinion based on archetype tendencies
        initial_opinion = _compute_initial_opinion(p)
        mem = AgentMemory(persona_id=pid, opinion_score=initial_opinion)
        mem.opinion_history.append((0, initial_opinion))
        memories[pid] = mem

    # Initialize platform states
    platform_states = {
        platform: PlatformState(platform=platform)
        for platform in config.platforms
    }

    return SimulationState(
        material_content=material_content,
        personas=personas,
        graph=graph,
        env_config=config,
        memories=memories,
        platform_states=platform_states,
    )


def _compute_initial_opinion(persona: dict) -> float:
    """Compute starting opinion from archetype and worldview triggers.

    Champions start positive, skeptics start negative, etc.
    """
    # Base from archetype behavioral tendencies
    engagement = persona.get("engagement_rate", 0.5)
    objection = persona.get("objection_tendency", 0.5) if "objection_tendency" in persona else 0.5
    # Higher engagement + lower objection = more positive initial lean
    base = (engagement - 0.5) * 0.4 - (objection - 0.5) * 0.4
    # Add noise for variety
    noise = random.gauss(0, 0.1)
    return max(-1.0, min(1.0, base + noise))


# ──────────────────────────────────────────────────────────────────────
# Engagement & Social Proof (MiroFish-aligned)
# ──────────────────────────────────────────────────────────────────────

def should_engage(persona: dict, memory: AgentMemory, state: SimulationState) -> bool:
    """MiroFish-aligned engagement filter.

    Considers: base rate, social proof, memory, opinion, content freshness,
    and the MiroFish finding that LLM agents are susceptible to herd behavior.
    """
    base_rate = persona["engagement_rate"]
    config = state.env_config

    # Social proof boost (herd behavior)
    herd_boost = state.social_proof_modifier * config.herd_behavior_weight
    adjusted = base_rate * (1.0 + herd_boost - config.herd_behavior_weight)

    # Content freshness decay (less interesting over time)
    adjusted *= state.content_freshness

    # Memory modifier: agents who already engaged are more likely to re-engage
    if memory.has_engaged:
        adjusted *= 1.2

    # Opinion modifier: strong opinions (positive OR negative) drive engagement
    opinion_intensity = abs(memory.opinion_score)
    adjusted *= (1.0 + opinion_intensity * 0.3)

    # Cap at 95%
    adjusted = min(adjusted, 0.95)

    return random.random() < adjusted


def compute_social_proof(state: SimulationState) -> float:
    """Social proof escalation with ceiling.

    MiroFish finding: LLM agents are MORE susceptible to herd behavior than humans.
    """
    if not state.exposed:
        return 1.0
    engagement_ratio = len(state.engaged) / max(len(state.exposed), 1)
    config = state.env_config
    proof = 1.0 + (engagement_ratio * config.social_proof_growth)
    return min(proof, config.social_proof_ceiling)


def compute_controversy(state: SimulationState) -> float:
    """Track controversy score from mixed sentiment.

    High controversy = more engagement (but polarized).
    """
    if not state.all_actions:
        return 0.0
    sentiments = [a.sentiment for a in state.all_actions if a.sentiment != Sentiment.NEUTRAL]
    if len(sentiments) < 3:
        return 0.0
    positive = sum(1 for s in sentiments if s == Sentiment.POSITIVE)
    negative = sum(1 for s in sentiments if s in (Sentiment.NEGATIVE, Sentiment.HOSTILE))
    total = len(sentiments)
    # Controversy is highest when split is 50/50
    if total == 0:
        return 0.0
    split = min(positive, negative) / max(positive, negative, 1)
    return split  # 0 = consensus, 1 = maximally controversial


# ──────────────────────────────────────────────────────────────────────
# Opinion Drift & Influence Propagation
# ──────────────────────────────────────────────────────────────────────

def propagate_influence(
    source_id: str,
    state: SimulationState,
    graph,
) -> list[str]:
    """Propagate opinion influence through the social graph.

    MiroFish rule: agents change their minds based on exposure to others' actions.
    Influence decays over graph distance.
    """
    from app.services.simulation.graph import get_neighbors

    config = state.env_config
    source_memory = state.memories[source_id]
    affected = []

    neighbors = get_neighbors(graph, source_id)
    for neighbor_id in neighbors:
        if neighbor_id in state.memories:
            neighbor_memory = state.memories[neighbor_id]

            # Skip if blocked/muted
            if source_id in neighbor_memory.blocked or source_id in neighbor_memory.muted:
                continue

            # Influence strength based on source's influence weight and opinion intensity
            personas_map = {p["id"]: p for p in state.personas}
            source_influence = personas_map.get(source_id, {}).get("influence_weight", 0.5)
            opinion_delta = source_memory.opinion_score * config.opinion_drift_rate * source_influence

            # Echo chamber: amplify if neighbor already agrees
            if (source_memory.opinion_score > 0 and neighbor_memory.opinion_score > 0) or \
               (source_memory.opinion_score < 0 and neighbor_memory.opinion_score < 0):
                opinion_delta *= (1.0 + config.echo_chamber_bonus)

            # Contrarian resistance
            neighbor_archetype = personas_map.get(neighbor_id, {}).get("primary_archetype", "")
            if neighbor_archetype in ("contrarian", "rebel", "skeptic", "cynic"):
                opinion_delta *= (1.0 - config.contrarian_resistance)

            neighbor_memory.update_opinion(
                state.current_round, opinion_delta, source=source_id,
            )
            affected.append(neighbor_id)

    return affected


def detect_coalitions(state: SimulationState, threshold: float = 0.3) -> list[set[str]]:
    """Detect emergent coalitions — groups of agents with aligned opinions.

    MiroFish rule: agents cluster and form opinion groups over time.
    """
    from app.services.simulation.graph import get_neighbors

    personas_map = {p["id"]: p for p in state.personas}
    visited = set()
    coalitions = []

    for persona in state.personas:
        pid = persona["id"]
        if pid in visited:
            continue

        memory = state.memories.get(pid)
        if not memory or not memory.has_engaged:
            continue

        # BFS to find aligned connected agents
        coalition = set()
        queue = [pid]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            current_mem = state.memories.get(current)
            if not current_mem:
                continue

            # Check opinion alignment
            if memory.opinion_score > 0 and current_mem.opinion_score > 0:
                coalition.add(current)
            elif memory.opinion_score < 0 and current_mem.opinion_score < 0:
                coalition.add(current)
            elif abs(memory.opinion_score - current_mem.opinion_score) < threshold:
                coalition.add(current)
            else:
                continue

            # Expand to neighbors
            if state.graph:
                for neighbor in get_neighbors(state.graph, current):
                    if neighbor not in visited:
                        queue.append(neighbor)

        if len(coalition) >= 3:  # minimum coalition size
            coalitions.append(coalition)

    return coalitions


# ──────────────────────────────────────────────────────────────────────
# Seed Selection
# ──────────────────────────────────────────────────────────────────────

def select_seeds(state: SimulationState) -> list[str]:
    """Pick initial seed personas. High-influence agents see the material first.

    Distributes seeds across platforms.
    """
    sorted_personas = sorted(
        state.personas,
        key=lambda p: p["influence_weight"],
        reverse=True,
    )
    return [p["id"] for p in sorted_personas[:state.env_config.seed_count]]


# ──────────────────────────────────────────────────────────────────────
# Platform-Specific Action Selection
# ──────────────────────────────────────────────────────────────────────

def get_available_actions(platform: Platform) -> list[ActionType]:
    """Return platform-specific available actions."""
    common = [
        ActionType.IGNORE, ActionType.READ, ActionType.LIKE,
        ActionType.COMMENT, ActionType.REPLY, ActionType.SHARE,
        ActionType.FOLLOW, ActionType.UNFOLLOW, ActionType.MUTE,
        ActionType.BLOCK, ActionType.SEARCH, ActionType.CLICK_PROFILE,
        ActionType.CLICK_LINK, ActionType.BOOKMARK, ActionType.REPORT,
        ActionType.DM, ActionType.SCREENSHOT, ActionType.CROSSPOST,
    ]
    if platform == Platform.TWITTER:
        return common + [ActionType.QUOTE, ActionType.EMOJI_REACT]
    elif platform == Platform.REDDIT:
        return common + [ActionType.UPVOTE, ActionType.DOWNVOTE, ActionType.AWARD]
    return common


# ──────────────────────────────────────────────────────────────────────
# Batching for LLM Calls
# ──────────────────────────────────────────────────────────────────────

def batch_personas_for_llm(
    persona_ids: list[str],
    personas_map: dict[str, dict],
    memories: dict[str, AgentMemory],
    batch_size: int | None = None,
) -> list[list[dict]]:
    """Group personas into batches for batched LLM calls.

    Includes memory context so agents can reference earlier rounds.
    """
    if batch_size is None:
        batch_size = settings.batch_size

    enriched = []
    for pid in persona_ids:
        persona = dict(personas_map[pid])  # copy
        memory = memories.get(pid)
        if memory:
            persona["memory_summary"] = {
                "opinion_score": memory.opinion_score,
                "interaction_count": memory.interaction_count,
                "recent_interactions": memory.interactions[-5:],  # last 5 interactions
                "followed": memory.followed[-10:],
                "has_engaged_before": memory.has_engaged,
            }
        enriched.append(persona)

    return [enriched[i:i + batch_size] for i in range(0, len(enriched), batch_size)]


# ──────────────────────────────────────────────────────────────────────
# Turn Execution — MiroFish-aligned round loop
# ──────────────────────────────────────────────────────────────────────

async def run_round(state: SimulationState) -> list[TurnAction]:
    """Execute one simulation round across all platforms.

    MiroFish rules of engagement:
    1. Determine which exposed personas engage (filter + memory + social proof)
    2. For each platform, batch engaging personas and call LLM
    3. Process actions: shares/crossposts expose new personas via graph
    4. Propagate opinion influence through social connections
    5. Update memory for all participating agents
    6. Detect emerging coalitions
    7. Update content freshness and controversy scores
    """
    round_actions: list[TurnAction] = []
    config = state.env_config
    personas_map = {p["id"]: p for p in state.personas}

    # Update global dynamics
    state.social_proof_modifier = compute_social_proof(state)
    state.controversy_score = compute_controversy(state)
    state.content_freshness = max(
        0.2,  # floor — content never fully dies
        1.0 - (state.current_round * config.content_freshness_decay)
            + (state.controversy_score * (config.controversy_boost - 1.0)),
    )

    # For each platform, run engagement
    for platform in config.platforms:
        platform_state = state.platform_states[platform]

        # Filter: which exposed personas engage this round on this platform?
        engaging = []
        ignoring = []
        for pid in state.exposed:
            persona = personas_map.get(pid)
            memory = state.memories.get(pid)
            if not persona or not memory:
                continue
            if pid in memory.blocked:
                continue

            if should_engage(persona, memory, state):
                engaging.append(pid)
            else:
                ignoring.append(pid)

        # Record ignores (no LLM cost)
        for pid in ignoring:
            round_actions.append(TurnAction(
                persona_id=pid,
                round_num=state.current_round,
                platform=platform,
                action=ActionType.IGNORE,
            ))

        # Batch engaging personas for LLM calls (with memory context)
        batches = batch_personas_for_llm(engaging, personas_map, state.memories)

        for batch in batches:
            # TODO: call batched LLM here (Haiku for reactions)
            # For now, rule-based placeholder
            for persona in batch:
                action_type, sentiment = _pick_action_and_sentiment(persona, platform, state)
                action = TurnAction(
                    persona_id=persona["id"],
                    round_num=state.current_round,
                    platform=platform,
                    action=action_type,
                    sentiment=sentiment,
                    content=None,  # LLM will generate
                )
                round_actions.append(action)

                # Update memory
                memory = state.memories[persona["id"]]
                memory.record_interaction(state.current_round, action_type, None, sentiment)

                # Opinion drift from own engagement
                opinion_delta = _sentiment_to_opinion_delta(sentiment, config)
                memory.update_opinion(state.current_round, opinion_delta)

                state.engaged.add(persona["id"])

                # Shares and crossposts expose new agents
                if action_type in (ActionType.SHARE, ActionType.CROSSPOST, ActionType.QUOTE):
                    platform_state.share_count += 1
                    _propagate_exposure(persona["id"], state)

                    # Cascade check
                    if platform_state.share_count / max(len(state.exposed), 1) > config.viral_threshold:
                        _trigger_viral_cascade(persona["id"], state)

                # Social graph influence propagation
                if action_type not in (ActionType.IGNORE, ActionType.READ, ActionType.BOOKMARK):
                    propagate_influence(persona["id"], state, state.graph)
                    platform_state.engagement_count += 1

                # Graph mutations (follow/block/mute)
                if action_type == ActionType.FOLLOW:
                    memory.followed.append(persona.get("target_persona", "unknown"))
                elif action_type == ActionType.MUTE:
                    memory.muted.append(persona.get("target_persona", "unknown"))
                elif action_type == ActionType.BLOCK:
                    memory.blocked.append(persona.get("target_persona", "unknown"))

        # Update platform trending
        platform_state.trending_score = (
            platform_state.engagement_count * 0.3
            + platform_state.share_count * 0.7
        )

    # Detect coalitions every 5 rounds
    if state.current_round % 5 == 0 and state.current_round > 0:
        state.coalitions = detect_coalitions(state)

    state.all_actions.extend(round_actions)
    state.current_round += 1
    return round_actions


def _pick_action_and_sentiment(
    persona: dict,
    platform: Platform,
    state: SimulationState,
) -> tuple[ActionType, Sentiment]:
    """Rule-based action + sentiment selection. Replaced by LLM in production."""
    memory = state.memories.get(persona["id"])
    opinion = memory.opinion_score if memory else 0.0

    # Sentiment from opinion
    if opinion > 0.4:
        sentiment = Sentiment.POSITIVE
    elif opinion < -0.4:
        sentiment = Sentiment.NEGATIVE if opinion > -0.7 else Sentiment.HOSTILE
    else:
        sentiment = Sentiment.NEUTRAL

    # Action selection weighted by persona rates and platform
    r = random.random()
    share_rate = persona.get("share_rate", 0.2)

    if r < share_rate * 0.3:
        action = ActionType.SHARE
    elif r < share_rate * 0.5 and platform == Platform.TWITTER:
        action = ActionType.QUOTE
    elif r < 0.15:
        action = ActionType.DM if random.random() < state.env_config.dark_social_rate else ActionType.COMMENT
    elif r < 0.35:
        action = ActionType.COMMENT
    elif r < 0.55:
        action = ActionType.REPLY
    elif r < 0.70:
        action = ActionType.LIKE if platform == Platform.TWITTER else ActionType.UPVOTE
    elif r < 0.80:
        action = ActionType.CLICK_LINK
    elif r < 0.88:
        action = ActionType.BOOKMARK
    elif r < 0.93:
        action = ActionType.FOLLOW
    elif r < 0.97:
        action = ActionType.SEARCH
    else:
        action = ActionType.CLICK_PROFILE

    # Hostile sentiment can trigger blocks/reports
    if sentiment == Sentiment.HOSTILE and random.random() < 0.2:
        action = random.choice([ActionType.BLOCK, ActionType.REPORT])

    return action, sentiment


def _sentiment_to_opinion_delta(sentiment: Sentiment, config: EnvironmentConfig) -> float:
    """Convert sentiment to opinion drift."""
    base = config.opinion_drift_rate
    return {
        Sentiment.POSITIVE: base * 1.5,
        Sentiment.NEUTRAL: base * 0.1,
        Sentiment.NEGATIVE: -base * 1.5,
        Sentiment.HOSTILE: -base * 2.5,
    }[sentiment]


def _propagate_exposure(sharer_id: str, state: SimulationState):
    """Expose the sharer's neighbors to the content."""
    from app.services.simulation.graph import get_neighbors
    if state.graph:
        for neighbor_id in get_neighbors(state.graph, sharer_id):
            state.exposed.add(neighbor_id)


def _trigger_viral_cascade(trigger_id: str, state: SimulationState):
    """Viral cascade: exponential exposure when threshold is crossed."""
    from app.services.simulation.graph import get_neighbors
    config = state.env_config
    cascade = {"trigger": trigger_id, "round": state.current_round, "new_exposed": []}

    if state.graph:
        # Two hops of cascade exposure
        first_hop = get_neighbors(state.graph, trigger_id)
        for fid in first_hop:
            if random.random() < config.cascade_probability:
                state.exposed.add(fid)
                cascade["new_exposed"].append(fid)
                # Second hop
                for sid in get_neighbors(state.graph, fid):
                    if random.random() < config.cascade_probability * config.influence_decay:
                        state.exposed.add(sid)
                        cascade["new_exposed"].append(sid)

    state.viral_cascades.append(cascade)


# ──────────────────────────────────────────────────────────────────────
# Full Simulation Loop
# ──────────────────────────────────────────────────────────────────────

async def run_simulation(state: SimulationState) -> SimulationState:
    """Run the full MiroFish-aligned simulation loop.

    1. Seed initial exposure
    2. Run 30-50 rounds with dual-platform parallel simulation
    3. Track opinion drift, coalitions, viral cascades
    4. Return final state for analysis
    """
    # Phase 1: Seed
    seeds = select_seeds(state)
    for sid in seeds:
        state.exposed.add(sid)

    # Phase 2: Simulate
    for round_num in range(state.env_config.max_rounds):
        await run_round(state)

        # Early termination: if everyone has been exposed and engagement is dead
        if len(state.exposed) >= len(state.personas) * 0.95:
            new_engagements = sum(
                1 for a in state.all_actions
                if a.round_num == state.current_round - 1
                and a.action not in (ActionType.IGNORE, ActionType.READ)
            )
            if new_engagements == 0:
                break

    # Phase 3: Final coalition detection
    state.coalitions = detect_coalitions(state)

    # Phase 4: Compute final opinion clusters by archetype
    archetype_opinions: dict[str, list[float]] = {}
    personas_map = {p["id"]: p for p in state.personas}
    for pid, memory in state.memories.items():
        archetype = personas_map.get(pid, {}).get("primary_archetype", "unknown")
        if archetype not in archetype_opinions:
            archetype_opinions[archetype] = []
        archetype_opinions[archetype].append(memory.opinion_score)

    state.opinion_clusters = {
        arch: sum(scores) / len(scores)
        for arch, scores in archetype_opinions.items()
        if scores
    }

    return state
