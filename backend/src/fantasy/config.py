from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DB_PATH: str = "data/fantasy.duckdb"
    PORTFOLIO_OWNER_ID: str | None = None
    PORTFOLIO_OWNER_DISPLAY_NAME: str | None = None
    INGEST_LOCK_TIMEOUT: int = 300
    DEV_AUTO_REFRESH: bool = False
    DEV_AUTO_REFRESH_LEAGUES: str = ""
    DEV_AUTO_REFRESH_INGEST_MODE: Literal["skip", "incremental", "full"] = "incremental"
    DEV_AUTO_REFRESH_SNAPSHOTS: bool = True
    INTELLIGENCE_PUBLIC_FEEDS: str = ""
    INTELLIGENCE_BROWSER_ENABLED: bool = False
    INTELLIGENCE_BROWSER_EXECUTABLE_PATH: str | None = None
    INTELLIGENCE_CACHE_DAYS: int = 7
    INTELLIGENCE_MIN_REQUEST_INTERVAL_SECONDS: float = 1.0
    INTELLIGENCE_USER_AGENT: str = "FantasyFreshIntelligence/2.0 (+local personal assistant)"
    INTELLIGENCE_EXTRACTOR_PROVIDER: Literal["none", "openai_compatible"] = "none"
    INTELLIGENCE_EXTRACTOR_BASE_URL: str = "http://127.0.0.1:11434/v1"
    INTELLIGENCE_EXTRACTOR_MODEL: str | None = None
    INTELLIGENCE_EXTRACTOR_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="FANTASY_",
        extra="ignore",
        env_file=str(REPO_ROOT / ".env"),
    )

    @property
    def db_path(self) -> str:
        if self.DB_PATH == ":memory:":
            return self.DB_PATH

        path = Path(self.DB_PATH)
        if path.is_absolute():
            return str(path)

        return str((REPO_ROOT / path).resolve())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
