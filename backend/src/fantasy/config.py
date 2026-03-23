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
