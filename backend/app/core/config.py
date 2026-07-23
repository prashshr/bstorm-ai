from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/ai_ensemble.db"
    cors_origins: list[str] = [
        "https://ai-ensemble.samkhya.cloud",
        "http://127.0.0.1:3000",
        "capacitor://localhost",
        "http://localhost",
        "https://localhost",
    ]
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    credential_encryption_key: str = "change-me-32-byte-key-change-me-32"
    tavily_api_key: str = ""
    searxng_url: str = "http://searxng-svc:8080"
    environment: str = "development"

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        if self.environment == "production":
            if self.jwt_secret == "change-me-in-production":
                raise ValueError(
                    "JWT_SECRET must be changed from its default value in production. "
                    "Set the JWT_SECRET environment variable to a strong random string."
                )
            if self.credential_encryption_key == "change-me-32-byte-key-change-me-32":
                raise ValueError(
                    "CREDENTIAL_ENCRYPTION_KEY must be changed from its default value in production. "
                    "Set the CREDENTIAL_ENCRYPTION_KEY environment variable to a 32-byte random string."
                )
        return self


settings = Settings()
