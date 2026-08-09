"""
Upload validation for both endpoints.

This is api/ layer code: it's the only place allowed to raise
HTTPException and touch FastAPI's UploadFile. It reads the upload into
plain bytes and hands those bytes onward -- services/ never sees an
UploadFile.
"""

from fastapi import HTTPException, UploadFile

from app.api.schemas import ErrorDetail, ErrorResponse
from app.config import Settings

_ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
_ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
_ALLOWED_LANGUAGES = {"bn", "en", "auto"}


def _structured_error(status_code: int, code: str, message: str) -> HTTPException:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return HTTPException(status_code=status_code, detail=body.model_dump())


def _extension_of(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


async def validate_and_read_audio(file: UploadFile, settings: Settings) -> bytes:
    ext = _extension_of(file.filename)
    if ext not in _ALLOWED_AUDIO_EXTENSIONS:
        raise _structured_error(
            status_code=400,
            code="unsupported_audio_format",
            message=(
                f"Unsupported audio format '{ext or 'unknown'}'. "
                f"Allowed formats: {sorted(_ALLOWED_AUDIO_EXTENSIONS)}."
            ),
        )

    audio_bytes = await file.read()
    _validate_size(len(audio_bytes), settings)
    return audio_bytes


async def validate_and_read_image(file: UploadFile, settings: Settings) -> bytes:
    ext = _extension_of(file.filename)
    if ext not in _ALLOWED_IMAGE_EXTENSIONS:
        raise _structured_error(
            status_code=400,
            code="unsupported_image_format",
            message=(
                f"Unsupported image format '{ext or 'unknown'}'. "
                f"Allowed formats: {sorted(_ALLOWED_IMAGE_EXTENSIONS)}."
            ),
        )

    image_bytes = await file.read()
    _validate_size(len(image_bytes), settings)
    return image_bytes


def _validate_size(size_bytes: int, settings: Settings) -> None:
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise _structured_error(
            status_code=400,
            code="file_too_large",
            message=(
                f"File is {size_bytes / (1024 * 1024):.1f} MB, exceeds the "
                f"{settings.max_upload_size_mb} MB limit."
            ),
        )
    if size_bytes == 0:
        raise _structured_error(
            status_code=400,
            code="empty_file",
            message="Uploaded file is empty.",
        )


def validate_language(language: str) -> str:
    if language not in _ALLOWED_LANGUAGES:
        raise _structured_error(
            status_code=400,
            code="unsupported_language",
            message=f"Unsupported language '{language}'. Allowed: {sorted(_ALLOWED_LANGUAGES)}.",
        )
    return language