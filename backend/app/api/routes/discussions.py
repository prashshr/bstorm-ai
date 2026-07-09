import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import Discussion, Message, SearchHistory, User
from app.schemas.discussion import (
    DiscussionCreateRequest,
    DiscussionResponse,
    DiscussionUpdateRequest,
    MessageCreateRequest,
    MessageResponse,
)
from app.core.crypto import encrypt_field, decrypt_field_or_plaintext
from app.services.retrieval import get_retrieved_context


router = APIRouter()


def _parse_state_flags(state_json: str) -> tuple:
    try:
        state = json.loads(state_json) if state_json else {}
    except (json.JSONDecodeError, TypeError):
        state = {}
    return (
        state.get("use_rag", False),
        state.get("deep_research", False),
    )


@router.post("", response_model=DiscussionResponse)
@limiter.limit("30/minute")
async def create_discussion(
    request: Request,
    payload: DiscussionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiscussionResponse:
    uek = getattr(current_user, "uek", None)
    if not uek:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User Encryption Key (UEK) is missing. Cannot create discussion."
        )

    retrieved_context = None
    if payload.use_rag:
        try:
            retrieved_context = await get_retrieved_context(payload.question)
        except Exception as e:
            print(f"Failed to get retrieved context: {e}")

    encrypted_title = encrypt_field(payload.title, uek)
    encrypted_question = encrypt_field(payload.question, uek)
    encrypted_context = encrypt_field(retrieved_context, uek) if retrieved_context else None

    discussion = Discussion(
        user_id=current_user.id,
        title=encrypted_title,
        question=encrypted_question,
        status="new",
        retrieved_context_encrypted=encrypted_context,
    )
    db.add(discussion)
    db.add(SearchHistory(user_id=current_user.id, query=encrypted_question))
    db.commit()
    db.refresh(discussion)
    return DiscussionResponse(
        id=discussion.id,
        title=payload.title,
        question=payload.question,
        status=discussion.status,
        use_rag=payload.use_rag,
        deep_research=payload.deep_research,
        retrieved_context=retrieved_context,
        created_at=discussion.created_at,
    )


@router.put("/{discussion_id}", response_model=DiscussionResponse)
@limiter.limit("60/minute")
def update_discussion(
    request: Request,
    discussion_id: int,
    payload: DiscussionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiscussionResponse:
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == discussion_id, Discussion.user_id == current_user.id)
        .first()
    )
    if not discussion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found")

    uek = getattr(current_user, "uek", None)
    if not uek:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User Encryption Key (UEK) is missing. Cannot update discussion."
        )

    if payload.status is not None:
        discussion.status = payload.status
    if payload.state_json is not None:
        discussion.state_json = encrypt_field(payload.state_json, uek)
    if payload.title is not None:
        discussion.title = encrypt_field(payload.title, uek)

    db.commit()
    db.refresh(discussion)
    state_decrypted = decrypt_field_or_plaintext(discussion.state_json, uek)
    flags = _parse_state_flags(state_decrypted) if discussion.state_json else (False, False)
    return DiscussionResponse(
        id=discussion.id,
        title=decrypt_field_or_plaintext(discussion.title, uek),
        question=decrypt_field_or_plaintext(discussion.question, uek),
        status=discussion.status,
        state_json=state_decrypted,
        use_rag=flags[0],
        deep_research=flags[1],
        retrieved_context=decrypt_field_or_plaintext(discussion.retrieved_context_encrypted, uek) if discussion.retrieved_context_encrypted else None,
        created_at=discussion.created_at,
    )


