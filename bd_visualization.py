"""Plotly-Abbildungen: Netz mit beiden Suchen und Fronten, μ und Schranke über die Schritte, Verteilungen, Experimente. Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen."""

import numpy as np
import plotly.graph_objects as go

import bd_constants as C

NET_NAMES = {"small": "Kleines Netz", "city": "Stadtnetz", "toronto": "Toronto Innenstadt", "random": "Zufallsnetz", "asym": "Ungleiche Dichte"}


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.08), plot_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _edge_segments(g):
    """Alle Kanten als eine Linienspur (None trennt die Segmente); Hin- und Rückrichtung nur einmal."""
    src = np.repeat(np.arange(g.n), g.degree())
    dst = g.indices
    lo, hi = np.minimum(src, dst), np.maximum(src, dst)
    keep = np.zeros(len(src), dtype=bool)
    _, first = np.unique(lo * g.n + hi, return_index=True)
    keep[first] = True
    u, v = lo[keep], hi[keep]
    x = np.full(3 * len(u), None, dtype=object)
    y = np.full(3 * len(u), None, dtype=object)
    x[0::3], x[1::3] = g.xy[u, 0], g.xy[v, 0]
    y[0::3], y[1::3] = g.xy[u, 1], g.xy[v, 1]
    return x, y


def _frontier(g, settled):
    """Knoten, die von einem festgelegten Knoten aus erreicht wurden, aber selbst noch nicht festgelegt sind (die Front der Suche)."""
    src = np.repeat(np.arange(g.n), g.degree())
    reached = np.zeros(g.n, dtype=bool)
    reached[g.indices[settled[src]]] = True
    return np.where(reached & ~settled)[0]


