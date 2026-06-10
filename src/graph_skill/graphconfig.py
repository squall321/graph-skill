"""Build a standalone graph config {engine, plugins, options, assets, meta} from a payload.

Used by meta-artifacts (review-matrix) to embed graph cells that re-mount a real engine
in-document. Lazy imports avoid the recipes <-> graphconfig import cycle.
"""

from __future__ import annotations


class MissingFieldsError(Exception):
    def __init__(self, graph_type: str, missing: list):
        self.graph_type = graph_type
        self.missing = missing
        super().__init__(f"{graph_type}: missing {[m['field'] for m in missing]}")


def graph_config(graph_type: str, payload: dict, *, validate_cell: bool = True) -> dict:
    from . import catalog
    from . import validate as _validate
    from .assets import engine_version
    from .recipes import REGISTRY

    if validate_cell:
        v = _validate.check(graph_type, payload)
        if not v["ok"]:
            raise MissingFieldsError(graph_type, v["missing"])
    resolved = catalog.resolve_type(graph_type)
    norm = REGISTRY[graph_type].normalize(payload, resolved)
    return {
        "engine": resolved.engine,
        "plugins": list(resolved.plugins),
        "options": norm["options"],
        "assets": norm["assets"],
        "meta": {
            "engine_version": engine_version(resolved.engine),
            "graph_type": graph_type,
            "recommended_height_px": resolved.height_px,
        },
    }
