"""
Integration test for POST /api/v1/documents/extract, run against the
mock adapter via FastAPI's TestClient.
"""

from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_extract_happy_path_returns_mock_report():
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("report.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_lab_report"] is True
    assert body["meta"]["patient_name"] == "Jane Doe"
    assert len(body["results"]) == 3

    # Confirm normalisation actually ran end to end through the HTTP layer
    hemoglobin = next(r for r in body["results"] if r["test_name"] == "Hemoglobin")
    assert hemoglobin["value"] == 12.5
    assert hemoglobin["unit"] == "g/dl"
    assert hemoglobin["raw_line"] == "Hemoglobin 12.5 g/dL (12.0-15.5)"

    # Comparator-prefixed value must survive as a string, not be dropped
    vitamin_d = next(r for r in body["results"] if r["test_name"] == "Vitamin D")
    assert vitamin_d["value"] == "<0.5"


def test_extract_rejects_unsupported_file_format():
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("report.pdf", b"fake-pdf-bytes", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "unsupported_image_format"


def test_extract_rejects_oversized_file():
    big_bytes = b"0" * (26 * 1024 * 1024)
    response = client.post(
        "/api/v1/documents/extract",
        files={"file": ("report.jpg", big_bytes, "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "file_too_large"