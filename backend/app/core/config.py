from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/ai_ensemble.db"
    cors_origins: list[str] = ["https://ai-ensemble.samkhya.cloud", "http://127.0.0.1:3000"]
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    credential_encryption_key: str = "change-me-32-byte-key-change-me-32"
    tavily_api_key: str = ""
    searxng_url: str = "http://searxng-svc:8080"


settings = Settings()
