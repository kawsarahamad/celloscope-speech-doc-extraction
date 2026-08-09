"""
Extraction orchestration service.

Pure Python, no FastAPI types, no provider SDK imports. Takes a
DocumentExtractionProvider (mock or real, injected by the caller) and
raw image bytes, and returns the final normalised result shape the API
layer will serialise into the HTTP response.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.adapters.base import DocumentExtractionProvider, RawResultRow, ReportMeta
from app.services.normalisation import normalise_date, normalise_unit, normalise_value


@dataclass
class NormalisedResultRow:
    test_name: str
    value: float | str  # numeric when confidently parsed, else verbatim raw_value
    unit: str | None
    reference_range: str | None
    flag: str | None
    raw_line: str  # always the untouched original line, never dropped


@dataclass
class NormalisedMeta:
    patient_name: str | None
    age: str | None
    sex: str | None
    report_date: str | None  # ISO YYYY-MM-DD when confidently parsed, else verbatim
    lab_name: str | None
    reference_no: str | None


@dataclass
class ExtractionOutcome:
    meta: NormalisedMeta
    results: list[NormalisedResultRow]
    is_lab_report: bool


def _normalise_meta(meta: ReportMeta) -> NormalisedMeta:
    return NormalisedMeta(
        patient_name=meta.patient_name,
        age=meta.age,
        sex=meta.sex,
        report_date=normalise_date(meta.report_date),
        lab_name=meta.lab_name,
        reference_no=meta.reference_no,
    )


def _normalise_row(row: RawResultRow) -> NormalisedResultRow:
    return NormalisedResultRow(
        test_name=row.test_name,
        value=normalise_value(row.raw_value),
        unit=normalise_unit(row.raw_unit),
        reference_range=row.reference_range,
        flag=row.flag,
        raw_line=row.raw_line,  # never touched, never dropped
    )


class ExtractionService:
    def __init__(self, provider: DocumentExtractionProvider):
        self._provider = provider

    def run(self, image_bytes: bytes) -> ExtractionOutcome:
        raw = self._provider.extract(image_bytes)

        if not raw.is_lab_report:
            # Degrade gracefully: no fabricated fields, no fabricated
            # rows. The caller (api/) is responsible for deciding what
            # HTTP status/response wrapper to use for this outcome; this
            # layer just reports the fact plainly.
            return ExtractionOutcome(
                meta=NormalisedMeta(
                    patient_name=None,
                    age=None,
                    sex=None,
                    report_date=None,
                    lab_name=None,
                    reference_no=None,
                ),
                results=[],
                is_lab_report=False,
            )

        return ExtractionOutcome(
            meta=_normalise_meta(raw.meta),
            results=[_normalise_row(row) for row in raw.results],
            is_lab_report=True,
        )