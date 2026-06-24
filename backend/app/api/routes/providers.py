from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.crypto import encrypt_secret
from app.db.session import get_db
from app.models.models import ProviderCredential, User
from app.schemas.provider import ProviderCredentialResponse, UpsertProviderCredentialRequest


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
    if row:
        row.api_key_encrypted = encrypted
        row.endpoint = payload.endpoint
    else:
        row = ProviderCredential(
            user_id=current_user.id,
            provider=payload.provider,
            endpoint=payload.endpoint,
            api_key_encrypted=encrypted,
        )
        db.add(row)

    db.commit()
    return ProviderCredentialResponse(provider=payload.provider, endpoint=payload.endpoint, has_key=True)


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
