import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.sessions import revoke_user_sessions
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.crypto import derive_pdk, encrypt_uek, decrypt_uek
from app.db.session import get_db
from app.models.models import RefreshToken, User, UserSetting

logger = logging.getLogger("ai_ensemble.user")

router = APIRouter()


class UserSettingsResponse(BaseModel):
    settings: Dict[str, Any]


class UserSettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any]


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    # Optional. When supplied and still valid for this user, the matching
    # session is preserved and every other session is revoked. When omitted,
    # all sessions are revoked, which is the safe default; the caller's
    # stateless access token keeps working until it expires on its own.
    refresh_token: str | None = None


@router.get("/settings", response_model=UserSettingsResponse)
@limiter.limit("60/minute")
def get_user_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    row = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    if not row:
        return UserSettingsResponse(settings={})
    try:
        data = json.loads(row.settings_json or "{}")
    except Exception:
        data = {}
    return UserSettingsResponse(settings=data)


@router.put("/settings", response_model=UserSettingsResponse)
@limiter.limit("30/minute")
def update_user_settings(
    request: Request,
    payload: UserSettingsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    row = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    if not row:
        row = UserSetting(user_id=current_user.id, settings_json=json.dumps(payload.settings))
        db.add(row)
    else:
        try:
            existing = json.loads(row.settings_json or "{}")
        except Exception:
            existing = {}
        existing.update(payload.settings)
        row.settings_json = json.dumps(existing)

    db.commit()
    db.refresh(row)
    return UserSettingsResponse(settings=json.loads(row.settings_json or "{}"))


@router.post("/change-password", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long.",
        )

    # Re-encrypt UEK with new password PDK if master_key_encrypted exists
    if current_user.master_key_encrypted and current_user.encryption_salt:
        try:
            old_pdk = derive_pdk(payload.current_password, current_user.encryption_salt, iterations=600_000)
            uek = decrypt_uek(current_user.master_key_encrypted, old_pdk)
        except Exception:
            old_pdk = derive_pdk(payload.current_password, current_user.encryption_salt, iterations=100_000)
            uek = decrypt_uek(current_user.master_key_encrypted, old_pdk)

        new_pdk = derive_pdk(payload.new_password, current_user.encryption_salt, iterations=600_000)
        current_user.master_key_encrypted = encrypt_uek(uek, new_pdk)

    current_user.password_hash = get_password_hash(payload.new_password)

    # Bump the token version so every access token issued before this moment
    # becomes invalid immediately. That closes the window for stateless web
    # tokens (UEK claim, no session id), which nothing else can revoke: they
    # are checked against users.token_version on every request instead of
    # surviving for the rest of their lifetime.
    current_user.token_version = (current_user.token_version or 1) + 1
    new_token_version = current_user.token_version

    # Revoke every other session so a password change actually ends access from
    # a stolen device. The session that is making this request is preserved when
    # it can be identified, so the user is not logged out of the action they
    # just performed.
    keep_sid: str | None = None
    if payload.refresh_token:
        token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
        candidate = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == current_user.id,
                RefreshToken.revoked == False,  # noqa: E712
            )
            .first()
        )
        # Only honour the hint when the row is still live and unexpired.
        # expires_at is read back from a timezone-naive DateTime column, so the
        # comparison must use a naive UTC value; comparing against an aware
        # datetime raises TypeError.
        if candidate is not None and candidate.expires_at > datetime.utcnow():
            keep_sid = candidate.sid

    rows = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked == False,  # noqa: E712
        )
        .all()
    )
    revoked = 0
    for row in rows:
        if keep_sid is not None and row.sid == keep_sid:
            continue
        row.revoked = True
        revoked += 1
    dropped_sessions = revoke_user_sessions(current_user.id, keep_sid=keep_sid)

    db.commit()

    # The bump above invalidated this session's own access token too, so hand
    # back a replacement: the user keeps looking at the dialog they just used
    # instead of being signed out of it. Refresh tokens are untouched — the
    # caller's session is the one that was preserved above.
    session_claims: dict = {}
    if current_user.sid:
        session_claims["sid"] = current_user.sid
    elif current_user.uek:
        session_claims["uek"] = current_user.uek
    access_token = create_access_token(
        str(current_user.id), new_token_version, extra_claims=session_claims or None
    )

    return {
        "ok": True,
        "message": "Password updated successfully.",
        "sessions_revoked": revoked,
        "server_sessions_dropped": dropped_sessions,
        "current_session_kept": keep_sid is not None,
        # Stateless clients must adopt this immediately: their previous token
        # no longer passes the token-version check.
        "access_token": access_token,
        "token_version": new_token_version,
    }
