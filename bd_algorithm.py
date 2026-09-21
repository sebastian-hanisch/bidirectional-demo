"""Bidirektionale Suche (zwei Dijkstra-Suchen von beiden Enden) mit zwei Abbruchregeln und drei Wechselstrategien, dazu die einseitige Dijkstra-Suche als Referenz.

Alles ist eigene Umsetzung auf dem CSR-Graphen aus bd_graph.py; networkx kommt nur in den Tests vor (Kreuzprobe)."""

from dataclasses import dataclass, field

import numpy as np

from bd_graph import route_cost
from bd_queues import QUEUES

INF = float("inf")
STOPS = ("correct", "first_meeting")
ALTERNATES = ("strict", "smaller_frontier", "min_key")


@dataclass
class Unidirectional:
    dist: np.ndarray                          # Kosten vom Start; bei festgelegten Knoten endgültig
    parent: np.ndarray
    order: list = field(default_factory=list)          # festgelegte Knoten in der Reihenfolge ihrer Festlegung
    found: int = -1
    counters: dict = field(default_factory=dict)

    def route(self, target):
        if not np.isfinite(self.dist[target]):
            return []
        path = [int(target)]
        while self.parent[path[-1]] >= 0:
            path.append(int(self.parent[path[-1]]))
        return path[::-1]


def dijkstra(g, source, target=None, queue="lazy"):
    """Einseitiges Dijkstra ab `source`, Abbruch beim Festlegen von `target` (bei None: ganzes Netz). Referenz für Kosten und für die Fläche, die die beidseitige Suche sparen soll."""
    ip, ix, w = g.indptr.tolist(), g.indices.tolist(), g.weight.tolist()
    q = QUEUES[queue](g.n, 1)
    dist, parent, settled = [INF] * g.n, [-1] * g.n, [False] * g.n
    dist[int(source)] = 0.0
    q.push_or_decrease(int(source), 0.0)
    order, found, relaxations = [], -1, 0
    while len(q):
        d, u = q.pop_min()
        if settled[u]:
            continue
        settled[u] = True
        order.append(u)
        if target is not None and u == int(target):
            found = u
            break
        for k in range(ip[u], ip[u + 1]):
            v = ix[k]
            relaxations += 1
            nd = d + w[k]
            if nd < dist[v] and not settled[v]:
                dist[v], parent[v] = nd, u
                q.push_or_decrease(v, nd)
    counters = q.as_dict()
    counters["relaxations"] = relaxations
    return Unidirectional(np.array(dist), np.array(parent), order, found, counters)


@dataclass
class Bidirectional:
    cost: float                               # Kosten der gefundenen Route (inf = keine)
    route: list                               # Knotenfolge Start ... Ziel (leer, wenn keine)
    meet: tuple                               # (u, v): die Kante, über die sich die Suchen treffen (u vom Start aus, v vom Ziel aus); bei s == t (s, s)
    order_f: list = field(default_factory=list)        # vorwärts festgelegte Knoten
    order_b: list = field(default_factory=list)        # rückwärts festgelegte Knoten
    steps: list = field(default_factory=list)          # je Festlegung: (Seite "f"/"b", Knoten)
    mu_hist: list = field(default_factory=list)        # beste bisher gefundene Routenlänge nach jeder Festlegung (Index 0 = vor der ersten)
    lower_hist: list = field(default_factory=list)     # untere Schranke top_f + top_b nach jeder Festlegung
    front_hist: list = field(default_factory=list)     # (Größe der Vorwärts-, der Rückwärts-Warteschlange) nach jeder Festlegung
    stopped_by: str = ""                      # "bound" (Schranke >= mu), "meeting" (erste Begegnung), "exhausted" (eine Seite leer), "trivial" (s == t)
    counters: dict = field(default_factory=dict)
    dist_f: np.ndarray = None
    dist_b: np.ndarray = None

    @property
    def settled(self):
        return len(self.order_f) + len(self.order_b)


