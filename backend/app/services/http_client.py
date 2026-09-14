"""Shared httpx.AsyncClient factory for provider + service HTTP calls.

Provides a module-level shared client per timeout value so provider clients
reuse connections (keep-alive) instead of constructing an AsyncClient per call.

Connection pooling: Limits(max_connections=100, max_keepalive_connections=20).
HTTP/2 is enabled when the `h2` package is available, otherwise plain HTTP/1.1.
"""

from __future__ import annotations

import httpx

_CLIENTS: dict[float, httpx.AsyncClient] = {}

_DEFAULT_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)


def build_timeout(timeout: float | int) -> httpx.Timeout:
    """Build a granular timeout from a per-call read timeout in seconds."""
    read = float(timeout)
    return httpx.Timeout(connect=10.0, read=read, write=10.0, pool=10.0)


def _http2_available() -> bool:
    try:
        import h2  # noqa: F401
        return True
    except ImportError:
        return False


def get_shared_client(timeout: float | int = 120) -> httpx.AsyncClient:
    """Return a module-level shared AsyncClient for the given read timeout.

    Clients are cached by timeout value. Do NOT close the returned client
    (no `async with` on the client itself); only use `async with` on
    `client.stream(...)` contexts which do not close the shared client.
    """
    key = float(timeout)
    existing = _CLIENTS.get(key)
    if existing is not None:
        return existing
    limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
    t = build_timeout(key)
    try:
        if _http2_available():
            client = httpx.AsyncClient(timeout=t, limits=limits, http2=True)
        else:
            client = httpx.AsyncClient(timeout=t, limits=limits)
    except ImportError:
        # httpx raises ImportError when http2=True but h2 is missing.
        client = httpx.AsyncClient(timeout=t, limits=limits)
    _CLIENTS[key] = client
    return client
