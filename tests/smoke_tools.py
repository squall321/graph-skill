"""Smoke the shared tool layer (no mcp/typer needed). Run with PYTHONPATH=src."""
import json
from pathlib import Path

from graph_skill import tools

ROOT = Path(__file__).resolve().parent
payload = json.loads((ROOT / "fixtures" / "base_xy.json").read_text(encoding="utf-8"))

print("== types ==")
tl = tools.types_list()
print([t["name"] for t in tl["types"]])

print("== schema ==")
sc = tools.schema_get("base-xy")
print("requires:", sc["requires"], "| engine:", sc["engine"], sc["engine_version"])

print("== validate (good) ==")
v = tools.validate_inputs("base-xy", payload)
print("ok:", v["ok"])
assert v["ok"]

print("== validate (missing axes) ==")
vm = tools.validate_inputs("base-xy", {"series": payload["series"], "axes": {}})
print("ok:", vm["ok"], "questions:", vm["questions"])
assert not vm["ok"]

print("== render needs_input ==")
ni = tools.render("base-xy", payload["series"], {}, out_path=str(ROOT.parent / "graph-out" / "x.html"))
print("status:", ni["status"], "missing:", [m["field"] for m in ni["missing"]])
assert ni["status"] == "needs_input"

print("== render ok ==")
out = str(ROOT.parent / "graph-out" / "tools_base_xy.html")
r = tools.render("base-xy", payload["series"], payload["axes"], title=payload.get("title"), out_path=out)
print("status:", r["status"], "| html_path:", r["html_path"], "| bytes:", r["bytes"])
assert r["status"] == "ok" and r["lint"]["ok"]

print("== lint ==")
ln = tools.lint_output(r["html_path"])
print(ln)
assert ln["ok"]

print("== embed_block ==")
eb = tools.embed_block(r["html_path"], height_px=480, caption="damped vs driven")
print(json.dumps(eb, ensure_ascii=False))
assert eb["type"] == "html_embed" and eb["input"]["height_px"] == 480

print("TOOLS SMOKE OK")
