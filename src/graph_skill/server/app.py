"""Single ASGI app exposing graph-skill over the web + remote MCP.

  POST /v1/render        render -> content-addressed artifact (returns hash + artifact_url)
  POST /v1/lint          lint a stored artifact by hash
  POST /v1/embed         report-write html_embed fragment for a stored artifact
  POST /v1/<tool>        pure-compute tools over tools.DISPATCH (types/find/schema/validate/
                         ingest_csv/ingest_s2p/resample/smooth)
  GET  /artifacts/<hash> serve the self-contained HTML (immutable cache + CSP)
  GET  /healthz          liveness
  GET  /metrics          Prometheus metrics (render counts/errors, inflight, store size)
  /mcp                   remote MCP over Streamable HTTP (reuses mcp_server._build_server)

Heavy renders (cad3d/numpy) are bounded by a concurrency semaphore (GRAPH_MAX_CONCURRENT_RENDERS).

The render core, engine assets, determinism and self-contained gate are reused unchanged;
only transport, artifact serving and env-gated security live here.
"""

from __future__ import annotations

import asyncio
import contextlib
import os

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Mount, Route

from .. import catalog, mcp_server, tools
from . import service
from .metrics import Metrics
from .security import SecurityMiddleware
from .store import ArtifactStore

# tools safe for the generic passthrough: pure compute, JSON in/out, no disk / statefulness.
# render/lint/embed get dedicated artifact-aware routes (the DISPATCH versions take disk
# paths and write files — wrong for a stateless server).
_PASSTHROUGH = frozenset({
    "graph_types_list", "graph_find", "graph_schema_get", "graph_validate_inputs",
    "ingest_csv", "ingest_s2p", "resample", "smooth",
})

_CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
        "img-src data: blob:; font-src data:; connect-src 'none'; base-uri 'none'")


async def _json_body(request) -> dict:
    try:
        body = await request.json()
        return body if isinstance(body, dict) else {}
    except Exception:
        return {}


