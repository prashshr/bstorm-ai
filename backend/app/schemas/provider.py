from pydantic import BaseModel, Field


class UpsertProviderCredentialRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=100)
    # API key is optional: providers like Google Vertex use Application Default
    # Credentials (ADC) instead of a static key.
    api_key: str = ""
    endpoint: str = ""
    label: str = ""
    project_id: str = ""
    region: str = ""
    # Raw Application Default Credentials JSON (service-account key or gcloud
    # user-ADC file). Stored encrypted per user. Optional — if omitted the
    # backend falls back to environment-level ADC (GOOGLE_APPLICATION_CREDENTIALS).
    adc_json: str = ""


class ProviderCredentialResponse(BaseModel):
    provider: str
    label: str = ""
    endpoint: str
    has_key: bool = True
    project_id: str = ""
    region: str = ""
    has_adc: bool = False
