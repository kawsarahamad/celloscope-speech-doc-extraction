"""
Mock transcription adapter.

Replays a fixed, recorded-looking response from disk. No network call,
no model load. This is the default adapter so a clean clone runs with
zero credentials -- see app/config.py and app/adapters/factory.py.
"""

import json
from pathlib import Path

from app.adapters.base import TranscriptionResult

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "testdata" / "fixtures"


class MockTranscriptionAdapter:
    def transcribe(self, audio_bytes: bytes, language: str) -> TranscriptionResult:
        # A real mock could branch on audio_bytes size/content to
        # simulate different fixtures (e.g. a "silence" test case) --
        # kept simple for now, expand once real fixture files exist.
        fixture_path = FIXTURES_DIR / "transcription_sample.json"

        if fixture_path.exists():
            data = json.loads(fixture_path.read_text())
        else:
            # Fallback so the mock still works before fixtures are committed.
            data = {
                "transcript": "This is a mock transcript for testing.",
                "detected_language": language if language != "auto" else "en",
                "duration_seconds": 3.5,
            }

        return TranscriptionResult(
            transcript=data["transcript"],
            detected_language=data["detected_language"],
            duration_seconds=data["duration_seconds"],
            provider="mock",
            no_speech_detected=False,
        )