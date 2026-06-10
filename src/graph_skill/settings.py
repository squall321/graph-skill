"""Runtime settings — no network, no tokens. Just where artifacts are written."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Resolved from environment with safe defaults."""

    out_dir: Path
    embed_mode: str  # "standalone" | "srcdoc-fragment"

    @classmethod
    def load(cls) -> "Settings":
        out = os.environ.get("GRAPH_OUT_DIR", "").strip()
        out_dir = Path(out) if out else Path.cwd() / "graph-out"
        embed = os.environ.get("GRAPH_EMBED_MODE", "standalone").strip() or "standalone"
        return cls(out_dir=out_dir, embed_mode=embed)
