"""LLM-facing guidance that JSON Schema can't carry: the preamble rule + per-type hints.

Mirrors SKILL-RECIPE §5b/§5c. The preamble is the "NEVER invent" rule in prompt form; the
hints tell the LLM which background params a type needs and what to ask when missing.
"""

from __future__ import annotations

PREAMBLE = (
    "NEVER invent axis units or physical background values (e.g. A0, L0, fs). "
    "Always call graph_validate_inputs first; if it returns a non-empty missing[], ASK the "
    "user the listed questions and DO NOT render until resolved. Rendering with a guessed "
    "value produces a confidently-wrong artifact."
)

_INPUT_HINTS = {
    "base-xy": (
        "Required: series[] (each {name, data:[[x,y],...] or [{x,y},...]}) and axes.x/y "
        "{label, unit}. unit may be '' for dimensionless. All interactions (hover tracking, "
        "crosshair, zoom/pan/box-zoom, log toggle, legend isolate, dark mode, PNG/CSV export) "
        "are automatic — do NOT try to configure them. If you don't know what a quantity or "
        "unit on an axis is, ASK; don't guess."
    ),
    "stress-strain": (
        "Input is RAW tensile data: each series data=[[displacement_mm, force_N], ...] "
        "(x=displacement, y=force). Required physics: params.A0 [mm^2], params.L0 [mm] — the "
        "engine converts σ=F/A0, ε=ΔL/L0. If A0 or L0 is missing, ASK; never guess (a wrong A0 "
        "silently produces a confidently-wrong curve). Axes are auto-set; UTS/Fracture markers "
        "and the Et tangent are automatic. params.true_stress=true for true stress/strain. "
        "params.regions=[{x0,x1,label}] (in strain) optionally shades elastic/plastic/necking."
    ),
    "force-displacement": (
        "Required: series (x=displacement, y=force) and axes.x/y {label, unit}. Hover shows the "
        "local stiffness dF/dd. If the data is already stress/strain use stress-strain instead."
    ),
    "correlation-scatter": (
        "Required: series (x=Test/measured, y=CAE/predicted, or any two variables) and axes.x/y "
        "{label, unit}. A linear regression line + R² + y=x identity line are automatic. "
        "Set options.identity=false to drop the identity line."
    ),
    "polar-plot": (
        "Polar (angle/radius). Required: series:[{name, theta:[deg], r:[value]}] (or data=[[theta,r]]) "
        "and radius {label,unit}. closed:true for a closed curve. θ=0 at top, clockwise."
    ),
    "radar-chart": (
        "Radar/spider for multi-metric profiles. Required: axes_labels:[metrics] + "
        "series:[{name, values:[per-metric]}]. Closed polygons; rmax fixes the scale."
    ),
    "rf-radiation-pattern": (
        "Antenna pattern (polar). Required: series:[{name, theta:[deg], r:[gain dBi]}]. "
        "radius defaults to Gain[dBi], closed automatically. Overlay E/H-plane cuts as separate series."
    ),
    "dual-axis": (
        "Two y-axes (left/right). Required: series with axis:'left'|'right', and axes.x/y (left) + "
        "axes.y2 (right) {label,unit}. The right axis auto-scales to its own data. e.g. power↔temperature."
    ),
    "bode": (
        "Bode plot. Required: freqs:[Hz], mag:[dB], phase:[deg] (same length). x=log frequency, "
        "left y=Magnitude[dB], right y=Phase[deg] are set automatically."
    ),
    "histogram": (
        "Distribution histogram. Required: values:[numbers] (or series data) and axes.x {label,unit} "
        "(the binned quantity). params.bins (default sqrt(n)), params.density=true for a density. "
        "The y axis (Frequency/Density) is automatic."
    ),
    "bar-plot": (
        "Categorical bar chart. Required: categories:[labels] + values:[numbers] (aligned) and "
        "axes.y {label,unit} (the measured quantity)."
    ),
    "box-plot": (
        "Group spread. Required: groups:[{label, values:[...]}, ...] and axes.y {label,unit}. "
        "Quartiles / 1.5·IQR whiskers / outliers are computed automatically (DOE/condition comparison)."
    ),
    "error-bar": (
        "Required: series with data=[[x, y, err], ...] (or data=[[x,y]] + series.err=[...]) and "
        "axes.x/y {label,unit}. Draws points with vertical error whiskers."
    ),
    "fft-spectrum": (
        "Time-domain signal in, frequency spectrum out, with a control-bar toggle to switch "
        "time <-> frequency. Required: series (each data=[[time, value], ...]) and params.fs [Hz] "
        "(ASK if unknown — without fs the frequency axis is meaningless). The one-sided amplitude "
        "spectrum + peak markers are automatic. params.window='rect' disables the Hann window."
    ),
    "filter-tuner": (
        "Interactive filter tuner. Required: series (data=[[time, value], ...]) and params.fs [Hz]. "
        "Renders the spectrum with a draggable cutoff slider; the filtered waveform/spectrum update "
        "live (client-side FFT). params.filter='low'|'high'|'band', fc (default fs/4), fc2 (band), "
        "edge (transition width). Fully self-contained — no server. ASK for fs if unknown."
    ),
    "review-matrix": (
        "A table, not a chart. Required: states[] (columns, each {id,label}) and items[] (rows, "
        "each {id, group, label, unit?, type, spec?, cells:{stateId: cell}}). A cell is one of: "
        "{kind:'number', value, ref?} / {kind:'status', status:'pass|fail|warn', value?} / "
        "{kind:'text', value, link?} / {kind:'image', image:{mode:'inline', mime, data:'<base64>'}} / "
        "{kind:'graph', graph_ref:{type:'base-xy'|..., payload:{axes, series}}}. Graph cells re-mount a "
        "real interactive graph in the cell. Images MUST be base64-inline (a single self-contained .html "
        "is the only publishable form). Search/filter/group-collapse/cell-modal are automatic."
    ),
    "design-state-compare": (
        "Compare ≥2 design states. Same shape as review-matrix PLUS: meta.baseline must be one of the "
        "state ids (ASK if unknown). Give each item a spec {min?, max?, target?, warn_at?, goal:'min'|'max'} "
        "to get pass/fail/warn badges + diff(▲▼) vs baseline. item.overlay_states=true overlays one item's "
        "states into a single graph cell. If only one state, use single-state-checklist instead."
    ),
    "single-state-checklist": (
        "One design state, item-by-item pass/fail. Same shape as review-matrix with states=[one]. "
        "Item spec gives pass/fail/warn badges."
    ),
    "contour-plot": (
        "2D scalar field z=f(x,y). Required: field={x:[nx col coords], y:[ny row coords], "
        "z:[[ny rows × nx cols]]} (uniform grid), axes.x/y {label,unit}, and z {label,unit} "
        "(ASK if the z quantity/unit is unknown — the colorbar is meaningless otherwise). "
        "z may contain null for gaps. colormap raster + iso-contours + colorbar + hover probe(z) "
        "+ zoom/pan are automatic. options: colormap/reverse/levels/zdomain/contours."
    ),
    "heatmap-grid": "Same input as contour-plot but color-only (no iso lines). options.contours=true to add them. ※ 이미 σ-ε로 환산된 데이터면 base-xy 사용(A0/L0 불필요). Skeleton: states:[{id,label}×2+], items:[{id,group,label,unit?,spec?{min,max,goal},cells:{<stateId>:{kind:'number',value}|{kind:'status',status}|{kind:'graph',graph_ref}}}], meta.baseline=<stateId>.",
    "scalar-field-2d": "Same as contour-plot. Generic CAE field (temperature/stress/potential/SAR...).",
    "mcae-stress-contour": (
        "Structural CAE stress map. Same input as contour-plot with z={label:'von Mises σ', unit:'MPa'} "
        "and axes in position units (mm). Use options.zdomain=[0, yield] to fix the color range to the "
        "yield strength. Hotspots read off the colorbar / contours."
    ),
}


def hint_for(graph_type: str) -> str:
    return _INPUT_HINTS.get(graph_type, "")
