from pydantic import BaseModel, Field


class UpsertProviderCredentialRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=100)
    api_key: str = Field(min_length=1)
    endpoint: str = ""


class ProviderCredentialResponse(BaseModel):
    provider: str
    endpoint: str
    has_key: bool = True
