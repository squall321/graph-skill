"""Web + remote-MCP serving surface.

Transport + artifact serving layered over the shared transport-agnostic core (tools.py):
``build_app()`` returns a single Starlette ASGI app exposing REST (/v1/*), self-contained
artifact serving (/artifacts/<hash>) and remote MCP over Streamable HTTP (/mcp).
"""

from __future__ import annotations

from .store import ArtifactStore

__all__ = ["ArtifactStore", "build_app"]


def build_app(*args, **kwargs):
    from .app import build_app as _build_app
    return _build_app(*args, **kwargs)
