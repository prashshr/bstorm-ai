from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    provider: str = Field(min_length=2)
    model: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    endpoint: str = ""
    max_tokens: int = 1000
    temperature: float = 0.7


class ChatResponse(BaseModel):
    provider: str
    model: str
    output: str
