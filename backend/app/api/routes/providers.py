from fastapi import APIRouter, Depends, HTTPException, status
import httpx
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.crypto import encrypt_secret
from app.db.session import get_db
from app.models.models import ProviderCredential, User
from app.schemas.provider import ProviderCredentialResponse, UpsertProviderCredentialRequest
from app.services.providers.endpoints import normalize_endpoint
from app.services.providers.factory import get_provider_client


router = APIRouter()


@router.post("", response_model=ProviderCredentialResponse)
def upsert_provider_credential(
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
    encrypted = encrypt_secret(payload.api_key)
    # Normalize endpoint to canonical form so model discovery + chat work correctly
    normalized_endpoint = normalize_endpoint(payload.endpoint or "")
    if row:
        row.api_key_encrypted = encrypted
        row.endpoint = normalized_endpoint
    else:
        row = ProviderCredential(
            user_id=current_user.id,
            provider=payload.provider,
            endpoint=normalized_endpoint,
            api_key_encrypted=encrypted,
        )
        db.add(row)

    db.commit()
    return ProviderCredentialResponse(
        provider=payload.provider,
        endpoint=normalized_endpoint,
        has_key=True,
    )


@router.get("", response_model=list[ProviderCredentialResponse])
def list_provider_credentials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProviderCredentialResponse]:
    rows = db.query(ProviderCredential).filter(ProviderCredential.user_id == current_user.id).all()
    return [
        ProviderCredentialResponse(provider=r.provider, endpoint=r.endpoint or "", has_key=True)
        for r in rows
    ]


@router.get("/{provider}/models", response_model=list[str])
async def list_provider_models(
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

    api_key = decrypt_secret(row.api_key_encrypted)
    try:
        return await client.list_models(endpoint=row.endpoint or "", api_key=api_key)
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        body = exc.response.text if exc.response is not None else ""
        detail = body[:300] if body else str(exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider model discovery failed: {detail}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider model discovery request failed: {exc}",
        )
