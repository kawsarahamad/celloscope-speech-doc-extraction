"""
Integration test for POST /api/v1/transcribe, run against the mock
adapter (the default provider when no .env overrides it) via FastAPI's
TestClient -- exercises real HTTP routing, validation, and response
serialisation end to end.
"""

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_transcribe_happy_path_returns_mock_transcript():
    response = client.post(
        "/api/v1/transcribe",
        files={"file": ("sample.wav", b"fake-audio-bytes", "audio/wav")},
        data={"language": "en"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["detected_language"] == "en"
    assert isinstance(body["transcript"], str) and body["transcript"] != ""
    assert body["no_speech_detected"] is False


def test_transcribe_rejects_unsupported_format_with_structured_error():
    response = client.post(
        "/api/v1/transcribe",
        files={"file": ("sample.exe", b"not-audio", "application/octet-stream")},
        data={"language": "en"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["error"]["code"] == "unsupported_audio_format"


def test_transcribe_rejects_oversized_file():
    big_bytes = b"0" * (26 * 1024 * 1024)  # 26 MB > 25 MB limit
    response = client.post(
        "/api/v1/transcribe",
        files={"file": ("sample.wav", big_bytes, "audio/wav")},
        data={"language": "en"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "file_too_large"


def test_transcribe_rejects_unsupported_language():
    response = client.post(
        "/api/v1/transcribe",
        files={"file": ("sample.wav", b"fake-audio", "audio/wav")},
        data={"language": "fr"},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "unsupported_language"