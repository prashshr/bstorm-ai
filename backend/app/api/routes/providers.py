from fastapi import APIRouter, Depends, HTTPException, Request, status
import httpx
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.crypto import encrypt_secret
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import ProviderCredential, User
from app.schemas.provider import ProviderCredentialResponse, UpsertProviderCredentialRequest
from app.services.providers.endpoints import normalize_endpoint
from app.services.providers.factory import get_provider_client


def _apply_provider_config(client, credential_row) -> None:
    """Attach stored provider-specific config (project id, region) to a client
    instance when the client supports it. Vertex uses these for ADC auth."""
    project_id = getattr(credential_row, "project_id", None)
    region = getattr(credential_row, "region", None)
    if project_id is not None:
        client.project_id = project_id
    if region is not None:
        client.region = region


router = APIRouter()


@router.post("", response_model=ProviderCredentialResponse)
@limiter.limit("30/minute")
def upsert_provider_credential(
    request: Request,
    payload: UpsertProviderCredentialRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProviderCredentialResponse:
    row = (
        db.query(ProviderCredential)
        .filter(
            ProviderCredential.user_id == current_user.id,
            ProviderCredential.provider == payload.provider,
        )
        .first()
    )
    encrypted = encrypt_secret(payload.api_key, key=getattr(current_user, "uek", None))
    adc_encrypted = encrypt_secret(payload.adc_json, key=getattr(current_user, "uek", None)) if payload.adc_json else None
    # Normalize endpoint to canonical form so model discovery + chat work correctly
    normalized_endpoint = normalize_endpoint(payload.endpoint or "")
    if row:
        row.api_key_encrypted = encrypted
        row.endpoint = normalized_endpoint
        row.project_id = payload.project_id or None
        row.region = payload.region or None
        row.adc_json_encrypted = adc_encrypted
    else:
        row = ProviderCredential(
            user_id=current_user.id,
            provider=payload.provider,
            endpoint=normalized_endpoint,
            api_key_encrypted=encrypted,
            project_id=payload.project_id or None,
            region=payload.region or None,
            adc_json_encrypted=adc_encrypted,
        )
        db.add(row)

    db.commit()
    return ProviderCredentialResponse(
        provider=payload.provider,
        endpoint=normalized_endpoint,
        has_key=bool(payload.api_key),
        project_id=payload.project_id or "",
        region=payload.region or "",
        has_adc=bool(payload.adc_json),
    )


@router.get("", response_model=list[ProviderCredentialResponse])
@limiter.limit("60/minute")
def list_provider_credentials(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProviderCredentialResponse]:
    rows = db.query(ProviderCredential).filter(ProviderCredential.user_id == current_user.id).all()
    return [
        ProviderCredentialResponse(
            provider=r.provider,
            endpoint=r.endpoint or "",
            has_key=bool(r.api_key_encrypted),
            project_id=r.project_id or "",
            region=r.region or "",
            has_adc=bool(r.adc_json_encrypted),
        )
        for r in rows
    ]


@router.get("/{provider}/models", response_model=list[str])
@limiter.limit("30/minute")
async def list_provider_models(
    request: Request,
    provider: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[str]:
    row = (
        db.query(ProviderCredential)
        .filter(
            ProviderCredential.user_id == current_user.id,
            ProviderCredential.provider == provider,
        )
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider credential not found for user",
        )

    client = get_provider_client(provider)
    from app.core.crypto import decrypt_secret

    api_key = decrypt_secret(row.api_key_encrypted, key=getattr(current_user, "uek", None))
    # Pass provider-specific config (e.g. Vertex project/region) to the client.
    _apply_provider_config(client, row)
    try:
        return await client.list_models(endpoint=row.endpoint or "", api_key=api_key)
    except HTTPException:
        raise
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider model discovery request failed: Could not reach {row.endpoint or provider} — {exc}",
        )
    except httpx.HTTPStatusError as exc:
        body = exc.response.text if exc.response is not None else ""
        detail = exc.response.reason_phrase or "Provider returned an error"
        status_code = exc.response.status_code if exc.response else 502

        if status_code == 401:
            detail = f"Authentication failed (401): Invalid API key for {row.endpoint or provider}"
        elif status_code == 404:
            detail = f"Model discovery not supported (404): {row.endpoint or provider}"
        elif status_code == 429:
            detail = f"Rate limited (429): Too many requests to {provider} — try again later"
        elif status_code == 502:
            detail = f"Bad Gateway (502): Could not reach {row.endpoint or provider}"

        raise HTTPException(
            status_code=status_code,
            detail=f"Provider model discovery failed: {detail}",
        )
    except Exception as exc:
        detail = str(exc)
        if "429" in detail:
            raise HTTPException(
                status_code=429,
                detail=f"Provider model discovery failed: Rate limited (429): Too many requests to {provider}",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider model discovery failed: {detail}",
        )


@router.delete("/{provider}", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
def delete_provider_credential(
    request: Request,
    provider: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    row = (
        db.query(ProviderCredential)
        .filter(
            ProviderCredential.user_id == current_user.id,
            ProviderCredential.provider == provider,
        )
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider credential not found for user",
        )
    db.delete(row)
    db.commit()
    return {"status": "deleted", "provider": provider}


@router.post("/{provider}/test", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def test_provider_connection(
    request: Request,
    provider: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Test a provider connection by calling the chat endpoint with a minimal prompt."""
    row = (
        db.query(ProviderCredential)
        .filter(
            ProviderCredential.user_id == current_user.id,
            ProviderCredential.provider == provider,
        )
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider credential not found for user",
        )

    from app.core.crypto import decrypt_secret
    api_key = decrypt_secret(row.api_key_encrypted, key=getattr(current_user, "uek", None))
    client = get_provider_client(provider)

    try:
        result = await client.chat(
            endpoint=row.endpoint or "",
            api_key=api_key,
            model="gpt-4o-mini",  # generic model name that most providers accept for testing
            prompt="Respond with just the word: connected",
            max_tokens=16,
            temperature=0,
        )
        if result.strip():
            return {"status": "connected", "message": "Connection successful! Provider is reachable."}
        return {"status": "connected", "message": "Connection successful (empty response)."}
    except Exception as exc:
        detail = str(exc)
        if "401" in detail or "Authentication" in detail or "Invalid API key" in detail:
            return {"status": "auth_failed", "message": "Authentication failed: Invalid API key"}
        if "429" in detail or "Rate limit" in detail:
            return {"status": "rate_limited", "message": "Rate limited by provider. Try again later."}
        if "502" in detail or "Bad Gateway" in detail or "Could not reach" in detail:
            return {"status": "connection_error", "message": "Could not reach provider endpoint"}
        if "404" in detail:
            return {"status": "connection_error", "message": "Endpoint not found. Check your endpoint URL."}
        return {"status": "connection_error", "message": f"Connection failed: {detail}"}
