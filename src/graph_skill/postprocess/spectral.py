"""FFT / spectral post-processing. Pure Python (no numpy) — iterative radix-2 with
zero-padding to the next power of two, Hann window, one-sided amplitude spectrum."""

from __future__ import annotations

import math


def _fft(re: list, im: list) -> None:
    """In-place iterative radix-2 Cooley-Tukey. len(re) must be a power of two."""
    n = len(re)
    j = 0
    for i in range(1, n):  # bit-reversal permutation
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            re[i], re[j] = re[j], re[i]
            im[i], im[j] = im[j], im[i]
    length = 2
    while length <= n:
        ang = -2.0 * math.pi / length
        wlr, wli = math.cos(ang), math.sin(ang)
        for i in range(0, n, length):
            wr, wi = 1.0, 0.0
            half = length >> 1
            for k in range(half):
                a, b = i + k, i + k + half
                tr = wr * re[b] - wi * im[b]
                ti = wr * im[b] + wi * re[b]
                re[b] = re[a] - tr
                im[b] = im[a] - ti
                re[a] += tr
                im[a] += ti
                wr, wi = wr * wlr - wi * wli, wr * wli + wi * wlr
        length <<= 1


def fft_onesided(y: list, fs: float, window: str = "hann"):
    """Return (freqs[Hz], amplitude[]) one-sided spectrum.

    Hann window with coherent-gain amplitude correction; ×2 for non-DC bins. fs in Hz.
    """
    vals = [float(v) for v in y if v is not None]
    n0 = len(vals)
    if n0 < 2:
        raise ValueError("need >= 2 samples for FFT")
    if not (fs > 0):
        raise ValueError("fs must be positive [Hz]")
    cg = 1.0
    if window == "hann" and n0 > 1:
        vals = [vals[i] * 0.5 * (1 - math.cos(2 * math.pi * i / (n0 - 1))) for i in range(n0)]
        cg = 0.5  # coherent gain of Hann
    n = 1
    while n < n0:
        n <<= 1
    re = list(vals) + [0.0] * (n - n0)
    im = [0.0] * n
    _fft(re, im)
    half = n // 2
    freqs, amp = [], []
    for k in range(half):
        freqs.append(fs * k / n)
        mag = math.hypot(re[k], im[k]) / n0 / cg
        if k != 0:
            mag *= 2.0
        amp.append(mag)
    return freqs, amp


