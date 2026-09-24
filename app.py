"""Bidirektionale Suche - von beiden Enden gleichzeitig - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EIN Verfahren - die bidirektionale Dijkstra-Suche - und lässt stattdessen das Beispiel wachsen.
Drittes Stück der Kürzeste-Wege-Linie der "Konzepte"-Reihe, Fortsetzung der Dijkstra-Demo: sie war blind in alle Richtungen, hier wachsen zwei kleine Kreise von beiden Enden - und die Frage, wann man aufhören darf.
Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import time

import numpy as np
import streamlit as st

import bd_constants as C
import bd_evaluation as ev
from bd_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    seed_widget,
    sync_query_params,
)
from bd_scenario import make_network
from bd_visualization import build_alternate, build_bounds, build_distance, build_net_comparison, build_network, build_speedup_hist, build_stop_comparison

st.set_page_config(page_title="Bidirektionale Suche – Sebastian Hanisch", layout="wide")


def _pct(x):
    return "–" if x is None or np.isnan(x) else f"{x:.0%}"


def _cost(net, x):
    return f"{x:,.0f} {net.unit}".replace(",", ".")


def _g(x):
    return "∞" if not np.isfinite(x) else f"{x:g}"


def _num(x):
    return f"{x:,}".replace(",", ".")


@st.cache_resource(show_spinner=False, max_entries=8)
def _network(params):
    return make_network(*params)


@st.cache_resource(show_spinner=False, max_entries=16)
def _analysis(params, distance, stop, alternate):
    net = _network(params)
    s, t = ev.pick_pair(net, distance, params[-1])
    return ev.analyse(net, s, t, stop, alternate)


@st.cache_data(show_spinner=False)
def _pair_stats(params, stop, alternate, pairs):
    return ev.pair_stats(_network(params), stop, alternate, pairs, params[-1])


@st.cache_data(show_spinner=False)
def _net_comparison():
    return ev.net_comparison()


@st.cache_data(show_spinner=False)
def _stop_comparison():
    return ev.stop_comparison()


@st.cache_data(show_spinner=False)
def _alternate_comparison():
    return ev.alternate_comparison()


@st.cache_data(show_spinner=False)
def _distance_curves():
    return {"city": ev.distance_curve("city"), "toronto": ev.distance_curve("toronto")}


st.title("🔀 Bidirektionale Suche – von beiden Enden gleichzeitig")
st.markdown(
    """
Dijkstra legt alles fest, was näher am Start liegt als das Ziel - ein Kreis, dessen Fläche mit dem Quadrat der Entfernung wächst. Die **bidirektionale Suche** startet zusätzlich **am Ziel** und läuft von dort rückwärts über die umgedrehten Kanten;
sobald sich beide Suchen treffen, steht die Route. Statt eines Kreises mit Radius $R$ wachsen zwei mit Radius $R/2$ - in der Ebene die halbe Fläche. Der Haken ist die Frage, **wann man aufhören darf**:
die erste Begegnung der beiden Suchen ist nicht immer die kürzeste Route. Diese Demo zeigt den Gewinn, wo er sich lohnt (und wo kaum), und misst, wie oft die einfache Abbruchregel danebenliegt.
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - drittes Stück der Kürzeste-Wege-Linie der \"Konzepte\"-Reihe, Fortsetzung der Dijkstra-Demo - **ein** Verfahren an einem wachsenden Beispiel. "
    "Die Schwächen der bidirektionalen Suche sind die Ansatzpunkte der nächsten Stücke: jede Anfrage beginnt von vorn (**Contraction Hierarchies** rechnen vor), und die Suche kennt die Richtung des Ziels nicht (**A\\***, bidirektionales A\\* in der Baumsuche-Linie). "
    "Das Verfahren folgt dem Algorithmus 3.5 in *Optimization Algorithms* (A. Khamis, Kap. 3.4.3), dessen Pseudocode bei der ersten Begegnung abbricht - beide Regeln laufen hier nebeneinander. Die Netze sind eigene Graphen und OpenStreetMap-Daten."
)

