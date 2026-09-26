from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parents[3] / ".env", Path(__file__).resolve().parents[2] / ".env"),
        extra="ignore", case_sensitive=False,
    )

    project_name: str = "SIMRAS Digital Twin"
    environment: str = "development"
    secret_key: str = "development-only-change-me"
    database_url: str = (
        "postgresql+asyncpg://simras:simras-change-me@localhost:5432/simras"
    )
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    public_read_enabled: bool = True
    admin_api_key: str = "development-admin-key"
    gemini_api_key: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.backend_cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
