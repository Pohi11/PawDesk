from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# The repo-root .env, located relative to this file so it works from any working directory.
# Inside Docker there is no .env file; Compose injects the same variables as environment
# variables, and real environment variables always win over .env values.
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    database_url: str
    # SecretStr prints as '**********' in logs, reprs, and tracebacks.
    # The real value is only available via .get_secret_value().
    openrouter_api_key: SecretStr
    openrouter_model: str = "deepseek/deepseek-v4.1-flash"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_timeout_seconds: float = 30.0  # per attempt
    llm_max_attempts: int = 3
    # Recorded responses (decision record 0016): "off", "record", or "replay".
    llm_cassette_mode: Literal["off", "record", "replay"] = "off"
    llm_cassette_dir: Path | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
