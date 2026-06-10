"""UX P0 — real-browser interaction verification (Playwright, headless Chromium).
Run: ./venv/Scripts/python.exe tests/verify_ux_p0.py
Checks the behaviours that static lint can't: wheel scroll-through, Ctrl+wheel zoom,
playback domains, hidden carriers, modal Esc, force-sim settle, pan→click, cell size."""
import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "graph-out" / "gallery"
FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 900, "height": 520})

        # 1) playback domain bug fixed: view.x spans the data, carriers hidden from legend
        pg.goto((OUT / "bubble-timeline.html").resolve().as_uri())
        pg.wait_for_timeout(700)
        vx = pg.evaluate("window.__graph && window.__graph.view ? window.__graph.view.x : null")
        legend = pg.evaluate("Array.from(document.querySelectorAll('.gs-legend-item')).map(e=>e.textContent)")
        check("bubble-timeline view.x spans data (not 0..1)", bool(vx) and vx[1] > 100, f"view.x={vx}")
        check("no _carrier in legend", all("_carrier" not in (t or "") for t in legend), str(legend))

        # 2) wheel without Ctrl does NOT zoom (+ hint appears); Ctrl+wheel zooms
        pg.goto((OUT / "bode.html").resolve().as_uri())
        pg.wait_for_timeout(500)
        before = pg.evaluate("window.__graph.view.x.slice()")
        box = pg.evaluate("(function(){var r=document.querySelector('canvas').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()")
        pg.mouse.move(box["x"], box["y"])
        pg.mouse.wheel(0, -240)
        pg.wait_for_timeout(200)
        after_plain = pg.evaluate("window.__graph.view.x.slice()")
        hint = pg.evaluate("(function(){var h=document.querySelector('.gs-zoom-hint');return h && h.classList.contains('gs-show');})()")
        check("plain wheel does not zoom", before == after_plain, f"{before} -> {after_plain}")
        check("zoom hint shown on plain wheel", bool(hint))
        pg.keyboard.down("Control")
        pg.mouse.wheel(0, -240)
        pg.keyboard.up("Control")
        pg.wait_for_timeout(200)
        after_ctrl = pg.evaluate("window.__graph.view.x.slice()")
        check("Ctrl+wheel zooms", after_ctrl != after_plain, f"{after_plain} -> {after_ctrl}")

        # 3) legend toggle keeps the zoom (was: autoFit reset)
        zoomed = pg.evaluate("window.__graph.view.x.slice()")
        pg.evaluate("document.querySelector('.gs-legend-item') && document.querySelector('.gs-legend-item').click()")
        pg.wait_for_timeout(150)
        after_toggle = pg.evaluate("window.__graph.view.x.slice()")
        check("legend toggle keeps zoom", after_toggle == zoomed, f"{zoomed} -> {after_toggle}")

        # 4) review-matrix: cell graph pinned to 220x130, modal Esc closes
        pg.goto((OUT / "design-state-compare.html").resolve().as_uri())
        pg.wait_for_timeout(900)
        rect = pg.evaluate("(function(){var g=document.querySelector('.gs-cell-graph');if(!g)return null;var r=g.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)];})()")
        check("cell graph pinned size", rect is not None and rect[1] == 130, f"rect={rect}")
        pg.evaluate("document.querySelector('.gs-cell-graph').click()")
        pg.wait_for_timeout(400)
        open1 = pg.evaluate("document.querySelector('.gs-modal').classList.contains('open')")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(200)
        open2 = pg.evaluate("document.querySelector('.gs-modal').classList.contains('open')")
        check("matrix modal opens + Esc closes", bool(open1) and not open2, f"open={open1} afterEsc={open2}")

        # 5) network force settles (no idle rAF): node positions stop changing
        pg.goto((OUT / "network-graph.html").resolve().as_uri())
        pg.wait_for_timeout(6000)
        c1 = pg.evaluate("(function(){var c=document.querySelector('.gs-fl-nnode');return c?c.getAttribute('cx'):null;})()")
        pg.wait_for_timeout(1200)
        c2 = pg.evaluate("(function(){var c=document.querySelector('.gs-fl-nnode');return c?c.getAttribute('cx'):null;})()")
        check("network sim settles", c1 is not None and c1 == c2, f"{c1} vs {c2}")

        # 6) flowchart: pan the background, then click a node -> modal still opens (panned reset)
        pg.goto((OUT / "flowchart.html").resolve().as_uri())
        pg.wait_for_timeout(900)
        stage = pg.evaluate("(function(){var r=document.querySelector('.gs-fl-stage').getBoundingClientRect();return {x:r.x+r.width-40,y:r.y+r.height-40};})()")
        pg.mouse.move(stage["x"], stage["y"])
        pg.mouse.down()
        pg.mouse.move(stage["x"] - 80, stage["y"] - 40, steps=5)
        pg.mouse.up()
        pg.wait_for_timeout(200)
        # real mouse click (synthetic .click() skips pointerdown, which resets the pan flag)
        node = pg.evaluate("(function(){var n=document.querySelector('.gs-fl-clickable');if(!n)return null;var r=n.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+10};})()")
        clicked = "no-node"
        if node:
            pg.mouse.click(node["x"], node["y"])
            pg.wait_for_timeout(300)
            clicked = pg.evaluate("document.querySelector('.gs-fl-modal').classList.contains('open')")
        check("flowchart node click works after pan", clicked is True, f"clicked={clicked}")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(150)
        fm = pg.evaluate("document.querySelector('.gs-fl-modal').classList.contains('open')")
        check("flow modal Esc closes", not fm)

        # 7) flow title no longer inside the toolbar (button overlap fix)
        pg.goto((OUT / "sankey-diagram.html").resolve().as_uri())
        pg.wait_for_timeout(500)
        sep = pg.evaluate("""(function(){
            var t=document.querySelector('.gs-fl-title'), bar=document.querySelector('.gs-fl-toolbar');
            if(!t||!bar) return 'missing';
            return !bar.contains(t);
        })()""")
        check("flow title outside toolbar", sep is True, f"sep={sep}")

        # 8) playbar/legend reservation: playbar must not overlap the plot area
        pg.goto((OUT / "bar-chart-race.html").resolve().as_uri())
        pg.wait_for_timeout(600)
        ov = pg.evaluate("""(function(){
            var pb=document.querySelector('.gs-playbar'); if(!pb) return 'no-playbar';
            var r=pb.getBoundingClientRect();
            var plot=window.__graph.plot;
            return r.top >= plot.bottom - 2;     // playbar sits below the plot
        })()""")
        check("playbar below plot (layout reserved)", ov is True, f"ov={ov}")

        b.close()

    print(("\nALL UX-P0 CHECKS PASSED" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}"))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
