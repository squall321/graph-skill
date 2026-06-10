"""HTML builder (the ``client.py`` slot, replaced for the artifact model).

Engine-agnostic: assembles the resolved engine family + plugins + normalized config +
inlined data into a single self-contained .html. Deterministic (same input -> same bytes).
The self-contained lint is run as an output gate before returning.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import assets, catalog, serialize, validate
from .recipes import REGISTRY


class MissingFieldsError(Exception):
    """Raised when required background inputs are absent — render is blocked."""

    def __init__(self, graph_type: str, missing: list[dict]):
        self.graph_type = graph_type
        self.missing = missing
        super().__init__(f"{graph_type}: missing {[m['field'] for m in missing]}")


def _html_escape(s: str) -> str:
    return (
        str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _collect_engines(primary: str, plugins: list, norm: dict):
    """Engines + (engine, plugin) pairs referenced by this artifact, including any graph
    cells embedded by a meta-artifact (review-matrix) via assets.graph_payloads."""
    engines = {primary}
    pairs = {(primary, p) for p in plugins}
    gps = (norm.get("assets") or {}).get("graph_payloads") or {}
    for gp in gps.values():
        engines.add(gp["engine"])
        for p in gp.get("plugins", []):
            pairs.add((gp["engine"], p))
    return engines, pairs


def assemble(graph_type: str, resolved, norm: dict, embed_mode: str = "standalone") -> str:
    engine = resolved.engine
    engines, pairs = _collect_engines(engine, list(resolved.plugins), norm)
    template = assets.read_shell("template.html")
    engine_js = "\n".join(assets.read_engine_js(e) for e in sorted(engines))
    engine_css = "\n".join(assets.read_engine_css(e) for e in sorted(engines))
    plugins_js = "\n".join(assets.read_plugin(e, p) for (e, p) in sorted(pairs))
    boot_js = assets.read_shell("boot.js")
    ev = assets.engine_version(engine)

    config = {
        "engine": engine,
        "plugins": list(resolved.plugins),
        "options": norm["options"],
        "assets": norm["assets"],
        "meta": {
            "engine_version": ev,
            "graph_type": graph_type,
            "recommended_height_px": resolved.height_px,
            "generator": "graph-skill",
        },
    }
    cfg_json = serialize.safe_js_literal(config)
    title = norm["options"].get("title") or graph_type

    html = (
        template
        .replace("{{ENGINE_NAME}}", engine)
        .replace("{{ENGINE_VERSION}}", ev)
        .replace("{{TITLE}}", _html_escape(title))
        .replace("{{CSS}}", engine_css)
        .replace("{{CONFIG}}", cfg_json)
        .replace("{{ENGINE_JS}}", engine_js)
        .replace("{{PLUGINS_JS}}", plugins_js)
        .replace("{{BOOT_JS}}", boot_js)
    )
    # srcdoc-fragment currently returns the same standalone document; consumers that target
    # iframe.srcdoc should set it via the .srcdoc *property* (no entity escaping needed).
    return html


def render(graph_type: str, payload: dict, out_path: str | None = None,
           embed_mode: str = "standalone") -> dict:
    """Validate -> normalize -> assemble -> lint -> (optionally write).

    Raises MissingFieldsError if the completeness gate is not satisfied.
    """
    if graph_type not in catalog.known_types():
        raise KeyError(f"unknown graph_type: '{graph_type}' (known: {catalog.known_types()})")

    v = validate.check(graph_type, payload)
    if not v["ok"]:
        raise MissingFieldsError(graph_type, v["missing"])

    resolved = catalog.resolve_type(graph_type)
    norm = REGISTRY[graph_type].normalize(payload, resolved)
    html = assemble(graph_type, resolved, norm, embed_mode)

    lint = serialize.lint_self_contained(html)
    if not lint["ok"]:
        raise RuntimeError(f"self-contained gate failed: {lint}")

    result = {
        "graph_type": graph_type,
        "engine": resolved.engine,
        "engine_version": assets.engine_version(resolved.engine),
        "recommended_height_px": resolved.height_px,
        "bytes": len(html.encode("utf-8")),
        "lint": lint,
    }
    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # newline="\n": no CRLF translation -> byte-identical artifacts across platforms.
        p.write_text(html, encoding="utf-8", newline="\n")
        result["html_path"] = str(p.resolve())
    else:
        result["html"] = html
    return result


def lint(html: str) -> dict:
    return serialize.lint_self_contained(html)


def lint_file(html_path: str) -> dict:
    html = Path(html_path).read_text(encoding="utf-8")
    res = serialize.lint_self_contained(html)
    res["bytes"] = len(html.encode("utf-8"))
    res["html_path"] = str(Path(html_path).resolve())
    return res


def _artifact_height(html_path: str) -> int | None:
    """Read meta.recommended_height_px back out of the artifact's #graph-config JSON."""
    try:
        html = Path(html_path).read_text(encoding="utf-8")
        m = re.search(r'<script id="graph-config" type="application/json">(.*?)</script>', html, re.S)
        if not m:
            return None
        cfg = json.loads(m.group(1))
        return int((cfg.get("meta") or {}).get("recommended_height_px"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def embed_block(html_path: str, height_px: int | None = None, caption: str | None = None) -> dict:
    """Produce a report-write `html_embed` draft fragment. upload_chain swaps local_path -> file_id.
    Default height comes from the artifact's own recommended_height_px (gauge 320 != matrix 600).
    `id` is required by report-write's extra_blocks contract (found in live publish testing)."""
    h = max(60, min(4000, int(height_px) if height_px else (_artifact_height(html_path) or 520)))
    block: dict = {
        "id": f"graph-{Path(html_path).stem}",
        "type": "html_embed",
        "input": {"local_path": str(Path(html_path).resolve()), "height_px": h},
    }
    if caption:
        block["input"]["caption"] = str(caption)[:200]
    return block
