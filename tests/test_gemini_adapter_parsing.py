"""
Tests for app/adapters/gemini_adapter.py's parse_gemini_response.

These test the JSON-handling logic in isolation from any live network
call to Gemini -- exactly the part of this adapter that can and should
be unit tested.
"""

from app.adapters.gemini_adapter import parse_gemini_response


def test_valid_lab_report_json_parses_correctly():
    response_text = """
    {
      "is_lab_report": true,
      "meta": {
        "patient_name": "Jane Doe",
        "age": "34",
        "sex": "F",
        "report_date": "15/01/2026",
        "lab_name": "Test Lab",
        "reference_no": "REF-1"
      },
      "results": [
        {
          "test_name": "Hemoglobin",
          "raw_value": "12.5",
          "raw_unit": "g/dL",
          "reference_range": "12.0 - 15.5",
          "flag": null,
          "raw_line": "Hemoglobin 12.5 g/dL (12.0-15.5)"
        }
      ]
    }
    """
    result = parse_gemini_response(response_text)

    assert result.is_lab_report is True
    assert result.meta.patient_name == "Jane Doe"
    assert len(result.results) == 1
    assert result.results[0].test_name == "Hemoglobin"
    assert result.results[0].raw_line == "Hemoglobin 12.5 g/dL (12.0-15.5)"


def test_markdown_fenced_json_is_stripped_and_parsed():
    response_text = """```json
    {
      "is_lab_report": true,
      "meta": {"patient_name": "John Smith", "age": null, "sex": null,
                "report_date": null, "lab_name": null, "reference_no": null},
      "results": []
    }
    ```"""
    result = parse_gemini_response(response_text)

    assert result.is_lab_report is True
    assert result.meta.patient_name == "John Smith"
    assert result.results == []


def test_non_lab_report_flag_produces_empty_extraction():
    response_text = """
    {
      "is_lab_report": false,
      "meta": {"patient_name": null, "age": null, "sex": null,
                "report_date": null, "lab_name": null, "reference_no": null},
      "results": []
    }
    """
    result = parse_gemini_response(response_text)

    assert result.is_lab_report is False
    assert result.results == []
    assert result.meta.patient_name is None


def test_completely_malformed_json_degrades_gracefully():
    response_text = "I'm sorry, I cannot process this image."
    result = parse_gemini_response(response_text)

    assert result.is_lab_report is False
    assert result.results == []


def test_empty_string_degrades_gracefully():
    result = parse_gemini_response("")
    assert result.is_lab_report is False


def test_json_array_instead_of_object_degrades_gracefully():
    # Model returned a JSON array rather than the expected object shape.
    result = parse_gemini_response('["not", "the", "right", "shape"]')
    assert result.is_lab_report is False


def test_row_missing_required_fields_is_skipped_not_crashed():
    response_text = """
    {
      "is_lab_report": true,
      "meta": {"patient_name": "Jane Doe", "age": null, "sex": null,
                "report_date": null, "lab_name": null, "reference_no": null},
      "results": [
        {"test_name": "Hemoglobin", "raw_value": "12.5", "raw_unit": "g/dL",
         "reference_range": null, "flag": null, "raw_line": "Hemoglobin 12.5 g/dL"},
        {"raw_value": "missing test_name and raw_line"}
      ]
    }
    """
    result = parse_gemini_response(response_text)

    assert result.is_lab_report is True
    assert len(result.results) == 1  # the malformed second row was skipped
    assert result.results[0].test_name == "Hemoglobin"


def test_missing_raw_unit_defaults_to_none_not_crash():
    response_text = """
    {
      "is_lab_report": true,
      "meta": {"patient_name": null, "age": null, "sex": null,
                "report_date": null, "lab_name": null, "reference_no": null},
      "results": [
        {"test_name": "Glucose", "raw_value": "90", "raw_line": "Glucose 90"}
      ]
    }
    """
    result = parse_gemini_response(response_text)

    assert result.results[0].raw_unit is None
    assert result.results[0].reference_range is None
    assert result.results[0].flag is None