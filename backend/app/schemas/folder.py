from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class FolderUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    position: Optional[int] = None


class FolderResponse(BaseModel):
    id: int
    name: str
    position: int
    discussion_ids: list[int] = []
    created_at: datetime
