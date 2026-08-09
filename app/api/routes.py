"""
HTTP routes.

Thin by design: validate the request, call into services/, map the
service's plain-Python result onto the pydantic response schema. No
business logic lives here -- if you're tempted to add an if/else about
*how* to process the data (as opposed to how to validate/serialise it),
it probably belongs in services/ instead.
"""

from fastapi import APIRouter, Depends, Form, UploadFile

from app.adapters.factory import get_extraction_provider, get_transcription_provider
from app.api.schemas import (
    ExtractResponse,
    ReportMetaResponse,
    ReportResultResponse,
    TranscribeResponse,
)
from app.api.validation import (
    validate_and_read_audio,
    validate_and_read_image,
    validate_language,
)
from app.config import Settings, get_settings
from app.services.extraction_service import ExtractionService
from app.services.transcription_service import TranscriptionService

router = APIRouter(prefix="/api/v1")


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    file: UploadFile,
    language: str = Form(...),
    settings: Settings = Depends(get_settings),
) -> TranscribeResponse:
    validate_language(language)
    audio_bytes = await validate_and_read_audio(file, settings)

    provider = get_transcription_provider(settings)
    service = TranscriptionService(provider)
    result = service.run(audio_bytes, language)

    return TranscribeResponse(
        transcript=result.transcript,
        detected_language=result.detected_language,
        duration_seconds=result.duration_seconds,
        provider=result.provider,
        no_speech_detected=result.no_speech_detected,
    )


@router.post("/documents/extract", response_model=ExtractResponse)
async def extract_document(
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> ExtractResponse:
    image_bytes = await validate_and_read_image(file, settings)

    provider = get_extraction_provider(settings)
    service = ExtractionService(provider)
    outcome = service.run(image_bytes)

    return ExtractResponse(
        meta=ReportMetaResponse(
            patient_name=outcome.meta.patient_name,
            age=outcome.meta.age,
            sex=outcome.meta.sex,
            report_date=outcome.meta.report_date,
            lab_name=outcome.meta.lab_name,
            reference_no=outcome.meta.reference_no,
        ),
        results=[
            ReportResultResponse(
                test_name=row.test_name,
                value=row.value,
                unit=row.unit,
                reference_range=row.reference_range,
                flag=row.flag,
                raw_line=row.raw_line,
            )
            for row in outcome.results
        ],
        is_lab_report=outcome.is_lab_report,
    )