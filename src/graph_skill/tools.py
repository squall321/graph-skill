"""Shared tool logic — the single implementation behind both the MCP server and the CLI
(3-view golden rule). Pure functions returning JSON-serializable dicts; no mcp/typer deps
so it stays unit-testable.
"""

from __future__ import annotations

import re

from . import builder, catalog, prompt, taxonomy, validate
from .settings import Settings

# --- JSON Schemas (shared by MCP tool registration) ------------------------------

_AXIS_SCHEMA = {
    "type": "object",
    "required": ["label", "unit"],
    "properties": {
        "label": {"type": "string", "description": "물리량 이름 (예: 'Time', '응력')"},
        "unit": {"type": "string", "description": "단위. 무차원이면 빈 문자열 ''"},
        "scale": {"enum": ["linear", "log"], "default": "linear"},
    },
}

_SERIES_SCHEMA = {
    "type": "array",
    "minItems": 1,
    "items": {
        "type": "object",
        "required": ["name", "data"],
        "properties": {
            "name": {"type": "string"},
            "data": {
                "type": "array",
                "description": "각 점은 [x, y] 또는 {x, y}. y 가 null/비유한이면 선이 끊김(gap).",
                "items": {
                    "oneOf": [
                        {"type": "array", "minItems": 2, "maxItems": 2},
                        {"type": "object", "required": ["x", "y"]},
                    ]
                },
            },
            "color": {"type": "string"},
            "style": {"enum": ["line", "markers", "line+markers", "step"], "default": "line"},
            "axis": {"enum": ["left", "right"], "default": "left"},
        },
    },
}

# payload (validate) = render minus out_path/embed_mode
_PAYLOAD_PROPS = {
    "graph_type": {"type": "string", "enum": catalog.known_types()},
    "series": _SERIES_SCHEMA,
    "axes": {"type": "object", "required": ["x", "y"], "properties": {"x": _AXIS_SCHEMA, "y": _AXIS_SCHEMA}},
    "params": {"type": "object", "description": "타입별 필수 물리 배경값 (예: {A0, L0, fs}). base-xy 는 불필요."},
    "options": {"type": "object", "description": "선택적 외형 override (curve/palette/theme/legend...). 보통 생략."},
    "title": {"type": "string"},
    "features": {"type": "array", "items": {"type": "string"}},
    # review-matrix family (점검/비교표): cells can be number/status/text/image/graph
    "states": {"type": "array", "description": "review-matrix: 열=설계 state [{id,label,...}]"},
    "items": {"type": "array", "description": "review-matrix: 행=점검항목 [{id,group,label,unit?,type,spec?,cells}]"},
    "spec": {"type": "object", "description": "review-matrix: 항목 외 공통 spec/targets/weights"},
    "meta": {"type": "object", "description": "review-matrix: {baseline, domain, model, source_records...}"},
    # field-core (contour/heatmap) — isosurface-3d 는 3D 배열 또는 "metaballs" 문자열도 허용
    "field": {"description": "field-core: {x:[nx], y:[ny], z:[[ny×nx]]} 2D 스칼라장 / isosurface-3d: [nx][ny][nz] 3D 배열 또는 'metaballs'"},
    "z": {"type": "object", "description": "색 축 메타 {label, unit}"},
}

# NOTE: 타입별 최상위 키(nodes/edges/links/tree/frames/path/steps/variables/matrix/points/
# z_grid/mesh/channels/value 등)는 graph_schema_get 의 hint 가 SSOT. 여기 미열거 키를
# additionalProperties:false 로 막으면 신규 패밀리 호출이 전부 거부되므로 막지 않는다.
VALIDATE_SCHEMA = {
    "type": "object",
    "required": ["graph_type"],
    "properties": _PAYLOAD_PROPS,
}

RENDER_SCHEMA = {
    "type": "object",
    "required": ["graph_type", "out_path"],
    "properties": {
        **_PAYLOAD_PROPS,
        "out_path": {"type": "string", "description": "산출 .html 절대경로"},
        "embed_mode": {"enum": ["standalone", "srcdoc-fragment"], "default": "standalone"},
    },
}

