# Changelog

All notable changes to graph-skill. SemVer (0.x). Engine assets carry a separate
`ENGINE_VERSION` baked into every artifact.

## [0.10.0] — equipment raw post-processing (ingest / resample / smooth)
### Added
- **`postprocess/{ingest,resample,smoothing}.py`** (pure Python): CSV/TSV ingest (header +
  units row + delimiter auto, non-numeric→None); uniform-grid resample (linear interp) +
  `is_uniform` detection + decimate; moving-average + **Savitzky-Golay** (normal-equations).
- **Helper tools** `ingest_csv` / `resample` / `smooth` (return numeric, not HTML) on MCP +
  CLI — the LLM pre-processes raw scope/Instron data, then feeds it to `graph_render`.
- Verified: ingest/resample/SG numeric correctness (SG noise RMSE 0.3→0.08) + e2e
  (ingest→resample→smooth→render) + pytest (88 passed).

## [0.9.0] — polar-core family (radiation pattern / radar)
### Added
- **New engine family `polar-core`** (engine 0.1.0) — angle/radius Canvas engine: polar grid
  (radius rings + angle spokes), series as polar polylines (θ=0 at top, clockwise), radar
  fill, hover probe (θ, r), legend, dark mode, PNG. Types `polar-plot`, `radar-chart`
  (categories→spokes, closed polygons, rmax scale), `rf-radiation-pattern` (Gain[dBi] preset).
- **validate preview made shape-agnostic** (handles theta/r and field series, not just x/y).
- Verified: render/lint + gates (radius/labels/series) + headless (engine renders, _pt maps,
  0 console errors) + pytest (79 passed).

## [0.8.0] — dual-axis + bode (secondary y-axis)
### Added
- **xy-core secondary y-axis**: series with `axis:"right"` get an independent right-hand
  scale (own data range, right ticks/labels/title via `axes.y2`); left/right domains are
  computed separately; hover/snap use the correct per-series scale. Guarded by `_hasRight`
  so single-axis rendering is byte-unchanged in behaviour.
- Types `dual-axis` (generic left/right, e.g. power↔temperature) and `bode` (log-frequency
  Magnitude[dB] left + Phase[deg] right, from `freqs/mag/phase`). Verified: 2nd-order system
  resonance peak ≈14 dB; right-axis scaling; gates; headless (right axis active, log-x,
  0 console errors) + pytest (72 passed).

## [0.7.0] — statistical & bar types (histogram / bar / box / error-bar)
### Added
- **xy-core engine** gained bar rendering (`style:"bar"` with baseline 0), a categorical x-axis
  (`axes.x.categories`), and a domain-only `style:"none"` series (for box-plot extents).
- **`stats` postprocess** — histogram binning (sqrt rule) + Tukey quartiles/whiskers/outliers.
- **box-plot / error-bars plugins** + types `histogram`, `bar-plot`, `box-plot`, `error-bar`
  (each with its own structural gate: histogram→values+axis.x, bar→categories+axis.y,
  box→groups+axis.y). Covers DOE / Monte-Carlo / reliability / margin reporting.
- Verified: stats correctness + gates + headless runtime (bars/categorical/box/error-bar
  render, 0 console errors) + pytest (65 passed).

## [0.6.0] — filter-tuner (interactive FFT filter)
### Added
- **`filter-tuner` type** (xy-core) — completes the "watch the FFT, drag the cutoff, see the
  time signal change" loop in a single self-contained HTML (no server). A `filter-panel`
  plugin renders a cutoff slider + type select + time/freq toggle; the filtered waveform and
  spectrum update live via a client-side radix-2 FFT, with a cutoff line drawn on the spectrum.
- **`spectral.fft_filter` / `amp_spectrum` / `_ifft`** — pure-Python FFT-domain filter
  (low/high/band, raised-cosine transition) used for the initial paint, matching the JS used
  for live updates. Verified: lowpass fc=80 keeps 30 Hz, removes 180 Hz; highpass inverts.
- Verified: filter correctness + fs gate + headless runtime (boot, cutoff change re-filters
  live, time/freq toggle, 0 console errors) + pytest (54 passed).

## [0.5.0] — fft-spectrum (time ↔ frequency toggle)
### Added
- **`fft-spectrum` type** (xy-core) — the headline "FFT toggle": a time-domain signal in,
  one-sided amplitude spectrum out, with a control-bar button that switches the chart between
  time and frequency at runtime (peak markers auto in freq).
- **`postprocess/spectral.py`** — pure-Python FFT (iterative radix-2, zero-pad to 2ⁿ, Hann
  window, one-sided amplitude) + peak finder. No numpy. Verified: peaks at 49.8 & 120.1 Hz
  for a 50 + 120 Hz signal.
- **`domain-toggle` plugin** — swaps series + axes (+ peak markers) between the pre-computed
  time and frequency domains; requires `params.fs` (gate asks if missing).
- Verified: FFT numeric correctness + fs gate + headless runtime (boots in freq at Nyquist,
  toggles to time/seconds and back, 0 console errors) + pytest (47 passed).

## [0.4.0] — field-core family (2D contour/heatmap, phase 3)
### Added
- **New engine family `field-core`** (engine 0.1.0) — 2D scalar field z=f(x,y): colormap
  raster (offscreen + drawImage, zoom-aware), **marching-squares iso-contours**, a colorbar
  legend, **probe-pick** (hover → x,y,z in HUD), zoom/pan/box-zoom, colormap cycle
  (viridis/turbo/coolwarm/gray) + reverse, dark mode, responsive, PNG export.
