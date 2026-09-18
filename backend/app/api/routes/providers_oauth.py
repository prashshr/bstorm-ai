"""OAuth device-code / browser-OAuth logins for providers without API keys.

Supported flows:

- ``codex`` — ChatGPT device-code flow against ``CODEX_ISSUER``.
- ``copilot`` — GitHub Copilot device-code flow against GitHub.
- ``openrouter`` — OpenRouter browser-OAuth (PKCE) flow.

Tokens are encrypted with the user's UEK (same pattern as the providers.py
save path) and stored in the ``ProviderOAuthToken`` vault table. A companion
``ProviderCredential`` row is upserted so the proxy and model listing keep
working through the existing credential lookup.

NOTE (multi-worker limitation): pending device-code / OAuth ``state``
records live in process-local in-memory dicts (``_CODEX_PENDING``,
``_COPILOT_PENDING``, ``_OPENROUTER_PENDING``). With more than one backend replica,
a poll/callback request may land on a different worker than the start request
and fail to find the pending record. The deployment runs a single replica
(see deploy/k8s/deployment.yaml), so this is acceptable for now; persist
pending records in the DB or Redis if replicas are ever scaled up.
"""

import base64
import hashlib
import html
import json
import logging
import secrets
import time
import urllib.parse
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
import httpx
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import ProviderCredential, ProviderOAuthToken, User

logger = logging.getLogger("ai_ensemble.oauth")

router = APIRouter()

# How long a pending login (device code / browser OAuth) stays valid.
PENDING_TTL_SECONDS = 15 * 60

CODEX_PROVIDER = "codex"
COPILOT_PROVIDER = "copilot"
OPENROUTER_PROVIDER = "openrouter"

CODEX_CREDENTIAL_ENDPOINT = "https://chatgpt.com/backend-api/codex"
COPILOT_CREDENTIAL_ENDPOINT = "https://api.githubcopilot.com"
OPENROUTER_CREDENTIAL_ENDPOINT = "https://openrouter.ai/api/v1"

# Process-local pending-login stores (see module docstring for the caveat).
_CODEX_PENDING: dict[str, dict] = {}
_COPILOT_PENDING: dict[str, dict] = {}
_OPENROUTER_PENDING: dict[str, dict] = {}
_OPENROUTER_STATES: dict[str, dict] = {}
_OPENROUTER_RESULTS: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Pure helpers (no DB / network — safe for unit tests and the test client).
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.utcnow()


def decode_jwt_no_verify(token: str) -> dict:
    """Decode a JWT payload WITHOUT verifying the signature.

    Only used to extract non-sensitive routing claims (account id / email)
    from tokens freshly issued by the provider's own token endpoint.
    """
    try:
        parts = (token or "").split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8")
        data = json.loads(decoded)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def extract_codex_account_id(access_token: str, id_token: str | None = None) -> str:
    """Pick the ChatGPT account id out of freshly issued tokens."""
    claims = decode_jwt_no_verify(access_token)
    account = claims.get("chatgpt_account_id") or claims.get(
        "https://api.openai.com/auth.chatgpt_account_id"
    )
    if not account:
        orgs = claims.get("organizations") or []
        if orgs and isinstance(orgs[0], dict):
            account = orgs[0].get("id")
    if not account and id_token:
        account = decode_jwt_no_verify(id_token).get("email")
    return str(account or "")


def is_pending_expired(created_at: float, now: float | None = None) -> bool:
    """True when a pending login record is older than the 15-minute TTL."""
    return (now if now is not None else time.time()) - created_at > PENDING_TTL_SECONDS


def _purge_expired_pending() -> None:
    now = time.time()
    for store in (_CODEX_PENDING, _COPILOT_PENDING, _OPENROUTER_PENDING, _OPENROUTER_STATES, _OPENROUTER_RESULTS):
        for key in [k for k, v in store.items() if is_pending_expired(v.get("created_at", 0), now)]:
            store.pop(key, None)


# ---------------------------------------------------------------------------
# Shared persistence helper.
# ---------------------------------------------------------------------------


