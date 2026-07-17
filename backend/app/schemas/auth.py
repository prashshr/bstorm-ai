from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str
    # If "mobile", the response also includes a refresh_token and the access
    # token carries a server session id (sid) instead of the UEK, so the UEK
    # never leaves the backend. Web clients omit this (legacy flow unchanged).
    client: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # Present only for mobile clients. Stored in OS secure storage (Keystore/
    # Keychain), never in localStorage. Absent for web clients.
    refresh_token: str | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime


class UserDeleteResponse(BaseModel):
    deleted: bool
    user_id: int
