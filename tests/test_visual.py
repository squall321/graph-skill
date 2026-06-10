"""Real-browser visual regression (pytest) — renders representative artifacts across all 6
engine families (incl. WebGL cad3d / smith) in headless Chromium and asserts they actually
draw with zero console errors. Skips cleanly if playwright/chromium isn't installed.
The full 58-type sweep lives in tests/playwright_smoke.py."""
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

GAL = Path(__file__).resolve().parent.parent / "graph-out" / "gallery"

# one per engine family + the engine-touching plugins / WebGL
REPRESENTATIVE = [
    "base-xy", "contour-plot", "vector-quiver-2d", "polar-plot", "wind-rose",
    "review-matrix", "scatter-matrix", "cad-3d-viewer", "mesh-result-3d", "smith-chart",
    "violin-plot", "waterfall-chart", "parallel-coordinates", "spectrogram", "nyquist-plot",
]

CHECK = """() => {
  const root = document.getElementById('graph-root');
  const cv = Array.from(document.querySelectorAll('canvas'));
  let maxLen = 0;
  for (const c of cv) { try { const u = c.toDataURL(); if (u.length > maxLen) maxLen = u.length; } catch (e) {} }
  return { booted: !!window.__graph, maxLen, textLen: (root && root.textContent || '').length };
}"""


@pytest.fixture(scope="module")
def browser():
    pw = None
    try:
        pw = sync_playwright().start()
        b = pw.chromium.launch()
    except Exception as e:  # noqa: BLE001  — no browser binary → skip the whole module
        if pw:
            pw.stop()
        pytest.skip(f"chromium unavailable: {str(e)[:80]}")
    yield b
    b.close()
    pw.stop()


@pytest.mark.parametrize("t", REPRESENTATIVE)
def test_renders_in_real_chromium(browser, t):
    f = GAL / f"{t}.html"
    if not f.exists():
        pytest.skip("gallery not built (run build_gallery.py)")
    errors = []
    page = browser.new_page(viewport={"width": 700, "height": 460})
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(f.as_uri(), wait_until="load", timeout=15000)
        page.wait_for_timeout(700)                 # async GLB load + rAF settle (cad3d/WebGL)
        r = page.evaluate(CHECK)
        assert r["booted"], f"{t}: engine did not boot"
        assert not errors, f"{t}: console/page errors {errors[:2]}"
        assert r["maxLen"] > 1500 or r["textLen"] > 30, f"{t}: canvas/DOM blank {r}"
    finally:
        page.close()