with st.expander("So funktioniert die bidirektionale Suche", expanded=True):
    st.markdown(
        """
1. **Zwei Suchen:** vorwärts vom Start über die Kanten, rückwärts vom Ziel über die **umgedrehten** Kanten (bei Einbahnstraßen zählt die Richtung). Beide sind gewöhnliches Dijkstra mit eigener Warteschlange; sie legen **abwechselnd** je einen Knoten fest.
2. **Beste Route μ:** prüft eine Suche eine Kante zu einem Knoten, den die andere Seite schon beschriftet hat, ergibt Entfernung vorwärts + Kante + Entfernung rückwärts die Länge einer echten Route. Das kleinste davon ist μ.
3. **Aufhören - die erste Begegnung reicht nicht:** ein Knoten, den beide Seiten erreichen, liegt nicht zwingend auf der kürzesten Route. Sicher ist erst: **kleinster Schlüssel vorwärts + kleinster Schlüssel rückwärts ≥ μ** - dann kann keine noch unentdeckte Route kürzer sein.
4. **Route:** vorwärts von der Treffer-Kante zurück zum Start, rückwärts weiter zum Ziel.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielnetz laden:")
preset_cols = st.columns(len(C.PRESETS))
for i, name in enumerate(C.PRESETS.keys()):
    with preset_cols[i]:
        st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox(
        "Netz", C.NETS, key="net_select", format_func=lambda k: C.NET_LABELS[k],
        help="Klein und fest (kleines Netz mit fester Aufgabe), erzeugt (Stadtnetz, Zufallsnetz, ungleiche Dichte) oder echtes Autonetz der Toronto-Innenstadt (OpenStreetMap, 10 153 Kreuzungen, 26 985 gerichtete Kanten). "
             "Alle Kosten sind ganze Zahlen.",
    )
    if net_key == "city":
        seed_widget("side_slider")
        side = st.slider("Kreuzungen je Seite", *bounds("side_slider"), key="side_slider", help="Größe des Stadtnetzes (Seite × Seite).")
        st.session_state[KEPT["side_slider"]] = side
        seed_widget("reach_slider")
        reach = st.slider("Reichweite der Straßen [Blocklängen]", *bounds("reach_slider"), key="reach_slider", step=0.1,
                          help="Wie weit eine Straße zwischen zwei Kreuzungen reichen darf (1 = nur Nachbarn im Raster, größer = auch längere Verbindungen).")
        st.session_state[KEPT["reach_slider"]] = reach
        seed_widget("spread_slider")
        spread = st.slider("Streuung der Kosten", *bounds("spread_slider"), key="spread_slider", step=0.25, help="Kosten einer Straße = Länge × (1 + Streuung × Zufall), gerundet auf ganze Meter.")
        st.session_state[KEPT["spread_slider"]] = spread
        seed_widget("blocked_slider")
        blocked = st.slider("Gesperrte Straßen [%]", *bounds("blocked_slider"), key="blocked_slider", help="Anteil der gesperrten Straßen (das Netz bleibt zusammenhängend).")
        st.session_state[KEPT["blocked_slider"]] = blocked
    else:
        side = int(st.session_state.get(KEPT["side_slider"], C.DEFAULT_SIDE))
        reach = float(st.session_state.get(KEPT["reach_slider"], C.DEFAULT_REACH))
        spread = float(st.session_state.get(KEPT["spread_slider"], C.DEFAULT_SPREAD))
        blocked = int(st.session_state.get(KEPT["blocked_slider"], C.DEFAULT_BLOCKED))
    if net_key in C.NODE_NETS:
        seed_widget("nodes_slider")
        nodes = st.slider("Knoten", *bounds("nodes_slider"), key="nodes_slider", step=100, help="Anzahl der Knoten des Zufallsnetzes.")
        st.session_state[KEPT["nodes_slider"]] = nodes
    else:
        nodes = int(st.session_state.get(KEPT["nodes_slider"], C.DEFAULT_NODES))
    if net_key == "random":
        seed_widget("degree_slider")
        degree = st.slider("Mittlerer Grad", *bounds("degree_slider"), key="degree_slider", step=0.5, help="Wie viele Nachbarn ein Knoten im Mittel hat. Mit mehr Nachbarn wachsen die Kugeln schneller.")
        st.session_state[KEPT["degree_slider"]] = degree
    else:
        degree = float(st.session_state.get(KEPT["degree_slider"], C.DEFAULT_DEGREE))
    if net_key != "small":
        seed_widget("distance_slider")
        distance = st.slider("Entfernung Start–Ziel [%]", *bounds("distance_slider"), key="distance_slider",
                             help="Welcher Knoten das Ziel ist: der, dessen Entfernung vom Start in der Rangfolge aller erreichbaren Knoten bei diesem Prozentwert liegt (100 = der am weitesten entfernte).")
        st.session_state[KEPT["distance_slider"]] = distance
    else:
        distance = int(st.session_state.get(KEPT["distance_slider"], C.DEFAULT_DISTANCE))
    stop = st.selectbox("Abbruchregel", list(C.STOP_LABELS), key="stop_select", format_func=lambda k: C.STOP_LABELS[k],
                        help="Korrekt: aufhören, wenn kleinster Schlüssel vorwärts + rückwärts ≥ beste gefundene Route μ. Erste Begegnung: aufhören, sobald eine Suche einen Knoten erreicht, den die andere schon festgelegt hat (so steht es im Pseudocode des Buchs). "
                             "Über Zufallspaare ist die Route bei der ersten Begegnung im Stadtnetz in 81 % der Fälle nicht die kürzeste (im Mittel 9 % zu lang), in Toronto in 45 % (im Mittel 1 %).")
    alternate = st.selectbox("Wechselstrategie", list(C.ALTERNATE_LABELS), key="alternate_select", format_func=lambda k: C.ALTERNATE_LABELS[k],
                             help="Welche Suche als Nächstes einen Knoten festlegt: strikt abwechselnd (Buch), die mit der kleineren Warteschlange, oder die mit dem kleineren Schlüssel (gleiche Radien). "
                                  "Bei ungleicher Dichte gewinnt die beidseitige Suche (Mittel über fünf feste Netze) strikt abwechselnd das 2.0-Fache, mit der kleineren Front zuerst das 2.7-Fache, mit gleichen Radien nur das 1.6-Fache.")
    if net_key in ("city", "random", "asym"):
        seed_widget("seed_input")
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Zufalls-Seed für das Netz.")
    else:
        seed = int(st.session_state.get(KEPT["seed_input"], C.DEFAULT_SEED))
        st.caption("Dieses Netz ist fest - es gibt nichts zu erzeugen.")

sync_query_params({"net_select": net_key, "side_slider": int(side), "reach_slider": round(float(reach), 1), "spread_slider": round(float(spread), 2), "blocked_slider": int(blocked),
                   "nodes_slider": int(nodes), "degree_slider": round(float(degree), 1), "distance_slider": int(distance), "stop_select": stop, "alternate_select": alternate, "seed_input": int(seed)})

# nicht zum Netz gehörende Regler ändern das Netz nicht: sonst würden gleiche Netze unter verschiedenen Schlüsseln mehrfach berechnet
if net_key in C.FIXED_NETS:
    params = (net_key, C.DEFAULT_SIDE, C.DEFAULT_REACH, C.DEFAULT_SPREAD, C.DEFAULT_BLOCKED, C.DEFAULT_NODES, C.DEFAULT_DEGREE, C.DEFAULT_SEED)
elif net_key == "city":
    params = (net_key, int(side), round(float(reach), 1), round(float(spread), 2), int(blocked), C.DEFAULT_NODES, C.DEFAULT_DEGREE, int(seed))
elif net_key == "random":
    params = (net_key, C.DEFAULT_SIDE, C.DEFAULT_REACH, C.DEFAULT_SPREAD, C.DEFAULT_BLOCKED, int(nodes), round(float(degree), 1), int(seed))
else:
    params = (net_key, C.DEFAULT_SIDE, C.DEFAULT_REACH, C.DEFAULT_SPREAD, C.DEFAULT_BLOCKED, int(nodes), C.DEFAULT_DEGREE, int(seed))
distance_used = C.DEFAULT_DISTANCE if net_key == "small" else int(distance)
with st.spinner("Rechne..."):
    a = _analysis(params, distance_used, stop, alternate)
net, bi, uni, m = a.net, a.bi, a.uni, a.metrics
g = net.graph
view_key = (params, distance_used, stop, alternate)

# --- Bidirektionale Suche in Aktion ----------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Bidirektionale Suche in Aktion")
last_step = len(bi.steps)
if st.session_state.get("bd_step_owner") != view_key:
    st.session_state["bd_step"] = last_step
    st.session_state["bd_step_owner"] = view_key
step_col, play_col = st.columns([5, 2])
with step_col:
    if last_step > 1:
        step = st.slider("Festlegungen (abwechselnd vorwärts und rückwärts)", 0, last_step, key="bd_step",
                         help="Wie viele Knoten die beiden Suchen zusammen schon festgelegt haben: 0 = nur Start und Ziel, ganz rechts = die Suche ist beendet und die Route erscheint.")
    else:
        step = last_step
        st.caption("Start und Ziel sind derselbe Knoten - es gibt keine Festlegung.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch")
show_uni = st.checkbox("Fläche der einseitigen Suche einblenden (grau)", key="show_uni",
                       help="Grau: alle Knoten, die einseitiges Dijkstra bis zum Ziel festgelegt hätte - ein großer Kreis gegen die zwei kleinen der beidseitigen Suche.")
view_slot = st.empty()


def _render(current):
    with view_slot.container():
        c1, c2 = st.columns([3, 2])
        c1.plotly_chart(build_network(net, a, current, show_uni), width="stretch", key=f"net_chart_{current}")
        c2.markdown("**Abbruchregel: beste Route μ gegen untere Schranke**")
        c2.plotly_chart(build_bounds(bi, current), width="stretch", key=f"bounds_chart_{current}")
        c2.caption(f"Nach {current} von {last_step} Festlegungen. Gestoppt wird ({'sobald die Schranke μ erreicht' if bi.stopped_by == 'bound' else 'bei der ersten Begegnung' if bi.stopped_by == 'meeting' else 'weil eine Suche nichts mehr zu tun hat'}): "
                   f"μ = {_g(bi.mu_hist[min(current, last_step)])}, Schranke = {_g(bi.lower_hist[min(current, last_step)])}.")


if auto_play:
    n_frames = min(max(last_step, 1), 60)
    for k in sorted({int(round(x)) for x in np.linspace(0, last_step, n_frames + 1)}):
        _render(k)
        time.sleep(min(0.6, 6.0 / n_frames))
    step = last_step
else:
    _render(step)

st.caption(net.note + (" Karte: © [OpenStreetMap-Mitwirkende](https://www.openstreetmap.org/copyright), Daten unter der [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/)." if net.key == "toronto" else ""))

st.markdown("---")

# --- Zwei kleine Kreise statt einem großen ------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Zwei kleine Kreise statt einem großen")
st.caption(
    "**Beschleunigung** = Knoten, die einseitiges Dijkstra bis zum Ziel festlegt, geteilt durch die der beidseitigen Suche (vorwärts + rückwärts). Die Zahl der festgelegten Knoten ist der Aufwand der Suche und plattformfest; Laufzeiten stehen unten im Vergleich."
)
if not m["reachable"]:
    st.warning("⚠️ Das Ziel ist vom Start aus nicht erreichbar - beide Verfahren melden das ausdrücklich, statt eine Route zu erfinden.")
else:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Kosten der beidseitigen Suche", _cost(net, m["cost_bi"]), delta=("gleich Dijkstra" if m["optimal"] else f"{_cost(net, m['cost_bi'] - m['cost_uni'])} mehr als Dijkstra ({m['excess']:+.0%})"), delta_color="off",
              help=f"Kosten der Route des einseitigen Dijkstra: {_cost(net, m['cost_uni'])}.")
    m2.metric("Festgelegte Knoten", _num(m["settled_bi"]), delta=f"vorwärts {_num(m['settled_f'])} · rückwärts {_num(m['settled_b'])}", delta_color="off",
              help="Beide Suchen zusammen; bei strikter Abwechslung sind es fast gleich viele je Seite.")
    m3.metric("Einseitig festgelegt", _num(m["settled_uni"]), delta=f"{_pct(m['settled_uni'] / m['n'])} des Netzes", delta_color="off", help=f"Von {_num(m['n'])} Knoten.")
    m4.metric("Beschleunigung", f"{m['speedup']:.1f}×", delta=f"{m['hops']} Kanten lang", delta_color="off", help="Einseitig festgelegte Knoten geteilt durch beidseitig festgelegte.")
    code = ev.verdict(a)
    if code == "wrong_route":
        st.warning(f"⚠️ Bei der Regel \"erste Begegnung\" ist die Route nicht die kürzeste: {_cost(net, m['cost_bi'])} statt {_cost(net, m['cost_uni'])} ({m['excess']:+.0%}). Die Suchen haben sich bei {m['settled_bi']} festgelegten Knoten getroffen, die korrekte Regel "
                   f"hätte weitergesucht ({m['settled_correct']} festgelegte Knoten) und {_cost(net, m['cost_correct'])} gefunden. Das \"gesparte\" Stück ist keine Beschleunigung, sondern eine falsche Antwort.")
    elif code == "faster":
        st.success(f"✅ Dieselben Kosten wie Dijkstra ({_cost(net, m['cost_bi'])}), aber nur {_num(m['settled_bi'])} statt {_num(m['settled_uni'])} festgelegte Knoten - **{m['speedup']:.1f}-fach weniger** "
                   f"(vorwärts {_num(m['settled_f'])}, rückwärts {_num(m['settled_b'])}).")
    else:
        st.info(f"ℹ️ Kein Gewinn für dieses Paar: die beidseitige Suche legt {_num(m['settled_bi'])} Knoten fest, einseitiges Dijkstra {_num(m['settled_uni'])}.")

    st.markdown("**Nicht nur dieses eine Paar**")
    ps = _pair_stats(params, stop, alternate, C.PAIRS)
    if ps["n_pairs"]:
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Beschleunigung (Median)", f"{ps['speedup_median']:.1f}×", delta=f"10 %–90 %: {ps['speedup_p10']:.1f}×–{ps['speedup_p90']:.1f}×", delta_color="off",
                  help=f"Über {ps['n_pairs']} zufällige erreichbare Paare (bei ungleicher Dichte: vom dichten in den dünnen Teil).")
        p2.metric("Paare ohne Gewinn", _pct(ps["share_worse"]), help="Anteil der Paare, in denen die beidseitige Suche nicht weniger Knoten festlegt als einseitiges Dijkstra.")
        p3.metric("Nicht kürzeste Routen", _pct(ps["share_wrong"]), delta=f"im Mittel {ps['excess_mean']:+.1%}" if stop == "first_meeting" else "korrekte Regel", delta_color="off",
                  help="Bei der Regel \"erste Begegnung\" der Anteil der Paare, in denen die Route länger als die kürzeste ist; bei der korrekten Regel immer 0.")
        p4.metric("Gesamtgewinn", f"{ps['speedup_total']:.1f}×", help="Summe der einseitig festgelegten Knoten geteilt durch die Summe der beidseitig festgelegten über alle Paare (Gesamtaufwand).")
        st.plotly_chart(build_speedup_hist(ps["speedup"]), width="stretch", key="speedup_hist")
        st.caption(f"{ps['n_pairs']} zufällige Start-Ziel-Paare im gewählten Netz. Der Gewinn streut stark: weit weniger als der Faktor 2 des Flächenarguments ist möglich, bei manchen Paaren gibt es keinen.")

st.markdown("---")

# --- Vergleich -----------------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – einseitig und beidseitig im Vergleich"):
    if m["reachable"]:
        st.table({"Verfahren": ["Dijkstra (einseitig)", "bidirektional (vorwärts)", "bidirektional (rückwärts)", "bidirektional (zusammen)"],
                  "Festgelegte Knoten": [_num(m["settled_uni"]), _num(m["settled_f"]), _num(m["settled_b"]), _num(m["settled_bi"])],
                  "Laufzeit [ms]": [f"{a.seconds['uni'] * 1000:.1f}", "–", "–", f"{a.seconds['bi'] * 1000:.1f}"]})
    st.caption("Die beidseitige Suche führt zwei Warteschlangen und einen umgedrehten Graphen mit: je Knoten mehr Arbeit. Weniger festgelegte Knoten heißen deshalb nicht automatisch weniger Rechenzeit - die Laufzeiten sind Messwerte dieses Laufs "
               "(reines Python, ein Lauf) und schwanken.")

st.markdown("---")

# --- Experimente ---------------------------------------------------------------------------------------------------------------------------

st.subheader("📐 Wann lohnt sich das? Der Gewinn je Netztyp")
if st.button("Stadtnetz, Toronto, Zufallsnetz und ungleiche Dichte vergleichen (dauert einige Sekunden)", key="netcmp_start"):
    st.session_state["netcmp_on"] = True
if st.session_state.get("netcmp_on"):
    with st.spinner("Vergleiche vier Netztypen × 5 Datensätze × 40 Paare..."):
        ncr = _net_comparison()
    st.plotly_chart(build_net_comparison(ncr), width="stretch", key="netcmp_chart")
    by = {r["net"]: r for r in ncr}
    st.caption(f"Median über 40 zufällige Paare je Datensatz, Mittel über 5 feste Datensätze (Toronto: ein festes Netz, 5 Paar-Datensätze); Balken 10 %–90 %. Im flachen Stadtnetz ({by['city']['median']:.1f}×) und im echten Toronto-Netz ({by['toronto']['median']:.1f}×) "
               f"liegt der Gewinn nahe beim Faktor 2 des Flächenarguments, in Toronto mit breiter Streuung und bei {_pct(by['toronto']['share_worse'])} der Paare ohne Gewinn. Im **Zufallsnetz** ({by['random']['median']:.1f}×) wachsen die Kugeln exponentiell - "
               "zwei Kugeln mit halber Tiefe sind dort unvergleichlich kleiner als eine mit voller: das Flächenargument ist eine Aussage über flache Netze.")

st.markdown("---")

st.subheader("🔬 Die erste Begegnung: wie oft liegt sie daneben?")
if st.button("Erste Begegnung gegen korrekte Regel vergleichen (dauert etwa 10 Sekunden)", key="stop_start"):
    st.session_state["stop_on"] = True
if st.session_state.get("stop_on"):
    with st.spinner("Vergleiche beide Regeln auf vier Netztypen × 5 Datensätze × 40 Paare..."):
        scr = _stop_comparison()
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(build_stop_comparison(scr), width="stretch", key="stop_chart")
    c2.table({"Netz": [{"city": "Stadtnetz", "toronto": "Toronto", "random": "Zufallsnetz", "asym": "Ungleiche Dichte"}[r["net"]] for r in scr],
              "Aufpreis (Mittel)": [f"{r['excess_mean']:+.1%}" for r in scr], "Aufpreis (wenn falsch)": [f"{r['excess_wrong']:+.1%}" for r in scr],
              "scheinbarer Gewinn": [f"{r['speedup_first']:.1f}× statt {r['speedup_correct']:.1f}×" for r in scr]})
    st.caption("Je Netztyp und Datensatz 40 zufällige Paare, strikt abwechselnd. Die Regel der ersten Begegnung liefert in einem großen Teil der Fälle eine Route, die länger als die kürzeste ist - und sieht dabei schneller aus (Spalte rechts), weil sie früher aufhört. "
               "Der Aufpreis ist im Mittel klein, im Einzelfall aber nicht: die Regel gibt keine Garantie. Die korrekte Regel kostet ein paar festgelegte Knoten mehr und ist immer optimal.")

st.markdown("---")

st.subheader("🔬 Welche Suche zuerst? Die drei Wechselstrategien")
if st.button("Strikt abwechselnd, kleinere Front und gleiche Radien vergleichen (dauert etwa 15 Sekunden)", key="alt_start"):
    st.session_state["alt_on"] = True
if st.session_state.get("alt_on"):
    with st.spinner("Vergleiche drei Strategien auf vier Netztypen × 5 Datensätze × 40 Paare..."):
        arows = _alternate_comparison()
    st.plotly_chart(build_alternate(arows), width="stretch", key="alt_chart")
    asym = {r["alternate"]: r["speedup"] for r in arows if r["net"] == "asym"}
    tor = {r["alternate"]: r for r in arows if r["net"] == "toronto"}
    st.caption(f"Alle drei liefern dieselben Kosten; sie unterscheiden sich im Aufwand. In flachen, gleichmäßigen Netzen sind die Unterschiede klein. Bei **ungleicher Dichte** legt \"kleinere Front zuerst\" die Arbeit dorthin, wo es billig ist: {asym['smaller_frontier']:.1f}-fach gegen {asym['strict']:.1f}-fach strikt; "
               f"\"gleiche Radien\" ist mit {asym['min_key']:.1f}-fach am schlechtesten. In Toronto legt \"gleiche Radien\" bei {_pct(tor['min_key']['share_worse'])} der Paare sogar mehr Knoten fest als einseitiges Dijkstra. Keine Strategie gewinnt überall - "
               "aber \"kleinere Front zuerst\" verliert hier nirgends gegen die Buch-Variante.")

st.markdown("---")

st.subheader("🔬 Kurze und lange Wege: hängt der Gewinn von der Entfernung ab?")
if st.button("Gewinn gegen Entfernung Start–Ziel (dauert wenige Sekunden)", key="dist_start"):
    st.session_state["dist_on"] = True
if st.session_state.get("dist_on"):
    with st.spinner("Messe zehn Entfernungen in Stadtnetz und Toronto..."):
        dc = _distance_curves()
    st.plotly_chart(build_distance(dc), width="stretch", key="dist_chart")
    tor = dc["toronto"]
    st.caption(f"Median über 3 Startknoten × 5 Datensätze je Entfernung (Rang der Entfernung des Ziels unter allen erreichbaren Knoten). Im Stadtnetz ist der Gewinn über alle Entfernungen etwa gleich. Im echten Toronto-Netz sinkt er von {tor[3]['speedup']:.1f}× bei mittleren Entfernungen "
               f"auf {tor[-1]['speedup']:.1f}× bei den entferntesten Zielen (am Rand des Netzes).")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Zwei kleine Kreise sind viel kleiner als ein großer** | Nur im Zufallsnetz (exponentielles Wachstum, 14-fach). In der Ebene bleibt es beim Flächenargument, im Stadtnetz 1.7-fach, im echten Toronto-Netz ebenfalls 1.7-fach - bei einem Prozent der Paare ohne Gewinn. | (kein Nachfolger: das ist die Natur flacher Netze) |
| **Die erste Begegnung genügt** | Im Stadtnetz ist die Route bei der ersten Begegnung in 81 % der Zufallspaare nicht die kürzeste (im Mittel 9 % zu lang), in Toronto in 45 %, im Zufallsnetz in 33 %. Korrekt ist erst: Schranke ≥ beste Route. | die korrekte Abbruchregel (diese Demo) |
| **Die Suche kennt kein Ziel** | Beide Suchen laufen weiter in alle Richtungen: im Toronto-Netz legt sie für das gezeigte Paar 3 547 Knoten fest, über ein Drittel des Netzes. | **A\\*** und bidirektionales A\\* (Baumsuche-Linie) |
| **Jede Anfrage beginnt von vorn** | Auch beidseitig kostet jede Anfrage tausende festgelegte Knoten; nichts wird für die nächste Anfrage aufgehoben. | **Contraction Hierarchies**: erst vorrechnen, dann blitzschnell fragen |
| **Ein Rückwärtsgraph und zwei Warteschlangen sind billig** | Der umgedrehte Graph verdoppelt den Speicher, jede Festlegung ist teurer: in reinem Python ist die beidseitige Suche trotz weniger Knoten nicht schneller (Laufzeiten im Vergleich oben). | |
"""
)
st.caption("Die Nachbarn der Kürzeste-Wege-Linie (noch nicht gebaut): Contraction Hierarchies, Bellman-Ford, Floyd-Warshall, Johnson und Mehrkriterien-Routing. Bereits gebaut: die Breitensuche-Demo und die Dijkstra-Demo. A\\* steht in der Baumsuche-Linie.")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** Gerichteter Graph $G=(V,E)$ mit Kosten $c_e \ge 0$; Start $s$, Ziel $t$; $\delta(s,t)$ = Kosten einer billigsten Route. Der umgedrehte Graph $G^R$ hat jede Kante $(u,v)$ als $(v,u)$ mit denselben Kosten;
Dijkstra auf $G^R$ ab $t$ liefert $d_b(v)=\delta(v,t)$.

