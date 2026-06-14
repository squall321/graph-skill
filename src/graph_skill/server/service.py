"""Stateless service layer for the web / remote-MCP surface.

``tools.render_payload`` always writes a file to ``Settings.out_dir`` (cwd-derived) — fine
for a local CLI, wrong for a multi-tenant server (shared cwd, client-controlled out_path).
These functions never touch arbitrary disk paths: ``render_to_store`` renders to a string
(``builder.render(out_path=None)``) and content-addresses it into an ``ArtifactStore``;
``lint_stored`` / ``embed_stored`` operate on stored hashes. The render core, engines,
determinism and self-contained gate are reused unchanged.
"""

from __future__ import annotations

import json
import re

from .. import builder, prompt, serialize
from .store import ArtifactStore

_CFG = re.compile(r'<script id="graph-config" type="application/json">(.*?)</script>', re.S)


def _artifact_height(html: str) -> int | None:
    m = _CFG.search(html)
    if not m:
        return None
    try:
        cfg = json.loads(m.group(1))
        return int((cfg.get("meta") or {}).get("recommended_height_px"))
    except (ValueError, TypeError):
        return None


def _url(base_url: str, h: str) -> str:
    base = (base_url or "").rstrip("/")
    return f"{base}/artifacts/{h}"


def render_to_store(graph_type: str, payload: dict, store: ArtifactStore, *,
                    embed_mode: str = "standalone", base_url: str = "") -> dict:
    """Render to a content-addressed artifact. Returns ok+hash+artifact_url, or needs_input
    (the NEVER-invent gate, never bypassed). Raises KeyError (unknown type) / RuntimeError
    (self-contained gate) for the caller to map to a 4xx."""
    try:
        res = builder.render(graph_type, payload, out_path=None, embed_mode=embed_mode)
    except builder.MissingFieldsError as e:
        return {
            "status": "needs_input",
            "graph_type": graph_type,
            "missing": e.missing,
            "questions": [m["ask"] for m in e.missing],
            "rule": prompt.PREAMBLE,
        }
    html = res.pop("html")
    h = store.put(html)
    res["status"] = "ok"
    res["hash"] = h
    res["artifact_url"] = _url(base_url, h)
    res["next"] = "GET artifact_url 로 self-contained HTML 수신, 또는 /v1/embed 로 게시 조각 생성"
    return res


def lint_stored(h: str, store: ArtifactStore) -> dict:
    data = store.get(h)
    if data is None:
        raise KeyError(f"unknown artifact: {h}")
    res = serialize.lint_self_contained(data.decode("utf-8"))
    res["bytes"] = len(data)
    res["hash"] = h
    return res


def embed_stored(h: str, store: ArtifactStore, *, height_px: int | None = None,
                 caption: str | None = None, base_url: str = "", mode: str = "url",
                 out_dir: str | None = None) -> dict:
    """report-write html_embed fragment for a stored artifact.
    mode='url' (default): {url} pointing at the served artifact (for URL-capable embedders).
    mode='local_path': materialize the artifact to a file and return {local_path} matching
    builder.embed_block's shape, so report-write's upload_chain swaps local_path->file_id
    (bridges a web-rendered graph to in-house ReportArchive publishing)."""
    data = store.get(h)
    if data is None:
        raise KeyError(f"unknown artifact: {h}")
    html = data.decode("utf-8")
    hp = max(60, min(4000, int(height_px) if height_px else (_artifact_height(html) or 520)))
    block: dict = {"id": f"graph-{h[:12]}", "type": "html_embed", "input": {"height_px": hp}}
    if mode == "local_path":
        import os
        import pathlib
        d = pathlib.Path(out_dir or os.environ.get("GRAPH_ARTIFACT_DIR") or ".")
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{h}.html"
        if not p.exists():
            p.write_bytes(data)
        block["input"]["local_path"] = str(p.resolve())
    else:
        block["input"]["url"] = _url(base_url, h)
    if caption:
        block["input"]["caption"] = str(caption)[:200]
    return block
