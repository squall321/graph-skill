"""구조해석·열전달·측정 8종 — mesh-convergence/stress-linearization/hysteresis/
thermal-response/nusselt/frf-coherence/allan/calibration.
Locks: 수치 정확성(Richardson p·외삽, 선형화 적분, 루프 면적, RC τ 복원, 멱지수,
Allan 백색노이즈 기울기, 선형적합), 렌더/lint, 게이트, 결정성."""
import json
import math
from pathlib import Path

from graph_skill import builder, catalog, taxonomy, validate
from graph_skill.postprocess import experiment as ex
from graph_skill.recipes import REGISTRY

FIX = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent.parent / "graph-out"
TYPES = {"mesh-convergence": "meshconv", "stress-linearization": "stresslin",
         "hysteresis-loop": "hysteresis", "thermal-response": "thermalresp",
         "nusselt-correlation": "nusselt", "frf-coherence": "frf",
         "allan-deviation": "allan", "calibration-curve": "calibration"}


def _load(n):
    return json.loads((FIX / f"{n}.json").read_text(encoding="utf-8"))


def test_registration_render():
    cov = taxonomy.coverage(catalog.known_types())
    assert cov["ok"], cov["bad_category"]
    for t, fxn in TYPES.items():
        assert t in REGISTRY
        p = _load(fxn)
        assert validate.check(t, p)["ok"], t
        assert builder.render(t, p, out_path=str(OUT / f"{t}.html"))["lint"]["ok"], t


def test_richardson_recovers_known_order():
    # phi(h) = 100 + 2 h^2 → p=2, phi_ext=100
    r = ex.richardson([1, 2, 4], [102, 108, 132])
    assert abs(r["p"] - 2.0) < 1e-6 and abs(r["phi_ext"] - 100.0) < 1e-6
    assert r["gci_fine_pct"] > 0


def test_stress_linearization_integrals():
    # 선형 분포 σ(x)=a+bx → membrane = a + b·t/2, bending 정확 복원
    xs = [i * 0.05 for i in range(81)]                  # t=4, fine path (trapezoid on quadratic integrand)
    sig = [200 - 30 * x for x in xs]
    lin = ex.stress_linearize(xs, sig)
    assert abs(lin["membrane"] - (200 - 30 * 2)) < 1e-9
    assert abs(lin["bending"] - 60.0) < 0.05            # σ(0)-σm = 60 = +σb


def test_loop_energy_circle():
    pts = [[math.cos(2 * math.pi * k / 360), math.sin(2 * math.pi * k / 360)] for k in range(360)]
    assert abs(ex.loop_energy(pts) - math.pi) < 1e-3


def test_thermal_rc_recovers_tau():
    t = [i * 1.0 for i in range(200)]
    y = [80 - (80 - 20) * math.exp(-ti / 33.0) for ti in t]
    f = ex.thermal_rc_fit(t, y)
    assert abs(f["tau"] - 33.0) / 33.0 < 0.05 and abs(f["t_inf"] - 80) < 1.0


def test_power_fit_exponent():
    pf = ex.power_fit([1e3, 1e4, 1e5], [0.023 * (1e3) ** 0.8, 0.023 * (1e4) ** 0.8, 0.023 * (1e5) ** 0.8])
    assert abs(pf["m"] - 0.8) < 1e-9 and pf["r2"] > 0.999999


def test_allan_white_noise_slope():
    import random
    random.seed(5)
    s = [random.gauss(0, 0.1) for _ in range(20000)]
    taus, sig = ex.allan_deviation(s, 100)
    sl = (math.log10(sig[8]) - math.log10(sig[0])) / (math.log10(taus[8]) - math.log10(taus[0]))
    assert -0.65 < sl < -0.35                           # 이론 -1/2


def test_frf_right_axis_and_peaks():
    out = REGISTRY["frf-coherence"].normalize(_load("frf"), catalog.resolve_type("frf-coherence"))
    ser = out["assets"]["series"]
    assert any(s.get("axis") == "right" for s in ser)   # coherence on y2
    peaks = next(s for s in ser if s["name"] == "공진")
    assert len(peaks["x"]) == 3                          # 3 modes in fixture


def test_mesh_convergence_title_has_gci():
    out = REGISTRY["mesh-convergence"].normalize(_load("meshconv"), catalog.resolve_type("mesh-convergence"))
    assert "GCI_fine" in out["options"]["title"] and "φ_ext" in out["options"]["title"]
    assert out["options"]["axes"]["x"]["log"] is True


def test_gating():
    assert not validate.check("mesh-convergence",
                              {"cases": [{"h": 1, "value": 1}, {"h": 2, "value": 2}],
                               "axes": {"y": {"label": "a", "unit": ""}}})["ok"]
    assert not validate.check("hysteresis-loop", {"loops": [{"data": [[0, 0], [1, 1], [0, 2], [-1, 1]]}]})["ok"]
    assert not validate.check("frf-coherence", {"freq": [1, 2], "frf": [1, 2]})["ok"]
    assert not validate.check("allan-deviation", {"samples": [0] * 500, "params": {"fs": 100}})["ok"]
    assert not validate.check("calibration-curve", {"data": [[0, 0], [1, 1], [2, 2]]})["ok"]


def test_determinism():
    for t, fxn in TYPES.items():
        p = _load(fxn)
        a = Path(builder.render(t, p, out_path=str(OUT / f"_{fxn}A.html"))["html_path"]).read_bytes()
        b = Path(builder.render(t, p, out_path=str(OUT / f"_{fxn}B.html"))["html_path"]).read_bytes()
        assert a == b, t
        (OUT / f"_{fxn}A.html").unlink(missing_ok=True)
        (OUT / f"_{fxn}B.html").unlink(missing_ok=True)
