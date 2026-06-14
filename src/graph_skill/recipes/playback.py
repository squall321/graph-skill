"""playback recipes — time-driven animation via the xy-core `playback` plugin.
All frames are embedded; the artifact stays deterministic (client-side replay).
A style:"none" carrier series is emitted so the engine autoscales axes to cover
every frame. Three types share one plugin:
  bubble-timeline     (mode bubble) — Gapminder-style moving/resizing points
  animated-trajectory (mode trail)  — marker sweeping a path (phase-portrait/sweep/hysteresis)
  bar-chart-race      (mode race)   — ranked horizontal bars over time
"""

from __future__ import annotations

import math

from .base import Recipe



def _carrier_series(pairs):
    """Engine setData reads s.x/s.y arrays — emit the autoscale carrier in that shape."""
    pairs = pairs or [[0, 0]]
    return [{"name": "_carrier", "style": "none",
             "x": [p[0] for p in pairs], "y": [p[1] for p in pairs]}]

def _axis(ax, key, dflt_label, dflt_unit):
    a = (ax or {}).get(key) or {}
    return {"label": str(a.get("label", dflt_label)), "unit": str(a.get("unit", dflt_unit)),
            "log": a.get("scale", "linear") == "log"}


class BubbleTimelineRecipe(Recipe):
    type_name = "bubble-timeline"

    def normalize(self, payload: dict, resolved) -> dict:
        frames_in = payload.get("frames") or []
        # size -> pixel radius mapping (sqrt area) when `r` not given
        smax = 0.0
        for fr in frames_in:
            for e in fr.get("entities") or []:
                if e.get("size") is not None:
                    smax = max(smax, float(e["size"]))
        carrier = []
        frames = []
        for fr in frames_in:
            ents = []
            for e in fr.get("entities") or []:
                x, y = float(e["x"]), float(e["y"])
                carrier.append([x, y])
                if e.get("r") is not None:
                    r = float(e["r"])
                elif e.get("size") is not None and smax > 0:
                    r = 6.0 + 26.0 * math.sqrt(float(e["size"]) / smax)
                else:
                    r = 11.0
                ent = {"id": str(e.get("id", e.get("label", len(ents)))), "x": x, "y": y, "r": round(r, 2)}
                if e.get("label") is not None:
                    ent["label"] = str(e["label"])
                if e.get("color"):
                    ent["color"] = e["color"]
                ents.append(ent)
            frames.append({"t": fr.get("t"), "entities": ents})

        opts = payload.get("options") or {}
        options = {
            "axes": {"x": _axis(payload.get("axes"), "x", "X", ""), "y": _axis(payload.get("axes"), "y", "Y", "")},
            "pluginConfig": {"playback": {
                "mode": "bubble", "frames": frames,
                "fps": float(opts.get("fps", 1.2)), "loop": opts.get("loop", True),
            }},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        series = _carrier_series(carrier)
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload: dict) -> list:
        miss = []
        frames = payload.get("frames") or []
        if len(frames) < 2:
            miss.append({"field": "frames", "why": "재생할 시간 프레임이 2개 미만",
                         "ask": "프레임 시퀀스를 주세요: frames:[{t:'2020', entities:[{id,x,y,size?,label?}]}, …] (각 프레임=한 시점)."})
        else:
            ok = any(e.get("x") is not None and e.get("y") is not None
                     for fr in frames for e in (fr.get("entities") or []))
            if not ok:
                miss.append({"field": "frames[].entities", "why": "엔티티에 x,y 좌표가 없음",
                             "ask": "각 프레임의 entities[]에 x,y(+size,label)를 채워주세요."})
        for k in ("x", "y"):
            a = (payload.get("axes") or {}).get(k) or {}
            if not a.get("label") or a.get("unit") is None:
                miss.append({"field": f"axes.{k}", "why": f"{k}축 의미/단위 미상",
                             "ask": f"{k}축의 label과 unit을 알려주세요(무차원이면 unit=\"\")."})
        return miss


