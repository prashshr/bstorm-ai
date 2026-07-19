from typing import List, Optional

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    """A user-supplied file attached to a message.

    `content` is the raw payload:
    - images: base64-encoded bytes (no data: prefix) so providers can embed
      them as multimodal content blocks.
    - text-like files: the decoded text content.
    """

    name: str
    type: str = "application/octet-stream"
    content: str


class ChatRequest(BaseModel):
    provider: str = Field(min_length=2)
    model: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    endpoint: str = ""
    max_tokens: int = 1000
    temperature: float = 0.7
    discussion_id: Optional[int] = None
    include_rag_context: bool = False
    attachments: List[Attachment] = Field(default_factory=list)


class ChatResponse(BaseModel):
    provider: str
    model: str
    output: str
