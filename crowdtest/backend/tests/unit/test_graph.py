"""Tests for social graph construction and traversal."""

import random

from app.services.simulation.graph import SocialGraph, build_social_graph, get_neighbors


class TestGraphConstruction:
    """Test small-world graph building."""

    def test_basic_graph_has_edges(self):
        ids = [f"agent_{i:03d}" for i in range(10)]
        weights = {pid: 0.5 for pid in ids}
        graph = build_social_graph(ids, weights)
        assert len(graph.edges) > 0
        assert len(graph.nodes) == 10

    def test_all_nodes_have_at_least_one_connection(self):
        random.seed(42)
        ids = [f"agent_{i:03d}" for i in range(20)]
        weights = {pid: 0.5 for pid in ids}
        graph = build_social_graph(ids, weights, avg_connections=4)
        for pid in ids:
            neighbors = get_neighbors(graph, pid)
            assert len(neighbors) > 0, f"{pid} has no connections"

    def test_edges_are_bidirectional(self):
        ids = [f"agent_{i:03d}" for i in range(10)]
        weights = {pid: 0.5 for pid in ids}
        graph = build_social_graph(ids, weights)
        for a, b in graph.edges:
            # Edge should be sorted (a < b), meaning it represents both directions
            assert a <= b, f"Edge ({a}, {b}) not sorted"

    def test_no_self_loops(self):
        ids = [f"agent_{i:03d}" for i in range(10)]
        weights = {pid: 0.5 for pid in ids}
        graph = build_social_graph(ids, weights)
        for a, b in graph.edges:
            assert a != b, f"Self-loop found: ({a}, {b})"

    def test_single_node_graph(self):
        graph = build_social_graph(["agent_000"], {"agent_000": 0.5})
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 0

    def test_two_node_graph(self):
        ids = ["agent_000", "agent_001"]
        weights = {pid: 0.5 for pid in ids}
        graph = build_social_graph(ids, weights)
        assert len(graph.nodes) == 2
        # Should have at least one edge connecting them
        assert len(graph.edges) >= 1

    def test_high_influence_nodes_attract_connections(self):
        """High-influence nodes should tend to have more connections after rewiring."""
        random.seed(42)
        ids = [f"agent_{i:03d}" for i in range(30)]
        weights = {pid: 0.1 for pid in ids}
        # Make one node very influential
        weights["agent_000"] = 10.0
        graph = build_social_graph(ids, weights, avg_connections=4)
        star_neighbors = len(get_neighbors(graph, "agent_000"))
        avg_neighbors = sum(len(get_neighbors(graph, pid)) for pid in ids) / len(ids)
        # Influential node should have more connections than average
        assert star_neighbors >= avg_neighbors

    def test_avg_connections_respected(self):
        """Total edges should be approximately n * avg_connections / 2."""
        random.seed(42)
        ids = [f"agent_{i:03d}" for i in range(50)]
        weights = {pid: 0.5 for pid in ids}
        graph = build_social_graph(ids, weights, avg_connections=6)
        # Expected: 50 * 6 / 2 = 150 edges (roughly)
        assert len(graph.edges) > 50  # at least some edges
        assert len(graph.edges) < 300  # not too many


class TestGetNeighbors:
    """Test neighbor lookup."""

    def test_returns_correct_neighbors(self):
        graph = SocialGraph(
            nodes=["a", "b", "c"],
            edges=[("a", "b"), ("a", "c")],
            influence_map={"a": 1, "b": 1, "c": 1},
        )
        assert set(get_neighbors(graph, "a")) == {"b", "c"}
        assert set(get_neighbors(graph, "b")) == {"a"}
        assert set(get_neighbors(graph, "c")) == {"a"}

    def test_node_with_no_edges(self):
        graph = SocialGraph(
            nodes=["a", "b", "c"],
            edges=[("a", "b")],
            influence_map={"a": 1, "b": 1, "c": 1},
        )
        assert get_neighbors(graph, "c") == []

    def test_nonexistent_node(self):
        graph = SocialGraph(
            nodes=["a", "b"],
            edges=[("a", "b")],
            influence_map={"a": 1, "b": 1},
        )
        assert get_neighbors(graph, "z") == []
