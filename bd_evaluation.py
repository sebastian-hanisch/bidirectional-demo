"""Läufe, Kennzahlen, Verteilung über zufällige Start-Ziel-Paare, Experimente (Netztyp, Abbruchregel, Wechselstrategie, Abstand) und das Urteil für die App."""

import time
from dataclasses import dataclass

import numpy as np

import bd_algorithm as alg
import bd_constants as C
from bd_scenario import make_network


@dataclass(frozen=True)
class Analysis:
    net: object
    s: int
    t: int
    uni: alg.Unidirectional        # einseitiges Dijkstra mit Abbruch beim Ziel (Vergleichsfläche)
    bi: alg.Bidirectional          # beidseitig mit der gewählten Regel und Strategie
    correct: alg.Bidirectional     # beidseitig mit der korrekten Regel (gleich `bi`, wenn diese gewählt ist)
    metrics: dict
    seconds: dict


def pick_pair(net, distance_pct=C.DEFAULT_DISTANCE, seed=C.DEFAULT_SEED):
    """Start und Ziel: bei Netzen mit fester Aufgabe diese; sonst ein Start (Netze mit Karte: nahe bei 30 % Breite und 50 % Höhe, damit die Kreise nicht am Rand abgeschnitten werden; ungleiche Dichte: im
    dichten Teil; sonst zufällig) und als Ziel der Knoten, dessen Entfernung vom Start in der Rangfolge aller erreichbaren Knoten bei `distance_pct` Prozent liegt."""
    if net.fixed_pair:
        return net.fixed_pair
    g = net.graph
    rng = np.random.default_rng([int(seed), 808])
    if net.split:
        s = int(rng.integers(0, net.split))
    elif net.geometric:
        lo, hi = g.xy.min(axis=0), g.xy.max(axis=0)
        s = int(np.argmin(np.hypot(*(g.xy - (lo + (hi - lo) * np.array([0.3, 0.5]))).T)))
    else:
        s = int(rng.integers(0, g.n))
    d = alg.dijkstra(g, s).dist
    reachable = np.where(np.isfinite(d))[0]
    reachable = reachable[reachable != s]
    order = reachable[np.argsort(d[reachable], kind="stable")]
    t = int(order[min(len(order) - 1, int(round(distance_pct / 100.0 * (len(order) - 1))))])
    return s, t


def analyse(net, s, t, stop=C.DEFAULT_STOP, alternate=C.DEFAULT_ALTERNATE, queue="lazy"):
    """Einseitig und beidseitig für ein Paar; bei der Regel "erste Begegnung" zusätzlich die korrekte Suche als Vergleich."""
    g, rg = net.graph, net.reverse
    t0 = time.perf_counter()
    uni = alg.dijkstra(g, s, t, queue)
    t_uni = time.perf_counter() - t0
    t0 = time.perf_counter()
    bi = alg.bidirectional(g, rg, s, t, stop, alternate, queue)
    t_bi = time.perf_counter() - t0
    correct = bi if stop == "correct" else alg.bidirectional(g, rg, s, t, "correct", alternate, queue)
    reachable = uni.found >= 0
    ref = float(uni.dist[t]) if reachable else float("nan")
    settled_uni = len(uni.order)
    metrics = {"reachable": reachable, "n": g.n, "m": g.m, "cost_uni": ref, "cost_bi": bi.cost, "cost_correct": correct.cost,
               "optimal": bool(reachable and abs(bi.cost - ref) < 1e-9), "excess": (bi.cost / ref - 1.0) if reachable and ref > 0 else 0.0,
               "settled_uni": settled_uni, "settled_f": len(bi.order_f), "settled_b": len(bi.order_b), "settled_bi": bi.settled, "settled_correct": correct.settled,
               "speedup": settled_uni / max(bi.settled, 1) if reachable else float("nan"), "stopped_by": bi.stopped_by, "hops": len(bi.route) - 1 if bi.route else 0,
               "pushes_uni": uni.counters["pushes"], "pushes_bi": bi.counters["pushes"]}
    return Analysis(net, s, t, uni, bi, correct, metrics, {"uni": t_uni, "bi": t_bi})


# --- Verteilung über zufällige Start-Ziel-Paare ------------------------------------------------------------------------------------------------

