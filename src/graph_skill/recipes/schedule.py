"""schedule/plan family — gantt-chart · milestone-timeline · calendar-heatmap (xy-core
plugins on a hidden-axes date frame) + task-table (review-matrix rich cells) +
work-plan (composite 업무계획서: overview rows + KPI stat-cards + gantt + timeline +
risk heat — multiple engines bundled into ONE self-contained artifact via graph cells).

Dates are ISO "YYYY-MM-DD" strings, parsed to epoch DAYS in Python (deterministic).
The TODAY line is drawn client-side at view time (always current, bytes unchanged).
D-day style derived values require an explicit `as_of` date — never the build clock."""

from __future__ import annotations

import datetime as _dt

from .base import Recipe
from .matrix_compare import MatrixRecipe

_EPOCH = _dt.date(1970, 1, 1)


def _day(iso):
    """ISO date -> epoch day, or None if unparseable."""
    try:
        return (_dt.date.fromisoformat(str(iso).strip()) - _EPOCH).days
    except (ValueError, TypeError):
        return None


def _fmt(day):
    d = _EPOCH + _dt.timedelta(days=int(day))
    return f"{d.month}/{d.day}"


def _date_ticks(t0, t1):
    """Nice date ticks across [t0, t1] (daily / weekly-Mon / monthly)."""
    span = t1 - t0
    ticks = []
    if span <= 21:                                   # daily
        for t in range(int(t0), int(t1) + 1):
            ticks.append({"t": t, "label": _fmt(t)})
    elif span <= 150:                                # weekly (Mondays)
        t = int(t0) + ((0 - (int(t0) + 3)) % 7)      # epoch day 0 = Thu; Monday ≡ 4 (mod 7)
        while t <= t1:
            if t >= t0:
                ticks.append({"t": t, "label": _fmt(t)})
            t += 7
    else:                                            # monthly (1st)
        d = _EPOCH + _dt.timedelta(days=int(t0))
        d = _dt.date(d.year + (1 if d.month == 12 else 0), 1 if d.month == 12 else d.month + 1, 1) \
            if d.day > 1 else d
        while (d - _EPOCH).days <= t1:
            ticks.append({"t": (d - _EPOCH).days,
                          "label": f"{d.year}-{d.month:02d}" if d.month == 1 or not ticks else f"{d.month}월"})
            d = _dt.date(d.year + (1 if d.month == 12 else 0), 1 if d.month == 12 else d.month + 1, 1)
    return ticks


def _ask_dates(field, what):
    return {"field": field, "why": f"{what}의 날짜가 없거나 형식 오류",
            "ask": f"{what}의 날짜를 ISO 형식(YYYY-MM-DD)으로 알려주세요."}


