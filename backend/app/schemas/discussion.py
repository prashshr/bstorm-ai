from datetime import datetime

from pydantic import BaseModel, Field


class DiscussionCreateRequest(BaseModel):
    question: str = Field(min_length=1)
    title: str = ""


class MessageCreateRequest(BaseModel):
    discussion_id: int
    round_number: int = 1
    model: str
    role: str = "assistant"
    content: str


class DiscussionResponse(BaseModel):
    id: int
    title: str
    question: str
    status: str
    created_at: datetime


class MessageResponse(BaseModel):
    id: int
    discussion_id: int
    round_number: int
    model: str
    role: str
    content: str
    created_at: datetime
