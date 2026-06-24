from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.models import Discussion, Message, SearchHistory, User
from app.schemas.discussion import (
    DiscussionCreateRequest,
    DiscussionResponse,
    MessageCreateRequest,
    MessageResponse,
)


router = APIRouter()


@router.post("", response_model=DiscussionResponse)
def create_discussion(
    payload: DiscussionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiscussionResponse:
    discussion = Discussion(
        user_id=current_user.id,
        title=payload.title,
        question=payload.question,
        status="new",
    )
    db.add(discussion)
    db.add(SearchHistory(user_id=current_user.id, query=payload.question))
    db.commit()
    db.refresh(discussion)
    return DiscussionResponse(
        id=discussion.id,
        title=discussion.title,
        question=discussion.question,
        status=discussion.status,
        created_at=discussion.created_at,
    )


@router.get("", response_model=list[DiscussionResponse])
def list_discussions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DiscussionResponse]:
    rows = (
        db.query(Discussion)
        .filter(Discussion.user_id == current_user.id)
        .order_by(Discussion.created_at.desc())
        .all()
    )
    return [
        DiscussionResponse(
            id=r.id,
            title=r.title,
            question=r.question,
            status=r.status,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/{discussion_id}/messages", response_model=list[MessageResponse])
def list_messages(
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
    return [
        MessageResponse(
            id=r.id,
            discussion_id=r.discussion_id,
            round_number=r.round_number,
            model=r.model,
            role=r.role,
            content=r.content,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/messages", response_model=MessageResponse)
def create_message(
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

    message = Message(
        discussion_id=payload.discussion_id,
        user_id=current_user.id,
        round_number=payload.round_number,
        model=payload.model,
        role=payload.role,
        content=payload.content,
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
        content=message.content,
        created_at=message.created_at,
    )