class GanttRecipe(Recipe):
    type_name = "gantt-chart"

    def normalize(self, payload, resolved):
        tasks = payload.get("tasks") or []
        rows, name_idx = [], {}
        for t in tasks:
            s = _day(t.get("start"))
            e = _day(t.get("end")) if t.get("end") is not None else s
            row = {"name": str(t.get("name", "")), "start": s, "end": e}
            for k in ("group", "owner", "color"):
                if t.get(k) is not None:
                    row[k] = str(t[k])
            if t.get("milestone"):
                row["milestone"] = True
                row["end"] = s
            if t.get("progress") is not None:
                row["progress"] = max(0.0, min(1.0, float(t["progress"])))
            name_idx[row["name"]] = len(rows)
            rows.append(row)
        deps = []
        for i, t in enumerate(tasks):
            for d in (t.get("deps") or []):
                j = d if isinstance(d, int) else name_idx.get(str(d))
                if j is not None and 0 <= j < len(rows) and j != i:
                    deps.append([j, i])
        t0 = min(r["start"] for r in rows)
        t1 = max(r["end"] for r in rows)
        pad = max(1, round((t1 - t0) * 0.04))
        t0, t1 = t0 - pad, t1 + pad
        pad_left = min(200, 24 + max(len(r["name"]) for r in rows) * 11)
        opts_in = payload.get("options") or {}
        options = {
            "hideAxes": True,
            "pad": {"left": pad_left, "right": 16, "bottom": 22},
            "axes": {"x": {"label": "날짜", "unit": ""}, "y": {"label": "", "unit": ""}},
            "interactions": {"zoom": True},
            "pluginConfig": {"gantt": {
                "rows": rows, "deps": deps, "t0": t0, "t1": t1,
                "ticks": _date_ticks(t0, t1),
                "today": opts_in.get("today", True),
                "weekends": opts_in.get("weekends", True),
            }},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        n = len(rows)
        series = [{"name": "_gantt", "style": "none", "x": [t0, t1], "y": [-0.5, n - 0.5]}]
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        tasks = payload.get("tasks") or []
        if not tasks:
            return [{"field": "tasks", "why": "일정 작업이 없음",
                     "ask": "작업 목록을 주세요: tasks:[{name, start:'YYYY-MM-DD', end:'YYYY-MM-DD', "
                            "progress?(0~1), group?, owner?, deps?[선행작업명], milestone?}]."}]
        bad = [t.get("name", "?") for t in tasks
               if _day(t.get("start")) is None
               or (not t.get("milestone") and _day(t.get("end")) is None)
               or (_day(t.get("end")) is not None and _day(t.get("start")) is not None
                   and _day(t.get("end")) < _day(t.get("start")))]
        if bad:
            return [{"field": "tasks", "why": f"날짜 누락/형식오류/역전: {bad[:3]}",
                     "ask": "각 작업의 start/end를 ISO(YYYY-MM-DD)로, end ≥ start가 되게 알려주세요."}]
        return []


class MilestoneTimelineRecipe(Recipe):
    type_name = "milestone-timeline"

    def normalize(self, payload, resolved):
        evs = []
        for e in payload.get("events") or payload.get("milestones") or []:
            t = _day(e.get("date"))
            ev = {"t": t, "label": str(e.get("label", ""))}
            if e.get("status") in ("done", "active", "pending"):
                ev["status"] = e["status"]
            for k in ("desc", "color"):
                if e.get(k):
                    ev[k] = str(e[k])
            evs.append(ev)
        evs.sort(key=lambda x: x["t"])
        t0, t1 = evs[0]["t"], evs[-1]["t"]
        pad = max(2, round((t1 - t0) * 0.07)) if t1 > t0 else 7
        t0, t1 = t0 - pad, t1 + pad
        options = {
            "hideAxes": True,
            "pad": {"left": 16, "right": 16, "bottom": 20},
            "axes": {"x": {"label": "날짜", "unit": ""}, "y": {"label": "", "unit": ""}},
            "pluginConfig": {"timeline": {
                "events": evs, "t0": t0, "t1": t1, "ticks": _date_ticks(t0, t1),
                "today": (payload.get("options") or {}).get("today", True),
            }},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        series = [{"name": "_tl", "style": "none", "x": [t0, t1], "y": [0, 1]}]
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        evs = payload.get("events") or payload.get("milestones") or []
        if not evs:
            return [{"field": "events", "why": "마일스톤 이벤트가 없음",
                     "ask": "이벤트를 주세요: events:[{date:'YYYY-MM-DD', label, status?(done|active|pending), desc?}]."}]
        if any(_day(e.get("date")) is None for e in evs):
            return [_ask_dates("events[].date", "각 이벤트")]
        return []


class CalendarHeatmapRecipe(Recipe):
    type_name = "calendar-heatmap"

    def normalize(self, payload, resolved):
        ent = payload.get("entries") or []
        vals = {}
        for e in ent:
            d = _day(e.get("date") if isinstance(e, dict) else e)
            v = float(e.get("value", 1)) if isinstance(e, dict) else 1.0
            vals[d] = vals.get(d, 0.0) + v
        t0, t1 = min(vals), max(vals)
        monday0 = t0 - ((t0 + 3) % 7)                # epoch day 0 = Thu → Monday-aligned origin
        cells, months, seen_m = [], [], set()
        for d in range(monday0, t1 + 1):
            w, dw = (d - monday0) // 7, (d - monday0) % 7
            date = _EPOCH + _dt.timedelta(days=d)
            if date.day == 1 or (d == monday0 and not months):
                key = (date.year, date.month)
                if key not in seen_m:
                    seen_m.add(key)
                    months.append({"w": w, "label": f"{date.month}월"})
            if d in vals or t0 <= d <= t1:
                cells.append({"w": w, "dw": dw, "v": round(vals.get(d, 0.0), 4), "t": d})
        nweeks = (t1 - monday0) // 7 + 1
        vmax = max(vals.values()) or 1.0
        options = {
            "hideAxes": True,
            "pad": {"left": 30, "right": 12, "bottom": 10, "top": 30},
            "axes": {"x": {"label": "", "unit": ""}, "y": {"label": "", "unit": ""}},
            "pluginConfig": {"calheat": {
                "cells": cells, "nweeks": int(nweeks), "vmax": vmax, "months": months,
                "value_label": str(payload.get("value_label", "값")),
            }},
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        series = [{"name": "_ch", "style": "none", "x": [0, float(nweeks)], "y": [0, 7]}]
        return {"engine": resolved.engine, "assets": {"series": series}, "options": options}

    def structural_requires(self, payload):
        ent = payload.get("entries") or []
        if not ent:
            return [{"field": "entries", "why": "날짜별 값이 없음",
                     "ask": "entries:[{date:'YYYY-MM-DD', value}] (또는 날짜 문자열 배열=건수 1씩)을 주세요."}]
        bad = sum(1 for e in ent if _day(e.get("date") if isinstance(e, dict) else e) is None)
        if bad:
            return [_ask_dates("entries[].date", f"{bad}개 항목")]
        return []


_STATUS_MAP = {"완료": "pass", "done": "pass", "진행": "warn", "active": "warn",
               "지연": "fail", "blocked": "fail", "delayed": "fail",
               "예정": "warn", "pending": "warn"}


class TaskTableRecipe(Recipe):
    """업무 목록표 — review-matrix rich cells (owner/기간/진척 bar/상태/우선순위/D-day)."""

    type_name = "task-table"
    _matrix = MatrixRecipe()

    def normalize(self, payload, resolved):
        as_of = _day(payload.get("as_of"))
        states = [{"id": "owner", "label": "담당"}, {"id": "period", "label": "기간"},
                  {"id": "prog", "label": "진척"}, {"id": "status", "label": "상태"}]
        if payload.get("priorities", True):
            states.append({"id": "prio", "label": "우선순위"})
        if as_of is not None:
            states.append({"id": "dday", "label": f"D-day (기준 {payload.get('as_of')})"})
        items = []
        for i, t in enumerate(payload.get("tasks") or []):
            s, e = _day(t.get("start")), _day(t.get("end"))
            cells = {
                "owner": {"kind": "text", "value": str(t.get("owner", "—"))},
                "period": {"kind": "text",
                           "value": (f"{_fmt(s)} ~ {_fmt(e)}" if s is not None and e is not None else "—")},
                "prog": {"kind": "bar", "value": round(float(t.get("progress", 0)) * 100, 1), "max": 100},
            }
            st = _STATUS_MAP.get(str(t.get("status", "")).lower()) or _STATUS_MAP.get(str(t.get("status", "")))
            cells["status"] = {"kind": "status", "status": st or "warn"}
            if payload.get("priorities", True):
                cells["prio"] = {"kind": "badges", "tags": [str(t.get("priority", "보통"))]}
            if as_of is not None and e is not None:
                cells["dday"] = {"kind": "delta", "value": e - as_of, "delta": float(e - as_of), "goal": "max"}
            items.append({"id": f"t{i}", "group": str(t.get("group", "")), "label": str(t.get("name", "")),
                          "type": "task", "cells": cells})
        mp = {"title": str(payload.get("title") or "업무 목록"), "states": states, "items": items,
              "options": {"diff": False}}
        return self._matrix.normalize(mp, resolved)

    def structural_requires(self, payload):
        if not (payload.get("tasks") or []):
            return [{"field": "tasks", "why": "업무 항목이 없음",
                     "ask": "tasks:[{name, owner?, start?, end?, progress?(0~1), status?(완료|진행|지연|예정), "
                            "priority?, group?}] 를 주세요. D-day 열이 필요하면 as_of:'YYYY-MM-DD'(기준일)도."}]
        return []


class WorkPlanRecipe(Recipe):
    """종합 업무계획서 — 개요/KPI(stat-card)/Gantt/마일스톤(timeline)/리스크 heat 를
    한 장의 self-contained 아티팩트로 결합 (review-matrix 그래프셀 = 멀티엔진 번들)."""

    type_name = "work-plan"
    _gantt = GanttRecipe()

    def normalize(self, payload, resolved):
        from .. import graphconfig  # lazy — recipes<->graphconfig cycle

        gp_store, items = {}, []

        def wide(rid, group, label, gtype, gpayload, h):
            gp = dict(graphconfig.graph_config(gtype, gpayload, validate_cell=False))
            o = dict(gp.get("options") or {})
            o.setdefault("exportButtons", [])
            gp["options"] = o
            gp_store[rid] = gp
            items.append({"id": rid, "group": group, "label": label, "type": "graph",
                          "overlay": rid, "h": h, "cells": {}})

        # ── 개요 ──
        meta_rows = [("기간", f"{payload.get('period', {}).get('start', '?')} ~ {payload.get('period', {}).get('end', '?')}")]
        for key, lab in (("owner", "책임자"), ("team", "팀"), ("objective", "목표")):
            if payload.get(key):
                meta_rows.append((lab, str(payload[key])))
        for i, (lab, val) in enumerate(meta_rows):
            items.append({"id": f"m{i}", "group": "개요", "label": lab, "type": "meta",
                          "cells": {"v": {"kind": "text", "value": val}}})

        # ── 핵심 지표 (gauge-core stat cards) ──
        if payload.get("kpis"):
            wide("kpi", "핵심 지표", "KPI", "stat-card", {"items": payload["kpis"]}, 170)

        # ── 일정 Gantt (xy-core + gantt plugin) ──
        tasks = payload.get("tasks") or []
        if tasks:
            wide("gantt", "일정", "Gantt", "gantt-chart",
                 {"tasks": tasks, "options": (payload.get("options") or {})},
                 max(220, 64 + 30 * len(tasks)))

        # ── 마일스톤 (xy-core + timeline plugin) ──
        if payload.get("milestones"):
            wide("tl", "마일스톤", "Timeline", "milestone-timeline",
                 {"events": payload["milestones"]}, 200)

        # ── 업무분장 ──
        owners = {}
        for t in tasks:
            o = str(t.get("owner", "")).strip()
            if o:
                owners.setdefault(o, []).append(str(t.get("name", "")))
        for i, (o, names) in enumerate(owners.items()):
            items.append({"id": f"o{i}", "group": "업무분장", "label": o, "type": "owner",
                          "cells": {"v": {"kind": "badges", "tags": names[:6]}}})

        # ── 리스크 (조건부 색) ──
        for i, r in enumerate(payload.get("risks") or []):
            imp = float(r.get("impact", 3))
            lik = float(r.get("likelihood", 3))
            label = str(r.get("risk", r.get("name", f"리스크{i + 1}")))
            cells = {"v": {"kind": "heat", "value": round(imp * lik, 1), "min": 1, "max": 25, "scale": "highbad"}}
            if r.get("mitigation"):
                label += f" — 대응: {r['mitigation']}"
            items.append({"id": f"r{i}", "group": "리스크 (영향×가능성)", "label": label,
                          "type": "risk", "cells": cells})

        assets = {"states": [{"id": "v", "label": ""}], "items": items, "baseline": "v",
                  "spec": {}, "graph_payloads": gp_store, "meta": {}}
        options = {"title": str(payload.get("title") or "업무계획서"), "theme": "auto", "diff": False}
        return {"engine": resolved.engine, "assets": assets, "options": options}

    def structural_requires(self, payload):
        miss = []
        per = payload.get("period") or {}
        if not (per.get("start") and per.get("end")) or _day(per.get("start")) is None or _day(per.get("end")) is None:
            miss.append({"field": "period", "why": "계획 기간이 없음/형식오류",
                         "ask": "계획 기간을 주세요: period:{start:'YYYY-MM-DD', end:'YYYY-MM-DD'}."})
        if not (payload.get("tasks") or []):
            miss.append({"field": "tasks", "why": "일정 작업이 없음",
                         "ask": "tasks:[{name,start,end,progress?,owner?,group?,deps?}] — Gantt와 업무분장의 원천입니다."})
        else:
            miss.extend(self._gantt.structural_requires({"tasks": payload["tasks"]}))
        return miss
