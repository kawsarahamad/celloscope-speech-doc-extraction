"""
Lab report extraction adapter using the Gemini API (free tier).

This file is the ONLY place (along with gemini_transcription_adapter.py)
allowed to import google.generativeai -- see the "no provider SDK
outside adapters/" rule.

Response parsing is split into a standalone function (parse_gemini_response)
specifically so it's unit-testable without a live network call -- the
network call itself can't be meaningfully unit tested here, but the
"can this code handle whatever text comes back" logic can and should be.
"""

import json
import mimetypes
import re
import tempfile

from google import genai
from google.genai import types

from app.adapters.base import RawExtraction, RawResultRow, ReportMeta

_EXTRACTION_PROMPT = """\
You are reading a photograph of a medical lab report. It may be \
photographed at an angle, in poor lighting, or with part of the page \
cut off.

Return ONLY a single JSON object, no markdown fences, no commentary, \
matching exactly this shape:

{
  "is_lab_report": true or false,
  "meta": {
    "patient_name": string or null,
    "age": string or null,
    "sex": string or null,
    "report_date": string or null,
    "lab_name": string or null,
    "reference_no": string or null
  },
  "results": [
    {
      "test_name": string,
      "raw_value": string,
      "raw_unit": string or null,
      "reference_range": string or null,
      "flag": string or null,
      "raw_line": string
    }
  ]
}

Rules:
- If the image is not a lab report (e.g. a receipt, a random document, \
an unrelated photo), set "is_lab_report" to false and return empty \
"meta" (all nulls) and an empty "results" list.
- "raw_line" must be the exact text of that result row as it appears in \
the image, character for character -- never cleaned up, never summarised.
- "raw_value" and "raw_unit" should be the literal substrings you read \
for the value and unit -- do not convert, round, or reformat them here.
- If a field is illegible or absent, use null rather than guessing.
- Never fabricate a row or a field value that is not actually visible \
in the image.
"""


def parse_gemini_response(response_text: str) -> RawExtraction:
    """
    Parses Gemini's raw text response into a RawExtraction. Isolated
    from the network call so this logic is unit-testable on its own.

    Never raises on malformed input -- degrades to is_lab_report=False
    with empty meta/results, consistent with how we handle genuinely
    non-lab-report images (brief point 8: degrade gracefully, don't
    produce garbage).
    """
    cleaned = _strip_markdown_fences(response_text).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return _empty_extraction()

    if not isinstance(data, dict):
        return _empty_extraction()

    is_lab_report = bool(data.get("is_lab_report", False))
    if not is_lab_report:
        return _empty_extraction()

    meta_data = data.get("meta") or {}
    meta = ReportMeta(
        patient_name=meta_data.get("patient_name"),
        age=meta_data.get("age"),
        sex=meta_data.get("sex"),
        report_date=meta_data.get("report_date"),
        lab_name=meta_data.get("lab_name"),
        reference_no=meta_data.get("reference_no"),
    )

    results: list[RawResultRow] = []
    for row in data.get("results") or []:
        if not isinstance(row, dict):
            continue  # skip malformed row rather than crashing the whole response
        # test_name and raw_line are the only fields we treat as
        # required for a row to be usable; skip rows missing either
        # rather than guessing at them.
        if "test_name" not in row or "raw_line" not in row:
            continue
        results.append(
            RawResultRow(
                test_name=row["test_name"],
                raw_value=row.get("raw_value", ""),
                raw_unit=row.get("raw_unit"),
                reference_range=row.get("reference_range"),
                flag=row.get("flag"),
                raw_line=row["raw_line"],
            )
        )

    return RawExtraction(meta=meta, results=results, is_lab_report=True)


def _empty_extraction() -> RawExtraction:
    return RawExtraction(meta=ReportMeta(), results=[], is_lab_report=False)


def _strip_markdown_fences(text: str) -> str:
    # Gemini sometimes wraps JSON in ```json ... ``` despite being asked
    # not to -- strip that defensively rather than failing to parse.
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text


class GeminiExtractionAdapter:
    def __init__(self, api_key: str, model_name: str):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    def extract(self, image_bytes: bytes) -> RawExtraction:
        with tempfile.NamedTemporaryFile(suffix=".image", delete=True) as tmp:
            tmp.write(image_bytes)
            tmp.flush()

            mime_type = mimetypes.guess_type(tmp.name)[0] or "image/jpeg"
            uploaded_file = self._client.files.upload(
                file=tmp.name, config=types.UploadFileConfig(mime_type=mime_type)
            )

            response = self._client.models.generate_content(
                model=self._model_name,
                contents=[_EXTRACTION_PROMPT, uploaded_file],
            )

        return parse_gemini_response(response.text or "")