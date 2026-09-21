"""Netze (kleines Netz, Stadtnetz, Zufallsnetz, ungleiche Dichte, Toronto Innenstadt), Paarwahl, Kennzahlen, Verteilungen, Experimente."""

import networkx as nx
import numpy as np
import pytest

import bd_algorithm as alg
import bd_constants as C
import bd_evaluation as ev
import bd_scenario as sc
from bd_graph import route_cost


def _components(g):
    G = nx.DiGraph()
    for u in range(g.n):
        for v in g.out(u):
            G.add_edge(u, int(v))
    return nx.number_strongly_connected_components(G)


# --- Netze -----------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("seed", range(3))
def test_city_is_connected_with_whole_number_costs_and_the_reverse_graph_matches(seed):
    net = sc.make_network("city", 12, 2.3, 1.0, 20, seed=seed)
    g = net.graph
    assert _components(g) == 1 and (g.weight >= 1).all() and np.array_equal(g.weight, np.rint(g.weight))
    assert np.array_equal(net.reverse.indices, g.indices) and np.array_equal(net.reverse.weight, g.weight)          # ungerichtet: derselbe Inhalt


def test_random_network_is_connected_has_the_requested_degree_and_is_deterministic():
    a, b, c = (sc.build_random(500, 4.0, s) for s in (1, 1, 2))
    assert _components(a) == 1 and abs(a.m / a.n - 4.0) < 0.05 and np.array_equal(a.indices, b.indices) and not np.array_equal(a.weight, c.weight)
    assert (a.weight >= 1).all() and (a.weight <= 9).all()


def test_asymmetric_network_has_a_dense_and_a_sparse_part():
    net = sc.make_network("asym", nodes=1000, seed=3)
    g, split = net.graph, net.split
    deg = g.degree()
    assert split == 400 and _components(g) == 1
    assert deg[:split].mean() > 3 * deg[split:].mean() and 10 < deg[:split].mean() < 14 and 2.0 < deg[split:].mean() < 3.2


def test_toronto_downtown_data_is_the_expected_excerpt():
    net = sc.toronto_network()
    g = net.graph
    assert (g.n, g.m) == (10153, 26985) and g.directed and net.unit == "m"
    assert (g.weight >= 1).all() and np.array_equal(g.weight, np.rint(g.weight))
    src = np.repeat(np.arange(g.n), g.degree())
    assert (src != g.indices).all() and len(set(zip(src.tolist(), g.indices.tolist()))) == g.m
    assert sum(g.arc(int(v), int(u)) < 0 for u, v in zip(src, g.indices)) > 100                   # es gibt Einbahnstraßen
    assert _components(g) == 1                                                                   # größte stark zusammenhängende Komponente


def test_toronto_reverse_graph_is_consistent_with_the_one_way_streets():
    net = sc.toronto_network()
    g, rg = net.graph, net.reverse
    rng = np.random.default_rng(1)
    for u in rng.integers(0, g.n, 200):
        for v, w in zip(g.out(int(u)), g.out_weights(int(u))):
            k = rg.arc(int(v), int(u))
            assert k >= 0 and rg.weight[k] == w


def test_small_network_matches_its_definition_and_the_first_meeting_is_misleading():
    net = sc.small_network()
    g = net.graph
    assert g.n == 8 and g.m == 2 * len(sc.SMALL_LINKS) and not g.directed and net.fixed_pair == (0, 4)
    s, t = net.fixed_pair
    first = alg.bidirectional(g, net.reverse, s, t, "first_meeting")
    right = alg.bidirectional(g, net.reverse, s, t, "correct")
    names = lambda r: [g.names[i] for i in r.route]
    assert names(first) == ["Depot", "Pass", "Kunde"] and first.cost == 11 and first.stopped_by == "meeting"
    assert names(right) == ["Depot", "Dorf", "Tal", "Kunde"] and right.cost == 9 and right.stopped_by == "bound"
    assert right.mu_hist == [float("inf"), float("inf"), 11.0, 11.0, 9.0] and right.lower_hist == [0.0, 1.0, 4.0, 6.0, 9.0]


# --- Paarwahl --------------------------------------------------------------------------------------------------------------------------------

def test_pick_pair_follows_the_distance_rank_and_is_deterministic():
    net = sc.make_network("city")
    pairs = {p: ev.pick_pair(net, p, 7) for p in (10, 50, 100)}
    assert pairs == {p: ev.pick_pair(net, p, 7) for p in (10, 50, 100)} and len({s for s, _ in pairs.values()}) == 1
    d = alg.dijkstra(net.graph, pairs[10][0]).dist
    assert d[pairs[10][1]] < d[pairs[50][1]] <= d[pairs[100][1]] and d[pairs[100][1]] == np.max(d)


