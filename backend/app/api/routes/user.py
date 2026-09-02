import json
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.core.security import get_password_hash, verify_password
from app.core.crypto import derive_pdk, encrypt_uek, decrypt_uek
from app.db.session import get_db
from app.models.models import User, UserSetting

logger = logging.getLogger("ai_ensemble.user")

router = APIRouter()


class UserSettingsResponse(BaseModel):
    settings: Dict[str, Any]


class UserSettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any]


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.get("/settings", response_model=UserSettingsResponse)
@limiter.limit("60/minute")
def get_user_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    row = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    if not row:
        return UserSettingsResponse(settings={})
    try:
        data = json.loads(row.settings_json or "{}")
    except Exception:
        data = {}
    return UserSettingsResponse(settings=data)


@router.put("/settings", response_model=UserSettingsResponse)
@limiter.limit("30/minute")
def update_user_settings(
    request: Request,
    payload: UserSettingsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserSettingsResponse:
    row = db.query(UserSetting).filter(UserSetting.user_id == current_user.id).first()
    if not row:
        row = UserSetting(user_id=current_user.id, settings_json=json.dumps(payload.settings))
        db.add(row)
    else:
        try:
            existing = json.loads(row.settings_json or "{}")
        except Exception:
            existing = {}
        existing.update(payload.settings)
        row.settings_json = json.dumps(existing)

    db.commit()
    db.refresh(row)
    return UserSettingsResponse(settings=json.loads(row.settings_json or "{}"))


@router.post("/change-password", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long.",
        )

    # Re-encrypt UEK with new password PDK if master_key_encrypted exists
    if current_user.master_key_encrypted and current_user.encryption_salt:
        try:
            old_pdk = derive_pdk(payload.current_password, current_user.encryption_salt, iterations=600_000)
            uek = decrypt_uek(current_user.master_key_encrypted, old_pdk)
        except Exception:
            old_pdk = derive_pdk(payload.current_password, current_user.encryption_salt, iterations=100_000)
            uek = decrypt_uek(current_user.master_key_encrypted, old_pdk)

        new_pdk = derive_pdk(payload.new_password, current_user.encryption_salt, iterations=600_000)
        current_user.master_key_encrypted = encrypt_uek(uek, new_pdk)

    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    return {"ok": True, "message": "Password updated successfully."}
