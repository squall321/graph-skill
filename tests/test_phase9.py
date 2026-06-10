"""Phase (D) regression tests — ingest / resample / smoothing."""
import math

from graph_skill import tools
from graph_skill.postprocess import ingest, resample, smoothing


def _rmse(a, b):
    return (sum((a[i] - b[i]) ** 2 for i in range(len(a))) / len(a)) ** 0.5


def test_ingest_parses_and_nulls():
    g = ingest.parse_csv("a,b\n1,2\n3,x\n")
    assert g["names"] == ["a", "b"] and g["rows"] == 2 and g["columns"]["b"][1] is None


def test_ingest_tsv_detect_and_comment():
    g = ingest.parse_csv("a\tb\n# note\n1\t2\n")
    assert g["columns"]["a"] == [1.0] and g["columns"]["b"] == [2.0]


def test_resample_uniform_exact_on_linear():
    gx, gy = resample.resample_uniform([0, 1, 3, 4, 7], [0, 1, 3, 4, 7], n=8)
    assert resample.is_uniform(gx) and max(abs(gy[i] - gx[i]) for i in range(len(gx))) < 1e-9


def test_is_uniform():
    assert resample.is_uniform([0, 1, 2, 3]) and not resample.is_uniform([0, 1, 3])


def test_decimate():
    x, y = resample.decimate(list(range(10)), list(range(10)), 3)
    assert x == [0, 3, 6, 9]


def test_savgol_reduces_noise():
    clean = [math.sin(i / 10) for i in range(120)]
    noisy = [clean[i] + (0.3 if i % 2 else -0.3) for i in range(120)]
    assert _rmse(smoothing.savgol(noisy, 11, 2), clean) < 0.5 * _rmse(noisy, clean)


def test_moving_average_constant():
    assert smoothing.moving_average([1, 1, 1, 1, 1], 3) == [1, 1, 1, 1, 1]


def test_tools_resample_smooth():
    s = [{"name": "a", "data": [[0, 0], [1, 1], [3, 3]]}]
    rs = tools.resample(s, n=5)
    assert len(rs["series"][0]["data"]) == 5 and rs["uniform_input"] == [False]
    sm = tools.smooth(rs["series"], "moving", 3)
    assert len(sm["series"][0]["data"]) == 5


def test_helper_tools_registered():
    assert {"ingest_csv", "resample", "smooth"} <= set(tools.DISPATCH)
    assert {"ingest_csv", "resample", "smooth"} <= {t["name"] for t in tools.TOOLS}