@router.get("", response_model=list[DiscussionResponse])
@limiter.limit("60/minute")
def list_discussions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DiscussionResponse]:
    rows = (
        db.query(Discussion)
        .filter(Discussion.user_id == current_user.id)
        .order_by(Discussion.created_at.desc())
        .all()
    )
    uek = getattr(current_user, "uek", None)
    return [
        DiscussionResponse(
            id=r.id,
            title=decrypt_field_or_plaintext(r.title, uek),
            question=decrypt_field_or_plaintext(r.question, uek),
            status=r.status,
            state_json=decrypt_field_or_plaintext(r.state_json, uek),
            retrieved_context=decrypt_field_or_plaintext(r.retrieved_context_encrypted, uek) if r.retrieved_context_encrypted else None,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/{discussion_id}", response_model=DiscussionResponse)
@limiter.limit("60/minute")
def get_discussion(
    request: Request,
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiscussionResponse:
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == discussion_id, Discussion.user_id == current_user.id)
        .first()
    )
    if not discussion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found")
    uek = getattr(current_user, "uek", None)
    state_decrypted = decrypt_field_or_plaintext(discussion.state_json, uek)
    flags = _parse_state_flags(state_decrypted) if discussion.state_json else (False, False)
    return DiscussionResponse(
        id=discussion.id,
        title=decrypt_field_or_plaintext(discussion.title, uek),
        question=decrypt_field_or_plaintext(discussion.question, uek),
        status=discussion.status,
        state_json=state_decrypted,
        use_rag=flags[0],
        deep_research=flags[1],
        retrieved_context=decrypt_field_or_plaintext(discussion.retrieved_context_encrypted, uek) if discussion.retrieved_context_encrypted else None,
        created_at=discussion.created_at,
    )


@router.delete("/{discussion_id}")
@limiter.limit("30/minute")
def delete_discussion(
    request: Request,
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == discussion_id, Discussion.user_id == current_user.id)
        .first()
    )
    if not discussion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found")

    db.delete(discussion)
    db.commit()
    return {"deleted": True, "discussion_id": discussion_id}


@router.get("/{discussion_id}/messages", response_model=list[MessageResponse])
@limiter.limit("60/minute")
def list_messages(
    request: Request,
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageResponse]:
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == discussion_id, Discussion.user_id == current_user.id)
        .first()
    )
    if not discussion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found")

    rows = (
        db.query(Message)
        .filter(Message.discussion_id == discussion_id, Message.user_id == current_user.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    uek = getattr(current_user, "uek", None)
    return [
        MessageResponse(
            id=r.id,
            discussion_id=r.discussion_id,
            round_number=r.round_number,
            model=r.model,
            role=r.role,
            content=decrypt_field_or_plaintext(r.content, uek),
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/messages", response_model=MessageResponse)
@limiter.limit("120/minute")
def create_message(
    request: Request,
    payload: MessageCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == payload.discussion_id, Discussion.user_id == current_user.id)
        .first()
    )
    if not discussion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found")

    uek = getattr(current_user, "uek", None)
    if not uek:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User Encryption Key (UEK) is missing. Cannot create message."
        )

    message = Message(
        discussion_id=payload.discussion_id,
        user_id=current_user.id,
        round_number=payload.round_number,
        model=payload.model,
        role=payload.role,
        content=encrypt_field(payload.content, uek),
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return MessageResponse(
        id=message.id,
        discussion_id=message.discussion_id,
        round_number=message.round_number,
        model=message.model,
        role=message.role,
        content=payload.content,
        created_at=message.created_at,
    )


@router.post("/{discussion_id}/research", response_model=DiscussionResponse)
@limiter.limit("30/minute")
async def research_next_round(
    request: Request,
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiscussionResponse:
    """Performs a new RAG search based on the last round of messages."""
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == discussion_id, Discussion.user_id == current_user.id)
        .first()
    )
    if not discussion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found")

    uek = getattr(current_user, "uek", None)
    if not uek:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User Encryption Key (UEK) is missing. Cannot perform research."
        )

    # Find the last round number
    last_round_number = db.query(func.max(Message.round_number)).filter(Message.discussion_id == discussion_id).scalar() or 0

    if last_round_number == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot perform research on a discussion with no messages."
        )

    # Get all messages from the last round
    messages = (
        db.query(Message)
        .filter(
            Message.discussion_id == discussion_id,
            Message.round_number == last_round_number,
        )
        .all()
    )

    # Synthesize a new query from the last round's messages
    synthesis_prompt = "Based on the following discussion, what is the main follow-up question?\n\n"
    for msg in messages:
        synthesis_prompt += f"{decrypt_field_or_plaintext(msg.content, uek)}\n"

    # Perform new RAG search
    retrieved_context = await get_retrieved_context(synthesis_prompt)

    # Update the discussion with the new context
    discussion.retrieved_context_encrypted = encrypt_field(retrieved_context, uek) if retrieved_context else None
    db.commit()
    db.refresh(discussion)

    state_decrypted = decrypt_field_or_plaintext(discussion.state_json, uek)
    flags = _parse_state_flags(state_decrypted) if discussion.state_json else (False, False)
    return DiscussionResponse(
        id=discussion.id,
        title=decrypt_field_or_plaintext(discussion.title, uek),
        question=decrypt_field_or_plaintext(discussion.question, uek),
        status=discussion.status,
        state_json=state_decrypted,
        use_rag=flags[0],
        deep_research=flags[1],
        retrieved_context=retrieved_context,
        created_at=discussion.created_at,
    )
