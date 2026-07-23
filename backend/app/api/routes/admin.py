from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import User
from app.schemas.auth import UserDeleteResponse, UserResponse


router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
@limiter.limit("30/minute")
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserResponse]:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can manage users",
        )
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.delete("/users/{user_id}", response_model=UserDeleteResponse)
@limiter.limit("30/minute")
def delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserDeleteResponse:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin can manage users",
        )

    # Prevent admin from deleting themselves
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own admin account",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.delete(user)
    db.commit()
    return UserDeleteResponse(deleted=True, user_id=user_id)