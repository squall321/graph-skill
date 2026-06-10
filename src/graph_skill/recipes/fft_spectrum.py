"""fft-spectrum recipe — compute the one-sided amplitude spectrum of time-domain series and
carry BOTH domains so the domain-toggle plugin can switch time <-> frequency at runtime.
extends base-xy; axes derived (require_axes=false). params.fs [Hz] required."""

from __future__ import annotations

from ..postprocess import spectral
from .base import Recipe
from .base_xy import BaseXYRecipe


class FFTSpectrumRecipe(Recipe):
    type_name = "fft-spectrum"
    _base = BaseXYRecipe()

    def normalize(self, payload: dict, resolved) -> dict:
        params = payload.get("params") or {}
        fs = float(params["fs"])
        window = params.get("window", "hann")
        axes_in = payload.get("axes") or {}

        time_series, freq_series = [], []
        for i, s in enumerate(payload.get("series") or []):
            ns = self._base._series(s, i)  # x=time, y=value
            time_series.append({"name": ns["name"], "x": ns["x"], "y": ns["y"]})
            freqs, amp = spectral.fft_onesided(ns["y"], fs, window)
            freq_series.append({"name": ns["name"], "x": freqs, "y": amp})

        pk = []
        if freq_series:
            for f, a in spectral.peaks(freq_series[0]["x"], freq_series[0]["y"], 4):
                pk.append({"x": f, "y": a, "label": f"{round(f, 1)} Hz", "color": "#dc2626"})

        tx, ty = axes_in.get("x") or {}, axes_in.get("y") or {}
        yunit = str(ty.get("unit", ""))
        time_axes = {"x": {"label": str(tx.get("label", "Time")), "unit": str(tx.get("unit", "s")), "log": False},
                     "y": {"label": str(ty.get("label", "Amplitude")), "unit": yunit, "log": False}}
        freq_axes = {"x": {"label": "Frequency", "unit": "Hz", "log": False},
                     "y": {"label": "|Amplitude|", "unit": yunit, "log": False}}

        options = {
            "curve": "straight",
            "axes": freq_axes,
            "pluginConfig": {
                "domain-toggle": {
                    "start": "freq",
                    "time": {"series": time_series, "axes": time_axes},
                    "freq": {"series": freq_series, "axes": freq_axes},
                    "peaks": pk,
                },
                "named-markers": {"markers": pk},
            },
        }
        if payload.get("title"):
            options["title"] = str(payload["title"])
        return {"engine": resolved.engine, "assets": {"series": freq_series}, "options": options}
