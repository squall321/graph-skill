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


def lint_self_contained(html: str) -> dict:
    """Static gate: the artifact must reference zero external resources and have one root."""
    external = _EXTERNAL_URL.findall(html) + _IMPORT_URL.findall(html)
    roots = _HTML_ROOT.findall(html)
    return {
        "ok": (len(external) == 0) and (len(roots) == 1),
        "external_urls": len(external),
        "self_contained": len(external) == 0,
        "single_root": len(roots) == 1,
    }