def _draw_pair(net, rng):
    """Zufallspaar: gleichverteilt; bei ungleicher Dichte vom dichten in den dünnen Teil (dort wirkt die Wechselstrategie)."""
    g = net.graph
    if net.split:
        return int(rng.integers(0, net.split)), int(rng.integers(net.split, g.n))
    return tuple(int(x) for x in rng.integers(0, g.n, 2))


def multi_pair_stats(net, configs, pairs=C.PAIRS, seed=0, queue="lazy"):
    """Wie `pair_stats` für mehrere Einstellungen [(Regel, Strategie), ...] auf DENSELBEN zufälligen erreichbaren Paaren (das einseitige Dijkstra läuft je Paar nur einmal).
    Kennzahlen je Einstellung: Beschleunigung (einseitig festgelegte Knoten / beidseitig; Median, 10 %-, 90 %-Quantil, Verhältnis der Summen), Anteil der Paare, in denen beidseitig nicht weniger
    festlegt, Anteil nicht kürzester Routen (nur bei der Regel "erste Begegnung") und mittlerer Aufpreis."""
    g, rg = net.graph, net.reverse
    rng = np.random.default_rng([int(seed), 1001])
    speed = {c: [] for c in configs}
    excess = {c: [] for c in configs}
    settled = {c: [] for c in configs}
    settled_uni = []
    tries = 0
    while len(settled_uni) < pairs and tries < pairs * 20:
        tries += 1
        s, t = _draw_pair(net, rng)
        if s == t:
            continue
        uni = alg.dijkstra(g, s, t, queue)
        if uni.found < 0:
            continue
        settled_uni.append(len(uni.order))
        for c in configs:
            bi = alg.bidirectional(g, rg, s, t, c[0], c[1], queue)
            speed[c].append(len(uni.order) / max(bi.settled, 1))
            excess[c].append(bi.cost / uni.dist[t] - 1.0 if uni.dist[t] > 0 else 0.0)
            settled[c].append(bi.settled)
    nan = float("nan")
    out = {}
    for c in configs:
        sp, ex = np.array(speed[c]), np.array(excess[c])
        if not len(sp):
            out[c] = {"speedup": sp, "excess": ex, "n_pairs": 0, "speedup_median": nan, "speedup_p10": nan, "speedup_p90": nan, "share_worse": nan, "share_wrong": nan, "excess_mean": nan,
                      "excess_wrong": nan, "speedup_total": nan}
            continue
        wrong = ex > 1e-9
        out[c] = {"speedup": sp, "excess": ex, "n_pairs": len(sp), "speedup_median": float(np.median(sp)), "speedup_p10": float(np.quantile(sp, 0.1)), "speedup_p90": float(np.quantile(sp, 0.9)),
                  "share_worse": float((sp < 1.0).mean()), "share_wrong": float(wrong.mean()), "excess_mean": float(ex.mean()), "excess_wrong": float(ex[wrong].mean()) if wrong.any() else 0.0,
                  "speedup_total": float(np.sum(settled_uni) / max(np.sum(settled[c]), 1))}
    return out


def pair_stats(net, stop=C.DEFAULT_STOP, alternate=C.DEFAULT_ALTERNATE, pairs=C.PAIRS, seed=0, queue="lazy"):
    return multi_pair_stats(net, [(stop, alternate)], pairs, seed, queue)[(stop, alternate)]


# --- Experimente -------------------------------------------------------------------------------------------------------------------------------

def _nets_for_seeds(key, seeds, **kw):
    """Feste Netze einmal, erzeugte Netze je Sweep-Datensatz."""
    if key in C.FIXED_NETS:
        return [(make_network(key), sd) for sd in seeds]
    return [(make_network(key, seed=sd, **kw), sd) for sd in seeds]


def net_comparison(keys=("city", "toronto", "random", "asym"), pairs=40, seeds=C.SWEEP_SEEDS):
    """Beschleunigung je Netztyp (korrekte Regel, strikte Abwechslung): Mittel über die Sweep-Datensätze von Median, 10 %- und 90 %-Quantil und dem Anteil der Paare ohne Gewinn."""
    rows = []
    for key in keys:
        st = [pair_stats(net, "correct", "strict", pairs, sd) for net, sd in _nets_for_seeds(key, seeds)]
        rows.append({"net": key, "median": float(np.mean([x["speedup_median"] for x in st])), "p10": float(np.mean([x["speedup_p10"] for x in st])), "p90": float(np.mean([x["speedup_p90"] for x in st])),
                     "share_worse": float(np.mean([x["share_worse"] for x in st])), "n": make_network(key).graph.n})
    return rows