**Verfahren.** Zwei Dijkstra-Suchen mit Entfernungen $d_f$ (auf $G$ ab $s$) und $d_b$ (auf $G^R$ ab $t$) und Schlüsseln $k_f, k_b$ = kleinste Schlüssel der beiden Warteschlangen. Prüft die Vorwärtssuche eine Kante $(u,v)$, ist
$d_f(u)+c_{uv}+d_b(v)$ die Länge einer echten Route, sobald $d_b(v)<\infty$; die Rückwärtssuche prüft entsprechend $d_f(v)+c_{vu}+d_b(u)$. $\mu$ ist das Minimum über alle bisher geprüften Kanten.

**Abbruchregel.** Stopp, sobald $k_f + k_b \ge \mu$. **Beweisidee:** angenommen, es gäbe eine Route $P$ mit Länge $L<\mu$. Auf $P$ sei $v$ der letzte Knoten mit Abstand $<k_f$ vom Start und $w$ sein Nachfolger. Alle Knoten mit $d_f<k_f$ sind vorwärts festgelegt, also $v$;
der Rest von $P$ ab $w$ ist kürzer als $L-k_f<\mu-k_f\le k_b$, also ist $w$ (und alles dahinter) rückwärts festgelegt. Wer von beiden zuletzt festgelegt wurde, hat die Kante $(v,w)$ geprüft, als die andere Beschriftung schon da war - dann wäre $\mu\le L$.
Widerspruch. **Die erste Begegnung genügt nicht:** ein Knoten $x$, den beide Seiten erreichen, ergibt $d_f(x)+d_b(x)$ als Routenlänge, das aber nur eine obere Schranke für $\delta(s,t)$ ist - die Regel kann eine längere Route zurückgeben (Gegenbeispiel: kleines Netz oben).

