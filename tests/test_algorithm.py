"""Bidirektionale Suche gegen networkx und gegen einseitiges Dijkstra: alle Wechselstrategien, beide Warteschlangen, gerichtet und ungerichtet, Grenzfälle, Abbruchregeln."""

import itertools

import networkx as nx
import numpy as np
import pytest

import bd_algorithm as alg
from bd_graph import from_arcs, reverse_graph, route_cost


def random_graph(n, m, seed, directed=False, integer=True, zero=0.0):
    rng = np.random.default_rng(seed)
    arcs = []
    for _ in range(m):
        u, v = rng.integers(0, n, 2)
        w = float(rng.integers(1, 9)) if integer else 0.5 + 5 * rng.random()
        if zero and rng.random() < zero:
            w = 0.0
        arcs.append((u, v, w))
    return from_arcs(n, arcs, np.zeros((n, 2)), directed=directed)


def to_nx(g):
    G = nx.DiGraph()
    G.add_nodes_from(range(g.n))
    for u in range(g.n):
        for v, w in zip(g.out(u), g.out_weights(u)):
            G.add_edge(u, int(v), weight=float(w))
    return G


# --- Umgekehrter Graph -------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("directed", [False, True])
def test_reverse_graph_swaps_every_arc_and_reversing_twice_restores_the_graph(directed):
    g = random_graph(40, 100, 3, directed)
    rg = reverse_graph(g)
    assert rg.m == g.m and rg.n == g.n
    for u in range(g.n):
        for v, w in zip(g.out(u), g.out_weights(u)):
            k = rg.arc(int(v), u)
            assert k >= 0 and rg.weight[k] <= w + 1e-12
    back = reverse_graph(rg)
    assert np.array_equal(back.indptr, g.indptr) and np.array_equal(back.indices, g.indices) and np.array_equal(back.weight, g.weight)
    if not directed:
        assert np.array_equal(rg.indices, g.indices) and np.array_equal(rg.weight, g.weight)


# --- Kosten gegen networkx ---------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("alternate", alg.ALTERNATES)
@pytest.mark.parametrize("queue", ["lazy", "binary"])
@pytest.mark.parametrize("seed", range(4))
@pytest.mark.parametrize("directed", [False, True])
def test_correct_stop_is_optimal_for_every_pair(alternate, queue, seed, directed):
    g = random_graph(45, 110, seed, directed, integer=False)
    rg, G = reverse_graph(g), to_nx(g)
    rng = np.random.default_rng(seed)
    for _ in range(25):
        s, t = (int(x) for x in rng.integers(0, g.n, 2))
        res = alg.bidirectional(g, rg, s, t, "correct", alternate, queue)
        if nx.has_path(G, s, t):
            ref = nx.dijkstra_path_length(G, s, t)
            assert res.cost == pytest.approx(ref) and route_cost(g, res.route) == pytest.approx(ref)
            assert res.route[0] == s and res.route[-1] == t
        else:
            assert res.route == [] and not np.isfinite(res.cost) and res.stopped_by == "exhausted"


def test_correct_stop_equals_networkx_bidirectional_and_one_sided_dijkstra():
    g = random_graph(80, 220, 9, directed=True)
    rg, G = reverse_graph(g), to_nx(g)
    for s, t in itertools.islice(itertools.permutations(range(0, 80, 7), 2), 60):
        if not nx.has_path(G, s, t):
            continue
        res, uni = alg.bidirectional(g, rg, s, t), alg.dijkstra(g, s, t)
        assert res.cost == pytest.approx(nx.bidirectional_dijkstra(G, s, t)[0]) == pytest.approx(uni.dist[t])


def test_zero_weight_edges_and_ties_do_not_break_the_stop_rule():
    for seed in range(6):
        g = random_graph(50, 130, seed, directed=True, zero=0.25)
        rg, G = reverse_graph(g), to_nx(g)
        for s, t in ((0, 49), (3, 40), (10, 11), (25, 2)):
            if nx.has_path(G, s, t):
                assert alg.bidirectional(g, rg, s, t).cost == pytest.approx(nx.dijkstra_path_length(G, s, t))


def test_start_equals_target_and_direct_edge():
    g = random_graph(20, 50, 1)
    rg = reverse_graph(g)
    r = alg.bidirectional(g, rg, 4, 4)
    assert r.cost == 0 and r.route == [4] and r.stopped_by == "trivial" and r.settled == 0
    g2 = from_arcs(3, [(0, 1, 5.0), (0, 2, 1.0), (2, 1, 1.0)], np.zeros((3, 2)), directed=True)
    assert alg.bidirectional(g2, reverse_graph(g2), 0, 1).cost == 2.0


