"""
API request/response schemas.

These are the HTTP-facing contract. Internal service/adapter dataclasses
(TranscriptionResult, ExtractionOutcome, etc.) are deliberately kept
separate from these -- the api/ layer maps one to the other -- so that
the wire format can evolve independently of internal representations,
and so services/ never has to know about pydantic or HTTP at all.
"""

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """
    Structured error body returned for any 4xx from these endpoints --
    never a raw stack trace (brief point 2).
    """
    error: ErrorDetail


# --- Endpoint 1: Transcription -----------------------------------------------

class TranscribeResponse(BaseModel):
    transcript: str
    detected_language: str
    duration_seconds: float
    provider: str
    no_speech_detected: bool = Field(
        description="True if the audio contained no detectable speech "
        "(silence or pure ambient noise). transcript will be empty in "
        "that case."
    )


# --- Endpoint 2: Lab report extraction ----------------------------------------

class ReportMetaResponse(BaseModel):
    patient_name: str | None = None
    age: str | None = None
    sex: str | None = None
    report_date: str | None = None
    lab_name: str | None = None
    reference_no: str | None = None


class ReportResultResponse(BaseModel):
    test_name: str
    value: float | str
    unit: str | None = None
    reference_range: str | None = None
    flag: str | None = None
    raw_line: str


class ExtractResponse(BaseModel):
    meta: ReportMetaResponse
    results: list[ReportResultResponse]
    is_lab_report: bool = Field(
        description="False when the uploaded image does not appear to be "
        "a lab report; meta and results will be empty in that case rather "
        "than containing fabricated data. This field is an addition on "
        "top of the brief's base schema -- documented in README.md."
    )