TOOLS = [
    {
        "name": "graph_types_list",
        "description": "사용 가능한 그래프 타입을 '목적 카테고리(19)'로 분류한 인덱스 + 타입별 dims/use_when/입력형태/필수배경값. 항상 먼저 호출. categories를 먼저 훑어 의도→카테고리→타입으로 좁힌다.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "graph_find",
        "description": "자연어 목적(예: '피로 수명', '3d 응력', '공정 능력')으로 적합한 그래프 타입 후보를 즉시 검색(순위). 타입이 많아 고르기 애매할 때 graph_types_list 대신 빠르게.",
        "inputSchema": {"type": "object", "required": ["query"], "properties": {
            "query": {"type": "string"}}, "additionalProperties": False},
    },
    {
        "name": "graph_schema_get",
        "description": "한 타입의 입력 스키마 + requires[](필수 물리 배경값) + plugin 목록 + 힌트. 렌더 전에 무엇이 필요한지 확인.",
        "inputSchema": {
            "type": "object",
            "required": ["graph_type"],
            "properties": {"graph_type": {"type": "string", "enum": catalog.known_types()}},
            "additionalProperties": False,
        },
    },
    {
        "name": "graph_validate_inputs",
        "description": "렌더 전 필수. 입력을 검증해 missing[]+questions[] 를 돌려준다. missing 가 비어있지 않으면 렌더하지 말고 사용자에게 질문하라.",
        "inputSchema": VALIDATE_SCHEMA,
    },
    {
        "name": "graph_render",
        "description": "검증된 입력으로 단일 self-contained 인터랙티브 .html 을 생성한다. 배경값이 부족하면 렌더 대신 needs_input 을 반환한다.",
        "inputSchema": RENDER_SCHEMA,
    },
    {
        "name": "graph_lint_output",
        "description": "산출 HTML 정적 검증: 외부 URL 0개 / 단일 루트 / self-contained. 게시 전 게이트.",
        "inputSchema": {
            "type": "object",
            "required": ["html_path"],
            "properties": {"html_path": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "graph_embed_block",
        "description": "산출 HTML 경로를 report-write 의 html_embed draft 조각(JSON)으로 변환. local_path 는 업로드 시 file_id 로 치환된다.",
        "inputSchema": {
            "type": "object",
            "required": ["html_path"],
            "properties": {
                "html_path": {"type": "string"},
                "height_px": {"type": "integer", "minimum": 60, "maximum": 4000, "default": 520},
                "caption": {"type": "string", "maxLength": 200},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "ingest_csv",
        "description": "장비 raw CSV/TSV 텍스트를 수치 컬럼으로 파싱(헤더/단위행/구분자 자동). HTML 아님 — 컬럼을 골라 series로 구성해 graph_render.",
        "inputSchema": {"type": "object", "required": ["text"], "properties": {
            "text": {"type": "string"}, "delimiter": {"type": "string"},
            "header": {"type": "boolean", "default": True}, "units_row": {"type": "boolean", "default": False}},
            "additionalProperties": False},
    },
    {
        "name": "resample",
        "description": "시계열을 균일 dt 그리드로 리샘플(선형보간). 비균일 입력 여부(uniform_input)도 반환. 수치만(HTML 아님). FFT/SG 전처리.",
        "inputSchema": {"type": "object", "required": ["series"], "properties": {
            "series": {"type": "array"}, "n": {"type": "integer"}, "dt": {"type": "number"}},
            "additionalProperties": False},
    },
    {
        "name": "smooth",
        "description": "스무딩(savgol|moving). window(홀수)/polyorder. 수치만(HTML 아님).",
        "inputSchema": {"type": "object", "required": ["series"], "properties": {
            "series": {"type": "array"}, "method": {"enum": ["savgol", "moving"], "default": "savgol"},
            "window": {"type": "integer", "default": 7}, "polyorder": {"type": "integer", "default": 2}},
            "additionalProperties": False},
    },
]


# --- helpers --------------------------------------------------------------------

_CONTROL_KEYS = ("graph_type", "out_path", "embed_mode")


def _payload(args: dict) -> dict:
    """All data keys flow through (engine-agnostic). Control keys are excluded so a new
    family's top-level inputs (series/axes, states/items, field/z, ...) never get dropped."""
    return {k: v for k, v in args.items() if k not in _CONTROL_KEYS and v is not None}


def _safe_name(name: str) -> str:
    s = re.sub(r"[^\w.-]+", "_", str(name)).strip("._")
    return s or "graph"


# --- tool implementations -------------------------------------------------------

def types_list() -> dict:
    """Categorized index for fast 'goal → category → type' selection, plus the enriched flat
    list. The LLM should scan ``categories`` first, then drill into a type's schema."""
    flat = catalog.list_types()
    for t in flat:
        m = taxonomy.meta(t["name"])
        t["category"] = m.get("category", "")
        t["dims"] = m.get("dims", "")
        t["use_when"] = m.get("use_when", "")
        t["data_shape"] = m.get("data", "")
    groups = [
        {"id": c["id"], "title": c["title"], "desc": c["desc"], "when": c["when"],
         "types": [{"name": x["name"], "dims": x.get("dims", ""), "use_when": x.get("use_when", ""),
                    "data": x.get("data", "")} for x in c["types"]]}
        for c in taxonomy.grouped()
    ]
    return {"categories": groups, "types": flat, "count": len(flat), "rule": prompt.PREAMBLE}


def types_find(query: str) -> dict:
    """Rank types by a free-text goal (keywords/use_when/category). Use to jump straight to
    candidates, then graph_schema_get the chosen one."""
    return {"query": query, "matches": taxonomy.find(query, 8), "rule": prompt.PREAMBLE}


def schema_get(graph_type: str) -> dict:
    sch = catalog.get_schema(graph_type)
    sch["input_schema"] = RENDER_SCHEMA
    sch["hint"] = prompt.hint_for(graph_type) or sch.get("hint", "")
    sch["rule"] = prompt.PREAMBLE
    return sch


def validate_inputs(graph_type: str, payload: dict) -> dict:
    res = validate.check(graph_type, payload)
    if not res["ok"]:
        res["rule"] = prompt.PREAMBLE
        # fall back to the catalog hint — _INPUT_HINTS only covers the early families
        res["hint"] = prompt.hint_for(graph_type) or catalog.get_schema(graph_type).get("hint", "")
    return res


def render(
    graph_type: str,
    series: list | None = None,
    axes: dict | None = None,
    params: dict | None = None,
    options: dict | None = None,
    title: str | None = None,
    features: list | None = None,
    out_path: str | None = None,
    embed_mode: str = "standalone",
    states: list | None = None,
    items: list | None = None,
    spec: dict | None = None,
    meta: dict | None = None,
) -> dict:
    payload = _payload(
        {"series": series, "axes": axes, "params": params, "options": options, "title": title,
         "features": features, "states": states, "items": items, "spec": spec, "meta": meta}
    )
    return render_payload(graph_type, payload, out_path=out_path, embed_mode=embed_mode)


def render_payload(graph_type: str, payload: dict, out_path: str | None = None,
                   embed_mode: str = "standalone") -> dict:
    """Engine-agnostic render entry — takes a full payload dict (any family). On missing
    background inputs returns needs_input (the gate) instead of raising."""
    if not out_path:
        s = Settings.load()
        out_path = str(s.out_dir / f"{_safe_name(payload.get('title') or graph_type)}.html")
    try:
        res = builder.render(graph_type, payload, out_path=out_path, embed_mode=embed_mode)
        res["status"] = "ok"
        res["next"] = "graph_lint_output -> graph_embed_block (게시 시)"
        return res
    except builder.MissingFieldsError as e:
        return {
            "status": "needs_input",
            "graph_type": graph_type,
            "missing": e.missing,
            "questions": [m["ask"] for m in e.missing],
            "rule": prompt.PREAMBLE,
        }


def lint_output(html_path: str) -> dict:
    return builder.lint_file(html_path)


def embed_block(html_path: str, height_px: int | None = None, caption: str | None = None) -> dict:
    return builder.embed_block(html_path, height_px=height_px, caption=caption)


# --- equipment raw post-processing helpers (return numeric, not HTML) -----------

def _xy(s: dict):
    if isinstance(s.get("x"), list) and isinstance(s.get("y"), list):
        return list(s["x"]), list(s["y"])
    xs, ys = [], []
    for pt in (s.get("data") or []):
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            try:
                xs.append(float(pt[0]))
            except (TypeError, ValueError):
                continue
            try:
                ys.append(float(pt[1]))
            except (TypeError, ValueError):
                ys.append(None)
        elif isinstance(pt, dict) and "x" in pt:
            xs.append(float(pt["x"]))
            try:
                ys.append(float(pt.get("y")))
            except (TypeError, ValueError):
                ys.append(None)
    return xs, ys


def ingest_csv(text: str, delimiter: str | None = None, header: bool = True, units_row: bool = False) -> dict:
    from .postprocess import ingest
    return ingest.parse_csv(text, delimiter=delimiter, header=header, units_row=units_row)


def resample(series: list, n: int | None = None, dt: float | None = None) -> dict:
    from .postprocess import resample as _R
    out, uni = [], []
    for s in series or []:
        x, y = _xy(s)
        uni.append(_R.is_uniform(x))
        gx, gy = _R.resample_uniform(x, y, n=n, dt=dt)
        out.append({"name": s.get("name", "series"), "data": [[gx[i], gy[i]] for i in range(len(gx))]})
    return {"series": out, "uniform_input": uni}


def smooth(series: list, method: str = "savgol", window: int = 7, polyorder: int = 2) -> dict:
    from .postprocess import smoothing as _S
    out = []
    for s in series or []:
        x, y = _xy(s)
        ys = _S.moving_average(y, window) if method == "moving" else _S.savgol(y, window, polyorder)
        out.append({"name": s.get("name", "series"), "data": [[x[i], ys[i]] for i in range(len(x))]})
    return {"series": out}


# --- dispatch (used by MCP server) ----------------------------------------------

DISPATCH = {
    "graph_types_list": lambda a: types_list(),
    "graph_find": lambda a: types_find(a["query"]),
    "graph_schema_get": lambda a: schema_get(a["graph_type"]),
    "graph_validate_inputs": lambda a: validate_inputs(a["graph_type"], _payload(a)),
    "graph_render": lambda a: render_payload(
        a["graph_type"], _payload(a), a.get("out_path"), a.get("embed_mode", "standalone")
    ),
    "graph_lint_output": lambda a: lint_output(a["html_path"]),
    "graph_embed_block": lambda a: embed_block(a["html_path"], a.get("height_px"), a.get("caption")),
    "ingest_csv": lambda a: ingest_csv(a["text"], a.get("delimiter"), a.get("header", True), a.get("units_row", False)),
    "resample": lambda a: resample(a["series"], a.get("n"), a.get("dt")),
    "smooth": lambda a: smooth(a["series"], a.get("method", "savgol"), a.get("window", 7), a.get("polyorder", 2)),
}
