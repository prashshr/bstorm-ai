from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AgentPersonaCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role_description: str = ""
    system_prompt: str = ""
    model: str = Field(min_length=1)
    avatar: str = "🤖"


class AgentPersonaUpdateRequest(BaseModel):
    name: Optional[str] = None
    role_description: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    avatar: Optional[str] = None


class AgentPersonaResponse(BaseModel):
    id: int
    user_id: int
    name: str
    role_description: str
    system_prompt: str
    model: str
    avatar: str
    created_at: datetime
