"""Rauchtests der Streamlit-Oberfläche per AppTest: Standard, jedes Preset, beide Abbruchregeln und alle Wechselstrategien, Randgrößen, Schritt-Zustand, ausgeblendete Regler, Permalink, Experimente auf Abruf, Schlüssel."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import bd_constants as C
from bd_presets import PRESET_KEYS

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"
EXPECTED_KIND = {"🔀 Kleines Netz": "warning", "🏙️ Stadtnetz": "success", "🍁 Toronto Innenstadt": "success", "🕸️ Zufallsnetz": "success", "⚖️ Ungleiche Dichte": "success"}


def _run(setup=None, timeout=600, net=None):
    at = AppTest.from_file(str(APP), default_timeout=timeout)
    if net:
        at.query_params["net"] = net
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if setup is not None:
        setup(at)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _apply(at, p):
    for key, state_key in PRESET_KEYS.items():
        at.session_state[state_key] = p[key]


def _labels(at):
    return {w.label for w in list(at.sidebar.slider) + list(at.sidebar.selectbox) + list(at.sidebar.number_input)}


def test_default_renders_without_exception():
    at = _run()
    assert any("Bidirektionale Suche in Aktion" in m.value for m in at.markdown)
    assert len(at.success) == 1 and not at.warning and not at.error                    # kleines Netz, korrekte Regel: dieselben Kosten, weniger Knoten


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_renders_with_its_verdict_kind(name):
    at = _run(lambda a: _apply(a, C.PRESETS[name]))
    kind = EXPECTED_KIND[name]
    assert (len(at.success) == 1 and not at.warning) if kind == "success" else (len(at.warning) == 1 and not at.success)


@pytest.mark.parametrize("stop", list(C.STOP_LABELS))
@pytest.mark.parametrize("alternate", list(C.ALTERNATE_LABELS))
def test_every_rule_and_strategy_renders_on_the_city_net(stop, alternate):
    def setup(at):
        at.session_state["net_select"] = "city"
        at.session_state["stop_select"] = stop
        at.session_state["alternate_select"] = alternate
    at = _run(setup)
    assert len(at.success) + len(at.warning) + len(at.info) == 1                                    # genau ein Urteil, keine Ausnahme
    if stop == "correct":
        assert len(at.warning) == 0                                                                # die korrekte Regel liefert nie eine falsche Route


def test_extreme_settings_render():
    def small(at):
        at.session_state["net_select"] = "city"
        at.session_state["side_slider"] = C.SIDE_MIN
        at.session_state["distance_slider"] = C.DISTANCE_MIN
    def big(at):
        at.session_state["net_select"] = "random"
        at.session_state["nodes_slider"] = C.NODES_MAX
        at.session_state["degree_slider"] = C.DEGREE_MAX
        at.session_state["distance_slider"] = C.DISTANCE_MAX
    for setup in (small, big):
        at = _run(setup)
        assert at.slider(key="bd_step").value == at.slider(key="bd_step").max


def test_hidden_controls_follow_the_net():
    def labels_for(net):
        return _labels(_run(net=net))
    small, city, rnd, asym, tor = (labels_for(n) for n in ("small", "city", "random", "asym", "toronto"))
    assert small == {"Netz", "Abbruchregel", "Wechselstrategie"}                                        # feste Aufgabe: kein Abstand, kein Seed
    assert {"Kreuzungen je Seite", "Reichweite der Straßen [Blocklängen]", "Streuung der Kosten", "Gesperrte Straßen [%]", "Entfernung Start–Ziel [%]", "Zufalls-Seed"} <= city and "Knoten" not in city
    assert {"Knoten", "Mittlerer Grad", "Entfernung Start–Ziel [%]", "Zufalls-Seed"} <= rnd and "Kreuzungen je Seite" not in rnd
    assert "Knoten" in asym and "Mittlerer Grad" not in asym
    assert tor == {"Netz", "Entfernung Start–Ziel [%]", "Abbruchregel", "Wechselstrategie"}


def test_hidden_slider_values_come_back_when_the_net_is_shown_again():
    # Die erste Sicht muss das Netz mit dem Regler sein: AppTest verliert den Wert, wenn der Regler zuerst ausgeblendet war (im echten Browser bleibt er erhalten).
    at = _run(net="city")
    at.session_state["spread_slider"] = 2.5
    at.run()
    at.session_state["net_select"] = "toronto"
    at.run()
    at.session_state["net_select"] = "city"
    at.run()
    assert not at.exception and at.slider(key="spread_slider").value == 2.5


def test_step_slider_returns_to_the_last_step_when_anything_changes():
    at = _run(net="city")
    at.slider(key="bd_step").set_value(5)
    at.run()
    assert at.slider(key="bd_step").value == 5
    at.session_state["stop_select"] = "first_meeting"
    at.run()
    assert not at.exception and at.slider(key="bd_step").value == at.slider(key="bd_step").max


def test_every_step_of_the_small_net_renders():
    at = _run()
    for k in range(0, int(at.slider(key="bd_step").max) + 1):
        at.slider(key="bd_step").set_value(k)
        at.run()
        assert not at.exception, k


def test_show_uni_checkbox_and_distance_slider_change_the_view():
    at = _run(net="city")
    at.checkbox(key="show_uni").set_value(True)
    at.run()
    assert not at.exception
    at.slider(key="distance_slider").set_value(20)
    at.run()
    assert not at.exception and at.slider(key="bd_step").value == at.slider(key="bd_step").max


def test_permalink_parameters_select_the_net_and_are_clamped():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["net"] = "random"
    at.query_params["nodes"] = "999999"
    at.query_params["stop"] = "never"
    at.query_params["alt"] = "smaller_frontier"
    at.run()
    assert not at.exception and at.selectbox(key="net_select").value == "random"
    assert at.slider(key="nodes_slider").value == C.NODES_MAX and at.selectbox(key="stop_select").value == C.DEFAULT_STOP and at.selectbox(key="alternate_select").value == "smaller_frontier"


def test_unknown_net_in_the_permalink_falls_back_to_the_default():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["net"] = "ring"
    at.run()
    assert not at.exception and at.selectbox(key="net_select").value == C.DEFAULT_NET


def test_experiments_run_on_demand():
    at = _run()
    assert not any("Median über 40 zufällige Paare je Datensatz" in c.value for c in at.caption)
    for key in ("netcmp_start", "stop_start", "alt_start", "dist_start"):
        at.button(key=key).click()
        at.run()
        assert not at.exception, (key, [e.value for e in at.exception])
    text = " ".join(c.value for c in at.caption)
    for needle in ("Median über 40 zufällige Paare je Datensatz", "Die Regel der ersten Begegnung liefert", "kleinere Front zuerst", "Median über 3 Startknoten"):
        assert needle in text, needle


def _calls(src, name):
    """Der Text jedes Aufrufs `name(...)` einschließlich verschachtelter Klammern."""
    out = []
    for m in re.finditer(re.escape(name) + r"\(", src):
        depth, i = 1, m.end()
        while depth:
            depth += {"(": 1, ")": -1}.get(src[i], 0)
            i += 1
        out.append(src[m.start():i])
    return out


def test_every_plotly_chart_has_an_explicit_unique_key_and_axes_are_locked():
    calls = _calls(APP.read_text(encoding="utf-8"), "plotly_chart")
    keys = [re.search(r'key=f?"([a-z_]+?)(?:_\{\w+\})?"', c).group(1) for c in calls]
    assert len(calls) == 7 and len(set(keys)) == 7, keys
    viz = (ROOT / "bd_visualization.py").read_text(encoding="utf-8")
    assert "fixedrange=True" in viz and viz.count("_base(fig") >= 6


def test_app_text_has_no_links_to_repository_files():
    assert not re.search(r"\]\(\w+\.py\)", APP.read_text(encoding="utf-8"))


def test_play_runs_through_all_frames_without_duplicate_chart_keys():
    """Beim Abspielen entstehen in einem Lauf mehrere Diagramme mit demselben Namen - die Schlüssel tragen deshalb den Schritt (Regression: StreamlitDuplicateElementKey bei mehr als einem Bild)."""
    at = _run()
    [b for b in at.button if b.label == "▶️ Abspielen"][0].click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