def test_pick_pair_keeps_the_fixed_pair_and_uses_the_dense_part_for_asymmetric_nets():
    small = sc.small_network()
    assert ev.pick_pair(small, 10, 1) == small.fixed_pair == ev.pick_pair(small, 99, 5)
    asym = sc.make_network("asym")
    assert ev.pick_pair(asym, 60, 3)[0] < asym.split


# --- Kennzahlen ------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("key", C.NETS)
def test_analysis_invariants_for_every_net(key):
    net = sc.make_network(key)
    s, t = ev.pick_pair(net)
    a = ev.analyse(net, s, t)
    m = a.metrics
    assert m["reachable"] and m["optimal"] and m["stopped_by"] == "bound" and m["cost_bi"] == m["cost_uni"] == pytest.approx(route_cost(net.graph, a.bi.route))
    assert m["settled_bi"] == m["settled_f"] + m["settled_b"] and m["speedup"] == pytest.approx(m["settled_uni"] / m["settled_bi"])
    assert a.bi.route[0] == s and a.bi.route[-1] == t and ev.verdict(a) in ("faster", "no_gain")


def test_first_meeting_metrics_carry_the_correct_run_for_comparison():
    net = sc.small_network()
    a = ev.analyse(net, *net.fixed_pair, stop="first_meeting")
    m = a.metrics
    assert not m["optimal"] and m["cost_bi"] == 11 and m["cost_uni"] == 9 == m["cost_correct"] and m["excess"] == pytest.approx(2 / 9) and ev.verdict(a) == "wrong_route"
    assert m["settled_correct"] > m["settled_bi"]


def test_all_wechselstrategien_give_the_same_cost_in_the_analysis():
    net = sc.make_network("city", 14)
    s, t = ev.pick_pair(net)
    assert len({ev.analyse(net, s, t, "correct", a).metrics["cost_bi"] for a in alg.ALTERNATES}) == 1


# --- Verteilung und Experimente ----------------------------------------------------------------------------------------------------------------

def test_pair_stats_fields_determinism_and_optimality():
    net = sc.make_network("city")
    a, b = ev.pair_stats(net, "correct", "strict", 30, 3), ev.pair_stats(net, "correct", "strict", 30, 3)
    assert a["n_pairs"] == 30 and np.array_equal(a["speedup"], b["speedup"]) and a["share_wrong"] == 0 and a["excess_mean"] == pytest.approx(0)
    assert a["speedup_p10"] <= a["speedup_median"] <= a["speedup_p90"]
    c = ev.pair_stats(net, "first_meeting", "strict", 30, 3)
    assert c["share_wrong"] > 0 and c["excess_mean"] > 0 and c["excess_wrong"] >= c["excess_mean"]


def test_multi_pair_stats_shares_the_pairs_between_configurations():
    net = sc.make_network("city", 12)
    cfgs = [("correct", "strict"), ("correct", "smaller_frontier")]
    multi = ev.multi_pair_stats(net, cfgs, 25, 2)
    for c in cfgs:
        single = ev.pair_stats(net, c[0], c[1], 25, 2)
        assert np.array_equal(multi[c]["speedup"], single["speedup"])


def test_asymmetric_pairs_run_from_the_dense_to_the_sparse_part():
    net = sc.make_network("asym", nodes=600, seed=2)
    rng = np.random.default_rng(0)
    for _ in range(20):
        s, t = ev._draw_pair(net, rng)
        assert s < net.split <= t


def test_net_comparison_rows():
    rows = ev.net_comparison(keys=("city", "random"), pairs=8, seeds=C.SWEEP_SEEDS[:2])
    assert [r["net"] for r in rows] == ["city", "random"] and rows[1]["median"] > rows[0]["median"] > 1


def test_stop_and_alternate_comparison_rows():
    st = ev.stop_comparison(keys=("city",), pairs=8, seeds=C.SWEEP_SEEDS[:2])[0]
    assert st["share_wrong"] > 0 and st["speedup_first"] > st["speedup_correct"]
    alt = ev.alternate_comparison(keys=("city",), pairs=8, seeds=C.SWEEP_SEEDS[:2])
    assert [r["alternate"] for r in alt] == list(alg.ALTERNATES) and all(r["speedup"] > 1 for r in alt)


def test_distance_curve_rows():
    rows = ev.distance_curve("city", pcts=(10, 100), sources=1, seeds=C.SWEEP_SEEDS[:2])
    assert [r["pct"] for r in rows] == [10, 100] and all(r["speedup"] > 1 for r in rows)
