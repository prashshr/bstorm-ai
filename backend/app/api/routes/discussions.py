from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

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


router = APIRouter()


@router.post("", response_model=DiscussionResponse)
@limiter.limit("30/minute")
def create_discussion(
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

    encrypted_title = encrypt_field(payload.title, uek)
    encrypted_question = encrypt_field(payload.question, uek)

    discussion = Discussion(
        user_id=current_user.id,
        title=encrypted_title,
        question=encrypted_question,
        status="new",
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
    return DiscussionResponse(
        id=discussion.id,
        title=decrypt_field_or_plaintext(discussion.title, uek),
        question=decrypt_field_or_plaintext(discussion.question, uek),
        status=discussion.status,
        state_json=decrypt_field_or_plaintext(discussion.state_json, uek),
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
    return DiscussionResponse(
        id=discussion.id,
        title=decrypt_field_or_plaintext(discussion.title, uek),
        question=decrypt_field_or_plaintext(discussion.question, uek),
        status=discussion.status,
        state_json=decrypt_field_or_plaintext(discussion.state_json, uek),
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
