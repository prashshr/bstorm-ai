from fastapi import APIRouter, Depends, HTTPException, status
import httpx
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.crypto import decrypt_secret
from app.db.session import get_db
from app.models.models import ProviderCredential, User
from app.schemas.provider_proxy import ChatRequest, ChatResponse
from app.services.providers.endpoints import normalize_endpoint
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
    endpoint = normalize_endpoint(payload.endpoint or cred.endpoint or "")
    api_key = decrypt_secret(cred.api_key_encrypted)

    try:
        output = await client.chat(
            endpoint=endpoint,
            api_key=api_key,
            model=payload.model,
            prompt=payload.prompt,
            max_tokens=payload.max_tokens,
            temperature=payload.temperature,
        )
    except httpx.HTTPStatusError as exc:
        body = exc.response.text if exc.response is not None else ""
        detail = body[:500] if body else str(exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider returned an error: {detail}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider request failed: {exc}",
        )

    return ChatResponse(provider=payload.provider, model=payload.model, output=output)
