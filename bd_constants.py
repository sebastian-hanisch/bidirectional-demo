"""Konstanten, Grenzen der Regler und Presets. Die Zahlen in Hilfetexten und Tabellen der App sind in tests/test_claims.py belegt."""

SPACING = 100.0                    # Meter zwischen benachbarten Kreuzungen im erzeugten Stadtnetz
JITTER = 0.25                      # Lageabweichung der Kreuzungen in Blocklängen

NETS = ("small", "city", "toronto", "random", "asym")
NET_LABELS = {
    "small": "🔀 Kleines Netz (erste Begegnung täuscht)",
    "city": "🏙️ Stadtnetz (erzeugt)",
    "toronto": "🍁 Toronto Innenstadt (OpenStreetMap)",
    "random": "🕸️ Zufallsnetz (erzeugt)",
    "asym": "⚖️ Ungleiche Dichte (erzeugt)",
}
FIXED_NETS = ("small", "toronto")   # keine Größenregler; das kleine Netz hat außerdem eine feste Aufgabe
NODE_NETS = ("random", "asym")      # Netze mit Knotenzahl-Regler (das Zufallsnetz zusätzlich mit mittlerem Grad)

SIDE_MIN, SIDE_MAX, DEFAULT_SIDE = 6, 40, 20
REACH_MIN, REACH_MAX, DEFAULT_REACH = 1.0, 3.2, 2.3
SPREAD_MIN, SPREAD_MAX, DEFAULT_SPREAD = 0.0, 3.0, 1.0
BLOCKED_MIN, BLOCKED_MAX, DEFAULT_BLOCKED = 0, 60, 20          # Prozent der Straßen
NODES_MIN, NODES_MAX, DEFAULT_NODES = 200, 5000, 2000
DEGREE_MIN, DEGREE_MAX, DEFAULT_DEGREE = 2.5, 8.0, 4.0
DISTANCE_MIN, DISTANCE_MAX, DEFAULT_DISTANCE = 10, 100, 60     # Prozent: Rang der Entfernung des Ziels vom Start
DEFAULT_SEED = 7
DEFAULT_NET = "small"
DEFAULT_STOP = "correct"
DEFAULT_ALTERNATE = "strict"

STOP_LABELS = {"correct": "korrekt (Schranke ≥ beste Route)", "first_meeting": "erste Begegnung (Buch-Variante)"}
ALTERNATE_LABELS = {"strict": "strikt abwechselnd", "smaller_frontier": "kleinere Front zuerst", "min_key": "kleinerer Schlüssel zuerst"}

SWEEP_SEEDS = tuple(range(100000, 100005))
PAIRS = 100                        # zufällige Start-Ziel-Paare je Netz für die Verteilungen

COLORS = {"forward": "#1f77b4", "backward": "#2ca02c", "route": "#d62728", "uni": "#9e9e9e", "start": "#111111", "goal": "#ff7f0e", "meet": "#9467bd"}

# Jedes Preset setzt alle Regler; nicht zum Netz gehörende Regler sind dort ausgeblendet und werden auf die Standardwerte gesetzt.
_BASE = dict(side=DEFAULT_SIDE, reach=DEFAULT_REACH, spread=DEFAULT_SPREAD, blocked=DEFAULT_BLOCKED, nodes=DEFAULT_NODES, degree=DEFAULT_DEGREE, distance=DEFAULT_DISTANCE,
             stop=DEFAULT_STOP, alternate=DEFAULT_ALTERNATE, seed=DEFAULT_SEED)
PRESETS = {
    "🔀 Kleines Netz": {**_BASE, "net": "small", "stop": "first_meeting"},
    "🏙️ Stadtnetz": {**_BASE, "net": "city"},
    "🍁 Toronto Innenstadt": {**_BASE, "net": "toronto"},
    "🕸️ Zufallsnetz": {**_BASE, "net": "random"},
    "⚖️ Ungleiche Dichte": {**_BASE, "net": "asym"},
}
PRESET_HELP = {
    "🔀 Kleines Netz": "Kleines eigenes Liefernetz mit der Abbruchregel des Buchs (erste Begegnung): die beiden Suchen treffen sich zuerst auf der teuren Direktstrecke und liefern 11 Minuten - die schnellste Route braucht 9. Mit der korrekten Regel ändert sich das.",
    "🏙️ Stadtnetz": "Erzeugtes Stadtnetz (20 × 20 Kreuzungen): für das gezeigte Paar legt die beidseitige Suche 126 statt 241 Knoten fest, im Median über Zufallspaare etwa das 1.7-Fache weniger - Flächenargument: zwei kleine Kreise gegen einen großen.",
    "🍁 Toronto Innenstadt": "Echtes Autonetz der Toronto-Innenstadt (10 153 Kreuzungen, Einbahnstraßen): 3 547 statt 6 093 festgelegte Knoten für das gezeigte Paar, im Median über Zufallspaare das 1.7-Fache weniger - deutlich weniger als der Faktor 2 des Flächenarguments, bei wenigen Paaren sogar kein Gewinn.",
    "🕸️ Zufallsnetz": "Erzeugter Zufallsgraph ohne Karte (2 000 Knoten, im Mittel 4 Nachbarn): die Kugeln wachsen exponentiell, die beidseitige Suche legt für das gezeigte Paar 80 statt 1 201 Knoten fest (15-fach), im Median über Zufallspaare rund das 14-Fache weniger.",
    "⚖️ Ungleiche Dichte": "Dichter Teil (12 Nachbarn) und dünner Teil (2,4 Nachbarn), verbunden über wenige Brücken; Paare vom dichten in den dünnen Teil. Im Mittel über fünf feste Netze gewinnt die beidseitige Suche strikt abwechselnd das 2.0-Fache, mit der Strategie \"kleinere Front zuerst\" das 2.7-Fache (das gezeigte Netz weicht davon ab).",
}
