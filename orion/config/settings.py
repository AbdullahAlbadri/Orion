from functools import lru_cache
from typing import Annotated, Optional

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration, read from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: SecretStr
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    consultant_model: str          # customer-facing chat (Arabic / English)
    manufacturer_model: str        # Chinese manufacturer side: translation, reading replies, answers
    classifier_model: str

    database_url: str

    # API and login
    jwt_secret: SecretStr = SecretStr("")             # signs access tokens; required to run the API
    login_code_secret: SecretStr = SecretStr("")      # peppers the hashes of one-time login codes
    app_base_url: str = "http://localhost:3000"       # customer website, used in login links
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    cookie_secure: bool = True                        # refresh-token cookie only over HTTPS (localhost is fine)
    email_from: str = "Orion <login@orionagentic.online>"
    google_client_id: Optional[str] = None            # Google sign-in is off until this is set
    apple_client_id: Optional[str] = None             # Apple sign-in is off until this is set

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value):
        # CORS_ORIGINS=https://a.example,https://b.example
        return [v.strip() for v in value.split(",") if v.strip()] if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
