"""
Mock document extraction adapter.

Replays a fixed, recorded-looking response from disk. No network call,
no model load. This is the default adapter so a clean clone runs with
zero credentials -- see app/config.py and app/adapters/factory.py.
"""

import json
from pathlib import Path

from app.adapters.base import RawExtraction, RawResultRow, ReportMeta

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "testdata" / "fixtures"


class MockExtractionAdapter:
    def extract(self, image_bytes: bytes) -> RawExtraction:
        fixture_path = FIXTURES_DIR / "extraction_sample.json"

        if fixture_path.exists():
            data = json.loads(fixture_path.read_text())
        else:
            # Fallback so the mock still works before fixtures are committed.
            data = {
                "meta": {
                    "patient_name": "Jane Doe",
                    "age": "34",
                    "sex": "F",
                    "report_date": "2026-01-15",
                    "lab_name": "Mock Diagnostics Ltd.",
                    "reference_no": "MOCK-0001",
                },
                "results": [
                    {
                        "test_name": "Hemoglobin",
                        "raw_value": "12.5",
                        "raw_unit": "g/dL",
                        "reference_range": "12.0 - 15.5",
                        "flag": None,
                        "raw_line": "Hemoglobin 12.5 g/dL (12.0-15.5)",
                    }
                ],
                "is_lab_report": True,
            }

        meta = ReportMeta(**data["meta"])
        results = [RawResultRow(**row) for row in data["results"]]

        return RawExtraction(
            meta=meta,
            results=results,
            is_lab_report=data.get("is_lab_report", True),
        )