- Types: `contour-plot`, `heatmap-grid` (color-only), `scalar-field-2d`, `mcae-stress-contour`
  (turbo preset). Input `field={x[],y[],z[][]}` + axes + z{label,unit}.
- **field recipe + structural gate**: asks for the z quantity/unit (colorbar meaning) and
  validates grid rectangularity (z is ny×nx); z sanitized to float|None (null = transparent).
- Verified: Python build/lint + z-meta & dimension gates + headless runtime (boot, 25×25 grid,
  bilinear probe, colormap re-rasterize, zoom clamp, 0 console errors) + pytest (40 passed).
  Implements `docs/RESULT-VIZ-STANDARD.md` §3.2 (field-core, highest-ROI new family).

## [0.3.0] — review-matrix family (design-state checklist/comparison, phase 2)
### Added
- **New engine family `review-matrix`** (engine 0.1.0) — a DOM-grid meta-artifact, not a
  chart. Renders states × items; cells are number / status(pass/fail/warn) / text / image
  (base64-inline) / **graph** (re-mounts a real graph-skill engine in the cell). Auto:
  search/filter, group collapse, sticky label column, diff(▲▼) vs baseline, spec badges,
  cell modal (full-graph re-mount / image lightbox), export-source JSON.
- **Multi-engine bundling** in the builder (`_collect_engines`) — a matrix HTML inlines its
  own engine + every engine/plugin its graph cells need (e.g. xy-core), deduped. Backward
  compatible (single-engine artifacts unchanged). Added `graphconfig.graph_config` helper.
- **validate-v2 structural gate** — `Recipe.structural_requires(payload)` for non-scalar
  checks; catalog `require_series` flag. Enforced: `items≥1`, `states≥2` (compare),
  `baseline ∈ states`. require_axes/require_series default off for matrix types.
- Types: `review-matrix`, `design-state-compare` (≥2 states + baseline, diff/spec badges,
  `overlay_states`), `single-state-checklist`. Tool surface accepts `states/items/spec/meta`.
- Verified: Python multi-engine bundle + structural gates + headless runtime (matrix boots,
  3 graph cells re-mount xy-core, modal full re-mount, 0 console errors) + pytest (31 passed).
  Implements `docs/DESIGN-STATE-TABLE.md` (inline-only publish, overlay, structured query).

## [0.2.0] — xy-core plugin layer (result-viz standard, phase 1)
### Added
- **Plugin composition seam** in `xy-core` (engine 1.1.0): `view.core` / `view.pluginConfig` /
  per-core `_pstate`, so shared singleton plugins carry per-graph config + state.
- **5 reusable plugins** (`data/engines/xy-core/plugins/`): `threshold-lines`,
  `region-shading`, `named-markers`, `live-tangent` (hover slope, recipe-relabelled:
  Et[GPa]/stiffness[N/mm]/CTE…), `regression-fit` (LSQ line + R² + y=x identity).
- **`postprocess/units.py`** — σ=F/A0, ε=ΔL/L0, eng→true (pure Python, guarded).
- **3 new types** via `extends` + plugin composition: `stress-strain` (requires A0/L0 →
  gate, auto UTS/Fracture markers + Et tangent, eng/true), `force-displacement`
  (stiffness tangent), `correlation-scatter` (regression + identity + R²).
- Verified: Python pipeline + headless plugin runtime (hover→Et/stiffness, regression draw,
  0 console errors) + pytest (23 passed). See `tests/{smoke_phase1.py,node_phase1.mjs,test_phase1.py}`.
  Implements `docs/RESULT-VIZ-STANDARD.md` §3.1 (xy-core domain types, first slice).

## [0.1.0] — base-xy MVP
### Added
- **Engine family architecture** (engine-agnostic builder/catalog/validate/shell). `xy-core`
  is the first family; `data/engines/<family>/` layout reserves space for future families
  (e.g. `cad-viewer`). See docs/SKILL-PLAN.md §18.
- **`xy-core` Canvas 2D engine** (`data/engines/xy-core/engine.js`, ENGINE_VERSION 1.0.0):
  multi-series, color-blind-safe palette, per-series hover tracking + crosshair + unified
  tooltip + HUD, click lock, wheel zoom (cursor-centered; Shift=x, Alt/Ctrl=y), drag pan,
  box zoom, double-click reset, log/linear toggle (x/y, non-positive guard), nice ticks,
  legend toggle/isolate, dark mode (auto/light/dark), responsive (ResizeObserver + DPR),
  PNG/CSV/config export, monotone-cubic/straight/step curves, gap handling.
- **Skill surface**: `tools.py` (shared) behind MCP (`mcp_server.py`) and CLI (`cli.py`).
  Tools: `graph_types_list`, `graph_schema_get`, `graph_validate_inputs`, `graph_render`,
  `graph_lint_output`, `graph_embed_block`.
- **Completeness gate** (`validate.py`): required axes + per-type `requires[]` → `missing[]`
  + questions; render is blocked (`MissingFieldsError` / `needs_input`) until resolved.
- **Self-contained guarantee**: deterministic, LF-only, zero external resources; static lint
  gate (`serialize.lint_self_contained`).
- `base-xy` recipe + catalog entry; SKILL.md; README; pytest suite + dependency-free smokes
  (`tests/smoke_build.py`, `tests/smoke_tools.py`) + headless engine execution
  (`tests/node_render.mjs`).