def build_network(net, analysis, k, show_uni=False, height=520):
    """Das Netz nach `k` Festlegungen (abwechselnd vorwärts und rückwärts): vorwärts festgelegte Knoten blau, rückwärts grün, Fronten als Ringe; die Fläche der einseitigen Suche grau (wenn gewünscht);
    am Ende die Route und die Kante, über die sich die Suchen treffen."""
    g, bi, uni = net.graph, analysis.bi, analysis.uni
    small = bool(g.names)
    fig = go.Figure()
    if net.geometric:
        ex, ey = _edge_segments(g)
        fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color="rgba(150,150,150,0.4)", width=1), hoverinfo="skip", showlegend=False))
    else:
        fig.add_trace(go.Scatter(x=g.xy[:, 0], y=g.xy[:, 1], mode="markers", marker=dict(size=3, color="rgba(170,170,170,0.5)"), hoverinfo="skip", showlegend=False))
    if show_uni and uni.order:
        o = np.array(uni.order, dtype=int)
        fig.add_trace(go.Scatter(x=g.xy[o, 0], y=g.xy[o, 1], mode="markers", name="einseitig festgelegt (Dijkstra)", hoverinfo="skip",
                                 marker=dict(size=7 if g.n < 1500 else 5, symbol="circle", color="rgba(120,120,120,0.35)")))
    sides = bi.steps[:k]
    fw = np.array([n for sd, n in sides if sd == "f"], dtype=int)
    bw = np.array([n for sd, n in sides if sd == "b"], dtype=int)
    msize = 14 if small else (3 if g.n > 1500 else 6)
    if small:
        settled_any = np.zeros(g.n, dtype=bool)
        settled_any[fw] = True
        settled_any[bw] = True
        rest = np.where(~settled_any)[0]
        fig.add_trace(go.Scatter(x=g.xy[rest, 0], y=g.xy[rest, 1], mode="markers+text", showlegend=False, text=[g.names[i] for i in rest], textposition="top center",
                                 marker=dict(size=12, color="white", line=dict(color="gray", width=1.5)), hoverinfo="skip"))
        src = np.repeat(np.arange(g.n), g.degree())
        seen = set()
        for u, v, w in zip(src.tolist(), g.indices.tolist(), g.weight.tolist()):
            if (v, u) in seen:
                continue
            seen.add((u, v))
            mid = (g.xy[u] + g.xy[v]) / 2
            fig.add_annotation(x=mid[0], y=mid[1], text=f"{w:g}", showarrow=False, font=dict(size=12, color="#555"), bgcolor="rgba(255,255,255,0.75)")
    for nodes, color, name, graph in ((fw, C.COLORS["forward"], "vorwärts vom Start", g), (bw, C.COLORS["backward"], "rückwärts vom Ziel", net.reverse)):
        if len(nodes):
            mask = np.zeros(g.n, dtype=bool)
            mask[nodes] = True
            front = _frontier(graph, mask)
            if len(front):
                fig.add_trace(go.Scatter(x=g.xy[front, 0], y=g.xy[front, 1], mode="markers+text" if small else "markers", showlegend=False, text=[g.names[i] for i in front] if small else None,
                                         textposition="top center", hoverinfo="skip",
                                         marker=dict(size=msize + 4 if small else msize + 3, color="rgba(255,255,255,0.0)", line=dict(color=color, width=2))))
            fig.add_trace(go.Scatter(x=g.xy[nodes, 0], y=g.xy[nodes, 1], mode="markers+text" if small else "markers", name=name, hoverinfo="skip",
                                     text=[g.names[i] for i in nodes] if small else None, textposition="top center", marker=dict(size=msize, color=color, opacity=0.9)))
    finished = k >= len(bi.steps)
    if finished and bi.route:
        pts = g.xy[bi.route]
        fig.add_trace(go.Scatter(x=pts[:, 0], y=pts[:, 1], mode="lines", name="gefundene Route", line=dict(color=C.COLORS["route"], width=5 if g.n > 40 else 6), hoverinfo="skip"))
        u, v = bi.meet
        mid = (g.xy[u] + g.xy[v]) / 2
        fig.add_trace(go.Scatter(x=[mid[0]], y=[mid[1]], mode="markers", name="Treffpunkt", hoverinfo="skip", marker=dict(size=18, color=C.COLORS["meet"], symbol="star", line=dict(color="white", width=1.5))))
    for node, name, color, sym in ((analysis.s, "Start", C.COLORS["start"], "diamond"), (analysis.t, "Ziel", C.COLORS["goal"], "square")):
        fig.add_trace(go.Scatter(x=[g.xy[node, 0]], y=[g.xy[node, 1]], mode="markers", name=name, hoverinfo="skip", marker=dict(size=15, color=color, symbol=sym, line=dict(color="white", width=1.5))))
    fig.update_xaxes(visible=False, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False)
    if small:
        lo, hi = g.xy.min(axis=0), g.xy.max(axis=0)
        pad = 0.14 * (hi - lo)
        fig.update_xaxes(range=[lo[0] - pad[0], hi[0] + pad[0]])
        fig.update_yaxes(range=[lo[1] - 0.15 * (hi[1] - lo[1]), hi[1] + 0.15 * (hi[1] - lo[1])])
    return _base(fig, height)


def build_bounds(bi, k=None, height=280):
    """Die Abbruchregel: beste bisher gefundene Route (μ, fällt) und untere Schranke (kleinster Schlüssel vorwärts + rückwärts, steigt) über die Festlegungen; gestoppt wird, wenn sie sich treffen."""
    x = np.arange(len(bi.mu_hist))
    mu = np.array(bi.mu_hist, dtype=float)
    fig = go.Figure()
    fin = np.isfinite(mu)
    mode = "lines+markers" if len(x) <= 200 else "lines"                                 # bei tausenden Schritten reichen Linien
    fig.add_trace(go.Scatter(x=x[fin], y=mu[fin], mode=mode, name="beste gefundene Route μ", line=dict(color=C.COLORS["route"], shape="hv"), hovertemplate="μ = %{y:g}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=bi.lower_hist, mode=mode, name="untere Schranke", line=dict(color=C.COLORS["forward"], shape="hv"), hovertemplate="Schranke (Schlüssel vorwärts + rückwärts) = %{y:g}<extra></extra>"))
    if k is not None:
        fig.add_vline(x=k, line=dict(color="gray", dash="dash"))
    fig.update_layout(xaxis_title="Festlegungen (abwechselnd)", yaxis_title="Kosten")
    _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.4))
    return fig


