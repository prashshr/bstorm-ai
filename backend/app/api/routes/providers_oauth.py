"""OAuth device-code / browser-OAuth logins for providers without API keys.

Supported flows:

- ``codex`` — ChatGPT device-code flow against ``CODEX_ISSUER``.
- ``google-oauth`` — Google 3-legged OAuth (browser popup) for Gemini.

Tokens are encrypted with the user's UEK (same pattern as the providers.py
save path) and stored in the ``ProviderOAuthToken`` vault table. A companion
``ProviderCredential`` row (empty api_key) is upserted so the proxy and model
listing keep working through the existing credential lookup.

NOTE (multi-worker limitation): pending device-code / OAuth ``state``
records live in process-local in-memory dicts (``_CODEX_PENDING``,
``_GOOGLE_STATES``, ``_GOOGLE_RESULTS``). With more than one backend replica,
a poll/callback request may land on a different worker than the start request
and fail to find the pending record. The deployment runs a single replica
(see deploy/k8s/deployment.yaml), so this is acceptable for now; persist
pending records in the DB or Redis if replicas are ever scaled up.
"""

import base64
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
GOOGLE_OAUTH_PROVIDER = "google-oauth"

CODEX_CREDENTIAL_ENDPOINT = "https://chatgpt.com/backend-api/codex"
COPILOT_CREDENTIAL_ENDPOINT = "https://api.githubcopilot.com"
GOOGLE_OAUTH_CREDENTIAL_ENDPOINT = "https://generativelanguage.googleapis.com"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES = (
    "openid email profile "
    "https://www.googleapis.com/auth/generative-language.retriever"
)

# Process-local pending-login stores (see module docstring for the caveat).
_CODEX_PENDING: dict[str, dict] = {}
_COPILOT_PENDING: dict[str, dict] = {}
_GOOGLE_STATES: dict[str, dict] = {}
_GOOGLE_RESULTS: dict[str, dict] = {}


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


def build_google_auth_url(client_id: str, redirect_uri: str, state: str, scopes: str = GOOGLE_SCOPES) -> str:
    """Build the Google authorize URL for the browser popup."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "state": state,
        "access_type": "offline",  # needed so Google issues a refresh_token
        "prompt": "consent",
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def google_redirect_uri() -> str:
    return f"{settings.backend_public_url.rstrip('/')}/api/providers/oauth/google/callback"


def _purge_expired_pending() -> None:
    now = time.time()
    for store in (_CODEX_PENDING, _COPILOT_PENDING, _GOOGLE_RESULTS):
        for key in [k for k, v in store.items() if is_pending_expired(v.get("created_at", 0), now)]:
            store.pop(key, None)
    for key in [k for k, v in _GOOGLE_STATES.items() if is_pending_expired(v.get("created_at", 0), now)]:
        _GOOGLE_STATES.pop(key, None)


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

    _purge_expired_pending()
    poll_token = secrets.token_urlsafe(32)
    _COPILOT_PENDING[poll_token] = {
        "device_code": device_code,
        "user_code": user_code,
        "user_id": current_user.id,
        "created_at": time.time(),
    }
    return {
        "verification_url": verification_url,
        "user_code": user_code,
        "poll_token": poll_token,
        "expires_in": expires_in,
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

    client_id = settings.copilot_client_id or "Iv1.b507a08c87ecfe98"
    async with httpx.AsyncClient(timeout=30) as http:
        try:
            resp = await http.post(
                "https://github.com/login/oauth/access_token",
                json={
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
    if err in ("authorization_pending", "slow_down"):
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
# Google browser-OAuth flow.
# ---------------------------------------------------------------------------


@router.get("/google/start")
@limiter.limit("30/minute")
async def google_start(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return the Google authorize URL + poll token for the browser popup."""
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured on this server "
            "(missing GOOGLE_OAUTH_CLIENT_ID/GOOGLE_OAUTH_CLIENT_SECRET).",
        )
    _purge_expired_pending()
    poll_token = secrets.token_urlsafe(32)
    state = secrets.token_urlsafe(32)
    _GOOGLE_STATES[state] = {
        "user_id": current_user.id,
        "poll_token": poll_token,
        "created_at": time.time(),
    }
    auth_url = build_google_auth_url(
        settings.google_oauth_client_id, google_redirect_uri(), state
    )
    return {"auth_url": auth_url, "poll_token": poll_token}


def _callback_html(*, ok: bool, provider: str = GOOGLE_OAUTH_PROVIDER, error: str = "") -> str:
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


