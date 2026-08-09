"""
Shared test fixtures.

Integration tests must run against the mock adapters regardless of
whatever real-provider config happens to be sitting in the local .env
-- otherwise `pytest` silently starts hitting real models/APIs (and
failing on fake test bytes, or burning quota) depending on whoever's
machine or CI job it runs on.
"""

import pytest

from app.api.main import app
from app.config import ExtractionProviderName, Settings, TranscriptionProviderName, get_settings


def _mock_settings() -> Settings:
    return Settings(
        transcription_provider=TranscriptionProviderName.MOCK,
        extraction_provider=ExtractionProviderName.MOCK,
    )


@pytest.fixture(autouse=True)
def _force_mock_providers():
    app.dependency_overrides[get_settings] = _mock_settings
    yield
    app.dependency_overrides.pop(get_settings, None)
