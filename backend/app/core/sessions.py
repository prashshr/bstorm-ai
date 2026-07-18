"""Server-side store that maps an opaque session id (sid) to a user's
decrypted User Encryption Key (UEK).

Why this exists:
- The web app embeds the UEK directly in the JWT (legacy flow, unchanged).
- Mobile clients must NEVER receive the UEK. Instead they get an access token
  carrying only a `sid`; the server resolves the UEK from this store.

The mapping is persisted in the database (the UEK encrypted with the server
key), so it survives backend process restarts. An in-memory cache is kept for
hot-path speed; the DB is the source of truth. On restart the cache is empty
but the DB still holds valid sessions, so mobile clients do not need to
re-login and the discussion list keeps decrypting titles correctly.
"""

from __future__ import annotations

import secrets
import threading
import time

from sqlalchemy import select

from app.core.crypto import encrypt_secret, decrypt_secret
from app.db.session import SessionLocal
from app.models.models import SessionStore

# Hot-path cache mirroring the DB: sid -> {"uek", "user_id", "exp"}
_CACHE: dict[str, dict] = {}
_LOCK = threading.Lock()


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


def put_uek(sid: str, user_id: int, uek: str, ttl_seconds: int) -> None:
    exp = time.time() + ttl_seconds
    encrypted = encrypt_secret(uek)  # server-key encrypted at rest
    with _LOCK:
        _CACHE[sid] = {"uek": uek, "user_id": user_id, "exp": exp}
    db = SessionLocal()
    try:
        row = db.get(SessionStore, sid)
        if row is None:
            row = SessionStore(sid=sid, user_id=user_id)
        row.user_id = user_id
        row.uek_encrypted = encrypted
        row.exp = exp
        db.add(row)
        db.commit()
    finally:
        db.close()


def get_uek(sid: str) -> str | None:
    with _LOCK:
        entry = _CACHE.get(sid)
        if entry and entry["exp"] >= time.time():
            return entry["uek"]
    # Fall back to DB (cache empty after restart, or expired in cache).
    db = SessionLocal()
    try:
        row = db.get(SessionStore, sid)
        if row is None:
            return None
        if row.exp < time.time():
            db.delete(row)
            db.commit()
            return None
        uek = decrypt_secret(row.uek_encrypted)
        # Repopulate hot-path cache.
        with _LOCK:
            _CACHE[sid] = {"uek": uek, "user_id": row.user_id, "exp": row.exp}
        return uek
    finally:
        db.close()


def drop_session(sid: str) -> None:
    with _LOCK:
        _CACHE.pop(sid, None)
    db = SessionLocal()
    try:
        row = db.get(SessionStore, sid)
        if row is not None:
            db.delete(row)
            db.commit()
    finally:
        db.close()


def drop_user(user_id: int) -> None:
    """Invalidate every stored session for a user (used on logout-all)."""
    with _LOCK:
        for key in [k for k, v in _CACHE.items() if v.get("user_id") == user_id]:
            _CACHE.pop(key, None)
    db = SessionLocal()
    try:
        rows = db.execute(
            select(SessionStore).where(SessionStore.user_id == user_id)
        ).scalars().all()
        for r in rows:
            db.delete(r)
        db.commit()
    finally:
        db.close()
