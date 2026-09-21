"""Die Netze der Demo: kleines Netz, in dem die erste Begegnung täuscht (eigener Graph), erzeugtes Stadtnetz, erzeugtes Zufallsnetz und Toronto Innenstadt (echte OpenStreetMap-Daten, Autonetz).
Alle Kosten sind ganze Zahlen (Meter, Minuten): Gleichstände sind exakt, Zähler und Kosten plattformfest."""

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

import bd_constants as C
from bd_graph import Graph, from_arcs, reverse_graph

DATA = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class Network:
    key: str
    graph: Graph
    reverse: Graph                 # umgedrehter Graph für die Rückwärtssuche (bei ungerichteten Netzen derselbe Inhalt)
    unit: str                      # Einheit der Kosten
    title: str
    note: str = ""
    side: int = 0                  # Kantenlänge des Rasters (nur erzeugtes Stadtnetz)
    fixed_pair: tuple = ()         # (Start, Ziel) bei Netzen mit fester Aufgabe, sonst leer
    geometric: bool = True         # Lage der Knoten ist eine Karte (Kanten zeichnen), sonst nur Punkte
    split: int = 0                 # Zufallsnetz mit ungleicher Dichte: Knoten unterhalb dieser Nummer sind der dichte Teil


def _net(key, g, unit, title, note, side=0, fixed_pair=(), geometric=True, split=0):
    return Network(key, g, reverse_graph(g), unit, title, note, side, tuple(fixed_pair), geometric, split)


# --- Stadtnetz ---------------------------------------------------------------------------------------------------------------------------

def _primitive_offsets(reach):
    """Verbindungen (dy, dx) auf dem Raster mit Länge <= reach, nur die primitiven (keine Verbindung überspringt einen Knoten, der auf ihr liegt), nur eine Richtung je Paar."""
    r = int(math.floor(reach + 1e-9))
    out = []
    for dy in range(0, r + 1):
        for dx in range(-r, r + 1):
            if (dy == 0 and dx <= 0) or dx * dx + dy * dy > reach * reach + 1e-9 or math.gcd(abs(dx), dy) != 1:
                continue
            out.append((dy, dx))
    return out


def build_city(side, reach, spread, blocked_pct, seed):
    """Gestörtes Raster: Kreuzungen im Abstand SPACING mit Lageabweichung, verbunden mit allen Nachbarn bis zur Reichweite `reach` (in Blocklängen). Kosten einer Straße = ihre Länge in Metern
    mal (1 + spread * Zufall): Ampeln, Steigung, Belag. Ein Teil der Straßen ist gesperrt, das Netz bleibt aber zusammenhängend (Spannbaum bleibt geschützt)."""
    rng = np.random.default_rng([int(seed), 101])
    n = side * side
    ij = np.stack(np.divmod(np.arange(n), side), axis=1)                      # (Zeile, Spalte)
    xy = np.stack([ij[:, 1], ij[:, 0]], axis=1) * C.SPACING + rng.uniform(-C.JITTER, C.JITTER, (n, 2)) * C.SPACING
    pairs = []
    for dy, dx in _primitive_offsets(reach):
        for i in range(side):
            for j in range(side):
                i2, j2 = i + dy, j + dx
                if 0 <= i2 < side and 0 <= j2 < side:
                    pairs.append((i * side + j, i2 * side + j2))
    pairs = np.array(pairs)
    length = np.hypot(*(xy[pairs[:, 0]] - xy[pairs[:, 1]]).T)
    cost = np.maximum(1.0, np.rint(length * (1.0 + spread * rng.random(len(pairs)))))
    order = rng.permutation(len(pairs))
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    in_tree = np.zeros(len(pairs), dtype=bool)
    for k in order:
        a, b = find(pairs[k, 0]), find(pairs[k, 1])
        if a != b:
            parent[a] = b
            in_tree[k] = True
    removable = [k for k in order if not in_tree[k]]
    drop = set(removable[: int(round(len(pairs) * blocked_pct / 100.0))])
    arcs = [(pairs[k, 0], pairs[k, 1], cost[k]) for k in range(len(pairs)) if k not in drop]
    return from_arcs(n, arcs, xy)


def city_network(side, reach, spread, blocked_pct, seed):
    g = build_city(side, reach, spread, blocked_pct, seed)
    return _net("city", g, "m", "Stadtnetz", "Erzeugtes Stadtnetz: Kreuzungen auf einem gestörten Raster; die Reichweite bestimmt, wie weit eine Straße zwischen zwei Kreuzungen reichen darf.", side)


# --- Zufallsnetz -------------------------------------------------------------------------------------------------------------------------

def build_random(n, degree, seed):
    """Zusammenhängender Zufallsgraph: jeder Knoten hängt an einem früheren, dann kommen zufällige Kanten bis zum mittleren Grad `degree`. Ganzzahlige Kosten 1 bis 9.
    Die Kugeln um einen Knoten wachsen hier exponentiell (wenige Schritte bis überall hin), nicht wie die Fläche eines Kreises."""
    rng = np.random.default_rng([int(seed), 707])
    arcs = {(int(rng.integers(0, i)), i): float(rng.integers(1, 10)) for i in range(1, n)}
    target_m = int(round(n * degree / 2))
    while len(arcs) < target_m:
        u, v = (int(x) for x in rng.integers(0, n, 2))
        if u != v and (u, v) not in arcs and (v, u) not in arcs:
            arcs[(u, v)] = float(rng.integers(1, 10))
    xy = rng.random((n, 2)) * 1000.0
    return from_arcs(n, [(u, v, w) for (u, v), w in arcs.items()], xy)


