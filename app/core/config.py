from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Creative Director Engine"
    app_version: str = "0.1.0"
    environment: str = "development"

    output_root: Path = Field(default=Path("output"))

    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-8b-instant"
    groq_fallback_models: str = ""
    groq_timeout_seconds: float = 90.0
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_max_retries: int = 2
    groq_retry_base_delay_seconds: float = 1.5
    groq_temperature: float = 0.2

    nanobanana_api_key: str | None = None
    nanobanana_base_url: str = "https://www.nananobanana.com/api/v1"
    nanobanana_default_model: str = "nano-banana"
    nanobanana_image_size: str = "1k"
    nanobanana_timeout_seconds: float = 120.0
    nanobanana_preferred_api_version: str = "v2"
    nanobanana_poll_attempts: int = 8
    nanobanana_poll_interval_seconds: float = 4.0

    storage_backend: str = "local"
    s3_bucket_name: str | None = None
    s3_region: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
