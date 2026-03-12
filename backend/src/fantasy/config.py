from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DB_PATH: str = "data/fantasy.duckdb"
    INGEST_LOCK_TIMEOUT: int = 300

    model_config = SettingsConfigDict(env_prefix="FANTASY_", extra="ignore")

    @property
    def db_path(self) -> str:
        if self.DB_PATH == ":memory:":
            return self.DB_PATH

        path = Path(self.DB_PATH)
        if path.is_absolute():
            return str(path)

        repo_root = Path(__file__).resolve().parents[3]
        return str((repo_root / path).resolve())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