def test_unreachable_target_is_reported_and_one_way_streets_are_respected():
    g = from_arcs(4, [(0, 1, 1.0), (2, 3, 1.0)], np.zeros((4, 2)), directed=True)
    rg = reverse_graph(g)
    assert alg.bidirectional(g, rg, 0, 3).route == [] and alg.bidirectional(g, rg, 1, 0).route == []
    assert alg.bidirectional(g, rg, 0, 1).cost == 1.0


# --- Beschleunigung und Zähler ------------------------------------------------------------------------------------------------------------

def test_bidirectional_settles_fewer_nodes_than_dijkstra_on_a_grid():
    side = 25
    arcs = [(i * side + j, i * side + j + 1, 1.0) for i in range(side) for j in range(side - 1)] + [(i * side + j, (i + 1) * side + j, 1.0) for i in range(side - 1) for j in range(side)]
    g = from_arcs(side * side, arcs, np.zeros((side * side, 2)))
    rg = reverse_graph(g)
    res, uni = alg.bidirectional(g, rg, 0, side * side - 1), alg.dijkstra(g, 0, side * side - 1)
    assert res.cost == uni.dist[-1] == 2 * (side - 1) and res.settled < len(uni.order)


def test_history_lengths_and_the_bound_never_decreases():
    g = random_graph(120, 320, 4, integer=False)
    rg = reverse_graph(g)
    res = alg.bidirectional(g, rg, 0, 100)
    n = res.settled
    assert len(res.mu_hist) == len(res.lower_hist) == len(res.front_hist) == n + 1 and len(res.steps) == n
    assert all(b >= a - 1e-9 for a, b in zip(res.lower_hist, res.lower_hist[1:]))               # die untere Schranke steigt
    assert all(b <= a + 1e-12 for a, b in zip(res.mu_hist, res.mu_hist[1:]))                    # mu fällt nur
    assert res.stopped_by == "bound" and res.lower_hist[-1] >= res.mu_hist[-1] - 1e-9


def test_strict_alternation_alternates():
    g = random_graph(100, 260, 2)
    res = alg.bidirectional(g, reverse_graph(g), 0, 60, alternate="strict")
    sides = [x for x, _ in res.steps]
    assert all(sides[i] != sides[i + 1] for i in range(len(sides) - 1)) or res.stopped_by != "bound"


def test_all_strategies_reach_the_same_cost():
    g = random_graph(90, 250, 6, directed=True, integer=False)
    rg = reverse_graph(g)
    G = to_nx(g)
    for s, t in ((0, 80), (5, 70), (33, 2)):
        if nx.has_path(G, s, t):
            costs = {a: alg.bidirectional(g, rg, s, t, "correct", a).cost for a in alg.ALTERNATES}
            assert all(c == pytest.approx(costs["strict"]) for c in costs.values())


# --- Erste Begegnung ---------------------------------------------------------------------------------------------------------------------

def _first_meeting_cases():
    for seed in range(12):
        g = random_graph(60, 160, seed, directed=False, integer=False)
        rg, G = reverse_graph(g), to_nx(g)
        for s, t in ((0, 59), (5, 44), (13, 31), (20, 2)):
            if nx.has_path(G, s, t):
                yield g, rg, s, t, nx.dijkstra_path_length(G, s, t)


def test_first_meeting_returns_a_real_route_that_is_never_shorter_than_the_optimum_and_sometimes_longer():
    longer, total = 0, 0
    for g, rg, s, t, ref in _first_meeting_cases():
        res = alg.bidirectional(g, rg, s, t, "first_meeting")
        assert res.stopped_by in ("meeting", "exhausted") and res.route[0] == s and res.route[-1] == t
        assert route_cost(g, res.route) == pytest.approx(res.cost) and res.cost >= ref - 1e-9
        longer += res.cost > ref + 1e-9
        total += 1
    assert total > 30 and longer > 0                                                          # die Buch-Variante liegt in manchen Fällen daneben


def test_correct_stop_never_returns_more_than_the_optimum_on_the_same_cases():
    for g, rg, s, t, ref in _first_meeting_cases():
        assert alg.bidirectional(g, rg, s, t, "correct").cost == pytest.approx(ref)


def test_first_meeting_stops_earlier_than_the_correct_rule():
    early = late = 0
    for g, rg, s, t, ref in _first_meeting_cases():
        a, b = alg.bidirectional(g, rg, s, t, "first_meeting"), alg.bidirectional(g, rg, s, t, "correct")
        early += a.settled
        late += b.settled
    assert early <= late
