from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.crypto import decrypt_secret
from app.db.session import get_db
from app.models.models import ProviderCredential, User
from app.schemas.provider_proxy import ChatRequest, ChatResponse
from app.services.providers.factory import get_provider_client


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def proxy_chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    cred = (
        db.query(ProviderCredential)
        .filter(
            ProviderCredential.user_id == current_user.id,
            ProviderCredential.provider == payload.provider,
        )
        .first()
    )
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider credential not found for user",
        )

    client = get_provider_client(payload.provider)
    endpoint = payload.endpoint or cred.endpoint or ""
    api_key = decrypt_secret(cred.api_key_encrypted)

    output = await client.chat(
        endpoint=endpoint,
        api_key=api_key,
        model=payload.model,
        prompt=payload.prompt,
        max_tokens=payload.max_tokens,
        temperature=payload.temperature,
    )

    return ChatResponse(provider=payload.provider, model=payload.model, output=output)