**Aufwand.** Bei Wachstum wie die Kreisfläche legt einseitiges Dijkstra $\approx \pi R^2$ Knoten fest, zwei Suchen mit Radius $R/2$ zusammen $2\pi(R/2)^2=\tfrac12\pi R^2$: Faktor 2. Bei exponentiellem Wachstum $b^R$ gegen $2\,b^{R/2}$: der Gewinn wächst mit dem Netz (Quadratwurzel).
Für Straßennetze ist das nur ein Anhaltspunkt: der Gewinn hängt von der Form des Netzes und der Lage der Knoten ab (Messwerte oben).

**Wechselstrategie.** Die Richtigkeit hängt nicht von der Reihenfolge ab, der Aufwand schon: strikt abwechselnd legt je Seite gleich viele Knoten fest, "kleinere Front zuerst" vermeidet die dichte Seite, "gleiche Radien" (kleinerer Schlüssel zuerst) legt gleiche Entfernungen fest.

Implementiert in `bd_graph.py` (CSR-Graph, umgedrehter Graph), `bd_queues.py` (zwei Binärheap-Varianten), `bd_algorithm.py` (einseitig, beidseitig mit beiden Abbruchregeln und drei Wechselstrategien), `bd_scenario.py` (Netze), `bd_evaluation.py` (Paare, Kennzahlen, Experimente).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
