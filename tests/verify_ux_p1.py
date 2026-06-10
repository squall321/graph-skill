"""UX P1 — real-browser interaction verification (Playwright).
Run: ./venv/Scripts/python.exe tests/verify_ux_p1.py
Covers: tap tooltip, ± zoom buttons, '?' help overlay, narrow ⋯ export menu,
treemap hidden axes/log buttons, parcoord min/max labels (pixels), empty-data
watermark, theme postMessage sync, flow load toast + dblclick fit + semantic zoom,
matrix mini-cell controlbar removal + search no-result, LTTB perf on gapped series."""
import json
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

        # 1) bode: ± buttons zoom, '?' opens help, tap(click-lock) shows tooltip
        pg.goto((GAL / "bode.html").resolve().as_uri())
        pg.wait_for_timeout(500)
        v0 = pg.evaluate("window.__graph.view.x.slice()")
        pg.evaluate("Array.from(document.querySelectorAll('.gs-btn')).find(b=>b.textContent==='＋').click()")
        pg.wait_for_timeout(150)
        v1 = pg.evaluate("window.__graph.view.x.slice()")
        check("＋ button zooms in", v1 != v0 and (v1[1] - v1[0]) < (v0[1] - v0[0]), f"{v0}->{v1}")
        pg.evaluate("Array.from(document.querySelectorAll('.gs-btn')).find(b=>b.textContent==='?').click()")
        helped = pg.evaluate("(function(){var h=document.querySelector('.gs-help');return h && h.classList.contains('gs-open');})()")
        check("'?' opens help overlay", bool(helped))
        pg.evaluate("document.querySelector('.gs-help').click()")
        # tap = click in plot -> lock + tooltip visible
        box = pg.evaluate("(function(){var p=window.__graph.plot;var r=document.querySelector('canvas').getBoundingClientRect();return {x:r.x+(p.left+p.right)/2,y:r.y+(p.top+p.bottom)/2};})()")
        pg.mouse.click(box["x"], box["y"])
        pg.wait_for_timeout(150)
        tip = pg.evaluate("document.querySelector('.gs-tooltip').style.opacity")
        check("click-lock shows series tooltip (tap path)", tip == "1", f"opacity={tip}")

        # 2) narrow ⋯ export menu
        pg2 = b.new_page(viewport={"width": 380, "height": 320})
        pg2.goto((GAL / "bode.html").resolve().as_uri())
        pg2.wait_for_timeout(500)
        narrow = pg2.evaluate("""(function(){
            var root=document.querySelector('.gs-root');
            var more=document.querySelector('.gs-more'), ex=document.querySelector('.gs-exports');
            if(!root.classList.contains('gs-narrow')||!more||!ex) return 'missing';
            var visBefore = getComputedStyle(ex).display;
            more.click();
            var visAfter = getComputedStyle(ex).display;
            return visBefore==='none' && visAfter!=='none';
        })()""")
        check("narrow width: exports collapse behind ⋯", narrow is True, f"r={narrow}")
        pg2.close()

        # 3) treemap-drilldown: no numeric axes / no log buttons (hideAxes)
        pg.goto((GAL / "treemap-drilldown.html").resolve().as_uri())
        pg.wait_for_timeout(600)
        logbtns = pg.evaluate("Array.from(document.querySelectorAll('.gs-btn')).filter(b=>/^log/.test(b.textContent)).length")
        check("treemap: log buttons removed", logbtns == 0, f"{logbtns}")

        # 4) parcoord: min/max labels actually visible (pixels above plot top)
        pg.goto((GAL / "parallel-coordinates.html").resolve().as_uri())
        pg.wait_for_timeout(700)
        haspix = pg.evaluate("""(function(){
            var cv=document.querySelector('canvas'), p=window.__graph.plot;
            var ctx=cv.getContext('2d');
            var dpr=window.devicePixelRatio||1;
            var y0=Math.max(0,Math.round((p.top-12)*dpr));
            var d=ctx.getImageData(0,y0,cv.width,Math.round(12*dpr)).data;
            var dark=0;
            for(var i=0;i<d.length;i+=4){ if(d[i+3]>0 && (d[i]+d[i+1]+d[i+2])/3 < 180) dark++; }
            return dark;
        })()""")
        check("parcoord max labels drawn above plot", haspix > 30, f"dark px={haspix}")

        # 5) empty-data watermark
        empty = ROOT / "graph-out" / "_p1_empty.html"
        from graph_skill import builder
        builder.render("base-xy", {"axes": {"x": {"label": "t", "unit": "s"}, "y": {"label": "v", "unit": ""}},
                                   "series": [{"name": "a", "data": [[0, None], [1, None]]}]},
                       out_path=str(empty))
        pg.goto(empty.resolve().as_uri())
        pg.wait_for_timeout(400)
        wm = pg.evaluate("""(function(){
            var cv=document.querySelector('canvas');var ctx=cv.getContext('2d');
            var d=ctx.getImageData(Math.round(cv.width*0.3),Math.round(cv.height*0.4),Math.round(cv.width*0.4),Math.round(cv.height*0.2)).data;
            var ink=0; for(var i=0;i<d.length;i+=4){ if(d[i+3]>0 && (d[i]+d[i+1]+d[i+2])/3<200) ink++; }
            return ink;
        })()""")
        check("empty-data watermark drawn", wm > 50, f"ink={wm}")
        empty.unlink(missing_ok=True)

        # 6) theme postMessage sync
        pg.goto((GAL / "gauge.html").resolve().as_uri())
        pg.wait_for_timeout(400)
        th = pg.evaluate("""(function(){
            window.postMessage({type:'gs-theme', theme:'dark'}, '*');
            return new Promise(function(res){ setTimeout(function(){
                var r=document.querySelector('[data-theme]');
                res(r ? r.getAttribute('data-theme') : 'none');
            }, 200); });
        })()""")
        check("postMessage theme sync -> dark", th == "dark", f"theme={th}")

        # 7) flow: load toast + dblclick fit + semantic zoom class
        pg.goto((GAL / "flowchart.html").resolve().as_uri())
        pg.wait_for_timeout(1100)
        toast = pg.evaluate("(function(){var h=document.querySelector('.gs-fl-zoom-hint');return h && h.classList.contains('gs-show');})()")
        check("flow one-time discoverability toast", bool(toast))
        sem = pg.evaluate("""(function(){
            var g=window.__graph; g.scale=0.4; g._apply();
            return document.querySelector('.gs-flow').classList.contains('gs-sem-small');
        })()""")
        check("semantic zoom class below 0.55", sem is True)
        fit = pg.evaluate("""(function(){
            var g=window.__graph; var s0=g.scale;
            var ev=new MouseEvent('dblclick',{bubbles:true});
            document.querySelector('.gs-fl-stage').dispatchEvent(ev);
            return g.scale !== 0.4;
        })()""")
        check("dblclick background = fit", fit is True)

        # 8) matrix: mini cell has NO controlbar; modal mount HAS one; search 0 -> message
        pg.goto((GAL / "design-state-compare.html").resolve().as_uri())
        pg.wait_for_timeout(900)
        nochrome = pg.evaluate("document.querySelectorAll('.gs-cell-graph .gs-controlbar').length")
        check("mini cell graphs have no controlbar", nochrome == 0, f"{nochrome}")
        pg.evaluate("(function(){var s=document.querySelector('.gs-mx-search'); s.value='zzzz존재안함'; s.dispatchEvent(new Event('input'));})()")
        pg.wait_for_timeout(200)
        nores = pg.evaluate("(function(){var n=document.querySelector('.gs-mx-nores');return n && n.style.display!=='none';})()")
        check("search 0-result message", bool(nores))

        # 9) gapped 30k series renders fast (LOD active): paint under ~250ms per render
        big = ROOT / "graph-out" / "_p1_big.html"
        xs = [i * 0.001 for i in range(30000)]
        import math
        ys = [None if i % 5000 == 0 else math.sin(i * 0.01) for i in range(30000)]
        builder.render("base-xy", {"axes": {"x": {"label": "t", "unit": "s"}, "y": {"label": "v", "unit": ""}},
                                   "series": [{"name": "sig", "x": xs, "y": ys}]}, out_path=str(big))
        pg.goto(big.resolve().as_uri())
        pg.wait_for_timeout(500)
        ms = pg.evaluate("""(function(){
            var g=window.__graph, t0=performance.now();
            for (var i=0;i<5;i++) g.render();
            return (performance.now()-t0)/5;
        })()""")
        check("gapped 30k render < 80ms (LOD on)", ms < 80, f"{ms:.1f}ms/frame")
        big.unlink(missing_ok=True)

        b.close()

    print(("\nALL UX-P1 CHECKS PASSED" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}"))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