def build_speedup_hist(speedup, height=300):
    fig = go.Figure(go.Histogram(x=np.clip(speedup, 0, 6), marker_color=C.COLORS["forward"], opacity=0.85, xbins=dict(start=0, end=6, size=0.25)))
    fig.add_vline(x=1.0, line=dict(color="black", dash="dot"), annotation_text="kein Gewinn", annotation_position="top left")
    fig.add_vline(x=float(np.median(speedup)), line=dict(color=C.COLORS["route"], dash="dash"), annotation_text="Median", annotation_position="top right")
    fig.update_layout(xaxis_title="Beschleunigung: einseitig festgelegte Knoten / beidseitig (gekappt bei 6)", yaxis_title="Start-Ziel-Paare")
    return _base(fig, height)


def build_net_comparison(rows, height=320):
    x = [NET_NAMES[r["net"]] for r in rows]
    fig = go.Figure(go.Bar(x=x, y=[r["median"] for r in rows], marker_color=C.COLORS["forward"], text=[f"{r['median']:.1f}×" for r in rows], textposition="outside",
                           error_y=dict(type="data", symmetric=False, array=[r["p90"] - r["median"] for r in rows], arrayminus=[r["median"] - r["p10"] for r in rows]),
                           hovertemplate="%{x}: Median %{y:.2f}-fach<extra></extra>"))
    fig.add_hline(y=2.0, line=dict(color="gray", dash="dot"), annotation_text="Flächenargument: 2×", annotation_position="top left")
    fig.update_layout(yaxis=dict(title="Beschleunigung (Median, Balken 10 %–90 %)", type="log"))
    return _base(fig, height)


def build_stop_comparison(rows, height=300):
    x = [NET_NAMES[r["net"]] for r in rows]
    fig = go.Figure(go.Bar(x=x, y=[r["share_wrong"] * 100 for r in rows], marker_color=C.COLORS["route"], text=[f"{r['share_wrong']:.0%}" for r in rows], textposition="outside",
                           hovertemplate="%{x}: %{y:.0f} % der Routen nicht kürzeste<extra></extra>"))
    fig.update_layout(yaxis=dict(title="Routen, die nicht die kürzeste sind [%]", range=[0, 100]))
    return _base(fig, height)


def build_alternate(rows, height=320):
    colors = {"strict": "#7f7f7f", "smaller_frontier": C.COLORS["forward"], "min_key": "#ff7f0e"}
    fig = go.Figure()
    for a in ("strict", "smaller_frontier", "min_key"):
        sel = [r for r in rows if r["alternate"] == a]
        fig.add_trace(go.Bar(x=[NET_NAMES[r["net"]] for r in sel], y=[r["speedup"] for r in sel], name=C.ALTERNATE_LABELS[a], marker_color=colors[a]))
    fig.update_layout(barmode="group", yaxis=dict(title="Beschleunigung (Verhältnis der Summen)", type="log"))
    return _base(fig, height)


def build_distance(curves, height=300):
    fig = go.Figure()
    palette = {"city": "#1f77b4", "toronto": "#d62728"}
    for key, rows in curves.items():
        fig.add_trace(go.Scatter(x=[r["pct"] for r in rows], y=[r["speedup"] for r in rows], mode="lines+markers", name=NET_NAMES[key], line=dict(color=palette.get(key))))
    fig.add_hline(y=1.0, line=dict(color="gray", dash="dot"))
    fig.update_layout(xaxis_title="Entfernung Start–Ziel (Rang unter allen erreichbaren Knoten) [%]", yaxis_title="Beschleunigung (Median)", yaxis_rangemode="tozero")
    return _base(fig, height)
