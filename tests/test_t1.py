"""T1 표준 보고 그래프 10종 — loop-gain-margin/conducted-emission/tdr/jitter-bathtub/
battery-cycle-fade/cc-cv/thermal-stack/hardness/xbar-r/fmea.
Locks: 등록·render·lint, 수치 self-check(안정도 마진·dual-Dirac·열저항 스택·X̄-R 상수·RPN/AP),
게이트(NEVER-invent), 결정성."""
import json
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.postprocess import domain_t1 as t1
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"loop-gain-margin": "loop_gain", "conducted-emission": "conducted_emission",
         "tdr-impedance-profile": "tdr", "jitter-bathtub": "jitter_bathtub",
         "battery-cycle-fade": "battery_cycle", "cc-cv-charge-profile": "cccv",
         "thermal-resistance-stack": "thermal_stack", "hardness-profile": "hardness",
         "xbar-r-chart": "xbar_r", "fmea-worksheet": "fmea"}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registration_render():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]
    for t, fx in TYPES.items():
        assert t in REGISTRY, t
        p = _load(fx)
        assert validate.check(t, p)["ok"], t
        assert builder.render(t, p, out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_stability_margins():
    # gain 0dB @ f=10 (φ=-135 → PM=45); phase -180 @ f=100 (gain=-20 → GM=20)
    m = t1.stability_margins([1, 10, 100], [20, 0, -20], [-90, -135, -180])
    assert abs(m["pm_deg"] - 45) < 1e-9 and abs(m["gm_db"] - 20) < 1e-9 and m["stable"] is True
    bad = t1.stability_margins([1, 10, 100], [20, 10, 5], [-90, -190, -260])  # never reaches 0dB
    assert bad["stable"] is False


def test_dual_dirac_bathtub():
    b = t1.dual_dirac_bathtub(0.02, 0.1, target_ber=1e-12)
    assert b["ber_left"][0] == 0.5 and b["ber_right"][-1] == 0.5            # edges at BER 0.5
    assert b["eye_opening"] is not None and 0 < b["eye_opening"] < 0.9      # finite opening


def test_thermal_stack():
    st = t1.thermal_stack(5.0, [{"name": "a", "r": 2}, {"name": "b", "r": 1}, {"name": "c", "r": 4}], 25)
    assert st["deltas"] == [10.0, 5.0, 20.0] and abs(st["total_dt"] - 35) < 1e-9
    assert abs(st["t_junction"] - 60) < 1e-9                                 # 25 + 35


def test_xbar_r_constants():
    st = t1.xbar_r([[1, 2, 3], [2, 3, 4]])
    assert st["n"] == 3 and abs(st["xbb"] - 2.5) < 1e-9 and abs(st["rb"] - 2) < 1e-9
    assert abs(st["x_ucl"] - (2.5 + 1.023 * 2)) < 1e-9                       # A2(n=3)=1.023
    assert abs(st["r_ucl"] - (2.574 * 2)) < 1e-9                            # D4(n=3)=2.574


def test_rpn_and_ap():
    assert t1.rpn(8, 3, 4) == 96
    assert t1.action_priority(10, 8, 9) == "H"      # high sev + high occ
    assert t1.action_priority(2, 2, 2) == "L"       # minor
    assert t1.action_priority(8, 3, 4) in ("L", "M")


def test_gating():
    assert not validate.check("loop-gain-margin", {"freq": [1], "gain_db": [0], "phase_deg": [-90]})["ok"]
    assert not validate.check("conducted-emission", {"spectrum": [[1e6, 50]]})["ok"]   # no limit
    assert not validate.check("tdr-impedance-profile", {"profile": [[0, 50], [1, 51]]})["ok"]  # no z0/unit
    assert not validate.check("hardness-profile", {"depth": [[0, 700], [1, 500]]})["ok"]  # no HV unit
    assert not validate.check("xbar-r-chart", {"subgroups": [[1, 2], [1, 2, 3]], "axes": {"y": {"unit": "mm"}}})["ok"]  # uneven
    assert not validate.check("fmea-worksheet", {"rows": [{"item": "x", "S": 11, "O": 2, "D": 3}]})["ok"]  # S out of range


def test_determinism():
    for t, fx in TYPES.items():
        p = _load(fx)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fx}B.html"))["html_path"]).read_bytes()
        assert a == b, t
        (OUT / f"_{fx}A.html").unlink(missing_ok=True)
        (OUT / f"_{fx}B.html").unlink(missing_ok=True)
