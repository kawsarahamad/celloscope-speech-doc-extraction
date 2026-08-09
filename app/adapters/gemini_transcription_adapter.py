"""
Transcription adapter using the Gemini API (free tier, no self-hosting
required). Adopted as the primary real transcription adapter after a
self-hosted Whisper (faster-whisper) implementation hit a CTranslate2 /
RTX 5080 (Blackwell) GPU compatibility gap -- see DECISIONS.md. The
Whisper adapter (whisper_adapter.py) is kept in the codebase and works
correctly in CPU mode; this file is the pragmatic choice to stay on
schedule while GPU support for very new architectures matures upstream.

This file is the ONLY place (along with gemini_adapter.py for
extraction) allowed to import google.generativeai -- see the "no
provider SDK outside adapters/" rule.
"""

import mimetypes
import tempfile

from google import genai
from google.genai import types

from app.adapters.audio_utils import get_audio_duration_seconds
from app.adapters.base import TranscriptionResult

_TRANSCRIPTION_PROMPT = (
    "Transcribe the speech in this audio file exactly as spoken. "
    "The audio may be in Bengali, English, or a mix of both. "
    "Return ONLY the transcript text, nothing else -- no preamble, "
    "no commentary, no markdown formatting. "
    "If the audio contains no speech at all (silence or pure ambient "
    "noise), return exactly: [NO_SPEECH]"
)


class GeminiTranscriptionAdapter:
    def __init__(self, api_key: str, model_name: str):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    def transcribe(self, audio_bytes: bytes, language: str) -> TranscriptionResult:
        # Gemini's file API wants a real file on disk (or an uploaded
        # File object) rather than raw bytes for audio input.
        with tempfile.NamedTemporaryFile(suffix=".audio", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()

            mime_type = mimetypes.guess_type(tmp.name)[0] or "audio/wav"
            uploaded_file = self._client.files.upload(
                file=tmp.name, config=types.UploadFileConfig(mime_type=mime_type)
            )

            response = self._client.models.generate_content(
                model=self._model_name,
                contents=[_TRANSCRIPTION_PROMPT, uploaded_file],
            )

        raw_text = (response.text or "").strip()
        no_speech = raw_text == "[NO_SPEECH]"
        transcript = "" if no_speech else raw_text

        # Gemini's response doesn't give us duration or detected_language
        # directly the way Whisper does. duration is computed separately
        # from the raw audio bytes (mutagen) since it's a required field
        # per the brief, not something we can omit or fabricate.
        # detected_language falls back to the requested language (or
        # "unknown" for auto) -- Gemini's text response doesn't reliably
        # expose a structured language code the way Whisper's info
        # object does. Documented as a known limitation in README.
        detected_language = language if language != "auto" else "unknown"
        duration_seconds = get_audio_duration_seconds(audio_bytes)

        return TranscriptionResult(
            transcript=transcript,
            detected_language=detected_language,
            duration_seconds=duration_seconds,
            provider="gemini",
            no_speech_detected=no_speech,
        )