def spectrogram(y: list, fs: float, nperseg=None, overlap: float = 0.5, window: str = "hann"):
    """STFT magnitude spectrogram. Returns (times[s], freqs[Hz], Z[freq][time]).

    Segments of nperseg (forced to a power of two ≤ N) hop by (1-overlap); each is FFT'd via
    ``fft_onesided`` so all columns share one freq axis. Reuses the existing radix-2 FFT."""
    vals = [float(v) for v in y if v is not None]
    n = len(vals)
    if n < 4:
        raise ValueError("need >= 4 samples for spectrogram")
    if not (fs > 0):
        raise ValueError("fs must be positive [Hz]")
    target = nperseg if nperseg else max(16, n // 20)
    p = 1
    while p * 2 <= min(int(target), n):
        p <<= 1
    nperseg = max(4, p)
    step = max(1, int(nperseg * (1 - overlap)))
    times, cols, freqs = [], [], []
    i = 0
    while i + nperseg <= n:
        fk, amp = fft_onesided(vals[i:i + nperseg], fs, window)
        freqs = fk
        times.append((i + nperseg / 2) / fs)
        cols.append(amp)
        i += step
    if not cols:
        freqs, amp = fft_onesided(vals[:nperseg], fs, window)
        cols, times = [amp], [nperseg / 2 / fs]
    z = [[cols[t][f] for t in range(len(cols))] for f in range(len(freqs))]
    return times, freqs, z


def welch(y: list, fs: float, nperseg=None, overlap: float = 0.5, window: str = "hann"):
    """Welch power spectral density — average |FFT|² over overlapping segments. Smoother than
    a single FFT. Returns (freqs[Hz], psd[]). Reuses ``fft_onesided`` per segment."""
    vals = [float(v) for v in y if v is not None]
    n = len(vals)
    if n < 4 or not (fs > 0):
        raise ValueError("need >= 4 samples and fs > 0")
    target = nperseg if nperseg else max(16, n // 8)
    p = 1
    while p * 2 <= min(int(target), n):
        p <<= 1
    nperseg = max(4, p)
    step = max(1, int(nperseg * (1 - overlap)))
    freqs, acc, cnt, i = [], None, 0, 0
    while i + nperseg <= n:
        fk, amp = fft_onesided(vals[i:i + nperseg], fs, window)
        freqs = fk
        if acc is None:
            acc = [a * a for a in amp]
        else:
            for k in range(len(acc)):
                acc[k] += amp[k] * amp[k]
        cnt += 1
        i += step
    if not cnt:
        freqs, amp = fft_onesided(vals[:nperseg], fs, window)
        acc, cnt = [a * a for a in amp], 1
    return freqs, [a / cnt for a in acc]


def _ifft(re: list, im: list) -> None:
    """Inverse FFT via conjugation. len must be a power of two."""
    n = len(re)
    for i in range(n):
        im[i] = -im[i]
    _fft(re, im)
    for i in range(n):
        re[i] /= n
        im[i] = -im[i] / n


def amp_spectrum(y: list, fs: float):
    """One-sided amplitude spectrum WITHOUT a window (matches the client-side JS for the
    filter-tuner, so the initial Python paint and live JS updates agree)."""
    vals = [float(v) for v in y if v is not None]
    n0 = len(vals)
    if n0 < 2 or not (fs > 0):
        raise ValueError("need >=2 samples and fs>0")
    n = 1
    while n < n0:
        n <<= 1
    re = list(vals) + [0.0] * (n - n0)
    im = [0.0] * n
    _fft(re, im)
    half = n // 2
    freqs, amp = [], []
    for k in range(half):
        freqs.append(fs * k / n)
        m = math.hypot(re[k], im[k]) / n0
        amp.append(m if k == 0 else m * 2)
    return freqs, amp


def _mask(fk: float, kind: str, fc: float, fc2, edge: float) -> float:
    """Raised-cosine transition of half-width edge*fc around the cutoff (reduces ringing)."""
    def lp(f, c):
        w = max(1e-9, edge * c)
        if f <= c - w:
            return 1.0
        if f >= c + w:
            return 0.0
        return 0.5 * (1 + math.cos(math.pi * (f - (c - w)) / (2 * w)))

    if kind == "high":
        return 1 - lp(fk, fc)
    if kind == "band" and fc2 is not None:
        return (1 - lp(fk, fc)) * lp(fk, fc2)
    return lp(fk, fc)  # low


def fft_filter(y: list, fs: float, kind: str = "low", fc: float = None, fc2=None, edge: float = 0.15):
    """FFT-domain filter (low/high/band) with a soft transition. Returns the filtered signal
    (same length as input). Matches the client-side JS used for live slider updates."""
    vals = [float(v) for v in y]
    n0 = len(vals)
    n = 1
    while n < n0:
        n <<= 1
    re = list(vals) + [0.0] * (n - n0)
    im = [0.0] * n
    _fft(re, im)
    for i in range(n):
        fk = fs * (i if i <= n // 2 else n - i) / n
        m = _mask(fk, kind, fc, fc2, edge)
        re[i] *= m
        im[i] *= m
    _ifft(re, im)
    return re[:n0]


def peaks(freqs: list, amp: list, topn: int = 4, min_ratio: float = 0.05):
    """Local maxima sorted by amplitude (descending). Skips DC and tiny peaks."""
    if not amp:
        return []
    amax = max(amp) or 1.0
    idx = [i for i in range(1, len(amp) - 1)
           if amp[i] > amp[i - 1] and amp[i] >= amp[i + 1] and amp[i] >= min_ratio * amax]
    idx.sort(key=lambda i: -amp[i])
    return [(freqs[i], amp[i]) for i in idx[:topn]]
