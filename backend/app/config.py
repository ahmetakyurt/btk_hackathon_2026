from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")
    gemini_timeout_seconds: int = Field(default=15, alias="GEMINI_TIMEOUT_SECONDS")

    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./optiprice.db", alias="DATABASE_URL"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    mock_trendyol_url: str = Field(default="http://localhost:9001", alias="MOCK_TRENDYOL_URL")
    mock_amazon_url: str = Field(default="http://localhost:9002", alias="MOCK_AMAZON_URL")
    mock_own_site_url: str = Field(default="http://localhost:9003", alias="MOCK_OWN_SITE_URL")

    competitor_poll_interval_seconds: int = Field(
        default=5, alias="COMPETITOR_POLL_INTERVAL_SECONDS"
    )
    pricing_agent_min_margin: float = Field(default=0.05, alias="PRICING_AGENT_MIN_MARGIN")


@lru_cache
def get_settings() -> Settings:
    return Settings()