def stop_comparison(keys=("city", "toronto", "random", "asym"), pairs=40, seeds=C.SWEEP_SEEDS):
    """Erste Begegnung gegen korrekte Regel: Anteil der nicht kürzesten Routen, mittlerer Aufpreis (über alle Paare und über die falschen) und die Beschleunigung, die dabei 'gewonnen' wird."""
    rows = []
    first_c, correct_c = ("first_meeting", "strict"), ("correct", "strict")
    for key in keys:
        wrong, ex_all, ex_wrong, sp_first, sp_correct = [], [], [], [], []
        for net, sd in _nets_for_seeds(key, seeds):
            st = multi_pair_stats(net, [first_c, correct_c], pairs, sd)
            wrong.append(st[first_c]["share_wrong"])
            ex_all.append(st[first_c]["excess_mean"])
            ex_wrong.append(st[first_c]["excess_wrong"])
            sp_first.append(st[first_c]["speedup_median"])
            sp_correct.append(st[correct_c]["speedup_median"])
        rows.append({"net": key, "share_wrong": float(np.mean(wrong)), "excess_mean": float(np.mean(ex_all)), "excess_wrong": float(np.mean(ex_wrong)),
                     "speedup_first": float(np.mean(sp_first)), "speedup_correct": float(np.mean(sp_correct))})
    return rows


def alternate_comparison(keys=("city", "toronto", "random", "asym"), pairs=40, seeds=C.SWEEP_SEEDS):
    """Die drei Wechselstrategien (korrekte Regel) auf denselben Paaren: mittlere Beschleunigung (Verhältnis der Summen) und Anteil der Paare ohne Gewinn."""
    rows = []
    configs = [("correct", a) for a in alg.ALTERNATES]
    for key in keys:
        acc = {a: {"total": [], "worse": []} for a in alg.ALTERNATES}
        for net, sd in _nets_for_seeds(key, seeds):
            st = multi_pair_stats(net, configs, pairs, sd)
            for a in alg.ALTERNATES:
                acc[a]["total"].append(st[("correct", a)]["speedup_total"])
                acc[a]["worse"].append(st[("correct", a)]["share_worse"])
        for a in alg.ALTERNATES:
            rows.append({"net": key, "alternate": a, "speedup": float(np.mean(acc[a]["total"])), "share_worse": float(np.mean(acc[a]["worse"]))})
    return rows


def distance_curve(key="city", pcts=(10, 20, 30, 40, 50, 60, 70, 80, 90, 100), sources=3, seeds=C.SWEEP_SEEDS):
    """Beschleunigung gegen die Entfernung Start–Ziel (Rang der Entfernung in Prozent): Median über Startknoten und Sweep-Datensätze. Kurze Wege gewinnen wenig."""
    out = {p: [] for p in pcts}
    for net, sd in _nets_for_seeds(key, seeds):
        for k in range(sources):
            s, _ = pick_pair(net, 50, sd * 10 + k)
            d = alg.dijkstra(net.graph, s).dist
            reach = np.where(np.isfinite(d))[0]
            reach = reach[reach != s]
            order = reach[np.argsort(d[reach], kind="stable")]
            for p in pcts:
                t = int(order[min(len(order) - 1, int(round(p / 100.0 * (len(order) - 1))))])
                uni, bi = alg.dijkstra(net.graph, s, t), alg.bidirectional(net.graph, net.reverse, s, t)
                out[p].append(len(uni.order) / max(bi.settled, 1))
    return [{"pct": p, "speedup": float(np.median(v))} for p, v in out.items()]


# --- Urteil ------------------------------------------------------------------------------------------------------------------------------------

def verdict(a):
    """Code für die App: unreachable / wrong_route / faster / no_gain."""
    m = a.metrics
    if not m["reachable"]:
        return "unreachable"
    if not m["optimal"]:
        return "wrong_route"
    return "faster" if m["speedup"] > 1.05 else "no_gain"
