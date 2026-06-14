"""Web + remote-MCP serving surface.
Locks: TOOLS<->DISPATCH parity (advertise-but-undispatchable drift — caught ingest_s2p),
content-addressed store (determinism, traversal guard), stateless service (render_to_store,
needs_input gate, lint/embed by hash), self-contained data-channel lint backstop (external
image.ref), and (web extra) REST endpoints + Streamable-HTTP MCP boot + security middleware."""
import json

import pytest

from graph_skill import catalog, serialize, tools
from graph_skill.server import service
from graph_skill.server.store import ArtifactStore

try:
    from starlette.testclient import TestClient

    import httpx  # noqa: F401  (TestClient needs it)
    from graph_skill.server.app import build_app
    _HAS_WEB = True
except Exception:  # pragma: no cover
    _HAS_WEB = False

web = pytest.mark.skipif(not _HAS_WEB, reason="web extra (starlette/httpx) not installed")

XY = {"graph_type": "base-xy", "axes": {"x": {"label": "t", "unit": "s"}, "y": {"label": "a", "unit": "mm"}},
      "series": [{"name": "a", "data": [[0, 0], [1, 1], [2, 4]]}]}


# --- transport-agnostic core (no web extra needed) ------------------------------

def test_tools_dispatch_parity():
    """Every advertised TOOL must be dispatchable, and vice versa. This is the guard that
    would have caught ingest_s2p being in TOOLS but missing from DISPATCH (unknown-tool
    failures only over MCP/remote, invisible to the CLI)."""
    advertised = {t["name"] for t in tools.TOOLS}
    dispatchable = set(tools.DISPATCH)
    assert advertised == dispatchable, {"advertised_only": sorted(advertised - dispatchable),
                                        "dispatch_only": sorted(dispatchable - advertised)}
    assert "ingest_s2p" in dispatchable


def test_store_determinism_and_traversal():
    st = ArtifactStore()
    h1 = st.put("<html>x</html>")
    h2 = st.put("<html>x</html>")
    assert h1 == h2 and len(h1) == 64               # byte-deterministic -> stable hash
    assert st.get(h1) == b"<html>x</html>"
    assert st.get("../../etc/passwd") is None        # non-hex key rejected before disk
    assert st.get("nope") is None


def test_service_render_lint_embed():
    st = ArtifactStore()
    r = service.render_to_store("base-xy", {k: v for k, v in XY.items() if k != "graph_type"}, st,
                                base_url="http://h")
    assert r["status"] == "ok" and r["artifact_url"].endswith(r["hash"])
    assert service.lint_stored(r["hash"], st)["ok"]
    emb = service.embed_stored(r["hash"], st, base_url="http://h", caption="c")
    assert emb["type"] == "html_embed" and emb["input"]["url"].endswith(r["hash"])
    with pytest.raises(KeyError):
        service.lint_stored("0" * 64, st)


def test_embed_local_path_mode(tmp_path):
    # report-write bridge: local_path mode materializes the artifact + returns the html_embed
    # fragment shape (id/type/input.local_path) that upload_chain swaps to a file_id.
    import pathlib

    st = ArtifactStore()
    h = st.put("<html>x</html>")
    blk = service.embed_stored(h, st, mode="local_path", out_dir=str(tmp_path), caption="c")
    assert blk["type"] == "html_embed" and "local_path" in blk["input"]
    assert pathlib.Path(blk["input"]["local_path"]).read_bytes() == b"<html>x</html>"
    assert blk["input"]["caption"] == "c"
    assert service.embed_stored(h, st, mode="url", base_url="http://h")["input"]["url"].endswith(h)


def test_service_needs_input_gate_not_bypassed():
    # NEVER-invent: missing A0/L0 -> needs_input (the server must never invent units)
    st = ArtifactStore()
    r = service.render_to_store("stress-strain", {"series": [{"name": "s", "data": [[0, 0], [1, 1]]}]}, st)
    assert r["status"] == "needs_input" and r["missing"]


def test_lint_backstop_external_data_ref():
    def blk(cfg):
        return f'<html><body><script id="graph-config" type="application/json">{json.dumps(cfg)}</script></body></html>'
    assert not serialize.lint_self_contained(blk({"image": {"ref": "https://evil/x.png"}}))["ok"]
    assert not serialize.lint_self_contained(blk({"image": {"ref": "//cdn.evil/x.png"}}))["ok"]
    assert serialize.lint_self_contained(blk({"image": {"mode": "inline", "data": "AAA"}}))["ok"]
    assert serialize.lint_self_contained(blk({"items": [{"cells": {"t": {"ref": "i0::v"}}}]}))["ok"]


# --- web surface (REST + remote MCP) --------------------------------------------

@web
def test_rest_render_artifact_roundtrip():
    c = TestClient(build_app(store=ArtifactStore(), mount_mcp=False))
    h = c.get("/healthz").json()
    assert h["status"] == "ok" and h["types"] == len(catalog.known_types()) and "ingest_s2p" in h["tools"]

    r = c.post("/v1/render", json=XY).json()
    assert r["status"] == "ok"
    art = c.get(f"/artifacts/{r['hash']}")
    assert art.status_code == 200 and art.headers["content-type"].startswith("text/html")
    assert "immutable" in art.headers.get("cache-control", "")
    assert "Content-Security-Policy" in art.headers
    assert art.text.lstrip().startswith("<")
    assert c.post("/v1/lint", json={"hash": r["hash"]}).json()["ok"]


