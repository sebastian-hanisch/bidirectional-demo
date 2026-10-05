"""Unabhängiges Orakel: Floyd-Warshall (eigene Schleife) auf Zufallsgraphen mit Nullkosten, Gleichständen, Parallelkanten und
unerreichbaren Zielen. Geprüft für jede Abbruchregel x Wechselstrategie x Warteschlange: die korrekte Regel liefert genau die
kürzeste Entfernung (kein vorzeitiges Stoppen), die Buch-Regel nie weniger als sie (echte Route); jede Seite legt Knoten mit
den wahren Entfernungen und in Entfernungsreihenfolge fest (Präfix-Eigenschaft); einseitiges Dijkstra legt zwischen
|{d < d(t)}| und |{d <= d(t)}| Knoten fest. Große Fassung (36 000 Läufe) im Scratchpad."""

import random

import numpy as np

import bd_algorithm as alg
from bd_graph import from_arcs, reverse_graph, route_cost

INF = float("inf")


def _floyd_warshall(n, arcs, directed):
    d = [[INF] * n for _ in range(n)]
    for i in range(n):
        d[i][i] = 0.0
    for u, v, w in arcs:
        if u != v:
            d[u][v] = min(d[u][v], w)
            if not directed:
                d[v][u] = min(d[v][u], w)
    for k in range(n):
        for i in range(n):
            for j in range(n):
                if d[i][k] + d[k][j] < d[i][j]:
                    d[i][j] = d[i][k] + d[k][j]
    return d


def test_bidirectional_matches_floyd_warshall_for_every_rule_strategy_and_queue():
    rng = random.Random(77)
    for it in range(40):
        n = rng.choice([1, 2, 3, 5, 8, 12])
        directed = rng.random() < 0.55
        zero = rng.random() < 0.3
        arcs = [(rng.randrange(n), rng.randrange(n), float(rng.randint(0 if zero else 1, rng.choice([1, 2, 4, 9]))))
                for _ in range(rng.randrange(0, 3 * n + 1))]
        g = from_arcs(n, arcs, np.zeros((n, 2)), directed=directed, clean=rng.random() < 0.7)
        rg = reverse_graph(g)
        ref = _floyd_warshall(n, arcs, directed)
        for _ in range(3):
            s, t = rng.randrange(n), rng.randrange(n)
            true = ref[s][t]
            uni = alg.dijkstra(g, s, t)
            assert (uni.found >= 0) == (true < INF)
            if true < INF:
                less = sum(1 for v in range(n) if ref[s][v] < true)
                leq = sum(1 for v in range(n) if ref[s][v] <= true)
                assert less <= len(uni.order) <= leq and uni.dist[t] == true
            for stop in alg.STOPS:
                for alt in alg.ALTERNATES:
                    for queue in ("lazy", "binary"):
                        b = alg.bidirectional(g, rg, s, t, stop, alt, queue)
                        if stop == "correct":
                            assert b.cost == true, (it, s, t, alt, queue)
                            if true < INF:
                                assert b.route[0] == s and b.route[-1] == t and route_cost(g, b.route) == true
                        elif true < INF:
                            assert b.cost >= true and route_cost(g, b.route) == b.cost
                        else:
                            assert b.cost == INF and b.route == []
                        if s == t:
                            continue
                        for order, dist, dd in ((b.order_f, b.dist_f, lambda v: ref[s][v]), (b.order_b, b.dist_b, lambda v: ref[v][t])):
                            assert all(dist[v] == dd(v) for v in order)  # festgelegt = wahre Entfernung
                            if order:
                                far = max(dd(v) for v in order)
                                assert all(v in set(order) for v in range(n) if dd(v) < far)  # Präfix der Entfernungsreihenfolge
