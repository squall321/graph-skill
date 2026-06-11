"""node_*.mjs가 읽는 렌더 산출물을 사전 생성한다 (CI/클린 체크아웃용).
node 테스트는 두 종류 이름을 읽는다: ① <type>.html (pytest가 생성) ② 레거시 fixture명
(base_xy.html 등 — 초기 phase 테스트 시절 명명). 여기서 ②와, pytest에 의존하고 싶지 않은
①의 안전망까지 한 번에 렌더한다. 사용: python tests/render_node_fixtures.py"""
import json
import pathlib
import re

from graph_skill import builder

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"

# 레거시 산출물명 → (type, fixture)
LEGACY = {
    "base_xy": ("base-xy", "base_xy"),
    "stress_strain": ("stress-strain", "stress_strain"),
    "design_state": ("design-state-compare", "design_state"),
    "field": ("contour-plot", "field"),
    "fft": ("fft-spectrum", "signal"),
    "filter": ("filter-tuner", "filter_signal"),
    "histogram": ("histogram", "hist"),
    "bode": ("bode", "bode"),
    "pattern": ("rf-radiation-pattern", "pattern"),
    "cad-3d-viewer": ("cad-3d-viewer", "cad_viewer"),
    "parallel-coordinates": ("parallel-coordinates", "parcoord"),
    "residual": ("residual-diagnostic-panel", "residual"),
    "nyquist": ("nyquist-plot", "nyquist"),
    "rootlocus": ("root-locus", "rootlocus"),
    "smith-chart": ("smith-chart", "smith"),
    "weibull": ("weibull-prob-paper", "weibull"),
    "polar": ("polar-plot", "pattern"),
    "radar": ("radar-chart", "radar"),
    "capability": ("process-capability-hist", "capability"),
    "spc": ("spc-control-chart", "spc"),
    "dual": ("dual-axis", "dual"),
    "box": ("box-plot", "box"),
    "qq": ("qq-plot", "qq"),
    "ecdf": ("ecdf-plot", "ecdf"),
    "pareto": ("pareto", "pareto"),
    "bar": ("bar-plot", "bar"),
    "correlation": ("correlation-scatter", "correlation"),
    "errbar": ("error-bar", "errbar"),
    "force_displacement": ("force-displacement", "force_displacement"),
}


def referenced_names():
    names = set()
    for f in (ROOT / "tests").glob("node_*.mjs"):
        for m in re.finditer(r'"([A-Za-z0-9_\-]+)\.html"', f.read_text(encoding="utf-8")):
            names.add(m.group(1))
    return names


def main():
    # 갤러리 MAP에서 <type> → fixture 역매핑 (타입명 산출물용)
    gal = (ROOT / "build_gallery.py").read_text(encoding="utf-8")
    type_fix = dict(re.findall(r'\("([\w\-]+)",\s*"([\w\-]+)",', gal))

    done, miss = 0, []
    for name in sorted(referenced_names()):
        out = ROOT / "graph-out" / f"{name}.html"
        if out.exists():
            continue
        if name in LEGACY:
            t, fx = LEGACY[name]
        elif name in type_fix:
            t, fx = name, type_fix[name]
        else:
            miss.append(name)
            continue
        payload = json.loads((FIX / f"{fx}.json").read_text(encoding="utf-8"))
        builder.render(t, payload, out_path=str(out))
        done += 1
    print(f"rendered {done} node-test artifacts" + (f"; UNMAPPED: {miss}" if miss else ""))
    if miss:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
