from fastapi import APIRouter, Depends, HTTPException, Request, status
import httpx
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.crypto import decrypt_secret
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import ProviderCredential, User
from app.schemas.provider_proxy import ChatRequest, ChatResponse
from app.services.providers.endpoints import normalize_endpoint
from app.services.providers.factory import get_provider_client


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("60/minute")
async def proxy_chat(
    request: Request,
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
    api_key = decrypt_secret(cred.api_key_encrypted, key=getattr(current_user, "uek", None))

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
        print(f"DEBUG PROXY STATUS EXCEPTION: status={exc.response.status_code}, url={exc.request.url}, body={body[:1000]}")
        detail = body[:500] if body else str(exc)
        
        # Provide more specific error messages based on status code
        if exc.response.status_code == 401:
            detail = f"Authentication failed (401): Invalid API key for {endpoint or payload.provider}"
        elif exc.response.status_code == 404:
            detail = f"Endpoint not found (404): {endpoint or payload.provider} - Check your endpoint URL"
        elif exc.response.status_code == 502:
            detail = f"Bad Gateway (502): Could not reach the provider at {endpoint or payload.provider} - Check your endpoint URL and connectivity"
        elif exc.response.status_code == 429:
            detail = f"Rate limited (429): Too many requests to {payload.provider}"
        
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Provider returned an error: {detail}",
        )
    except httpx.RequestError as exc:
        # Handle other request errors like connection timeouts
        detail = str(exc)
        if "502" in detail or "Bad Gateway" in detail:
            detail = f"Could not reach the provider - Check your endpoint URL and connectivity"
        elif "401" in detail or "Authentication" in detail.lower():
            detail = f"Authentication failed: Invalid API key"
        elif "404" in detail:
            detail = f"Endpoint not found - Check your endpoint URL"
        elif "timeout" in detail.lower():
            detail = f"Request timed out - The provider took too long to respond"
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Provider request failed: {detail}",
        )

    return ChatResponse(provider=payload.provider, model=payload.model, output=output)
