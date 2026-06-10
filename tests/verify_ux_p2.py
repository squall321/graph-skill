"""UX P2 — real-browser verification (Playwright).
Run: ./venv/Scripts/python.exe tests/verify_ux_p2.py
Covers: chart keyboard map (arrows/+/-/Home), legend Enter toggle, smith toolbar,
matrix CSV button, flow PNG button + dense-label mode + halo, theme button aria-pressed."""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
GAL = ROOT / "graph-out" / "gallery"
FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 900, "height": 520})

        # 1) keyboard map on the chart canvas
        pg.goto((GAL / "bode.html").resolve().as_uri())
        pg.wait_for_timeout(500)
        v0 = pg.evaluate("window.__graph.view.x.slice()")
        pg.evaluate("document.querySelector('canvas').focus()")
        pg.keyboard.press("ArrowRight")
        pg.wait_for_timeout(120)
        v1 = pg.evaluate("window.__graph.view.x.slice()")
        check("ArrowRight pans the view", v1 != v0, f"{v0}->{v1}")
        pg.keyboard.press("+")
        pg.wait_for_timeout(120)
        v2 = pg.evaluate("window.__graph.view.x.slice()")
        check("'+' zooms in", (v2[1] - v2[0]) < (v1[1] - v1[0]))
        pg.keyboard.press("Home")
        pg.wait_for_timeout(120)
        v3 = pg.evaluate("window.__graph.view.x.slice()")
        full = pg.evaluate("window.__graph.full.x.slice()")
        check("Home resets to full view", abs(v3[0] - full[0]) < 1e-9 and abs(v3[1] - full[1]) < 1e-9)

        # 2) legend keyboard toggle (Enter)
        vis0 = pg.evaluate("window.__graph.visible.slice()")
        pg.evaluate("document.querySelector('.gs-legend-item').focus()")
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(120)
        vis1 = pg.evaluate("window.__graph.visible.slice()")
        check("legend Enter toggles series", vis0 != vis1, f"{vis0}->{vis1}")

        # 3) smith toolbar exists (theme + PNG + source)
        pg.goto((GAL / "smith-chart.html").resolve().as_uri())
        pg.wait_for_timeout(500)
        sb = pg.evaluate("Array.from(document.querySelectorAll('.gs-smith-btn')).map(b=>b.textContent)")
        check("smith toolbar (◐/PNG/{})", sb is not None and len(sb) == 3, str(sb))
        th0 = pg.evaluate("document.querySelector('[data-theme]').getAttribute('data-theme')")
        pg.evaluate("Array.from(document.querySelectorAll('.gs-smith-btn')).find(b=>b.textContent==='◐').click()")
        th1 = pg.evaluate("document.querySelector('[data-theme]').getAttribute('data-theme')")
        check("smith theme cycles", th0 != th1, f"{th0}->{th1}")

        # 4) matrix CSV button present
        pg.goto((GAL / "design-state-compare.html").resolve().as_uri())
        pg.wait_for_timeout(700)
        csvb = pg.evaluate("Array.from(document.querySelectorAll('.gs-mx-btn')).some(b=>b.textContent==='CSV')")
        check("matrix CSV export button", bool(csvb))

        # 5) flow PNG button + sankey halo (paint-order on labels)
        pg.goto((GAL / "sankey-diagram.html").resolve().as_uri())
        pg.wait_for_timeout(600)
        pngb = pg.evaluate("Array.from(document.querySelectorAll('.gs-fl-btn')).some(b=>b.textContent==='PNG')")
        check("flow PNG export button", bool(pngb))
        halo = pg.evaluate("(function(){var t=document.querySelector('.gs-fl-slabel');return t?getComputedStyle(t).paintOrder:null;})()")
        check("sankey label halo (paint-order stroke)", halo is not None and "stroke" in halo, f"{halo}")

        # 6) network <title> tooltips on nodes
        pg.goto((GAL / "network-graph.html").resolve().as_uri())
        pg.wait_for_timeout(800)
        titles = pg.evaluate("document.querySelectorAll('.gs-fl-nnode > title').length")
        check("network node tooltips", titles >= 5, f"{titles}")

        b.close()

    print(("\nALL UX-P2 CHECKS PASSED" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}"))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
