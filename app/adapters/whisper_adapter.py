"""
Self-hosted transcription adapter using faster-whisper (CTranslate2
reimplementation of Whisper) -- GPU-accelerated when available, no API
key, no network call at inference time (only the one-time model
download on first use).

This file is the ONLY place in the codebase allowed to import
faster_whisper -- see the "no provider SDK outside adapters/" rule.
"""

import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

from app.adapters.base import TranscriptionResult

# Loaded once per process on first real use, not per-request -- model
# load is the expensive part, we don't want to repeat it on every call.
_model_cache: dict[tuple[str, str], WhisperModel] = {}


def _get_model(model_size: str, device: str) -> WhisperModel:
    key = (model_size, device)
    if key not in _model_cache:
        # device="auto" picks GPU if available (CUDA), falls back to CPU
        # otherwise -- keeps this adapter usable even without a GPU,
        # just slower. Callers can force "cpu"/"cuda" via WHISPER_DEVICE.
        _model_cache[key] = WhisperModel(
            model_size, device=device, compute_type="auto"
        )
    return _model_cache[key]


class WhisperAdapter:
    def __init__(self, model_size: str = "small", device: str = "auto"):
        self._model_size = model_size
        self._device = device

    def transcribe(self, audio_bytes: bytes, language: str) -> TranscriptionResult:
        model = _get_model(self._model_size, self._device)

        # faster-whisper reads from a file path; write the uploaded
        # bytes to a temp file for the duration of this call.
        with tempfile.NamedTemporaryFile(suffix=".audio", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()

            # "auto" -> let Whisper detect the language itself.
            # Otherwise force it, since the caller already knows (bn/en).
            forced_language = None if language == "auto" else language

            segments, info = model.transcribe(
                tmp.name,
                language=forced_language,
                vad_filter=True,  # filters out silence/non-speech segments
            )
            segments = list(segments)  # faster-whisper returns a generator

        transcript = " ".join(segment.text.strip() for segment in segments).strip()

        return TranscriptionResult(
            transcript=transcript,
            detected_language=info.language,
            duration_seconds=info.duration,
            provider="whisper",
            # Left as False here deliberately -- the service layer's
            # safety net (services/transcription_service.py) is the
            # single source of truth for this flag, based on whether
            # transcript ends up empty. Keeps the decision in one place
            # rather than duplicated across every adapter.
            no_speech_detected=False,
        )