from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DiscussionCreateRequest(BaseModel):
    question: str = Field(min_length=1)
    title: str = ""
    use_rag: bool = False
    rag_mode: Optional[str] = "model-self"
    deep_research: bool = False


class DiscussionUpdateRequest(BaseModel):
    status: Optional[str] = None
    state_json: Optional[str] = None
    title: Optional[str] = None


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
    use_rag: bool = False
    deep_research: bool = False
    state_json: str = ""
    retrieved_context: Optional[str] = None
    created_at: datetime


class MessageResponse(BaseModel):
    id: int
    discussion_id: int
    round_number: int
    model: str
    role: str
    content: str
    created_at: datetime


class TriageDocumentRequest(BaseModel):
    filename: str
    content: str
    query: str = ""
    max_chars_budget: int = 16000


class TriageDocumentResponse(BaseModel):
    filename: str
    triaged_content: str
    is_triaged: bool
    original_length: int
    triaged_length: int
    has_prompt_injection: bool = False
    safety_advisory: Optional[str] = None


class DeliberationTopologyRequest(BaseModel):
    question: str
    model_responses: dict[str, str]


class DeliberationTopologyResponse(BaseModel):
    model_count: int
    consensus_score: float
    consensus_percent: int
    has_disagreement: bool
    primary_divergence: str
    dissenting_model: Optional[str] = None
    should_deliberate_round_2: bool
    deliberation_directive: Optional[str] = None
    summary_badge: str
    rationale: str
