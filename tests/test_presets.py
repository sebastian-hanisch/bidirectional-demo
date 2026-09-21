"""Presets, Permalink-Angaben und Regler-Grenzen sind untereinander stimmig."""

import pytest

import bd_constants as C
import bd_presets as P
from bd_scenario import make_network


def test_every_preset_sets_every_control_within_bounds_and_has_help():
    assert set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESETS) == 5
    for name, p in C.PRESETS.items():
        assert set(p) == set(P.PRESET_KEYS) and p["net"] in C.NETS and p["stop"] in C.STOP_LABELS and p["alternate"] in C.ALTERNATE_LABELS
        for key, state_key in P.PRESET_KEYS.items():
            spec = P.SETTING_SPECS[state_key]
            if spec.lo is not None:
                assert spec.lo <= p[key] <= spec.hi, (name, key)
        make_network(p["net"], p["side"], p["reach"], p["spread"], p["blocked"], p["nodes"], p["degree"], p["seed"])
    assert [p["net"] for p in C.PRESETS.values()] == list(C.NETS)


def test_setting_specs_and_kept_keys_are_consistent():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS) and set(P.KEPT) <= set(P.SETTING_SPECS)
    for spec in P.SETTING_SPECS.values():
        assert spec.lo is None or spec.lo < spec.hi                                 # kein Regler mit gleichen Grenzen (Streamlit bricht ab)
    assert len({s.url_param for s in P.SETTING_SPECS.values()}) == len(P.SETTING_SPECS)
    assert "stop_select" not in P.KEPT and "alternate_select" not in P.KEPT           # diese Regler sind bei jedem Netz sichtbar


def test_defaults_lie_inside_the_bounds_and_the_default_is_the_small_net_with_the_correct_rule():
    assert C.SIDE_MIN <= C.DEFAULT_SIDE <= C.SIDE_MAX and C.REACH_MIN <= C.DEFAULT_REACH <= C.REACH_MAX and C.SPREAD_MIN <= C.DEFAULT_SPREAD <= C.SPREAD_MAX
    assert C.BLOCKED_MIN <= C.DEFAULT_BLOCKED <= C.BLOCKED_MAX and C.NODES_MIN <= C.DEFAULT_NODES <= C.NODES_MAX and C.DEGREE_MIN <= C.DEFAULT_DEGREE <= C.DEGREE_MAX
    assert C.DISTANCE_MIN <= C.DEFAULT_DISTANCE <= C.DISTANCE_MAX and C.DEFAULT_NET == "small" and C.DEFAULT_STOP == "correct"


def test_choice_casters_reject_unknown_values():
    for key, good, bad in (("net_select", "toronto", "ring"), ("stop_select", "first_meeting", "never"), ("alternate_select", "min_key", "random")):
        cast = P.SETTING_SPECS[key].caster
        assert cast(good) == good
        with pytest.raises(ValueError):
            cast(bad)