def build_app(store: ArtifactStore | None = None, *, mount_mcp: bool = True) -> Starlette:
    store = store or ArtifactStore(disk_dir=os.environ.get("GRAPH_ARTIFACT_DIR") or None)
    metrics = Metrics()
    # Bound concurrent heavy renders (cad3d/numpy) so a burst can't exhaust the threadpool/memory.
    max_render = max(1, int(os.environ.get("GRAPH_MAX_CONCURRENT_RENDERS", str(max(2, (os.cpu_count() or 4))))))
    render_sem = asyncio.Semaphore(max_render)
    inflight = [0]

    async def health(request):
        return JSONResponse({"status": "ok", "service": "graph-skill",
                             "types": len(catalog.known_types()),
                             "tools": sorted(tools.DISPATCH)})

    async def metrics_ep(request):
        metrics.gauge("graphskill_store_items", len(store))
        metrics.gauge("graphskill_render_max_concurrency", max_render)
        return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")

    async def passthrough(request):
        name = request.path_params["tool"]
        if name not in _PASSTHROUGH:
            return JSONResponse({"error": f"unknown or non-REST tool: {name}"}, status_code=404)
        args = await _json_body(request)
        try:  # offload to a thread — ingest/resample/smooth can be CPU-heavy on large input
            return JSONResponse(await run_in_threadpool(tools.DISPATCH[name], args))
        except KeyError as e:
            return JSONResponse({"error": "bad_request", "message": str(e)}, status_code=400)
        except Exception as e:  # surface as data (same contract as the MCP adapter)
            return JSONResponse({"error": type(e).__name__, "message": str(e)}, status_code=400)

    async def render(request):
        args = await _json_body(request)
        gt = args.get("graph_type")
        if not gt:
            return JSONResponse({"error": "missing graph_type"}, status_code=400)
        base = str(request.base_url).rstrip("/")
        metrics.inc("graphskill_render_requests_total")
        async with render_sem:                        # bound concurrent heavy renders
            inflight[0] += 1
            metrics.gauge("graphskill_render_inflight", inflight[0])
            try:  # builder.render is sync + CPU-heavy (cad3d/numpy) — never run it on the event loop
                res = await run_in_threadpool(service.render_to_store, gt, tools._payload(args), store,
                                              embed_mode=args.get("embed_mode", "standalone"), base_url=base)
            except KeyError as e:
                metrics.inc("graphskill_render_errors_total")
                return JSONResponse({"error": "unknown_graph_type", "message": str(e)}, status_code=404)
            except RuntimeError as e:  # self-contained gate (e.g. external image.ref)
                metrics.inc("graphskill_render_errors_total")
                return JSONResponse({"error": "self_contained_gate", "message": str(e)}, status_code=422)
            finally:
                inflight[0] -= 1
                metrics.gauge("graphskill_render_inflight", inflight[0])
        if res.get("status") == "needs_input":
            metrics.inc("graphskill_needs_input_total")
        else:
            metrics.inc("graphskill_renders_total")
        return JSONResponse(res, status_code=422 if res.get("status") == "needs_input" else 200)

    async def lint(request):
        args = await _json_body(request)
        if not args.get("hash"):
            return JSONResponse({"error": "provide 'hash' of a rendered artifact"}, status_code=400)
        try:
            return JSONResponse(await run_in_threadpool(service.lint_stored, args["hash"], store))
        except KeyError as e:
            return JSONResponse({"error": "unknown_artifact", "message": str(e)}, status_code=404)

    async def embed(request):
        args = await _json_body(request)
        if not args.get("hash"):
            return JSONResponse({"error": "provide 'hash' of a rendered artifact"}, status_code=400)
        base = str(request.base_url).rstrip("/")
        try:
            return JSONResponse(await run_in_threadpool(service.embed_stored, args["hash"], store,
                                height_px=args.get("height_px"), caption=args.get("caption"),
                                base_url=base, mode=args.get("mode", "url")))
        except KeyError as e:
            return JSONResponse({"error": "unknown_artifact", "message": str(e)}, status_code=404)

    async def artifact(request):
        data = store.get(request.path_params["h"])
        if data is None:
            metrics.inc("graphskill_artifacts_miss_total")
            return JSONResponse({"error": "not found"}, status_code=404)
        metrics.inc("graphskill_artifacts_served_total")
        return Response(data, media_type="text/html; charset=utf-8", headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "Content-Security-Policy": _CSP,
            "X-Content-Type-Options": "nosniff",
        })

    routes = [
        Route("/healthz", health, methods=["GET"]),
        Route("/metrics", metrics_ep, methods=["GET"]),
        Route("/v1/render", render, methods=["POST"]),
        Route("/v1/lint", lint, methods=["POST"]),
        Route("/v1/embed", embed, methods=["POST"]),
        Route("/v1/{tool}", passthrough, methods=["POST"]),
        Route("/artifacts/{h}", artifact, methods=["GET"]),
    ]

    lifespan = None
    if mount_mcp:
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

        sm = StreamableHTTPSessionManager(app=mcp_server._build_server(), stateless=True)

        async def handle_mcp(scope, receive, send):
            await sm.handle_request(scope, receive, send)

        @contextlib.asynccontextmanager
        async def _lifespan(_app):
            async with sm.run():
                yield

        lifespan = _lifespan
        routes.append(Mount("/mcp", app=handle_mcp))

    app = Starlette(routes=routes, lifespan=lifespan)
    app.add_middleware(SecurityMiddleware)
    app.state.store = store
    app.state.metrics = metrics
    return app


def main() -> None:
    import uvicorn

    uvicorn.run(build_app(), host=os.environ.get("GRAPH_HOST", "127.0.0.1"),
                port=int(os.environ.get("GRAPH_PORT", "8000")), log_level="info")


if __name__ == "__main__":
    main()
