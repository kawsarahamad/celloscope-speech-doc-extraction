"""
Adapter factories.

The only place that branches on "which provider is configured." Real
adapter classes (Whisper, Gemini) are imported lazily, inside the
branch that selects them -- so a mock-only run never imports whisper
or google.generativeai at all, and never needs their dependencies
installed to boot.
"""

from app.adapters.base import DocumentExtractionProvider, TranscriptionProvider
from app.adapters.mock_extraction_adapter import MockExtractionAdapter
from app.adapters.mock_transcription_adapter import MockTranscriptionAdapter
from app.config import ExtractionProviderName, Settings, TranscriptionProviderName


def get_transcription_provider(settings: Settings) -> TranscriptionProvider:
    if settings.transcription_provider == TranscriptionProviderName.MOCK:
        return MockTranscriptionAdapter()

    if settings.transcription_provider == TranscriptionProviderName.WHISPER:
        from app.adapters.whisper_adapter import WhisperAdapter  # local import: keeps
        # whisper (and its heavy deps) uninstalled/unloaded on the mock-only path
        return WhisperAdapter(model_size=settings.whisper_model_size, device=settings.whisper_device)

    if settings.transcription_provider == TranscriptionProviderName.GEMINI:
        from app.adapters.gemini_transcription_adapter import GeminiTranscriptionAdapter  # local import
        if not settings.gemini_api_key:
            raise ValueError(
                "transcription_provider is set to 'gemini' but gemini_api_key is not "
                "configured. Set GEMINI_API_KEY in .env."
            )
        return GeminiTranscriptionAdapter(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_model_name,
        )

    raise ValueError(f"Unknown transcription provider: {settings.transcription_provider}")


def get_extraction_provider(settings: Settings) -> DocumentExtractionProvider:
    if settings.extraction_provider == ExtractionProviderName.MOCK:
        return MockExtractionAdapter()

    if settings.extraction_provider == ExtractionProviderName.GEMINI:
        from app.adapters.gemini_adapter import GeminiExtractionAdapter  # local import
        if not settings.gemini_api_key:
            raise ValueError(
                "extraction_provider is set to 'gemini' but gemini_api_key is not "
                "configured. Set GEMINI_API_KEY in .env."
            )
        return GeminiExtractionAdapter(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_model_name,
        )

    raise ValueError(f"Unknown extraction provider: {settings.extraction_provider}")