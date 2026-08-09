"""
Tests for app/services/transcription_service.py.

Uses lightweight stub providers so these tests exercise the service's
own orchestration/silence-detection logic in isolation from any real
provider or fixture file.
"""

from app.adapters.base import TranscriptionResult
from app.services.transcription_service import TranscriptionService


class _StubProvider:
    """Returns a fixed TranscriptionResult, configurable per test."""

    def __init__(self, result: TranscriptionResult):
        self._result = result

    def transcribe(self, audio_bytes: bytes, language: str) -> TranscriptionResult:
        return self._result


def test_happy_path_passes_through_unchanged():
    stub_result = TranscriptionResult(
        transcript="Hello, this is a test.",
        detected_language="en",
        duration_seconds=4.2,
        provider="mock",
        no_speech_detected=False,
    )
    service = TranscriptionService(_StubProvider(stub_result))
    outcome = service.run(b"irrelevant", "en")

    assert outcome.transcript == "Hello, this is a test."
    assert outcome.no_speech_detected is False


def test_empty_transcript_forces_no_speech_flag_even_if_adapter_forgot():
    # Simulates an adapter that produced an empty transcript but failed
    # to set no_speech_detected itself -- the service must catch this
    # regardless, since reliability here can't depend on every adapter
    # getting it right.
    stub_result = TranscriptionResult(
        transcript="",
        detected_language="en",
        duration_seconds=3.0,
        provider="whisper",
        no_speech_detected=False,  # adapter "forgot" to flag it
    )
    service = TranscriptionService(_StubProvider(stub_result))
    outcome = service.run(b"silent-audio-bytes", "en")

    assert outcome.no_speech_detected is True
    assert outcome.transcript == ""


def test_whitespace_only_transcript_treated_as_no_speech():
    stub_result = TranscriptionResult(
        transcript="   \n  ",
        detected_language="en",
        duration_seconds=2.5,
        provider="whisper",
        no_speech_detected=False,
    )
    service = TranscriptionService(_StubProvider(stub_result))
    outcome = service.run(b"ambient-noise-bytes", "en")

    assert outcome.no_speech_detected is True
    assert outcome.transcript == ""


def test_adapter_correctly_flagging_no_speech_is_respected():
    stub_result = TranscriptionResult(
        transcript="",
        detected_language="en",
        duration_seconds=5.0,
        provider="whisper",
        no_speech_detected=True,  # adapter already got it right
    )
    service = TranscriptionService(_StubProvider(stub_result))
    outcome = service.run(b"silent-audio-bytes", "en")

    assert outcome.no_speech_detected is True