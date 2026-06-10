"""Eye diagram — fold a serial waveform into overlapping unit-interval windows and accumulate
a 2D (phase × amplitude) persistence histogram. Pure Python. Reused by the field-core heatmap."""

from __future__ import annotations


def eye_histogram(signal: list, sps: int, ui: int = 2, n_phase: int = 96, n_amp: int = 64):
    """Return (phase_centers[UI], amp_centers, Z[amp][phase]) — counts of traces through each cell.

    sps = samples per unit interval. Windows of ``ui`` UIs slide by 1 UI so every transition folds
    onto the eye."""
    vals = [float(v) for v in signal if v is not None]
    n = len(vals)
    if n < 2 * sps or sps < 2:
        raise ValueError("need sps >= 2 and at least 2 UI of samples")
    amin = min(vals)
    amax = max(vals)
    if amax <= amin:
        amax = amin + 1.0
    window = ui * sps
    z = [[0 for _ in range(n_phase)] for _ in range(n_amp)]
    i = 0
    while i + window <= n:
        for k in range(window):
            v = vals[i + k]
            ph = int(k / window * n_phase)
            if ph >= n_phase:
                ph = n_phase - 1
            ai = int((v - amin) / (amax - amin) * (n_amp - 1))
            ai = 0 if ai < 0 else (n_amp - 1 if ai >= n_amp else ai)
            z[ai][ph] += 1
        i += sps
    phase_centers = [(j + 0.5) / n_phase * ui for j in range(n_phase)]
    amp_centers = [amin + (amax - amin) * (a + 0.5) / n_amp for a in range(n_amp)]
    return phase_centers, amp_centers, z