def _store_oauth_tokens(
    db: Session,
    *,
    user_id: int,
    provider: str,
    access_token: str,
    refresh_token: str,
    expires_in: int | None,
    account: str,
    scopes: str,
    uek: str | None,
    credential_endpoint: str,
) -> None:
    """Encrypt + upsert the vault row and its companion credential row.

    ``uek`` may be None (e.g. the unauthenticated Google callback); in that
    case encryption falls back to the server key and ``decrypt_secret`` still
    resolves it later via its legacy-key fallback.
    """
    now = _utcnow()
    expires_at = now + timedelta(seconds=int(expires_in)) if expires_in else None

    row = (
        db.query(ProviderOAuthToken)
        .filter(
            ProviderOAuthToken.user_id == user_id,
            ProviderOAuthToken.provider == provider,
        )
        .first()
    )
    if row:
        row.access_encrypted = encrypt_secret(access_token, key=uek)
        row.refresh_encrypted = encrypt_secret(refresh_token or "", key=uek)
        row.expires_at = expires_at
        row.account = account or None
        row.scopes = scopes or ""
    else:
        row = ProviderOAuthToken(
            user_id=user_id,
            provider=provider,
            access_encrypted=encrypt_secret(access_token, key=uek),
            refresh_encrypted=encrypt_secret(refresh_token or "", key=uek),
            expires_at=expires_at,
            account=account or None,
            scopes=scopes or "",
        )
        db.add(row)

    # Companion credential row (empty api_key, has_key=False) so the proxy's
    # existing credential lookup and model listing keep working. This
    # intentionally follows the providers.py upsert pattern.
    cred = (
        db.query(ProviderCredential)
        .filter(
            ProviderCredential.user_id == user_id,
            ProviderCredential.provider == provider,
        )
        .first()
    )
    empty_encrypted = encrypt_secret("", key=uek)
    if cred:
        cred.endpoint = credential_endpoint
        cred.api_key_encrypted = empty_encrypted
    else:
        cred = ProviderCredential(
            user_id=user_id,
            provider=provider,
            endpoint=credential_endpoint,
            api_key_encrypted=empty_encrypted,
        )
        db.add(cred)

    db.commit()


# ---------------------------------------------------------------------------
# Codex device-code flow.
# ---------------------------------------------------------------------------


