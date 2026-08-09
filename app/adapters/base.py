"""
Adapter interfaces.

Every provider (mock or real) for a given endpoint implements the same
Protocol here. services/ only ever depends on these interfaces, never
on a concrete provider class or its SDK -- that's what makes swapping
mock <-> real a config change instead of a code change.

No FastAPI types and no provider SDK imports belong in this file: it is
pure dataclasses + typing, shared vocabulary between services/ and
adapters/.
"""

from dataclasses import dataclass
from typing import Protocol


# ---------------------------------------------------------------------------
# Endpoint 1: Transcription
# ---------------------------------------------------------------------------

@dataclass
class TranscriptionResult:
    transcript: str
    detected_language: str
    duration_seconds: float
    provider: str
    # True when the audio contained no detectable speech (silence / pure
    # ambient noise). transcript will be "" in that case -- see
    # services/transcription_service.py for the decision behind this.
    no_speech_detected: bool = False


class TranscriptionProvider(Protocol):
    def transcribe(self, audio_bytes: bytes, language: str) -> TranscriptionResult:
        ...


# ---------------------------------------------------------------------------
# Endpoint 2: Lab report extraction
# ---------------------------------------------------------------------------

@dataclass
class ReportMeta:
    patient_name: str | None = None
    age: str | None = None
    sex: str | None = None
    report_date: str | None = None
    lab_name: str | None = None
    reference_no: str | None = None


@dataclass
class RawResultRow:
    """
    A single result row exactly as the provider read it -- no parsing or
    normalisation applied yet. raw_value/raw_unit are the literal
    substrings the provider identified; raw_line is the full original
    line, always preserved verbatim regardless of what normalisation
    later succeeds or fails to do with it.
    """
    test_name: str
    raw_value: str
    raw_unit: str | None
    reference_range: str | None
    flag: str | None
    raw_line: str


@dataclass
class RawExtraction:
    """
    What a provider hands back to services/ -- unnormalised, as close to
    the provider's own output shape as practical. Normalisation into the
    final API schema (numeric value, canonical unit) happens in
    services/normalisation.py, not here, so that logic is
    provider-independent and unit-testable on its own.
    """
    meta: ReportMeta
    results: list[RawResultRow]
    is_lab_report: bool = True


class DocumentExtractionProvider(Protocol):
    def extract(self, image_bytes: bytes) -> RawExtraction:
        ...