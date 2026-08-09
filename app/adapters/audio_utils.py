"""
Shared audio helpers used by adapters that don't get duration for free
from their own SDK response (e.g. Gemini's text-only reply). Kept
separate from base.py since this is an implementation detail (mutagen),
not part of the shared adapter interface.
"""

import tempfile

from mutagen import File as MutagenFile


def get_audio_duration_seconds(audio_bytes: bytes) -> float:
    with tempfile.NamedTemporaryFile(suffix=".audio") as tmp:
        tmp.write(audio_bytes)
        tmp.flush()

        audio = MutagenFile(tmp.name)
        if audio is None or audio.info is None:
            raise ValueError("Could not determine audio duration: unrecognised format")

        return float(audio.info.length)
