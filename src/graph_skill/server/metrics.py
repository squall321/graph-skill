"""Minimal in-process metrics in Prometheus text-exposition format (no external deps).
Thread-safe counters + gauges, served at GET /metrics for scraping."""

from __future__ import annotations

import threading


class Metrics:
    def __init__(self) -> None:
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._lock = threading.Lock()

    def inc(self, name: str, n: float = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + n

    def gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def snapshot(self) -> dict:
        with self._lock:
            return {"counters": dict(self._counters), "gauges": dict(self._gauges)}

    def render(self) -> str:
        lines = []
        with self._lock:
            for k, v in sorted(self._counters.items()):
                lines.append(f"# TYPE {k} counter")
                lines.append(f"{k} {v:g}")
            for k, v in sorted(self._gauges.items()):
                lines.append(f"# TYPE {k} gauge")
                lines.append(f"{k} {v:g}")
        return "\n".join(lines) + "\n"