@router.post("/codex/start")
@limiter.limit("30/minute")
async def codex_start(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Start a ChatGPT device-code login; frontend shows user_code + link."""
    issuer = settings.codex_issuer.rstrip("/")
    async with httpx.AsyncClient(timeout=30) as http:
        try:
            resp = await http.post(
                f"{issuer}/api/accounts/deviceauth/usercode",
                json={"client_id": settings.codex_client_id},
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not reach OpenAI device auth: {exc}",
            )
    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="device code login is not enabled for this account/server",
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"OpenAI device auth failed ({resp.status_code}): {resp.text[:250]}",
        )
    try:
        data = resp.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI device auth returned an unexpected response",
        )
    device_auth_id = data.get("device_auth_id") or data.get("device_id") or data.get("id")
    user_code = data.get("user_code") or data.get("userCode") or data.get("code")
    if not device_auth_id or not user_code:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenAI device auth returned an unexpected response",
        )
    verification_url = (
        data.get("verification_url")
        or data.get("verification_uri")
        or f"{issuer}/codex/device"
    )

    _purge_expired_pending()
    poll_token = secrets.token_urlsafe(32)
    _CODEX_PENDING[poll_token] = {
        "device_auth_id": device_auth_id,
        "user_code": user_code,
        "user_id": current_user.id,
        "created_at": time.time(),
    }
    return {
        "verification_url": verification_url,
        "user_code": user_code,
        "poll_token": poll_token,
        "expires_in": 900,
    }


async def _poll_codex_once(
    db: Session,
    *,
    poll_token: str,
    user_id: int,
    uek: str | None,
) -> dict:
    entry = _CODEX_PENDING.get(poll_token)
    if entry is None:
        return {"status": "error", "error": "Login session expired or not found. Please start again."}
    if entry.get("user_id") != user_id:
        return {"status": "error", "error": "Login session does not belong to this user."}
    if is_pending_expired(entry.get("created_at", 0)):
        _CODEX_PENDING.pop(poll_token, None)
        return {"status": "error", "error": "Login session expired. Please start again."}

    issuer = settings.codex_issuer.rstrip("/")
    # ONE upstream poll attempt per call; the frontend re-polls every ~2.5s.
    async with httpx.AsyncClient(timeout=30) as http:
        try:
            resp = await http.post(
                f"{issuer}/api/accounts/deviceauth/token",
                json={
                    "device_auth_id": entry["device_auth_id"],
                    "user_code": entry["user_code"],
                },
            )
        except httpx.RequestError:
            return {"status": "pending"}
    if resp.status_code in (403, 404):
        return {"status": "pending"}
    if resp.status_code != 200:
        return {"status": "pending"}
    try:
        data = resp.json()
    except Exception:
        return {"status": "pending"}
    code = data.get("authorization_code") or data.get("code")
    code_verifier = data.get("code_verifier")
    if not code:
        return {"status": "pending"}

    exchange_payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": f"{issuer}/deviceauth/callback",
        "client_id": settings.codex_client_id,
    }
    if code_verifier:
        exchange_payload["code_verifier"] = code_verifier
    async with httpx.AsyncClient(timeout=30) as http:
        try:
            exchange = await http.post(f"{issuer}/oauth/token", data=exchange_payload)
        except httpx.RequestError as exc:
            _CODEX_PENDING.pop(poll_token, None)
            return {"status": "error", "error": f"Token exchange failed: {exc}"}
    if exchange.status_code >= 400:
        _CODEX_PENDING.pop(poll_token, None)
        return {
            "status": "error",
            "error": f"Token exchange failed ({exchange.status_code}). Please start again.",
        }
    tokens = exchange.json()
    access_token = tokens.get("access_token")
    if not access_token:
        _CODEX_PENDING.pop(poll_token, None)
        return {"status": "error", "error": "Token exchange returned no access token."}

    account = extract_codex_account_id(access_token, tokens.get("id_token"))
    _store_oauth_tokens(
        db,
        user_id=user_id,
        provider=CODEX_PROVIDER,
        access_token=access_token,
        refresh_token=tokens.get("refresh_token") or "",
        expires_in=tokens.get("expires_in"),
        account=account,
        scopes="",
        uek=uek,
        credential_endpoint=CODEX_CREDENTIAL_ENDPOINT,
    )
    _CODEX_PENDING.pop(poll_token, None)
    logger.info("Codex OAuth connected for user_id=%s account=%s", user_id, account)
    return {"status": "ok", "provider": CODEX_PROVIDER, "account": account}


# ---------------------------------------------------------------------------
# GitHub Copilot device-code flow.
# ---------------------------------------------------------------------------


@router.post("/copilot/start")
@limiter.limit("30/minute")
async def copilot_start(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Start a GitHub Copilot device-code login; frontend shows user_code + link."""
    client_id = settings.copilot_client_id or "Iv1.b507a08c87ecfe98"
    async with httpx.AsyncClient(timeout=30) as http:
        try:
            resp = await http.post(
                "https://github.com/login/device/code",
                json={"client_id": client_id, "scope": "read:user"},
                headers={"Accept": "application/json", "User-Agent": "AI-Ensemble"},
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not reach GitHub device auth: {exc}",
            )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub device auth failed ({resp.status_code}): {resp.text[:250]}",
        )
    try:
        data = resp.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub device auth returned an unexpected response",
        )
    device_code = data.get("device_code")
    user_code = data.get("user_code")
    if not device_code or not user_code:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub device auth returned an incomplete response",
        )
    verification_url = data.get("verification_uri") or "https://github.com/login/device"
    expires_in = int(data.get("expires_in") or 900)
    interval = int(data.get("interval") or 5)

    _purge_expired_pending()
    poll_token = secrets.token_urlsafe(32)
    _COPILOT_PENDING[poll_token] = {
        "device_code": device_code,
        "user_code": user_code,
        "user_id": current_user.id,
        "created_at": time.time(),
        "interval": interval,
        "last_upstream_poll": 0.0,
    }
    return {
        "verification_url": verification_url,
        "user_code": user_code,
        "poll_token": poll_token,
        "expires_in": expires_in,
        "interval": interval,
    }


