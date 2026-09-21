# Bidirektionale Suche – von beiden Enden gleichzeitig – Streamlit-Demo

**[→ Demo live ausprobieren](https://sebastianhanisch-bidirectional-demo.streamlit.app/)**

Drittes Stück der **Kürzeste-Wege-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", Fortsetzung der [Dijkstra-Demo](../dijkstra-demo):
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **ein** Verfahren – die **bidirektionale Dijkstra-Suche** – an einem wachsenden Beispiel.
Dijkstra legt alles fest, was näher am Start liegt als das Ziel – einen Kreis, dessen Fläche mit dem Quadrat der Entfernung wächst. Die bidirektionale Suche startet zusätzlich **am Ziel** und läuft rückwärts über die umgedrehten Kanten:
zwei Kreise mit halbem Radius statt einem großen. Der Haken ist die Frage, **wann man aufhören darf** – die erste Begegnung der beiden Suchen ist nicht immer die kürzeste Route.

**Einordnung in die Reihe (die Kanten des Graphen):** die Bidirektionale Suche setzt an Dijkstras Schwäche "blind in alle Richtungen" an und ist selbst wieder Baustein: jede Anfrage beginnt von vorn
(→ Contraction Hierarchies, deren Abfrage bidirektional ist und ein großes echtes Straßennetz braucht), und die Suche kennt die Richtung des Ziels nicht (→ A\*, bidirektionales A\* in der Baumsuche-Linie).
```
bfs-demo (Wurzel: Kanten zählen, nicht Kosten)                              [gebaut]
  └─ dijkstra-demo (Kosten korrekt, blind in alle Richtungen)               [gebaut]
       ├─ bidirectional-demo (von beiden Enden) → Contraction Hierarchies   [dieses Stück → nicht gebaut]
       ├─ Bellman-Ford + Floyd-Warshall → Johnson (Konvergenz: Umgewichtung) [nicht gebaut]
       └─ Mehrkriterien-Routing (Zeit gegen CO₂, Pareto)                    [nicht gebaut]
A* steht einmal in der Baumsuche-Linie und wird von hier aus nur verlinkt.
```

## Quellen

| Bestandteil | Quelle |
|---|---|
| Verfahren, Abbruch bei der ersten Begegnung | Idee aus *Optimization Algorithms* (A. Khamis), Kap. 3.4.3, Algorithmus 3.5 – der Pseudocode bricht bei der ersten Begegnung ab; hier laufen **beide** Regeln nebeneinander |
| Flächenargument, "etwa zweimal schneller" | dieselbe Stelle; die Zahlen dieser Demo sind **eigene Messungen**, nicht die des Buchs |
| **Kleines Netz**, Zufallsnetz, ungleiche Dichte, Stadtnetz | eigene Graphen und Erzeuger |
| **Toronto Innenstadt** | **echte OpenStreetMap-Daten**: befahrbares Netz im 9-km-Umkreis der City Hall (10 153 Knoten, 26 985 gerichtete Kanten), einmalig geholt (`tools/fetch_osm.py`), fest in `data/toronto_downtown.json`, Kosten in der App auf ganze Meter gerundet |

Aus den Büchern stammt nur die Idee; Text, Abbildungen, Code, Graphen und Zahlen der Bücher sind nicht übernommen.

**Daten und Lizenz:** Kartendaten © [OpenStreetMap-Mitwirkende](https://www.openstreetmap.org/copyright), Open Database License (ODbL) 1.0. `data/toronto_downtown.json` ist ein Auszug daraus und steht deshalb ebenfalls unter der ODbL – siehe [data/LICENSE-ODbL.md](data/LICENSE-ODbL.md).

## Ergebnis (Zahlen aus den Tests)

| Frage | Ergebnis |
|---|---|
| Kleines Netz | ❌ Bei der ersten Begegnung liefert die Suche **11 Minuten** (über die teure Direktstrecke), die schnellste Route braucht **9**; die korrekte Regel läuft weiter und findet sie |
| Gewinn im Stadtnetz | ✅ Median über Zufallspaare **1.7-fach** weniger festgelegte Knoten (10 %–90 %: 1.3–2.6), für das gezeigte Paar 126 statt 241 – das Flächenargument (Faktor 2) |
| Gewinn im echten Toronto-Netz | ⚠️ ebenfalls Median **1.7-fach**, aber breit gestreut (10 %–90 %: 1.2–2.4) und bei etwa **1 %** der Paare kein Gewinn; für das gezeigte Paar 3 547 statt 6 093 festgelegte Knoten – immer noch über ein Drittel des Netzes |
| Zufallsnetz (exponentielles Wachstum) | ✅ Median **14-fach** (für das gezeigte Paar 80 statt 1 201): das Flächenargument gilt nur für flache Netze |
| Ungleiche Dichte | ✅ strikt abwechselnd im Mittel **2.0-fach**, mit "kleinere Front zuerst" **2.7-fach**, mit "gleiche Radien" nur **1.6-fach** |
| Erste Begegnung gegen korrekte Regel | ❌ im Stadtnetz ist die Route bei **81 %** der Zufallspaare nicht die kürzeste (im Mittel 9 % zu lang), in Toronto bei **45 %** (im Mittel 1 %), im Zufallsnetz bei 33 %; die falsche Regel sieht dabei **schneller** aus (Stadtnetz scheinbar 2.2- statt 1.7-fach), weil sie früher aufhört |
| Wechselstrategie | ✅ "kleinere Front zuerst" verliert nirgends gegen die strikte Abwechslung des Buchs; ❌ "gleiche Radien" legt in Toronto bei rund 8 % der Paare sogar mehr Knoten fest als einseitiges Dijkstra |
| Entfernung Start–Ziel | ⚠️ im Stadtnetz über alle Entfernungen etwa gleich (2–3-fach), in Toronto sinkt der Gewinn von etwa 2.3–2.9-fach bei mittleren Entfernungen auf rund 1.5-fach bei den entferntesten Zielen (Rand des Netzes) |
| Korrektheit | ✅ die korrekte Regel liefert auf jedem geprüften Paar (alle Netze, alle Strategien) exakt die Kosten von einseitigem Dijkstra und networkx |

Die Zahl der festgelegten Knoten ist der Aufwand der Suche und plattformfest. Laufzeiten stehen in der App nur als Messwerte: in reinem Python ist die beidseitige Suche trotz weniger Knoten nicht schneller (zwei Warteschlangen, umgedrehter Graph).

## Was die Demo zeigt

1. **Bidirektionale Suche in Aktion** (Schritt-Regler + Abspielen): vorwärts festgelegte Knoten blau, rückwärts grün, Fronten als Ringe, Treffpunkt und Route; zuschaltbar die **Fläche der einseitigen Suche** in Grau (ein großer Kreis gegen zwei kleine). Daneben die **Abbruchregel als Diagramm**: beste gefundene Route μ (fällt) gegen untere Schranke (kleinster Schlüssel vorwärts + rückwärts, steigt).
2. **Zwei kleine Kreise statt einem großen** – Kennzahlen des gezeigten Paars (Kosten, festgelegte Knoten, Beschleunigung) mit Urteil, dazu die **Verteilung über 100 Zufallspaare** (Median, 10 %–90 %, Paare ohne Gewinn, nicht kürzeste Routen, Histogramm).
3. **Vergleich** (Expander) der Zähler; **Experimente auf Knopfdruck**: Gewinn je Netztyp, erste Begegnung gegen korrekte Regel, drei Wechselstrategien, Gewinn gegen Entfernung.
4. **Wo die Annahmen enden** (Tabelle mit den Ansatzpunkten der nächsten Stücke) und **Mathematische Formulierung** (μ, Beweisidee der Abbruchregel, Flächen- und Exponentialargument, Gegenbeispiel zur ersten Begegnung).

Bedienung: Beispielnetz per Schnellstart-Knopf laden oder in der Seitenleiste Netz, Abstand Start–Ziel, **Abbruchregel** und **Wechselstrategie** wählen; die Adresszeile spiegelt die Konfiguration (Permalink). Regler, die zum gewählten Netz nicht gehören, sind ausgeblendet.

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `bd_graph.py` | gerichteter Graph in CSR-Form, **umgedrehter Graph** für die Rückwärtssuche |
| `bd_queues.py` | zwei Binärheap-Varianten (mit Decrease-Key, faul) mit Zählern |
| `bd_algorithm.py` | einseitiges Dijkstra, bidirektionale Suche mit beiden Abbruchregeln und drei Wechselstrategien |
| `bd_scenario.py` | Netze: kleines Netz, Stadtnetz, Zufallsnetz, ungleiche Dichte, Toronto Innenstadt |
| `bd_evaluation.py` | Paarwahl, Kennzahlen, Verteilung über Paare, Experimente |
| `bd_visualization.py`, `bd_presets.py`, `bd_constants.py` | Abbildungen, Presets und Permalink, Konstanten |
| `tools/fetch_osm.py` | Einmal-Skript: holt das Toronto-Autonetz (braucht `osmnx`, nicht in `requirements.txt`) |
| `data/toronto_downtown.json` | der OSM-Auszug |

## Lokal starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

Tests: `pip install -r requirements-dev.txt` und `python -m pytest tests/`. Jede Zahl in Hilfetexten, Presets und Tabellen ist in `tests/test_claims.py` belegt; die Kreuzprobe läuft gegen networkx (`dijkstra_path_length`, `bidirectional_dijkstra`).
