# Lizenz der Daten in `toronto_downtown.json`

Die Datei `toronto_downtown.json` enthält einen **Auszug aus OpenStreetMap**.

© OpenStreetMap-Mitwirkende – Daten unter der **Open Database License (ODbL) 1.0**:
<https://opendatacommons.org/licenses/odbl/1-0/> · Hinweise zur Namensnennung: <https://www.openstreetmap.org/copyright>

**Was der Auszug ist:** das für Autos befahrbare Straßennetz im Umkreis von 9 000 m um die Toronto City Hall (43.653482, -79.384293),
abgefragt am 21.09.2026 über die Overpass-Schnittstelle mit `osmnx` (`tools/fetch_osm.py`, `network_type="drive"`).

**Was daran verändert wurde:** die Straßen sind zu Knoten und gerichteten Kanten vereinfacht (osmnx-Vereinfachung), Einbahnstraßen sind gerichtete Kanten, Parallelkanten sind auf die kürzeste reduziert,
Selbstschleifen entfernt, es bleibt nur die größte stark zusammenhängende Komponente; die Koordinaten sind lokale Meter relativ zum Mittelpunkt, die Kantenlängen in Metern (in der App auf ganze Meter gerundet).

**Was das für Sie bedeutet:** die Datei darf unter den Bedingungen der ODbL weitergegeben, verändert und genutzt werden – mit Namensnennung (siehe oben) und
**Share-Alike**: wer sie oder eine daraus abgeleitete Datenbank öffentlich weitergibt, muss das unter der ODbL tun. Diese Lizenz gilt nur für die Daten in dieser Datei,
nicht für den übrigen Inhalt des Repositories.
