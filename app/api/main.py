"""
FastAPI application entrypoint.

This module (and everything else under app/api/) is the only place
allowed to import FastAPI types (Request, Response, UploadFile,
HTTPException) and to know that HTTP exists at all. Business logic
lives in app/services/ and never imports from here.
"""

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings

app = FastAPI(
    title="Celloscope Speech & Document Extraction",
    version="0.1.0",
)
app.include_router(router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """
    Basic liveness check. Also surfaces which providers are active so a
    reviewer can immediately see whether they're hitting mocks or real
    adapters without digging into .env.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "transcription_provider": settings.transcription_provider.value,
        "extraction_provider": settings.extraction_provider.value,
    }