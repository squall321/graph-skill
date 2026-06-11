"""Touchstone v1 .s2p 파서 — 옵션라인(# <unit> S <MA|DB|RI> R <z0>) + 2포트 S-파라미터.
RF 측정 파일 하나로 smith(S11 Γ)/S21 dB/VSWR 그래프를 바로 만들 수 있게 변환한다."""

from __future__ import annotations

import cmath
import math

_FREQ_MULT = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}


def parse_s2p(text: str) -> dict:
    """반환: {freq_hz[], z0, s11/s21/s12/s22: [(re,im)…], *_db[], s11_vswr[]}"""
    fmt, z0, mult = "ma", 50.0, 1e9
    rows = []
    for raw in text.splitlines():
        line = raw.split("!")[0].strip()
        if not line:
            continue
        if line.startswith("#"):
            tok = line[1:].lower().split()
            for i, t in enumerate(tok):
                if t in _FREQ_MULT:
                    mult = _FREQ_MULT[t]
                if t in ("ma", "db", "ri"):
                    fmt = t
                if t == "r" and i + 1 < len(tok):
                    z0 = float(tok[i + 1])
            continue
        parts = [float(v) for v in line.split()]
        if len(parts) >= 9:
            rows.append(parts[:9])

    def to_complex(a, b):
        if fmt == "ri":
            return complex(a, b)
        mag = a if fmt == "ma" else 10 ** (a / 20.0)
        return cmath.rect(mag, math.radians(b))

    out = {"freq_hz": [], "z0": z0, "s11": [], "s21": [], "s12": [], "s22": []}
    for r in rows:
        out["freq_hz"].append(r[0] * mult)
        out["s11"].append(to_complex(r[1], r[2]))
        out["s21"].append(to_complex(r[3], r[4]))
        out["s12"].append(to_complex(r[5], r[6]))
        out["s22"].append(to_complex(r[7], r[8]))

    def db(seq):
        return [20 * math.log10(max(1e-12, abs(c))) for c in seq]

    out["s11_db"] = db(out["s11"])
    out["s21_db"] = db(out["s21"])
    out["s12_db"] = db(out["s12"])
    out["s22_db"] = db(out["s22"])
    out["s11_vswr"] = [(1 + min(abs(c), 0.9999)) / (1 - min(abs(c), 0.9999)) for c in out["s11"]]
    return out


def to_tool_payload(text: str) -> dict:
    """ingest_s2p 도구 응답 — JSON 직렬화 가능 형태 + 바로 쓸 그래프 입력 조각."""
    p = parse_s2p(text)
    f_mhz = [round(f / 1e6, 6) for f in p["freq_hz"]]
    return {
        "n_points": len(f_mhz), "z0": p["z0"], "freq_mhz": f_mhz,
        "s11_db": [round(v, 4) for v in p["s11_db"]],
        "s21_db": [round(v, 4) for v in p["s21_db"]],
        "vswr": [round(v, 4) for v in p["s11_vswr"]],
        "s11_gamma": [[round(c.real, 6), round(c.imag, 6)] for c in p["s11"]],
        "usage": {
            "smith-chart": "series:[{name:'S11', gamma:<s11_gamma>}]",
            "vswr-curve": "vswr:[[freq_mhz[i], vswr[i]] …] (f_unit:'MHz')",
            "base-xy(S21)": "series:[{name:'S21', data:[[freq_mhz[i], s21_db[i]] …]}], y unit 'dB'",
        },
    }
