"""
Central, typed application configuration.

Every provider adapter is selected here via env vars, defaulting to the
mock provider so `docker compose up` works with zero credentials and
zero model downloads on a clean clone.

Deliberately lives outside api/, services/, and adapters/ since it is a
cross-cutting concern all three layers may read (read-only) without
violating the "dependencies point inward" rule -- settings has no
dependents pointing *out* of it, and nothing here imports FastAPI or
any provider SDK.
"""

from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class TranscriptionProviderName(str, Enum):
    MOCK = "mock"
    WHISPER = "whisper"


class ExtractionProviderName(str, Enum):
    MOCK = "mock"
    GEMINI = "gemini"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- Provider selection ---
    # Defaults to mock so a clean clone with no .env still runs fully.
    transcription_provider: TranscriptionProviderName = TranscriptionProviderName.MOCK
    extraction_provider: ExtractionProviderName = ExtractionProviderName.MOCK

    # --- Real adapter config (only required if the matching provider above is selected) ---
    whisper_model_size: str = "small"
    gemini_api_key: str | None = None
    gemini_model_name: str = "gemini-2.0-flash"

    # --- Validation limits (endpoint 1 & 2 share the same file-size ceiling) ---
    max_upload_size_mb: int = 25


def get_settings() -> Settings:
    """
    Factory function rather than a bare module-level singleton, so tests
    can override settings (e.g. via dependency_overrides in FastAPI)
    without relying on import-time global state.
    """
    return Settings()