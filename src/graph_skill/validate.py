"""The completeness gate. ``check`` computes the set of missing background inputs so the
LLM can ask the user before rendering. This is the data-driven implementation of the
"NEVER invent physical params" rule — there is no path that renders with guessed values.
"""

from __future__ import annotations

from . import catalog
from .recipes import REGISTRY


def _dig(payload: dict, dotted: str):
    cur = payload
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur


def check(graph_type: str, payload: dict) -> dict:
    """Return {ok, missing[], questions[], normalized_preview?}.

    ``missing`` items are {field, why, ask}. ``ok`` is True only when every required
    background param and both axis meta are present. When ok, a small normalized preview
    is attached so the caller can sanity-check the shaping before rendering.
    """
    rt = catalog.resolve_type(graph_type)
    missing: list[dict] = []

    for r in rt.requires:
        if _dig(payload, r["field"]) is None:
            missing.append({"field": r["field"], "why": r.get("why", ""), "ask": r.get("ask", "")})

    if rt.require_axes:
        for ax in ("x", "y"):
            a = _dig(payload, f"axes.{ax}")
            # unit may be "" (dimensionless) but the KEY must be present and label non-empty
            if not (isinstance(a, dict) and a.get("label") and ("unit" in a)):
                missing.append(
                    {
                        "field": f"axes.{ax}",
                        "why": "축 의미/단위 미상 → 눈금 SI 접두·툴팁 단위·로그 가드 불가",
                        "ask": (
                            f"{ax}축이 무슨 물리량이고 단위가 무엇인가요? "
                            "(예: '시간 [s]', '응력 [MPa]'; 무차원이면 unit 을 빈 문자열로)"
                        ),
                    }
                )

    if rt.require_series and not (payload.get("series") or _dig(payload, "assets.series")):
        missing.append(
            {"field": "series", "why": "그릴 데이터가 없음", "ask": "그릴 (x,y) 시리즈 데이터를 알려주세요."}
        )

    recipe = REGISTRY.get(graph_type)
    # structural gate (validate-v2): array-length / referential-integrity / asset-presence
    # checks that a single dotted-path scalar can't express (states>=2, baseline in states...).
    if recipe is not None and hasattr(recipe, "structural_requires"):
        try:
            sp = dict(payload)
            sp["graph_type"] = graph_type  # so the hook can branch on the type
            for m in recipe.structural_requires(sp) or []:
                missing.append(m)
        except Exception:  # noqa: BLE001 — structural hook must never crash the gate
            pass

    seen_fields: set = set()
    deduped: list[dict] = []
    for m in missing:                       # require_axes + structural hooks may both flag the same field
        key = m.get("field")
        if key in seen_fields:
            continue
        seen_fields.add(key)
        deduped.append(m)
    missing = deduped

    result = {"ok": not missing, "missing": missing, "questions": [m["ask"] for m in missing]}

    if not missing:
        if recipe is not None:
            try:
                norm = recipe.normalize(payload, rt)
                sers = norm["assets"].get("series", [])

                def _plen(s):
                    for kk in ("x", "theta", "r", "data"):
                        if isinstance(s.get(kk), list):
                            return len(s[kk])
                    return 0

                result["normalized_preview"] = {
                    "engine": norm["engine"],
                    "series_count": len(sers),
                    "points_per_series": [_plen(s) for s in sers],
                }
            except Exception as e:  # shaping failure surfaces as a question, not a crash
                result["ok"] = False
                result["missing"].append(
                    {
                        "field": "series",
                        "why": f"데이터 정규화 실패: {e}",
                        "ask": "데이터 형식을 확인해 주세요 (각 점은 [x, y] 쌍 또는 {x, y}).",
                    }
                )
                result["questions"] = [m["ask"] for m in result["missing"]]

    return result