async def _poll_copilot_once(
    db: Session,
    *,
    poll_token: str,
    user_id: int,
    uek: str | None,
) -> dict:
    entry = _COPILOT_PENDING.get(poll_token)
    if entry is None:
        return {"status": "error", "error": "Login session expired or not found. Please start again."}
    if entry.get("user_id") != user_id:
        return {"status": "error", "error": "Login session does not belong to this user."}
    if is_pending_expired(entry.get("created_at", 0)):
        _COPILOT_PENDING.pop(poll_token, None)
        return {"status": "error", "error": "Login session expired. Please start again."}

    now = time.time()
    interval = entry.get("interval", 5)
    last_poll = entry.get("last_upstream_poll", 0.0)
    # RFC 8628 rate-limit pacing: return pending immediately to the frontend
    # without querying GitHub upstream if called faster than interval.
    if now - last_poll < interval:
        return {"status": "pending"}

    entry["last_upstream_poll"] = now
    client_id = settings.copilot_client_id or "Iv1.b507a08c87ecfe98"
    async with httpx.AsyncClient(timeout=30) as http:
        try:
            resp = await http.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": client_id,
                    "device_code": entry["device_code"],
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json", "User-Agent": "AI-Ensemble"},
            )
        except httpx.RequestError:
            return {"status": "pending"}

    if resp.status_code >= 400:
        return {"status": "pending"}

    try:
        data = resp.json()
    except Exception:
        return {"status": "pending"}

    err = data.get("error")
    if err == "authorization_pending":
        return {"status": "pending"}
    if err == "slow_down":
        entry["interval"] = max(interval + 5, int(data.get("interval") or (interval + 5)))
        return {"status": "pending"}
    if err:
        _COPILOT_PENDING.pop(poll_token, None)
        return {"status": "error", "error": data.get("error_description") or err}

    access_token = data.get("access_token")
    if not access_token:
        return {"status": "pending"}

    account = "github-user"
    async with httpx.AsyncClient(timeout=15) as http:
        try:
            user_resp = await http.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                    "User-Agent": "AI-Ensemble",
                },
            )
            if user_resp.status_code == 200:
                user_data = user_resp.json()
                account = user_data.get("login") or user_data.get("name") or account
        except Exception:
            pass

    _store_oauth_tokens(
        db,
        user_id=user_id,
        provider=COPILOT_PROVIDER,
        access_token=access_token,
        refresh_token="",
        expires_in=None,
        account=account,
        scopes=data.get("scope", "read:user"),
        uek=uek,
        credential_endpoint=COPILOT_CREDENTIAL_ENDPOINT,
    )
    _COPILOT_PENDING.pop(poll_token, None)
    logger.info("GitHub Copilot connected for user_id=%s account=%s", user_id, account)
    return {"status": "ok", "provider": COPILOT_PROVIDER, "account": account}


# ---------------------------------------------------------------------------
# OpenRouter browser-OAuth (PKCE) flow.
# ---------------------------------------------------------------------------


def _callback_html(*, ok: bool, provider: str = OPENROUTER_PROVIDER, error: str = "") -> str:
    payload = {"provider": provider, "ok": ok}
    if error:
        payload["error"] = error
    body_msg = "Connected! You can close this window." if ok else f"Login failed: {html.escape(error)}"
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>AI-Ensemble OAuth</title></head><body>"
        f"<p>{body_msg}</p>"
        f"<script>try{{window.opener.postMessage({json.dumps(payload)},'*');}}catch(e){{}}window.close();</script>"
        "</body></html>"
    )


