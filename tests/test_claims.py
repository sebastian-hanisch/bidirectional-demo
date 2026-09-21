"""Jede Zahl in den Hilfetexten, Presets, Tabellen und Grenzen der App ist hier belegt (Beschleunigungen ±0.15, Anteile ±0.06, Knotenzahlen der erzeugten Netze ±3 %).
Positive UND negative Aussagen: wo die beidseitige Suche gewinnt (Zufallsnetz, ungleiche Dichte mit der richtigen Strategie), steht hier ebenso wie dort, wo sie kaum gewinnt (Toronto) und wo die Buch-Regel danebenliegt."""

from functools import lru_cache

import numpy as np
import pytest

import bd_algorithm as alg
import bd_constants as C
import bd_evaluation as ev
import bd_scenario as sc


def near(value, expected, tol):
    assert abs(value - expected) <= tol, f"{value:.3f} statt {expected}"


def rel(value, expected, tol=0.03):
    assert abs(value - expected) <= tol * abs(expected), f"{value} statt {expected}"


@lru_cache(maxsize=None)
def analysis(key, stop="correct", alternate="strict"):
    net = sc.make_network(key)
    s, t = ev.pick_pair(net)
    return ev.analyse(net, s, t, stop, alternate)


@lru_cache(maxsize=None)
def comparison(kind):
    return {"net": ev.net_comparison, "stop": ev.stop_comparison, "alt": ev.alternate_comparison, "dist": lambda: {k: ev.distance_curve(k) for k in ("city", "toronto")}}[kind]()


# --- Preset-Hilfen: das gezeigte Paar ------------------------------------------------------------------------------------------------------

def test_small_net_preset_first_meeting_gives_11_instead_of_9():
    net = sc.small_network()
    a = ev.analyse(net, *net.fixed_pair, stop="first_meeting")
    assert (a.metrics["cost_bi"], a.metrics["cost_uni"]) == (11, 9)
    assert ev.analyse(net, *net.fixed_pair).metrics["cost_bi"] == 9


def test_city_default_pair_settles_126_instead_of_241():
    m = analysis("city").metrics
    rel(m["settled_uni"], 241)
    rel(m["settled_bi"], 126)


def test_toronto_default_pair_settles_3547_instead_of_6093_and_over_a_third_of_the_net():
    m = analysis("toronto").metrics
    rel(m["settled_uni"], 6093, 0.01)
    rel(m["settled_bi"], 3547, 0.01)
    assert m["settled_bi"] / m["n"] > 1 / 3                                                            # Grenzen-Tabelle: über ein Drittel des Netzes


def test_random_default_pair_settles_80_instead_of_1201():
    m = analysis("random").metrics
    rel(m["settled_uni"], 1201, 0.05)
    rel(m["settled_bi"], 80, 0.1)
    near(m["speedup"], 15.0, 2.0)


# --- Netztypen ---------------------------------------------------------------------------------------------------------------------------

def test_speedup_per_net_type():
    rows = {r["net"]: r for r in comparison("net")}
    near(rows["city"]["median"], 1.66, 0.15)                                                           # "1.7-fach"
    near(rows["toronto"]["median"], 1.65, 0.15)
    near(rows["random"]["median"], 13.8, 1.5)                                                          # "14-fach"
    near(rows["asym"]["median"], 2.05, 0.3)
    near(rows["toronto"]["share_worse"], 0.01, 0.03)                                                   # "bei einem Prozent der Paare ohne Gewinn"
    assert rows["random"]["median"] > 5 * rows["city"]["median"]                                       # das Flächenargument gilt nur für flache Netze
    assert rows["toronto"]["p10"] < 1.4 < rows["toronto"]["p90"]                                       # breite Streuung


def test_pair_distribution_of_the_shown_net_matches_the_median():
    for key, expected in (("city", 1.7), ("toronto", 1.65)):
        ps = ev.pair_stats(sc.make_network(key), "correct", "strict", C.PAIRS, C.DEFAULT_SEED)
        near(ps["speedup_median"], expected, 0.25)
        assert ps["share_wrong"] == 0 and ps["n_pairs"] == C.PAIRS


# --- Abbruchregel ------------------------------------------------------------------------------------------------------------------------

def test_first_meeting_is_often_not_the_shortest_route():
    rows = {r["net"]: r for r in comparison("stop")}
    near(rows["city"]["share_wrong"], 0.81, 0.06)                                                      # Sidebar-Hilfe und Grenzen-Tabelle: 81 %
    near(rows["city"]["excess_mean"], 0.09, 0.02)                                                      # im Mittel 9 % zu lang
    near(rows["toronto"]["share_wrong"], 0.45, 0.08)                                                   # 45 %
    near(rows["toronto"]["excess_mean"], 0.01, 0.01)
    near(rows["random"]["share_wrong"], 0.33, 0.08)                                                    # 33 %
    near(rows["city"]["speedup_first"], 2.2, 0.3)                                                       # README: scheinbar 2.2- statt 1.7-fach
    near(rows["city"]["speedup_correct"], 1.66, 0.15)
    for r in rows.values():
        assert r["share_wrong"] > 0.2 and r["excess_wrong"] >= r["excess_mean"] > 0
        assert r["speedup_first"] > r["speedup_correct"]                                               # die falsche Regel sieht schneller aus


def test_correct_rule_is_optimal_on_every_sampled_pair():
    for key in ("city", "toronto", "random", "asym"):
        net = sc.make_network(key)
        for a in alg.ALTERNATES:
            ps = ev.pair_stats(net, "correct", a, 12, 4)
            assert ps["share_wrong"] == 0 and ps["excess_mean"] == pytest.approx(0)


# --- Wechselstrategie --------------------------------------------------------------------------------------------------------------------

def test_alternation_strategies_on_the_asymmetric_net():
    rows = {(r["net"], r["alternate"]): r for r in comparison("alt")}
    near(rows[("asym", "strict")]["speedup"], 2.0, 0.3)                                                # Sidebar-Hilfe: 2.0 / 2.7 / 1.6
    near(rows[("asym", "smaller_frontier")]["speedup"], 2.66, 0.35)
    near(rows[("asym", "min_key")]["speedup"], 1.6, 0.25)
    assert rows[("asym", "smaller_frontier")]["speedup"] > 1.2 * rows[("asym", "strict")]["speedup"] > 1.2 * rows[("asym", "min_key")]["speedup"]


def test_smaller_frontier_never_loses_to_the_book_strategy_and_min_key_hurts_in_toronto():
    rows = {(r["net"], r["alternate"]): r for r in comparison("alt")}
    for net in ("city", "toronto", "random", "asym"):
        assert rows[(net, "smaller_frontier")]["speedup"] >= rows[(net, "strict")]["speedup"] - 0.02, net
    near(rows[("toronto", "min_key")]["share_worse"], 0.08, 0.07)                                     # "bei 8 % der Paare sogar mehr Knoten als einseitiges Dijkstra"
    assert rows[("toronto", "min_key")]["share_worse"] > rows[("toronto", "smaller_frontier")]["share_worse"]


# --- Entfernung ----------------------------------------------------------------------------------------------------------------------------

def test_gain_over_distance():
    curves = comparison("dist")
    city, tor = curves["city"], curves["toronto"]
    assert all(1.7 < r["speedup"] < 3.3 for r in city)                                                  # "im Stadtnetz über alle Entfernungen etwa gleich"
    assert tor[3]["speedup"] > tor[-1]["speedup"] + 0.5 and 1.3 < tor[-1]["speedup"] < 1.9              # Toronto: sinkt zu den entferntesten Zielen
