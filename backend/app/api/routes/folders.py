from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.folder import Folder
from app.models.models import Discussion, User
from app.schemas.folder import (
    FolderCreateRequest,
    FolderResponse,
    FolderUpdateRequest,
)


router = APIRouter()


def _serialize(folder: Folder) -> FolderResponse:
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        position=folder.position,
        discussion_ids=[d.id for d in folder.discussions],
        created_at=folder.created_at,
    )


def _get_owned(db: Session, folder_id: int, user: User) -> Folder:
    folder = (
        db.query(Folder)
        .filter(Folder.id == folder_id, Folder.user_id == user.id)
        .first()
    )
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


@router.get("", response_model=list[FolderResponse])
@limiter.limit("60/minute")
def list_folders(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FolderResponse]:
    rows = (
        db.query(Folder)
        .filter(Folder.user_id == current_user.id)
        .order_by(Folder.position.asc(), Folder.created_at.asc())
        .all()
    )
    return [_serialize(r) for r in rows]


@router.post("", response_model=FolderResponse, status_code=201)
@limiter.limit("30/minute")
def create_folder(
    request: Request,
    payload: FolderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FolderResponse:
    max_pos = db.query(Folder).filter(Folder.user_id == current_user.id).count()
    folder = Folder(
        user_id=current_user.id,
        name=payload.name,
        position=max_pos,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return _serialize(folder)


@router.put("/{folder_id}", response_model=FolderResponse)
@limiter.limit("60/minute")
def update_folder(
    request: Request,
    folder_id: int,
    payload: FolderUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FolderResponse:
    folder = _get_owned(db, folder_id, current_user)
    if payload.name is not None:
        folder.name = payload.name
    if payload.position is not None:
        folder.position = payload.position
    db.commit()
    db.refresh(folder)
    return _serialize(folder)


@router.delete("/{folder_id}")
@limiter.limit("30/minute")
def delete_folder(
    request: Request,
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = _get_owned(db, folder_id, current_user)
    db.delete(folder)
    db.commit()
    return {"deleted": True, "folder_id": folder_id}


@router.post("/{folder_id}/discussions/{discussion_id}", response_model=FolderResponse)
@limiter.limit("60/minute")
def add_discussion(
    request: Request,
    folder_id: int,
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FolderResponse:
    folder = _get_owned(db, folder_id, current_user)
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == discussion_id, Discussion.user_id == current_user.id)
        .first()
    )
    if not discussion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found")
    if discussion not in folder.discussions:
        folder.discussions.append(discussion)
    db.commit()
    db.refresh(folder)
    return _serialize(folder)


@router.delete("/{folder_id}/discussions/{discussion_id}", response_model=FolderResponse)
@limiter.limit("60/minute")
def remove_discussion(
    request: Request,
    folder_id: int,
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FolderResponse:
    folder = _get_owned(db, folder_id, current_user)
    discussion = (
        db.query(Discussion)
        .filter(Discussion.id == discussion_id, Discussion.user_id == current_user.id)
        .first()
    )
    if not discussion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found")
    if discussion in folder.discussions:
        folder.discussions.remove(discussion)
    db.commit()
    db.refresh(folder)
    return _serialize(folder)
