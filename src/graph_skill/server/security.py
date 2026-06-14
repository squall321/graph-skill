"""Env-gated security middleware: API-key auth + body-size limit + in-memory token-bucket
rate limit. Frictionless in dev (each control is off unless its env var is set), enforced in
prod via env. Implemented as a *pure ASGI* middleware (not BaseHTTPMiddleware) so it never
buffers responses — critical for the /mcp Streamable-HTTP (SSE) mount. Full OAuth and
distributed rate limiting are P2 (infra).

Env:
  GRAPH_API_KEY    if set, every request except /healthz must send it (Bearer or X-API-Key)
  GRAPH_MAX_BODY   max request body bytes (default 4 MiB) -> 413 (Content-Length + streaming)
  GRAPH_RATE_RPS   per-identity requests/sec (0 = off) -> 429
"""

from __future__ import annotations

import hmac
import json
import os
import threading
import time


class _TokenBucket:
    def __init__(self, rate: float, burst: float, idle_ttl: float = 3600.0, max_keys: int = 10000) -> None:
        self.rate = rate
        self.burst = burst
        self.idle_ttl = idle_ttl
        self.max_keys = max_keys
        self._b: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()
        self._calls = 0

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            self._calls += 1
            if self._calls % 1024 == 0:
                self._prune(now)
            tokens, last = self._b.get(key, (self.burst, now))
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            if tokens < 1.0:
                self._b[key] = (tokens, now)
                return False
            self._b[key] = (tokens - 1.0, now)
            return True

    def _prune(self, now: float) -> None:
        # drop idle identities, then hard-cap to bound memory under key-rotation attacks
        cutoff = now - self.idle_ttl
        for k in [k for k, (_t, last) in self._b.items() if last < cutoff]:
            del self._b[k]
        if len(self._b) > self.max_keys:
            stale = sorted(self._b, key=lambda k: self._b[k][1])[: len(self._b) - self.max_keys]
            for k in stale:
                del self._b[k]


async def _send_json(send, status: int, obj: dict) -> None:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json; charset=utf-8")]})
    await send({"type": "http.response.body", "body": body})


class SecurityMiddleware:
    def __init__(self, app) -> None:
        self.app = app
        self.api_key = os.environ.get("GRAPH_API_KEY", "").strip()
        self.max_body = int(os.environ.get("GRAPH_MAX_BODY", str(4 * 1024 * 1024)))
        rps = float(os.environ.get("GRAPH_RATE_RPS", "0") or "0")
        self.limiter = _TokenBucket(rps, max(1.0, rps * 2.0)) if rps > 0 else None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}
        path = scope.get("path", "")

        # 1) Content-Length fast reject (cheap, before any body read)
        cl = headers.get("content-length", "")
        if cl.isdigit() and int(cl) > self.max_body:
            return await _send_json(send, 413, {"error": "payload too large", "limit_bytes": self.max_body})

        # 2) auth — exact /healthz exemption (not prefix), constant-time key compare
        if self.api_key and path != "/healthz":
            auth = headers.get("authorization", "")
            token = auth[7:].strip() if auth.lower().startswith("bearer ") else headers.get("x-api-key", "")
            if not (token and hmac.compare_digest(token, self.api_key)):
                return await _send_json(send, 401, {"error": "unauthorized"})

        # 3) rate limit
        if self.limiter is not None:
            client = scope.get("client")
            ident = headers.get("x-api-key") or (client[0] if client else "anon")
            if not self.limiter.allow(ident):
                return await _send_json(send, 429, {"error": "rate limited"})

        # 4) streaming body guard — covers chunked / missing Content-Length (CL check above is
        # only a fast path). Wrap receive: stop feeding the app past the limit, suppress its
        # truncated response, emit our own 413.
        state = {"total": 0, "over": False, "started": False}

        async def rcv():
            if state["over"]:
                return {"type": "http.disconnect"}
            msg = await receive()
            if msg.get("type") == "http.request":
                state["total"] += len(msg.get("body", b""))
                if state["total"] > self.max_body:
                    state["over"] = True
                    return {"type": "http.disconnect"}
            return msg

        async def snd(message):
            if state["over"]:
                return  # drop the app's now-truncated response; we send 413 after
            if message["type"] == "http.response.start":
                state["started"] = True
            await send(message)

        await self.app(scope, rcv, snd)
        if state["over"] and not state["started"]:
            await _send_json(send, 413, {"error": "payload too large", "limit_bytes": self.max_body})
