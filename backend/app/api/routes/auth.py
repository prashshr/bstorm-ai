from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.core.sessions import new_session_id, put_uek, drop_session, drop_user, get_uek
from app.core.config import settings
from app.db.session import get_db
from app.models.models import User, ProviderCredential, Discussion, Message, SearchHistory, RefreshToken
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, RefreshRequest
from app.core.crypto import (
    generate_salt,
    generate_random_key,
    derive_pdk,
    encrypt_uek,
    decrypt_uek,
    decrypt_secret,
    encrypt_secret,
    encrypt_field,
    decrypt_field_or_plaintext,
)
import hashlib


router = APIRouter()


def _normalize_email(raw: str) -> str:
    """Allow short local usernames (e.g. "admin") by mapping them to the
    internal local domain, mirroring the frontend behaviour."""
    raw = (raw or "").strip()
    if not raw:
        return raw
    if "@" not in raw:
        return f"{raw}@local.ai-ensemble"
    return raw


@router.post("/register", response_model=TokenResponse)
@limiter.limit("10/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = _normalize_email(payload.email)
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    # Generate salt and user-specific master key (UEK)
    salt_hex = generate_salt()
    uek = generate_random_key()
    pdk = derive_pdk(payload.password, salt_hex)
    uek_encrypted = encrypt_uek(uek, pdk)

    user = User(
        email=email,
        password_hash=get_password_hash(payload.password),
        encryption_salt=salt_hex,
        master_key_encrypted=uek_encrypted,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(str(user.id), extra_claims={"uek": uek}))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = _normalize_email(payload.email)
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Auto-migration for legacy users
    if not user.master_key_encrypted:
        salt_hex = generate_salt()
        uek = generate_random_key()
        pdk = derive_pdk(payload.password, salt_hex)
        uek_encrypted = encrypt_uek(uek, pdk)

        user.encryption_salt = salt_hex
        user.master_key_encrypted = uek_encrypted

        # Re-encrypt legacy provider credentials for this user
        creds = db.query(ProviderCredential).filter(ProviderCredential.user_id == user.id).all()
        for cred in creds:
            try:
                # Decrypt using legacy server key (decrypt_secret with no custom key falls back to legacy)
                api_key_plain = decrypt_secret(cred.api_key_encrypted)
                # Re-encrypt using the new user encryption key (UEK)
                cred.api_key_encrypted = encrypt_secret(api_key_plain, uek)
            except Exception:
                # Skip if already migrated or if decryption fails
                pass

        # Re-encrypt discussions
        discussions = db.query(Discussion).filter(Discussion.user_id == user.id).all()
        for disc in discussions:
            try:
                plain_title = decrypt_field_or_plaintext(disc.title, None)
                disc.title = encrypt_field(plain_title, uek)
                plain_question = decrypt_field_or_plaintext(disc.question, None)
                disc.question = encrypt_field(plain_question, uek)
                if disc.state_json:
                    plain_state = decrypt_field_or_plaintext(disc.state_json, None)
                    disc.state_json = encrypt_field(plain_state, uek)
            except Exception:
                pass

        # Re-encrypt messages
        messages = db.query(Message).filter(Message.user_id == user.id).all()
        for msg in messages:
            try:
                plain_content = decrypt_field_or_plaintext(msg.content, None)
                msg.content = encrypt_field(plain_content, uek)
            except Exception:
                pass

        # Re-encrypt search history
        histories = db.query(SearchHistory).filter(SearchHistory.user_id == user.id).all()
        for hist in histories:
            try:
                plain_query = decrypt_field_or_plaintext(hist.query, None)
                hist.query = encrypt_field(plain_query, uek)
            except Exception:
                pass

        db.commit()
        db.refresh(user)
    else:
        # Normal login: derive PDK and decrypt UEK
        # Try new iteration count first, fall back to legacy 100K for older users
        try:
            pdk = derive_pdk(payload.password, user.encryption_salt, iterations=600_000)
            uek = decrypt_uek(user.master_key_encrypted, pdk)
        except Exception:
            try:
                legacy_pdk = derive_pdk(payload.password, user.encryption_salt, iterations=100_000)
                uek = decrypt_uek(user.master_key_encrypted, legacy_pdk)
                # Re-encrypt with new iteration count for next login
                new_pdk = derive_pdk(payload.password, user.encryption_salt, iterations=600_000)
                user.master_key_encrypted = encrypt_uek(uek, new_pdk)
                db.commit()
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to decrypt secure storage key.",
                )

    access_token = create_access_token(str(user.id), extra_claims={"uek": uek})

    # Mobile clients: issue a refresh token and return an access token that
    # carries a server session id (sid) instead of the UEK, so the UEK is
    # never transmitted to or stored on the device.
    if payload.client == "mobile":
        sid = new_session_id()
        put_uek(sid, user.id, uek, ttl_seconds=settings.refresh_token_expire_days * 86400)
        refresh_jwt = create_refresh_token(str(user.id), extra_claims={"sid": sid})
        rt_hash = hashlib.sha256(refresh_jwt.encode()).hexdigest()
        db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=rt_hash,
                sid=sid,
                device_id=(request.headers.get("X-Device-Id") or None),
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=settings.refresh_token_expire_days),
                revoked=False,
            )
        )
        db.commit()
        # Access token for mobile carries sid, NOT uek.
        access_token = create_access_token(str(user.id), extra_claims={"sid": sid})
        return TokenResponse(access_token=access_token, refresh_token=refresh_jwt)

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("60/minute")
def refresh(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if claims.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    sid = claims.get("sid")
    row = db.query(RefreshToken).filter(RefreshToken.sid == sid).first()
    if not row or row.revoked or row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or expired")

    # Rotate: revoke the old refresh token, issue a new pair.
    row.revoked = True
    new_sid = new_session_id()
    uek = get_uek(sid)
    if not uek:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired; please log in again")
    put_uek(new_sid, row.user_id, uek, ttl_seconds=settings.refresh_token_expire_days * 86400)
    new_refresh = create_refresh_token(str(row.user_id), extra_claims={"sid": new_sid})
    db.add(
        RefreshToken(
            user_id=row.user_id,
            token_hash=hashlib.sha256(new_refresh.encode()).hexdigest(),
            sid=new_sid,
            device_id=row.device_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
            revoked=False,
        )
    )
    db.commit()
    access_token = create_access_token(str(row.user_id), extra_claims={"sid": new_sid})
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
def logout(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)) -> dict:
    try:
        claims = decode_token(payload.refresh_token)
    except Exception:
        return {"ok": True}
    sid = claims.get("sid")
    if sid:
        drop_session(sid)
        row = db.query(RefreshToken).filter(RefreshToken.sid == sid).first()
        if row:
            row.revoked = True
            db.commit()
    return {"ok": True}
