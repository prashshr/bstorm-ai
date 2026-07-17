"""Server-side short-lived cache that maps an opaque session id (sid) to a
user's decrypted User Encryption Key (UEK).

Why this exists:
- The web app embeds the UEK directly in the JWT (legacy flow, unchanged).
- Mobile clients must NEVER receive the UEK. Instead they get an access token
  carrying only a `sid`; the server resolves the UEK from this cache.

The cache lives only in process memory and is keyed by a cryptographically
random sid. Entries expire with the refresh token. On process restart all
sessions are invalidated (users simply re-login) — acceptable for this app.
"""

from __future__ import annotations

import secrets
import threading
import time

# sid -> {"uek": str, "user_id": int, "exp": float}
_CACHE: dict[str, dict] = {}
_LOCK = threading.Lock()


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


def put_uek(sid: str, user_id: int, uek: str, ttl_seconds: int) -> None:
    with _LOCK:
        _CACHE[sid] = {
            "uek": uek,
            "user_id": user_id,
            "exp": time.time() + ttl_seconds,
        }


def get_uek(sid: str) -> str | None:
    with _LOCK:
        entry = _CACHE.get(sid)
        if not entry:
            return None
        if entry["exp"] < time.time():
            _CACHE.pop(sid, None)
            return None
        return entry["uek"]


def drop_session(sid: str) -> None:
    with _LOCK:
        _CACHE.pop(sid, None)


def drop_user(user_id: int) -> None:
    """Invalidate every cached session for a user (used on logout-all)."""
    with _LOCK:
        for key in [k for k, v in _CACHE.items() if v.get("user_id") == user_id]:
            _CACHE.pop(key, None)
