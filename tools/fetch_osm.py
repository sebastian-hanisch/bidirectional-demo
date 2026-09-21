"""Einmal-Skript: holt das befahrbare Straßennetz der Toronto-Innenstadt aus OpenStreetMap und legt es als data/toronto_downtown.json ab.

Läuft NICHT in der App (die liest nur die JSON-Datei) und braucht osmnx, das nicht in requirements.txt steht:
    pip install osmnx scikit-learn && python tools/fetch_osm.py --dist 5000

Mittelpunkt: Toronto City Hall; Netz: alle für Autos befahrbaren Straßen im Umkreis (osmnx `network_type="drive"`, vereinfacht), Einbahnstraßen als gerichtete Kanten,
davon nur die größte stark zusammenhängende Komponente (von jedem Knoten kommt man zu jedem anderen). Parallelkanten: die kürzeste bleibt, Schleifen entfallen.
Daten: (c) OpenStreetMap-Mitwirkende, ODbL 1.0 (https://www.openstreetmap.org/copyright)."""

import argparse
import json
import math
from pathlib import Path

import osmnx as ox

CENTER = (43.653482, -79.384293)          # Toronto City Hall
OUT = Path(__file__).resolve().parent.parent / "data" / "toronto_downtown.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", type=int, default=5000, help="Umkreis in Metern")
    ap.add_argument("--dry", action="store_true", help="nur zählen, nichts schreiben")
    args = ap.parse_args()
    G = ox.graph_from_point(CENTER, dist=args.dist, network_type="drive", simplify=True)
    G = ox.truncate.largest_component(G, strongly=True)
    ids = list(G.nodes)
    index = {osm: i for i, osm in enumerate(ids)}
    lat0, lon0 = CENTER
    kx, ky = 111320.0 * math.cos(math.radians(lat0)), 110540.0
    nodes = [[round((G.nodes[o]["x"] - lon0) * kx, 1), round((G.nodes[o]["y"] - lat0) * ky, 1)] for o in ids]
    arcs = {}
    for u, v, data in G.edges(data=True):
        if u == v:
            continue
        key = (index[u], index[v])
        length = round(float(data["length"]), 1)
        if key not in arcs or length < arcs[key]:
            arcs[key] = length
    print(len(nodes), "Knoten,", len(arcs), "gerichtete Kanten (dist", args.dist, "m)")
    if args.dry:
        return
    payload = {"source": "OpenStreetMap, ODbL 1.0", "center": CENTER, "dist_m": args.dist, "network_type": "drive", "nodes_xy_m": nodes, "arcs": [[u, v, w] for (u, v), w in sorted(arcs.items())]}
    OUT.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print("->", OUT, OUT.stat().st_size // 1024, "kB")


if __name__ == "__main__":
    main()