class AnimatedTrajectoryRecipe(Recipe):
    type_name = "animated-trajectory"

    def normalize(self, payload: dict, resolved) -> dict:
        path = payload.get("path")
        if not path and payload.get("series"):
            d = (payload["series"][0] or {}).get("data") or []
            path = [[p[0], p[1]] if isinstance(p, (list, tuple)) else [p["x"], p["y"]] for p in d]
        path = [[float(p[0]), float(p[1])] for p in (path or [])]
        opts = payload.get("options") or {}
        pcfg = {"mode": "trail", "path": path, "fps": float(opts.get("fps", 18)),
                "loop": opts.get("loop", True)}
        if payload.get("times"):
            pcfg["times"] = list(payload["times"])
        if opts.get("trail_len"):
            pcfg["trail_len"] = int(opts["trail_len"])
        options = {
            "axes": {"x": _axis(payload.get("axes"), "x", "X", ""), "y": _axis(payload.get("axes"), "y", "Y", "")},
            "curve": opts.get("curve", "straight"),
            "pluginConfig": {"playback": pcfg},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        series = _carrier_series(path)
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload: dict) -> list:
        miss = []
        path = payload.get("path")
        if not path and payload.get("series"):
            path = (payload["series"][0] or {}).get("data")
        if not path or len(path) < 2:
            miss.append({"field": "path", "why": "궤적 점이 2개 미만",
                         "ask": "궤적 좌표열을 주세요: path:[[x,y], …] (시간 순서; 위상평면이면 [x, dx/dt])."})
        for k in ("x", "y"):
            a = (payload.get("axes") or {}).get(k) or {}
            if not a.get("label") or a.get("unit") is None:
                miss.append({"field": f"axes.{k}", "why": f"{k}축 의미/단위 미상",
                             "ask": f"{k}축의 label과 unit을 알려주세요(무차원이면 unit=\"\")."})
        return miss


class BarChartRaceRecipe(Recipe):
    type_name = "bar-chart-race"

    def normalize(self, payload: dict, resolved) -> dict:
        frames_in = payload.get("frames") or []
        ids = []
        maxv = 1.0
        frames = []
        for fr in frames_in:
            ents = []
            for e in fr.get("entities") or []:
                v = float(e.get("value", 0))
                maxv = max(maxv, v)
                eid = str(e.get("id", e.get("label", len(ents))))
                if eid not in ids:
                    ids.append(eid)
                ent = {"id": eid, "label": str(e.get("label", eid)), "value": v}
                if e.get("color"):
                    ent["color"] = e["color"]
                ents.append(ent)
            frames.append({"t": fr.get("t"), "entities": ents})

        opts = payload.get("options") or {}
        top = int(opts.get("top", min(12, len(ids))))
        vl = payload.get("value_label") or "값"
        vu = payload.get("value_unit", "")
        options = {
            "axes": {"x": {"label": str(vl), "unit": str(vu)}, "y": {"label": "순위", "unit": ""}},
            "pluginConfig": {"playback": {
                "mode": "race", "frames": frames, "top": top,
                "fps": float(opts.get("fps", 1.6)), "loop": opts.get("loop", True),
            }},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        carrier = [[0, 0], [maxv * 1.08, max(1, top)]]
        series = _carrier_series(carrier)
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload: dict) -> list:
        miss = []
        frames = payload.get("frames") or []
        if len(frames) < 2:
            miss.append({"field": "frames", "why": "재생할 시간 프레임이 2개 미만",
                         "ask": "프레임 시퀀스를 주세요: frames:[{t:'1월', entities:[{id,label,value}]}, …]."})
        elif not any(e.get("value") is not None for fr in frames for e in (fr.get("entities") or [])):
            miss.append({"field": "frames[].entities[].value", "why": "막대 값(value)이 없음",
                         "ask": "각 엔티티의 value(막대 길이)를 채워주세요."})
        return miss
