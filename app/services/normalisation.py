"""
Normalisation of raw OCR/model-extracted strings into canonical forms.

Design (documented here and in README.md):

- Numeric value: parsed to `float` when confidently parseable.
  - Plain numbers: "12.5" -> 12.5
  - Thousands separators: "12,500" -> 12500.0
  - Scientific/multiplier notation: "1.2 x 10^3" -> 1200.0
  - Comparison-prefixed values ("<0.5", ">100"): the prefix cannot be
    collapsed into a single float without losing information (it's a
    bound, not a point value), so these are treated as NOT confidently
    parseable and preserved verbatim in `value` as the original string.
    This is a judgement call: an alternative would be to parse the
    numeric part and carry the comparator separately, but the brief
    requires "a numeric value" for every result while also requiring
    verbatim preservation of anything not confidently parsed -- treating
    comparator-prefixed values as verbatim keeps both promises truthfully
    rather than silently discarding the "<" / ">" semantic.
  - Ranges given as a single "value" field (e.g. "0.8 - 1.2" appearing
    where a point value was expected): NOT parsed to a single float;
    preserved verbatim, since collapsing a range to one number would be
    guessing.
  - Anything else that fails to parse: preserved verbatim, never guessed.

- Unit: lowercased and whitespace-normalised, then passed through a
  small alias table so equivalent spellings collapse to one canonical
  form (e.g. "gm/dl", "Gm/dL", "g/dl" -> "g/dl"). Units not in the alias
  table are kept as-is (lowercased/stripped) rather than rejected --
  we only canonicalise variants we can confidently map, we don't
  invent normalisation for units we don't recognise.

- Date: attempts a fixed list of common lab-report date formats and
  returns ISO 8601 (YYYY-MM-DD) on a confident match. Anything
  ambiguous or unparseable is preserved verbatim.
"""

from __future__ import annotations

import re
from datetime import datetime

# --- Value parsing ----------------------------------------------------------

_SCIENTIFIC_MULTIPLIER_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s*[xX×]\s*10\s*\^?\s*([+-]?\d+)\s*$"
)
_PLAIN_NUMBER_RE = re.compile(r"^\s*([+-]?\d[\d,]*(?:\.\d+)?)\s*$")
_COMPARATOR_RE = re.compile(r"^\s*[<>]=?\s*\d")
_RANGE_HYPHEN_RE = re.compile(r"^\s*[+-]?\d[\d,]*(?:\.\d+)?\s*-\s*[+-]?\d[\d,]*(?:\.\d+)?\s*$")


def normalise_value(raw_value: str) -> float | str:
    """
    Returns a float when raw_value is confidently a single numeric
    point value; otherwise returns raw_value unchanged (verbatim).
    """
    candidate = raw_value.strip()

    # Comparator-prefixed ("<0.5", ">=100") -- not a single point value,
    # preserve verbatim rather than dropping the comparator's meaning.
    if _COMPARATOR_RE.match(candidate):
        return raw_value

    # A hyphenated range showing up where a single value was expected
    # ("0.8 - 1.2") -- ambiguous which end (if either) is meant,
    # preserve verbatim rather than guessing.
    if _RANGE_HYPHEN_RE.match(candidate):
        return raw_value

    # Scientific/multiplier notation: "1.2 x 10^3" -> 1200.0
    sci_match = _SCIENTIFIC_MULTIPLIER_RE.match(candidate)
    if sci_match:
        mantissa, exponent = sci_match.groups()
        try:
            return float(mantissa) * (10 ** int(exponent))
        except ValueError:
            return raw_value

    # Plain number, possibly with thousands separators: "12,500" -> 12500.0
    plain_match = _PLAIN_NUMBER_RE.match(candidate)
    if plain_match:
        try:
            return float(plain_match.group(1).replace(",", ""))
        except ValueError:
            return raw_value

    # Anything else (unexpected symbols, free text, etc.) -- verbatim.
    return raw_value


# --- Unit normalisation ------------------------------------------------------

_UNIT_ALIASES: dict[str, str] = {
    "gm/dl": "g/dl",
    "g/dl": "g/dl",
    "mg/dl": "mg/dl",
    "mmol/l": "mmol/l",
    "10^3/ul": "10^3/µl",
    "10^3/µl": "10^3/µl",
    "10e3/ul": "10^3/µl",
    "ng/ml": "ng/ml",
    "µg/dl": "µg/dl",
    "ug/dl": "µg/dl",
}


def normalise_unit(raw_unit: str | None) -> str | None:
    """
    Returns a canonical unit string for known aliases; otherwise returns
    the input lowercased/stripped unchanged. Returns None if raw_unit is
    None (unit genuinely absent, not the same as unparseable).
    """
    if raw_unit is None:
        return None

    cleaned = raw_unit.strip().lower()
    return _UNIT_ALIASES.get(cleaned, cleaned)


# --- Date normalisation -------------------------------------------------------

_DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
]


def normalise_date(raw_date: str | None) -> str | None:
    """
    Returns an ISO 8601 (YYYY-MM-DD) date string on a confident match
    against a fixed list of common lab-report date formats. Returns the
    original string unchanged if no format matches -- never guesses at
    an ambiguous date (e.g. 01/02/2026 could be Jan 2 or Feb 1;
    day-first is assumed per _DATE_FORMATS ordering, documented here as
    a deliberate choice since the brief gives no locale to disambiguate).
    """
    if raw_date is None:
        return None

    candidate = raw_date.strip()
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(candidate, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return raw_date