def bidirectional(g, rg, s, t, stop="correct", alternate="strict", queue="lazy"):
    """Zwei Dijkstra-Suchen: vorwärts von `s` auf `g`, rückwärts von `t` auf `rg` (dem umgedrehten Graphen), abwechselnd.

    Bei jeder Kante (u, v), die eine Seite prüft, ist `d_f(u) + c + d_b(v)` (bzw. umgekehrt) die Länge einer echten Route; das kleinste davon ist mu.
    `stop="correct"`: Abbruch, wenn die beiden kleinsten Schlüssel in den Warteschlangen zusammen mu erreichen - keine noch unentdeckte Route kann kürzer sein.
    `stop="first_meeting"` (Buch-Variante): Abbruch bei der ersten Kante, die zu einem Knoten führt, den die andere Seite schon festgelegt hat - die Route dorthin muss nicht die kürzeste sein.
    `alternate`: "strict" abwechselnd, "smaller_frontier" die Seite mit der kleineren Warteschlange, "min_key" die Seite mit dem kleineren Schlüssel (gleiche Radien)."""
    s, t = int(s), int(t)
    if s == t:
        return Bidirectional(0.0, [s], (s, s), [], [], [], [0.0], [0.0], [(1, 1)], "trivial", {"pushes": 0, "pops": 0, "relaxations": 0}, np.zeros(g.n), np.zeros(g.n))
    sides = (
        (g.indptr.tolist(), g.indices.tolist(), g.weight.tolist()),
        (rg.indptr.tolist(), rg.indices.tolist(), rg.weight.tolist()),
    )
    qs = [QUEUES[queue](g.n, 1), QUEUES[queue](g.n, 1)]
    dist = [[INF] * g.n, [INF] * g.n]
    parent = [[-1] * g.n, [-1] * g.n]
    settled = [[False] * g.n, [False] * g.n]
    orders = [[], []]
    dist[0][s], dist[1][t] = 0.0, 0.0
    qs[0].push_or_decrease(s, 0.0)
    qs[1].push_or_decrease(t, 0.0)
    mu, meet, stopped = INF, None, ""
    steps, mu_hist, lower_hist, front_hist = [], [INF], [0.0], [(1, 1)]
    relaxations, turn = 0, 0
    while True:
        kf, kb = qs[0].peek_key(), qs[1].peek_key()
        if kf == INF or kb == INF:
            stopped = "exhausted"
            break
        if stop == "correct" and kf + kb >= mu:
            stopped = "bound"
            break
        if alternate == "strict":
            side = turn
            turn = 1 - turn
        elif alternate == "smaller_frontier":
            side = 0 if len(qs[0]) <= len(qs[1]) else 1
        else:
            side = 0 if kf <= kb else 1
        other = 1 - side
        d, u = qs[side].pop_min()
        settled[side][u] = True
        orders[side].append(u)
        steps.append(("f" if side == 0 else "b", u))
        ip, ix, w = sides[side]
        collided = False
        for k in range(ip[u], ip[u + 1]):
            v = ix[k]
            relaxations += 1
            nd = d + w[k]
            total = nd + dist[other][v]                      # Länge einer echten Route über die Kante (u, v), wenn die andere Seite v schon beschriftet hat
            if total < mu:
                mu, meet = total, ((u, v) if side == 0 else (v, u))
            if stop == "first_meeting" and (settled[other][v] or dist[other][v] == 0.0):
                collided = True                              # Begegnung: die andere Seite hat v festgelegt (oder v ist deren Wurzel)
                mu, meet = total, ((u, v) if side == 0 else (v, u))
                break
            if nd < dist[side][v] and not settled[side][v]:
                dist[side][v], parent[side][v] = nd, u
                qs[side].push_or_decrease(v, nd)
        mu_hist.append(mu)
        lower_hist.append(qs[0].peek_key() + qs[1].peek_key())
        front_hist.append((len(qs[0]), len(qs[1])))
        if collided:
            stopped = "meeting"
            break
    counters = {"pushes": qs[0].pushes + qs[1].pushes, "pops": qs[0].pops + qs[1].pops, "relaxations": relaxations}
    if not np.isfinite(mu):
        return Bidirectional(INF, [], (-1, -1), orders[0], orders[1], steps, mu_hist, lower_hist, front_hist, stopped, counters, np.array(dist[0]), np.array(dist[1]))
    u, v = meet
    left = [u]
    while parent[0][left[-1]] >= 0:
        left.append(parent[0][left[-1]])
    right = [v]
    while parent[1][right[-1]] >= 0:
        right.append(parent[1][right[-1]])
    route = left[::-1] + right
    return Bidirectional(route_cost(g, route), route, meet, orders[0], orders[1], steps, mu_hist, lower_hist, front_hist, stopped, counters, np.array(dist[0]), np.array(dist[1]))
