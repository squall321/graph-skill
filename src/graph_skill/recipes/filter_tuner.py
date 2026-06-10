"""filter-tuner recipe — carries the raw signal + fs so the filter-panel plugin can run an
interactive FFT-domain filter client-side (drag cutoff -> live filtered waveform/spectrum).
The initial paint (filtered-at-default-fc spectrum) is computed in Python with the SAME
algorithm the JS uses, so first paint and live updates agree. params.fs [Hz] required."""

from __future__ import annotations

from ..postprocess import spectral
from .base import Recipe
from .base_xy import BaseXYRecipe


class FilterTunerRecipe(Recipe):
    type_name = "filter-tuner"
    _base = BaseXYRecipe()

    def normalize(self, payload: dict, resolved) -> dict:
        params = payload.get("params") or {}
        fs = float(params["fs"])
        kind = params.get("filter", "low")
        fc = float(params.get("fc", fs / 4))
        fc2 = float(params["fc2"]) if params.get("fc2") is not None else None
        edge = float(params.get("edge", 0.15))

        s = self._base._series((payload.get("series") or [{}])[0], 0)  # first series only
        t, y = s["x"], s["y"]
        filt = spectral.fft_filter(y, fs, kind, fc, fc2, edge)
        fr, ao = spectral.amp_spectrum(y, fs)
        _, af = spectral.amp_spectrum(filt, fs)

        cols = ["#9aa3af", "#2563eb"]
        freq_series = [{"name": "original", "x": fr, "y": ao, "color": cols[0]},
                       {"name": "filtered", "x": fr, "y": af, "color": cols[1]}]
        ax = payload.get("axes") or {}
        tx, ty = ax.get("x") or {}, ax.get("y") or {}
        yunit = str(ty.get("unit", ""))
        time_axes = {"x": {"label": str(tx.get("label", "Time")), "unit": str(tx.get("unit", "s"))},
                     "y": {"label": str(ty.get("label", "Amplitude")), "unit": yunit}}
        freq_axes = {"x": {"label": "Frequency", "unit": "Hz"}, "y": {"label": "|Amplitude|", "unit": yunit}}

        options = {
            "curve": "straight",
            "axes": freq_axes,
            "pluginConfig": {
                "filter-panel": {
                    "fs": fs, "t": t, "y": y, "fc": fc, "fc2": fc2, "kind": kind, "edge": edge,
                    "timeAxes": time_axes, "freqAxes": freq_axes, "start": "freq", "colors": cols,
                }
            },
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": freq_series}, "options": options}
