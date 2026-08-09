"""
Tests for app/services/extraction_service.py.

Uses lightweight stub providers (not the real mock adapter) so these
tests are decoupled from fixture file content and test the service's
own orchestration logic in isolation.
"""

from app.adapters.base import RawExtraction, RawResultRow, ReportMeta
from app.services.extraction_service import ExtractionService


class _StubProvider:
    """Returns a fixed RawExtraction, configurable per test."""

    def __init__(self, raw_extraction: RawExtraction):
        self._raw_extraction = raw_extraction

    def extract(self, image_bytes: bytes) -> RawExtraction:
        return self._raw_extraction


def test_happy_path_normalises_all_fields():
    raw = RawExtraction(
        meta=ReportMeta(
            patient_name="Jane Doe",
            age="34",
            sex="F",
            report_date="15/01/2026",
            lab_name="Test Lab",
            reference_no="REF-1",
        ),
        results=[
            RawResultRow(
                test_name="Hemoglobin",
                raw_value="12.5",
                raw_unit="gm/dl",
                reference_range="12.0 - 15.5",
                flag=None,
                raw_line="Hemoglobin 12.5 gm/dl (12.0-15.5)",
            )
        ],
        is_lab_report=True,
    )
    service = ExtractionService(_StubProvider(raw))
    outcome = service.run(b"irrelevant")

    assert outcome.is_lab_report is True
    assert outcome.meta.report_date == "2026-01-15"  # normalised to ISO
    assert outcome.results[0].value == 12.5  # numeric, parsed
    assert outcome.results[0].unit == "g/dl"  # alias collapsed
    assert outcome.results[0].raw_line == "Hemoglobin 12.5 gm/dl (12.0-15.5)"  # untouched


def test_comparator_value_preserved_verbatim_not_dropped():
    raw = RawExtraction(
        meta=ReportMeta(),
        results=[
            RawResultRow(
                test_name="Vitamin D",
                raw_value="<0.5",
                raw_unit="ng/mL",
                reference_range="30 - 100",
                flag="L",
                raw_line="Vitamin D <0.5 ng/mL (30-100) L",
            )
        ],
        is_lab_report=True,
    )
    service = ExtractionService(_StubProvider(raw))
    outcome = service.run(b"irrelevant")

    # Must not be silently coerced/guessed into 0.5 -- that would lose
    # the "<" meaning.
    assert outcome.results[0].value == "<0.5"
    assert outcome.results[0].raw_line == "Vitamin D <0.5 ng/mL (30-100) L"


def test_non_lab_report_degrades_gracefully():
    raw = RawExtraction(meta=ReportMeta(), results=[], is_lab_report=False)
    service = ExtractionService(_StubProvider(raw))
    outcome = service.run(b"a-receipt-photo")

    assert outcome.is_lab_report is False
    assert outcome.results == []
    assert outcome.meta.patient_name is None


def test_empty_results_list_does_not_crash():
    raw = RawExtraction(meta=ReportMeta(patient_name="John Smith"), results=[], is_lab_report=True)
    service = ExtractionService(_StubProvider(raw))
    outcome = service.run(b"irrelevant")

    assert outcome.is_lab_report is True
    assert outcome.results == []
    assert outcome.meta.patient_name == "John Smith"