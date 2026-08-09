"""
Transcription orchestration service.

Pure Python, no FastAPI types, no provider SDK imports. Takes a
TranscriptionProvider (mock or real, injected by the caller) and raw
audio bytes, and returns the final result shape the API layer will
serialise into the HTTP response.
"""

from __future__ import annotations

from app.adapters.base import TranscriptionProvider, TranscriptionResult


class TranscriptionService:
    def __init__(self, provider: TranscriptionProvider):
        self._provider = provider

    def run(self, audio_bytes: bytes, language: str) -> TranscriptionResult:
        result = self._provider.transcribe(audio_bytes, language)

        # Safety net: silence/no-speech detection must be reliable
        # regardless of whether a given adapter implementation correctly
        # sets no_speech_detected itself. An empty or whitespace-only
        # transcript is treated as "no speech" here, deterministically,
        # rather than trusting every current and future adapter to get
        # this right on its own.
        transcript_is_empty = result.transcript.strip() == ""

        if transcript_is_empty and not result.no_speech_detected:
            return TranscriptionResult(
                transcript="",
                detected_language=result.detected_language,
                duration_seconds=result.duration_seconds,
                provider=result.provider,
                no_speech_detected=True,
            )

        return result