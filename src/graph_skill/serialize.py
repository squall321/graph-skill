"""Safe, deterministic JSON serialization for inlining data into a <script> tag.

Single source of truth — the builder must never call ``json.dumps`` directly. This
neutralizes the sentinels that would break the ``</script>`` / srcdoc / template-literal
boundaries, and ``sort_keys=True`` makes the output deterministic (byte-identical for the
same input), which is what the golden/regression tests rely on.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Characters that would break out of a <script>...</script> or a JS string/template.
# Built with explicit code points to avoid raw control chars living in the source file.
_ESCAPES = {
    "<": "\\u003c",          # blocks </script>
    ">": "\\u003e",
    "&": "\\u0026",
    chr(0x2028): "\\u2028",  # JS line separator -> syntax error if left raw
    chr(0x2029): "\\u2029",  # JS paragraph separator
    "`": "\\u0060",          # template-literal backtick
}


def safe_js_literal(obj: Any) -> str:
    """Serialize ``obj`` to a JS-injection-safe, deterministic JSON string."""
    s = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,  # NaN/Inf must be replaced with null upstream (gap)
    )
    for k, v in _ESCAPES.items():
        s = s.replace(k, v)
    return s


_EXTERNAL_URL = re.compile(r'(?:src|href)\s*=\s*["\'](?:https?:)?//', re.IGNORECASE)
_IMPORT_URL = re.compile(r'@import\s+url\(\s*["\']?\s*https?:', re.IGNORECASE)
_HTML_ROOT = re.compile(r"(?im)^\s*<html\b")

# Data-channel external refs: the #graph-config JSON can carry image.ref/src/url/href
# values that an engine injects as a runtime <img src> — invisible to the markup-only
# regexes above (this was a real self-contained gate bypass). Parse the config block and
# flag external URLs under resource-bearing keys. data: URIs and internal ids never match.
_CFG_BLOCK = re.compile(r'<script id="graph-config" type="application/json">(.*?)</script>', re.S)
_EXTERNAL_VALUE = re.compile(r'^\s*(?:https?:)?//', re.IGNORECASE)
_RESOURCE_KEYS = frozenset({"ref", "src", "href", "url"})


def _walk_external(obj: Any, key: str | None = None) -> int:
    if isinstance(obj, dict):
        return sum(_walk_external(v, k) for k, v in obj.items())
    if isinstance(obj, list):
        return sum(_walk_external(v, key) for v in obj)
    if isinstance(obj, str) and key in _RESOURCE_KEYS and _EXTERNAL_VALUE.match(obj):
        return 1
    return 0


def _external_data_refs(html: str) -> int:
    total = 0
    for m in _CFG_BLOCK.finditer(html):
        try:
            total += _walk_external(json.loads(m.group(1)))
        except (ValueError, TypeError):
            continue
    return total


def lint_self_contained(html: str) -> dict:
    """Static gate: the artifact must reference zero external resources and have one root.
    Covers both the markup (src/href/@import) and the #graph-config data channel
    (image.ref/src/url the engine would turn into a runtime fetch)."""
    markup = _EXTERNAL_URL.findall(html) + _IMPORT_URL.findall(html)
    data_refs = _external_data_refs(html)
    external = len(markup) + data_refs
    roots = _HTML_ROOT.findall(html)
    return {
        "ok": (external == 0) and (len(roots) == 1),
        "external_urls": external,
        "external_markup": len(markup),
        "external_data_refs": data_refs,
        "self_contained": external == 0,
        "single_root": len(roots) == 1,
    }