def random_network(n, degree, seed):
    return _net("random", build_random(int(n), float(degree), int(seed)), "Einheiten", "Zufallsnetz",
                "Erzeugter Zufallsgraph: jeder Knoten hat im Mittel dieselbe Zahl Nachbarn, es gibt keine Karte - die Punkte sind zufällig verteilt und die Kanten nicht gezeichnet.", geometric=False)


def build_asymmetric(n, seed, dense_share=0.4, degree_dense=12.0, degree_sparse=2.4, bridges=6):
    """Zwei Zufallsgraphen, verbunden über wenige Brücken: ein dichter Teil (viele Nachbarn) und ein dünner Teil (wenige Nachbarn). Die Kugeln wachsen im dichten Teil viel schneller.
    Ganzzahlige Kosten 1 bis 9. Rückgabe: Graph und Nummer, ab der der dünne Teil beginnt."""
    rng = np.random.default_rng([int(seed), 909])
    n_dense = int(round(n * dense_share))
    arcs = {}

    def block(lo, hi, degree):
        for i in range(lo + 1, hi):
            arcs[(int(rng.integers(lo, i)), i)] = float(rng.integers(1, 10))
        count = hi - lo - 1
        while count < int(round((hi - lo) * degree / 2)):
            u, v = (int(x) for x in rng.integers(lo, hi, 2))
            if u != v and (u, v) not in arcs and (v, u) not in arcs:
                arcs[(u, v)] = float(rng.integers(1, 10))
                count += 1
    block(0, n_dense, degree_dense)
    block(n_dense, n, degree_sparse)
    for _ in range(bridges):
        arcs[(int(rng.integers(0, n_dense)), int(rng.integers(n_dense, n)))] = float(rng.integers(1, 10))
    angle = rng.random(n) * 2 * np.pi
    radius = np.where(np.arange(n) < n_dense, 60.0 * np.sqrt(rng.random(n)), 300.0 + 500.0 * rng.random(n))
    xy = np.stack([np.cos(angle) * radius, np.sin(angle) * radius], axis=1)
    return from_arcs(n, [(u, v, w) for (u, v), w in arcs.items()], xy), n_dense


def asymmetric_network(n, seed):
    g, split = build_asymmetric(int(n), int(seed))
    return _net("asym", g, "Einheiten", "Ungleiche Dichte", "Erzeugtes Netz aus einem dichten Teil (im Mittel 12 Nachbarn, in der Mitte zusammengedrängt) und einem dünnen (2,4 Nachbarn, außen verteilt), verbunden über wenige Brücken; die Kanten sind nicht gezeichnet.",
                geometric=False, split=split)


# --- Toronto Innenstadt ------------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _toronto_payload():
    return json.loads((DATA / "toronto_downtown.json").read_text(encoding="utf-8"))


def toronto_network():
    p = _toronto_payload()
    xy = np.array(p["nodes_xy_m"], dtype=float)
    g = from_arcs(len(xy), [(u, v, max(1.0, round(w))) for u, v, w in p["arcs"]], xy, directed=True)
    return _net("toronto", g, "m", "Toronto Innenstadt", "Befahrbares Straßennetz im 9-km-Umkreis der Toronto City Hall (größte stark zusammenhängende Komponente; Einbahnstraßen sind gerichtete Kanten).")


# --- Kleines Netz, in dem die erste Begegnung täuscht ------------------------------------------------------------------------------------

SMALL_STOPS = [("Depot", 0.0, 1.6), ("Pass", 3.0, 3.2), ("Dorf", 2.0, 0.5), ("Tal", 4.0, 0.5), ("Kunde", 6.0, 1.6), ("Werk", 1.4, 2.8), ("Markt", 3.0, 2.2), ("Fähre", 4.6, 2.6)]
SMALL_LINKS = [("Depot", "Pass", 1), ("Pass", "Kunde", 10), ("Depot", "Dorf", 3), ("Dorf", "Tal", 3), ("Tal", "Kunde", 3), ("Depot", "Werk", 5), ("Werk", "Markt", 5), ("Markt", "Kunde", 6)]


def small_network():
    names = [s[0] for s in SMALL_STOPS]
    idx = {n: i for i, n in enumerate(names)}
    g = from_arcs(len(names), [(idx[a], idx[b], w) for a, b, w in SMALL_LINKS], [(s[1], s[2]) for s in SMALL_STOPS], names)
    return _net("small", g, "Minuten", "Kleines Netz", "Ein eigenes kleines Liefernetz: die Zahl an einer Strecke sind Fahrminuten. Die Suchen treffen sich zuerst auf der teuren Direktstrecke - die erste Begegnung ist hier nicht die schnellste Route.",
                fixed_pair=(idx["Depot"], idx["Kunde"]))


# --- Zusammenbau -------------------------------------------------------------------------------------------------------------------------

def make_network(net, side=C.DEFAULT_SIDE, reach=C.DEFAULT_REACH, spread=C.DEFAULT_SPREAD, blocked=C.DEFAULT_BLOCKED, nodes=C.DEFAULT_NODES, degree=C.DEFAULT_DEGREE, seed=C.DEFAULT_SEED):
    if net == "city":
        return city_network(int(side), float(reach), float(spread), int(blocked), int(seed))
    if net == "random":
        return random_network(int(nodes), float(degree), int(seed))
    if net == "asym":
        return asymmetric_network(int(nodes), int(seed))
    if net == "toronto":
        return toronto_network()
    if net == "small":
        return small_network()
    raise ValueError(net)
