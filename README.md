# graph-skill

Generate **self-contained interactive HTML graphs** from data + axis metadata, driven by an
LLM skill. The rendering engine is a fixed, version-controlled asset — so the same `(x, y)`
data always yields the same rich interaction level (hover tracking, zoom/pan, log toggle,
legend isolate, dark mode, export) with **zero per-request configuration**.

Engine-family based: `xy-core` (Canvas 2D) is the first family. The same builder / catalog /
validate / self-contained machinery is designed to host future families such as `cad-viewer`
(3D CAD: STEP→GLB, section views). See [docs/SKILL-PLAN.md](docs/SKILL-PLAN.md) §18.

## Status — v0.1.0 (base-xy MVP)
`base-xy` is implemented and verified end-to-end (Python pipeline, tool layer, and headless
engine execution). Output is a single `.html` with **0 external resources**, byte-deterministic.

## Install
```powershell
pip install -e .            # or: pip install dist/graph_skill-0.1.0-py3-none-any.whl
```
Bundled JS engine assets ship as `package_data` (`src/graph_skill/data/**`).

## CLI
```powershell
graph-skill types
graph-skill schema base-xy
graph-skill validate --in tests/fixtures/base_xy.json
graph-skill render   --in tests/fixtures/base_xy.json --out graph-out/plot.html
graph-skill lint     graph-out/plot.html
graph-skill embed-block graph-out/plot.html --height 520
graph-skill version
```

## MCP
Register the stdio server (`graph-skill-mcp`) in your MCP config:
```json
{ "mcpServers": { "graph-skill": { "command": "graph-skill-mcp" } } }
```
Tools: `graph_types_list`, `graph_schema_get`, `graph_validate_inputs`, `graph_render`,
`graph_lint_output`, `graph_embed_block`. See `.claude/skills/graph-skill/SKILL.md`.

## Architecture (recipe → artifact model)
| layer | file | role |
|---|---|---|
| catalog | `data/catalog/types.json` + `catalog.py` | type → {engine, plugins, requires} (single source of truth) |
| recipe | `recipes/*.py` | normalize loose input → `{engine, assets, options}` |
| gate | `validate.py` | compute `missing[]` background params → LLM asks the user |
| builder | `builder.py` | engine + plugins + config + data → single self-contained `.html` |
| serialize | `serialize.py` | safe, deterministic JSON inlining + self-contained lint |
| engine | `data/engines/xy-core/engine.js` | fixed Canvas 2D engine (all interactions) |
| shell | `data/shell/{template.html,boot.js}` | family-agnostic bootstrap (engine registry) |
| tools | `tools.py` | shared logic behind both MCP (`mcp_server.py`) and CLI (`cli.py`) |

## Tests
```powershell
pytest                                   # if pytest installed
# dependency-free smokes:
$env:PYTHONPATH="src"; python tests/smoke_build.py
$env:PYTHONPATH="src"; python tests/smoke_tools.py
node tests/node_render.mjs               # headless engine execution (no browser needed)
```