@web
def test_rest_ingest_s2p_remote():
    c = TestClient(build_app(mount_mcp=False))
    s2p = "# MHz S DB R 50\n1000 -9.542425094393249 45 -1 10 -30 5 -12 20\n"
    r = c.post("/v1/ingest_s2p", json={"text": s2p})
    assert r.status_code == 200 and r.json()["n_points"] == 1


@web
def test_rest_error_mapping():
    c = TestClient(build_app(mount_mcp=False))
    # needs_input -> 422 (gate never bypassed)
    assert c.post("/v1/render", json={"graph_type": "stress-strain",
                                      "series": [{"name": "s", "data": [[0, 0], [1, 1]]}]}).status_code == 422
    assert c.post("/v1/render", json={"graph_type": "nope"}).status_code == 404      # unknown type
    assert c.post("/v1/lint", json={"hash": "0" * 64}).status_code == 404            # unknown artifact
    assert c.post("/v1/zzz", json={}).status_code == 404                             # non-REST tool


@web
def test_rest_image_ref_attack_blocked():
    c = TestClient(build_app(mount_mcp=False))
    attack = {"graph_type": "review-matrix", "states": [{"id": "v", "label": "V"}],
              "items": [{"id": "i0", "label": "x",
                         "cells": {"v": {"kind": "image", "image": {"mode": "ref", "ref": "https://evil/t.png"}}}}]}
    r = c.post("/v1/render", json=attack)
    assert r.status_code == 422 and r.json()["error"] == "self_contained_gate"


@web
def test_remote_mcp_streamable_http_boots():
    with TestClient(build_app(mount_mcp=True)) as c:   # context -> lifespan -> sm.run()
        assert c.get("/healthz").status_code == 200
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                           "clientInfo": {"name": "probe", "version": "0"}}}
        r = c.post("/mcp", json=init, headers={"Accept": "application/json, text/event-stream"})
        assert r.status_code == 200 and "graph-skill" in r.text


@web
def test_security_api_key(monkeypatch):
    monkeypatch.setenv("GRAPH_API_KEY", "secret123")
    c = TestClient(build_app(mount_mcp=False))               # middleware reads env at init
    assert c.get("/healthz").status_code == 200              # health exempt
    assert c.post("/v1/graph_types_list", json={}).status_code == 401
    assert c.post("/v1/graph_types_list", json={}, headers={"X-API-Key": "secret123"}).status_code == 200
    assert c.post("/v1/graph_types_list", json={},
                  headers={"Authorization": "Bearer secret123"}).status_code == 200


@web
def test_security_body_limit(monkeypatch):
    monkeypatch.setenv("GRAPH_MAX_BODY", "200")
    c = TestClient(build_app(mount_mcp=False))
    big = {"graph_type": "base-xy", "series": [{"name": "a", "data": [[i, i] for i in range(2000)]}]}
    assert c.post("/v1/render", json=big).status_code == 413


# --- P0 hardening guards --------------------------------------------------------

def test_store_lru_eviction():
    st = ArtifactStore(max_items=3)
    hs = [st.put(f"<html>{i}</html>") for i in range(5)]
    assert len(st) == 3                       # bounded — no unbounded growth (OOM guard)
    assert st.get(hs[0]) is None and st.get(hs[1]) is None   # oldest evicted
    assert st.get(hs[3]) is not None and st.get(hs[4]) is not None  # newest kept


def test_token_bucket_bounded():
    import time

    from graph_skill.server.security import _TokenBucket
    tb = _TokenBucket(rate=1000.0, burst=1000.0, idle_ttl=3600.0, max_keys=50)
    for i in range(5000):
        tb.allow(f"id{i}")                    # key-rotation attack simulation
    tb._prune(time.monotonic())
    assert len(tb._b) <= 50                   # hard cap bounds memory


@web
def test_render_offloaded_does_not_block_event_loop(monkeypatch):
    import asyncio
    import time

    from graph_skill.server import service as svc

    def slow(*a, **k):                        # simulate a heavy sync render (cad3d/numpy)
        time.sleep(0.6)
        return {"status": "ok", "hash": "0" * 64, "artifact_url": "u", "lint": {"ok": True}, "bytes": 1}

    monkeypatch.setattr(svc, "render_to_store", slow)
    app = build_app(mount_mcp=False)

    async def body():
        tr = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=tr, base_url="http://t") as c:
            task = asyncio.create_task(c.post("/v1/render", json={"graph_type": "base-xy", "series": []}))
            await asyncio.sleep(0.05)         # let the render start (and occupy a worker thread)
            t0 = time.monotonic()
            h = await c.get("/healthz")        # must NOT wait for the 0.6s render
            dt = time.monotonic() - t0
            await task
            return h.status_code, dt

    code, dt = asyncio.run(body())
    assert code == 200 and dt < 0.3           # event loop free -> healthz returns immediately


@web
def test_body_limit_streaming_chunked(monkeypatch):
    import asyncio

    monkeypatch.setenv("GRAPH_MAX_BODY", "500")
    app = build_app(mount_mcp=False)

    async def body():
        async def gen():
            for _ in range(20):               # 2000 bytes, chunked, NO Content-Length
                yield b"x" * 100

        tr = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/v1/render", content=gen())
            return r.status_code

    assert asyncio.run(body()) == 413          # streaming guard catches CL-less overflow