@router.get("/openrouter/start")
@router.post("/openrouter/start")
@limiter.limit("30/minute")
async def openrouter_start(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return the OpenRouter authorize URL (PKCE) + poll token for the browser popup."""
    _purge_expired_pending()
    code_verifier = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(hashed).decode("utf-8").rstrip("=")

    poll_token = secrets.token_urlsafe(32)
    state = secrets.token_urlsafe(32)

    callback_url = f"{settings.backend_public_url.rstrip('/')}/api/providers/oauth/openrouter/callback"
    params = {
        "callback_url": callback_url,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"https://openrouter.ai/auth?{urllib.parse.urlencode(params)}"

    _OPENROUTER_STATES[state] = {
        "user_id": current_user.id,
        "poll_token": poll_token,
        "code_verifier": code_verifier,
        "created_at": time.time(),
    }
    _OPENROUTER_PENDING[poll_token] = {
        "user_id": current_user.id,
        "state": state,
        "created_at": time.time(),
    }
    return {"auth_url": auth_url, "poll_token": poll_token}


@router.get("/openrouter/callback")
@limiter.limit("30/minute")
async def openrouter_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Handle OpenRouter OAuth callback, exchanging code for user API key."""
    if error:
        return HTMLResponse(_callback_html(ok=False, provider=OPENROUTER_PROVIDER, error=error))
    if not code:
        return HTMLResponse(_callback_html(ok=False, provider=OPENROUTER_PROVIDER, error="Missing authorization code"))

    entry = None
    if state and state in _OPENROUTER_STATES:
        entry = _OPENROUTER_STATES.pop(state)
    elif _OPENROUTER_STATES:
        newest_state = max(_OPENROUTER_STATES.keys(), key=lambda s: _OPENROUTER_STATES[s]["created_at"])
        entry = _OPENROUTER_STATES.pop(newest_state)

    if not entry or is_pending_expired(entry.get("created_at", 0)):
        return HTMLResponse(_callback_html(ok=False, provider=OPENROUTER_PROVIDER, error="Login session expired or invalid"))

    user_id = entry["user_id"]
    code_verifier = entry["code_verifier"]
    poll_token = entry["poll_token"]

    async with httpx.AsyncClient(timeout=30) as http:
        try:
            exchange = await http.post(
                "https://openrouter.ai/api/v1/auth/keys",
                json={
                    "code": code,
                    "code_verifier": code_verifier,
                    "code_challenge_method": "S256",
                },
                headers={"Content-Type": "application/json", "User-Agent": "AI-Ensemble"},
            )
        except httpx.RequestError as exc:
            return HTMLResponse(_callback_html(ok=False, provider=OPENROUTER_PROVIDER, error=f"Token exchange failed: {exc}"))

    if exchange.status_code >= 400:
        err_msg = exchange.text[:200]
        _OPENROUTER_RESULTS[poll_token] = {
            "status": "error",
            "error": f"OpenRouter exchange failed: {err_msg}",
            "user_id": user_id,
            "created_at": time.time(),
        }
        return HTMLResponse(_callback_html(ok=False, provider=OPENROUTER_PROVIDER, error=f"Exchange failed ({exchange.status_code})"))

    data = exchange.json()
    api_key = data.get("key")
    if not api_key:
        return HTMLResponse(_callback_html(ok=False, provider=OPENROUTER_PROVIDER, error="OpenRouter returned no API key"))

    account = "openrouter"
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            key_info = await http.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {api_key}", "User-Agent": "AI-Ensemble"},
            )
            if key_info.status_code == 200:
                kdata = key_info.json().get("data", {})
                account = kdata.get("label") or account
    except Exception:
        pass

    _store_oauth_tokens(
        db,
        user_id=user_id,
        provider=OPENROUTER_PROVIDER,
        access_token=api_key,
        refresh_token="",
        expires_in=None,
        account=account,
        scopes="",
        uek=None,
        credential_endpoint=OPENROUTER_CREDENTIAL_ENDPOINT,
    )
    cred = (
        db.query(ProviderCredential)
        .filter(
            ProviderCredential.user_id == user_id,
            ProviderCredential.provider == OPENROUTER_PROVIDER,
        )
        .first()
    )
    if cred:
        cred.api_key_encrypted = encrypt_secret(api_key, key=None)
        cred.endpoint = OPENROUTER_CREDENTIAL_ENDPOINT
    else:
        cred = ProviderCredential(
            user_id=user_id,
            provider=OPENROUTER_PROVIDER,
            endpoint=OPENROUTER_CREDENTIAL_ENDPOINT,
            api_key_encrypted=encrypt_secret(api_key, key=None),
        )
        db.add(cred)
    db.commit()

    _OPENROUTER_RESULTS[poll_token] = {
        "status": "ok",
        "provider": OPENROUTER_PROVIDER,
        "account": account,
        "user_id": user_id,
        "created_at": time.time(),
    }
    logger.info("OpenRouter connected for user_id=%s account=%s", user_id, account)
    return HTMLResponse(_callback_html(ok=True, provider=OPENROUTER_PROVIDER))


