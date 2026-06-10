"""Rainflow (fatigue) regression — ASTM E1049 cycle counting + cycle-count heatmap."""
import json
from pathlib import Path

from graph_skill import builder, catalog, validate
from graph_skill.postprocess import fatigue

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"


def test_reversals_keeps_turning_points():
    rev = list(fatigue.reversals([0, 1, 2, 1, 0, 3, 0]))
    assert rev[0] == 0 and rev[-1] == 0 and 2 in rev and 3 in rev


def test_simple_cycle_0_5_0():
    cyc = fatigue.extract_cycles([0, 5, 0])
    assert all(abs(r - 5.0) < 1e-9 for r, _, _ in cyc)
    assert abs(sum(c for *_, c in cyc) - 1.0) < 1e-9     # two halves = 1 full


def test_count_conservation_nonnegative_ranges():
    cyc = fatigue.extract_cycles([-3, 5, -2, 4, -1, 3, -4, 2, -1])
    assert cyc and all(r >= 0 and c in (0.5, 1.0) for r, _, c in cyc)


def test_matrix_dims_and_total():
    mc, rc, Z = fatigue.rainflow_matrix([-3, 5, -2, 4, -1, 3, -4, 2], 6, 6)
    assert len(Z) == 6 and all(len(row) == 6 for row in Z)
    cyc = fatigue.extract_cycles([-3, 5, -2, 4, -1, 3, -4, 2])
    assert abs(sum(sum(row) for row in Z) - sum(c for *_, c in cyc)) < 1e-9


def test_registered_on_field_core():
    assert catalog.resolve_type("rainflow-cycle-histogram").engine == "field-core"


def test_render_and_axes_labels():
    p = json.loads((FIX / "rainflow.json").read_text(encoding="utf-8"))
    assert validate.check("rainflow-cycle-histogram", p)["ok"]
    h = Path(builder.render("rainflow-cycle-histogram", p,
                            out_path=str(OUT / "rainflow.html"))["html_path"]).read_text(encoding="utf-8")
    assert "Mean Stress" in h and "range" in h and "Cycles" in h


def test_gating():
    assert not validate.check("rainflow-cycle-histogram", {"signal": [1, 2, 3, 4]})["ok"]      # no load meta
    assert not validate.check("rainflow-cycle-histogram", {"load": {"label": "S", "unit": "MPa"}})["ok"]  # no signal
