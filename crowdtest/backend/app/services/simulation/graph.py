"""Social graph builder: small-world network generation for persona connections."""

import random
from dataclasses import dataclass


@dataclass
class SocialGraph:
    nodes: list[str]  # persona IDs
    edges: list[tuple[str, str]]  # bidirectional connections
    influence_map: dict[str, float]  # persona_id -> influence score


def build_social_graph(
    persona_ids: list[str],
    influence_weights: dict[str, float],
    avg_connections: int = 4,
) -> SocialGraph:
    """Build a small-world social graph.

    Each persona gets ~avg_connections links, biased toward high-influence nodes.
    Creates clusters (friend groups) with some cross-cluster bridges.
    """
    n = len(persona_ids)
    edges: set[tuple[str, str]] = set()

    # Phase 1: Ring lattice (each node connects to nearest neighbors)
    k = min(avg_connections, n - 1)
    half_k = max(k // 2, 1)  # ensure at least 1 neighbor per direction
    for i in range(n):
        for j in range(1, half_k + 1):
            neighbor = (i + j) % n
            if neighbor != i:  # guard against self-loop on tiny graphs
                edge = tuple(sorted([persona_ids[i], persona_ids[neighbor]]))
                edges.add(edge)

    # Phase 2: Rewire with small-world probability (Watts-Strogatz style)
    rewire_prob = 0.15
    for edge in list(edges):
        if random.random() < rewire_prob:
            a = edge[0]
            # Pick a random new target, biased toward high-influence nodes
            candidates = [
                pid for pid in persona_ids
                if pid != a and tuple(sorted([a, pid])) not in edges
            ]
            if candidates:
                weights = [influence_weights.get(c, 0.5) for c in candidates]
                total = sum(weights)
                if total > 0:
                    probs = [w / total for w in weights]
                    new_target = random.choices(candidates, weights=probs, k=1)[0]
                    edges.discard(edge)
                    edges.add(tuple(sorted([a, new_target])))

    return SocialGraph(
        nodes=persona_ids,
        edges=list(edges),
        influence_map=influence_weights,
    )


def get_neighbors(graph: SocialGraph, persona_id: str) -> list[str]:
    """Get all connected persona IDs for a given persona."""
    neighbors = []
    for a, b in graph.edges:
        if a == persona_id:
            neighbors.append(b)
        elif b == persona_id:
            neighbors.append(a)
    return neighbors
