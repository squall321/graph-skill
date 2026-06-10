"""실전 게시 품질 점검 — report-archive 실페이지에서 임베드 동작 검증.
Usage: ./venv/Scripts/python.exe tests/verify_publish.py <report_id>
플랫폼 동작(v0.25.0): html_embed는 인라인 placeholder(캡션+전체화면)로 렌더되고,
전체화면 클릭 시 sandbox(allow-scripts) srcdoc iframe 모달로 라이브 렌더된다.
검사: 본문/임베드 8개 렌더, 모달 라이브 렌더(픽셀), Ctrl+휠 줌이 모달 안에서 동작(픽셀 diff),
3D WebGL 모달, 부모 콘솔 에러, 데스크톱/모바일 스크린샷."""
import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

RID = sys.argv[1] if len(sys.argv) > 1 else "54"
BASE = "http://localhost:3001"
ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKEN = (ROOT / "graph-out" / "publish" / "_tok.txt").read_text(encoding="utf-8").strip()
SHOT = ROOT / "audit-shots"
SHOT.mkdir(exist_ok=True)
FAILS = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def login(pg):
    pg.goto(f"{BASE}/login", wait_until="domcontentloaded")
    pg.evaluate("t => localStorage.setItem('ra:access_token:v1', t)", TOKEN)


def open_modal_by_index(pg, idx1):
    """임베드 카드 순서(1-base)로 전체화면 클릭 — buttons[0]은 페이지 전체화면이라 건너뜀."""
    btns = pg.query_selector_all("button:has-text('전체화면')")
    if len(btns) <= idx1:
        return None
    btns[idx1].click()
    pg.wait_for_timeout(3500)
    return pg.query_selector("iframe")


def ink(pg, sel="iframe"):
    """모달 iframe 영역 스크린샷의 픽셀 시그니처(상호작용 전/후 비교용)."""
    f = pg.query_selector(sel)
    img = f.screenshot()
    return len(img), sum(img[::577]) % 100000


def main():
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:160]))
        pg.on("console", lambda m: errs.append(m.text[:160]) if m.type == "error" else None)
        login(pg)

        t0 = time.time()
        pg.goto(f"{BASE}/w/personal-3/reports/{RID}", wait_until="load")
        pg.wait_for_timeout(5000)
        check("report page loads", time.time() - t0 < 15, f"{time.time()-t0:.1f}s")

        txt = pg.evaluate("document.body.innerText")
        nfull = txt.count("전체화면")
        check("8 embed cards rendered", nfull >= 9, f"전체화면 x{nfull} (1 page + 8 embeds)")
        check("captions visible", "Bode" in txt or "주파수응답" in txt)
        pg.screenshot(path=str(SHOT / f"publish_{RID}_desktop.png"), full_page=True)

        # ── bode 모달: 라이브 렌더 + Ctrl+휠 줌이 iframe 안에서 동작하는가 (픽셀 diff)
        fr = open_modal_by_index(pg, 1)  # embed 1 = bode
        check("bode modal iframe", fr is not None and fr.get_attribute("sandbox") == "allow-scripts",
              fr.get_attribute("sandbox") if fr else "none")
        if fr:
            s1 = ink(pg)
            box = fr.bounding_box()
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            pg.mouse.move(cx, cy)
            pg.keyboard.down("Control")
            pg.mouse.wheel(0, -400)
            pg.keyboard.up("Control")
            pg.wait_for_timeout(700)
            s2 = ink(pg)
            check("Ctrl+wheel zooms INSIDE sandboxed embed", s1 != s2, f"{s1} -> {s2}")
            pg.screenshot(path=str(SHOT / f"publish_{RID}_bode_modal.png"))
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(600)
            if pg.query_selector("iframe"):
                pg.click("text=✕") if pg.query_selector("text=✕") else pg.keyboard.press("Escape")
                pg.wait_for_timeout(500)

        # ── work-plan 모달 (멀티엔진 컴포지트)
        fr = open_modal_by_index(pg, 2)  # embed 2 = work-plan
        check("work-plan modal iframe", fr is not None)
        if fr:
            pg.wait_for_timeout(1500)
            pg.screenshot(path=str(SHOT / f"publish_{RID}_workplan_modal.png"))
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(500)

        # ── 3D WebGL 모달: 드래그 회전이 동작하는가 (픽셀 diff)
        fr = open_modal_by_index(pg, 7)  # embed 7 = mesh-result-3d
        check("3D modal iframe", fr is not None)
        if fr:
            pg.wait_for_timeout(2000)
            s1 = ink(pg)
            box = fr.bounding_box()
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            pg.mouse.move(cx, cy)
            pg.mouse.down()
            pg.mouse.move(cx + 150, cy + 60, steps=8)
            pg.mouse.up()
            pg.wait_for_timeout(700)
            s2 = ink(pg)
            check("WebGL orbit works in sandboxed embed", s1 != s2, f"{s1} -> {s2}")
            pg.screenshot(path=str(SHOT / f"publish_{RID}_3d_modal.png"))
            pg.keyboard.press("Escape")

        real = [e for e in errs if "favicon" not in e.lower() and "React Router" not in e]
        check("no console errors", not real, "; ".join(real[:3]))

        # 모바일
        m = b.new_context(viewport={"width": 400, "height": 800})
        mp = m.new_page()
        login(mp)
        mp.goto(f"{BASE}/w/personal-3/reports/{RID}", wait_until="load")
        mp.wait_for_timeout(4000)
        mp.screenshot(path=str(SHOT / f"publish_{RID}_mobile.png"), full_page=True)
        m.close()
        b.close()

    print(("\nPUBLISH CHECKS PASSED" if not FAILS else f"\n{len(FAILS)} FAILED: {FAILS}"))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
