from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration, read from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: SecretStr
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    consultant_model: str          # customer-facing chat (Arabic / English)
    manufacturer_model: str        # Chinese manufacturer side: translation, reading replies, answers
    classifier_model: str

    database_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