def _poll_openrouter(*, poll_token: str, user_id: int) -> dict:
    result = _OPENROUTER_RESULTS.get(poll_token)
    if result is not None:
        if result.get("user_id") != user_id:
            return {"status": "error", "error": "Login session does not belong to this user."}
        if is_pending_expired(result.get("created_at", 0)):
            _OPENROUTER_RESULTS.pop(poll_token, None)
            return {"status": "error", "error": "Login session expired. Please start again."}
        if result.get("status") == "ok":
            _OPENROUTER_RESULTS.pop(poll_token, None)
            return {
                "status": "ok",
                "provider": OPENROUTER_PROVIDER,
                "account": result.get("account", "openrouter"),
            }
        _OPENROUTER_RESULTS.pop(poll_token, None)
        return {"status": "error", "error": result.get("error", "Login failed.")}

    if poll_token in _OPENROUTER_PENDING:
        pending_entry = _OPENROUTER_PENDING[poll_token]
        if pending_entry.get("user_id") != user_id:
            return {"status": "error", "error": "Login session does not belong to this user."}
        if is_pending_expired(pending_entry.get("created_at", 0)):
            _OPENROUTER_PENDING.pop(poll_token, None)
            return {"status": "error", "error": "Login session expired. Please start again."}
        return {"status": "pending"}
    return {"status": "error", "error": "Login session expired or not found. Please start again."}


# ---------------------------------------------------------------------------
# Shared poll / list / delete endpoints.
# ---------------------------------------------------------------------------


@router.get("/{provider}/poll")
@limiter.limit("60/minute")
async def oauth_poll(
    request: Request,
    provider: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Poll a pending login. Codex and Copilot perform rate-paced upstream attempts."""
    uek = getattr(current_user, "uek", None)
    if provider == CODEX_PROVIDER:
        return await _poll_codex_once(db, poll_token=token, user_id=current_user.id, uek=uek)
    if provider == COPILOT_PROVIDER:
        return await _poll_copilot_once(db, poll_token=token, user_id=current_user.id, uek=uek)
    if provider == OPENROUTER_PROVIDER:
        return _poll_openrouter(poll_token=token, user_id=current_user.id)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"OAuth is not supported for provider '{provider}'",
    )


@router.get("")
@limiter.limit("60/minute")
async def list_oauth_connections(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    rows = (
        db.query(ProviderOAuthToken)
        .filter(ProviderOAuthToken.user_id == current_user.id)
        .all()
    )
    return {
        "connected": [
            {"provider": r.provider, "account": r.account or ""} for r in rows
        ]
    }


@router.delete("/{provider}")
@limiter.limit("30/minute")
async def delete_oauth_connection(
    request: Request,
    provider: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    row = (
        db.query(ProviderOAuthToken)
        .filter(
            ProviderOAuthToken.user_id == current_user.id,
            ProviderOAuthToken.provider == provider,
        )
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OAuth connection found for provider '{provider}'",
        )
    db.delete(row)
    cred = (
        db.query(ProviderCredential)
        .filter(
            ProviderCredential.user_id == current_user.id,
            ProviderCredential.provider == provider,
        )
        .first()
    )
    if cred is not None:
        db.delete(cred)
    db.commit()
    return {"status": "deleted", "provider": provider}
