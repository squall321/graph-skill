"""Content-addressed artifact store.

graph-skill artifacts are byte-deterministic (same input -> identical bytes), so
``sha256(html)`` is a natural, collision-safe key: identical render requests dedupe for
free and the resulting URL is immutable (CDN-cacheable). In-memory by default; set a disk
dir for cross-process / restart persistence. Keys are validated as 64-hex before any disk
access, so a hash coming from a URL path can never traverse the filesystem.

The in-memory map is a bounded LRU (``GRAPH_STORE_MAX_ITEMS``, default 512) so a
long-running server can't grow without limit -> OOM. In disk mode the directory is the
source of truth and ``_mem`` is just a small hot cache; a cache miss re-reads from disk.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections import OrderedDict
from pathlib import Path
from threading import RLock

_HEX = re.compile(r"^[0-9a-f]{64}$")


class ArtifactStore:
    def __init__(self, disk_dir: str | None = None, max_items: int | None = None) -> None:
        self._mem: "OrderedDict[str, bytes]" = OrderedDict()
        self._lock = RLock()
        self._dir = Path(disk_dir) if disk_dir else None
        if max_items is None:
            max_items = int(os.environ.get("GRAPH_STORE_MAX_ITEMS", "512"))
        self._max = max(1, max_items)
        if self._dir is not None:
            self._dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(html: str) -> str:
        return hashlib.sha256(html.encode("utf-8")).hexdigest()

    def _evict(self) -> None:
        while len(self._mem) > self._max:
            self._mem.popitem(last=False)  # drop least-recently-used

    def put(self, html: str) -> str:
        """Store the artifact, return its content hash. Idempotent (dedupes by hash)."""
        h = self.key(html)
        data = html.encode("utf-8")  # builder already used newline="\n" -> byte-identical
        with self._lock:
            self._mem[h] = data
            self._mem.move_to_end(h)
            self._evict()
            if self._dir is not None:
                p = self._dir / f"{h}.html"
                if not p.exists():
                    p.write_bytes(data)
        return h

    def get(self, h: str) -> bytes | None:
        if not _HEX.match(h or ""):
            return None  # reject non-hash keys before touching disk (traversal guard)
        with self._lock:
            if h in self._mem:
                self._mem.move_to_end(h)  # LRU touch
                return self._mem[h]
            if self._dir is not None:
                p = self._dir / f"{h}.html"
                if p.is_file():
                    data = p.read_bytes()
                    self._mem[h] = data  # promote into the bounded hot cache
                    self._mem.move_to_end(h)
                    self._evict()
                    return data
        return None

    def __contains__(self, h: str) -> bool:
        return self.get(h) is not None

    def __len__(self) -> int:
        return len(self._mem)
