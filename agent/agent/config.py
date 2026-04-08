from __future__ import annotations

from functools import lru_cache

from dotenv import find_dotenv
from pydantic import AnyUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    App settings loaded from environment variables and (optionally) a `.env`.

    We use `find_dotenv()` so this works whether the agent is launched from repo
    root or from within the `agent/` directory.
    """

    anthropic_api_key: SecretStr = Field(validation_alias="ANTHROPIC_API_KEY")
    api_server_url: AnyUrl = Field(validation_alias="API_SERVER_URL")

    model_config = SettingsConfigDict(
        env_file=find_dotenv(usecwd=True) or None,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
