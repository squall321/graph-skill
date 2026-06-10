"""Real-browser visual smoke for every rendered artifact (graph-out/gallery/*.html).

Unlike the node stubs (which no-op every canvas call), this loads each self-contained HTML
in headless Chromium and verifies it ACTUALLY draws: engine booted, zero console/page errors,
and the canvas/DOM has real content (a blank canvas compresses to a tiny data-URL — drawn
canvases are large). Covers WebGL (cad3d / smith) which the stubs cannot exercise.

Run: venv/Scripts/python.exe tests/playwright_smoke.py [glob]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
GAL = ROOT / "graph-out" / "gallery"

CHECK = """() => {
  const root = document.getElementById('graph-root');
  const booted = !!window.__graph;
  const cv = Array.from(document.querySelectorAll('canvas'));
  let maxLen = 0;
  for (const c of cv) { try { const u = c.toDataURL(); if (u.length > maxLen) maxLen = u.length; } catch (e) {} }
  const textLen = (root && root.textContent || '').length;
  return { booted, nCanvas: cv.length, maxLen, textLen };
}"""


def main():
    pattern = sys.argv[1] if len(sys.argv) > 1 else "*.html"
    files = sorted(f for f in GAL.glob(pattern) if f.name != "index.html")
    if not files:
        print("no gallery files — run build_gallery.py first")
        return 1
    fails = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for f in files:
            errors = []
            page = browser.new_page(viewport={"width": 700, "height": 460})
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            try:
                page.goto(f.as_uri(), wait_until="load", timeout=15000)
                page.wait_for_timeout(700)              # let async GLB load + rAF settle (cad3d)
                r = page.evaluate(CHECK)
                drew = r["maxLen"] > 1500 or r["textLen"] > 30
                ok = r["booted"] and not errors and drew
                status = "ok  " if ok else "FAIL"
                print(f"  {status} {f.name:<30} booted={r['booted']} canvas={r['nCanvas']} "
                      f"draw={'Y' if drew else 'N'}({r['maxLen']}) err={len(errors)}")
                if not ok:
                    fails.append((f.name, r, errors[:3]))
            except Exception as e:  # noqa: BLE001
                print(f"  FAIL {f.name:<30} EXCEPTION {str(e)[:60]}")
                fails.append((f.name, None, [str(e)[:120]]))
            finally:
                page.close()
        browser.close()
    print(f"\n{len(files) - len(fails)}/{len(files)} rendered clean in real Chromium")
    for name, r, errs in fails:
        print(f"  ✗ {name}: {errs}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