@router.get("/google/callback")
@limiter.limit("30/minute")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """OAuth redirect target (no auth cookie — the ``state`` binds the user)."""
    if error:
        if state and state in _GOOGLE_STATES:
            entry = _GOOGLE_STATES.pop(state)
            _GOOGLE_RESULTS[entry["poll_token"]] = {
                "status": "error",
                "error": f"Google login failed: {error}",
                "user_id": entry["user_id"],
                "created_at": time.time(),
            }
        return HTMLResponse(_callback_html(ok=False, error=error))
    if not code or not state:
        return HTMLResponse(_callback_html(ok=False, error="Missing code/state"))
    entry = _GOOGLE_STATES.get(state)
    if entry is None:
        return HTMLResponse(_callback_html(ok=False, error="Invalid or expired login session"))
    if is_pending_expired(entry.get("created_at", 0)):
        _GOOGLE_STATES.pop(state, None)
        return HTMLResponse(_callback_html(ok=False, error="Login session expired"))

    async with httpx.AsyncClient(timeout=30) as http:
        try:
            exchange = await http.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_oauth_client_id,
                    "client_secret": settings.google_oauth_client_secret,
                    "redirect_uri": google_redirect_uri(),
                    "grant_type": "authorization_code",
                },
            )
        except httpx.RequestError as exc:
            return HTMLResponse(_callback_html(ok=False, error=f"Token exchange failed: {exc}"))
    if exchange.status_code >= 400:
        _GOOGLE_STATES.pop(state, None)
        _GOOGLE_RESULTS[entry["poll_token"]] = {
            "status": "error",
            "error": "Google token exchange failed. Please try again.",
            "user_id": entry["user_id"],
            "created_at": time.time(),
        }
        return HTMLResponse(_callback_html(ok=False, error="Google token exchange failed"))

    tokens = exchange.json()
    access_token = tokens.get("access_token")
    if not access_token:
        _GOOGLE_STATES.pop(state, None)
        return HTMLResponse(_callback_html(ok=False, error="Google returned no access token"))

    email = ""
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            userinfo = await http.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if userinfo.status_code == 200:
            email = str(userinfo.json().get("email") or "")
    except httpx.RequestError:
        pass
    if not email and tokens.get("id_token"):
        email = str(decode_jwt_no_verify(tokens["id_token"]).get("email") or "")

    # No auth context here (browser redirect), so UEK is unavailable and
    # encryption falls back to the server key — decrypt_secret() resolves
    # that transparently on later reads.
    _store_oauth_tokens(
        db,
        user_id=entry["user_id"],
        provider=GOOGLE_OAUTH_PROVIDER,
        access_token=access_token,
        refresh_token=tokens.get("refresh_token") or "",
        expires_in=tokens.get("expires_in"),
        account=email,
        scopes=GOOGLE_SCOPES,
        uek=None,
        credential_endpoint=GOOGLE_OAUTH_CREDENTIAL_ENDPOINT,
    )
    _GOOGLE_STATES.pop(state, None)
    _GOOGLE_RESULTS[entry["poll_token"]] = {
        "status": "ok",
        "provider": GOOGLE_OAUTH_PROVIDER,
        "account": email,
        "user_id": entry["user_id"],
        "created_at": time.time(),
    }
    logger.info("Google OAuth connected for user_id=%s account=%s", entry["user_id"], email)
    return HTMLResponse(_callback_html(ok=True))


def _poll_google(*, poll_token: str, user_id: int) -> dict:
    result = _GOOGLE_RESULTS.get(poll_token)
    if result is not None:
        if result.get("user_id") != user_id:
            return {"status": "error", "error": "Login session does not belong to this user."}
        if is_pending_expired(result.get("created_at", 0)):
            _GOOGLE_RESULTS.pop(poll_token, None)
            return {"status": "error", "error": "Login session expired. Please start again."}
        if result.get("status") == "ok":
            _GOOGLE_RESULTS.pop(poll_token, None)
            return {
                "status": "ok",
                "provider": result.get("provider", GOOGLE_OAUTH_PROVIDER),
                "account": result.get("account", ""),
            }
        _GOOGLE_RESULTS.pop(poll_token, None)
        return {"status": "error", "error": result.get("error", "Login failed.")}
    # Still waiting in the browser popup?
    for state_entry in _GOOGLE_STATES.values():
        if state_entry.get("poll_token") == poll_token:
            if state_entry.get("user_id") != user_id:
                return {"status": "error", "error": "Login session does not belong to this user."}
            if is_pending_expired(state_entry.get("created_at", 0)):
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
    """Poll a pending login. Codex performs ONE upstream attempt per call."""
    uek = getattr(current_user, "uek", None)
    if provider == CODEX_PROVIDER:
        return await _poll_codex_once(db, poll_token=token, user_id=current_user.id, uek=uek)
    if provider == COPILOT_PROVIDER:
        return await _poll_copilot_once(db, poll_token=token, user_id=current_user.id, uek=uek)
    if provider == GOOGLE_OAUTH_PROVIDER:
        return _poll_google(poll_token=token, user_id=current_user.id)
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
