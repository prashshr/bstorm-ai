import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
import httpx
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.crypto import decrypt_secret, decrypt_field_or_plaintext
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import Discussion, ProviderCredential, User
from app.schemas.provider_proxy import ChatRequest, ChatResponse
from app.services.providers.endpoints import normalize_endpoint
from app.services.providers.factory import get_provider_client


def _apply_vertex_config(client, credential_row, uek: str | None = None) -> None:
    """Attach stored Vertex project/region/ADC to a client instance when supported."""
    project_id = getattr(credential_row, "project_id", None)
    region = getattr(credential_row, "region", None)
    if project_id is not None:
        client.project_id = project_id
    if region is not None:
        client.region = region
    adc_encrypted = getattr(credential_row, "adc_json_encrypted", None)
    if adc_encrypted:
        try:
            client.adc_json = decrypt_secret(adc_encrypted, key=uek)
        except Exception:  # noqa: BLE001
            client.adc_json = None


router = APIRouter()


async def _resolve_credential_and_prompt(
    payload: ChatRequest,
    db: Session,
    current_user: User,
) -> tuple:
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

    prompt = payload.prompt

    if payload.include_rag_context and payload.discussion_id:
        discussion = (
            db.query(Discussion)
            .filter(
                Discussion.id == payload.discussion_id,
                Discussion.user_id == current_user.id,
            )
            .first()
        )
        if discussion and discussion.retrieved_context_encrypted:
            uek = getattr(current_user, "uek", None)
            rag_context = decrypt_field_or_plaintext(
                discussion.retrieved_context_encrypted, uek
            )
            if rag_context:
                rag_block = (
                    "=== WEB RESEARCH CONTEXT (LIVE, retrieved just now) ===\n"
                    "The content below was fetched from the internet via our real-time web "
                    "search pipeline and MUST be treated as your PRIMARY source for any current "
                    "information, prices, dates, and events.\n\n"
                    "STRICT INSTRUCTIONS — you are in MODEL/SELF retrieval mode:\n"
                    "1. You MUST use the context above as the primary basis for current facts.\n"
                    "2. If you have your OWN web search / browsing capability, you MUST also "
                    "perform a live web search to verify and supplement the provided context. "
                    "Do not skip it.\n"
                    "3. You MAY also draw on your training data where it adds value, but never "
                    "contradict the live context without citing a newer source.\n\n"
                    "RESPONSE FORMAT — Start with EXACTLY ONE LINE:\n"
                    "RAG data: [Used/Not Used] | "
                    "Self Websearch: [Used/Not Available] | "
                    "Training Data: [Used/Not Used]\n"
                    "Then proceed to answer. Keep the status line brief.\n\n"
                    f"{rag_context}\n\n"
                    "=== END WEB RESEARCH CONTEXT ===\n\n"
                    "Answer the user's question below. Start with your one-line data source "
                    "status, then answer:\n\n"
                )
                prompt = rag_block + prompt
                logger = logging.getLogger("ai_ensemble.rag")
                logger.info(
                    f"[RAG] Injected {len(rag_context)} chars of context into prompt "
                    f"for discussion {payload.discussion_id}"
                )

    endpoint = normalize_endpoint(payload.endpoint or cred.endpoint or "")
    uek = getattr(current_user, "uek", None)
    api_key = decrypt_secret(cred.api_key_encrypted, key=uek)
    return prompt, endpoint, api_key, cred


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("60/minute")
async def proxy_chat(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    prompt, endpoint, api_key, cred = await _resolve_credential_and_prompt(payload, db, current_user)

    client = get_provider_client(payload.provider)
    _apply_vertex_config(client, cred, uek=getattr(current_user, "uek", None))

    try:
        output = await client.chat(
            endpoint=endpoint,
            api_key=api_key,
            model=payload.model,
            prompt=prompt,
            max_tokens=payload.max_tokens,
            temperature=payload.temperature,
        )
    except httpx.HTTPStatusError as exc:
        body = exc.response.text if exc.response is not None else ""
        print(f"DEBUG PROXY STATUS EXCEPTION: status={exc.response.status_code}, url={exc.request.url}, body={body[:1000]}")
        detail = body[:500] if body else str(exc)
        
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


@router.post("/chat/stream")
@limiter.limit("60/minute")
async def proxy_chat_stream(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    prompt, endpoint, api_key, cred = await _resolve_credential_and_prompt(payload, db, current_user)

    client = get_provider_client(payload.provider)
    _apply_vertex_config(client, cred, uek=getattr(current_user, "uek", None))

    async def event_stream():
        full_text = ""
        try:
            async for chunk in client.chat_stream(
                endpoint=endpoint,
                api_key=api_key,
                model=payload.model,
                prompt=prompt,
                max_tokens=payload.max_tokens,
                temperature=payload.temperature,
            ):
                full_text += chunk
                event = json.dumps({"type": "delta", "content": chunk})
                yield f"data: {event}\n\n"
            event = json.dumps({"type": "done", "content": full_text})
            yield f"data: {event}\n\n"
        except httpx.HTTPStatusError as exc:
            detail = f"Provider returned error: {exc.response.status_code}"
            event = json.dumps({"type": "error", "detail": detail})
            yield f"data: {event}\n\n"
        except httpx.RequestError as exc:
            detail = f"Provider request failed: {exc}"
            event = json.dumps({"type": "error", "detail": str(detail)})
            yield f"data: {event}\n\n"
        except Exception as exc:
            detail = f"Streaming failed: {exc}"
            event = json.dumps({"type": "error", "detail": str(detail)})
            yield f"data: {event}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
