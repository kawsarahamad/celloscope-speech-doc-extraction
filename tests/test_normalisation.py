"""
Tests for app/services/normalisation.py.

Covers every value/unit/date format explicitly called out in the take-
home brief, plus the verbatim-preservation guarantee for anything not
confidently parseable.
"""

from app.services.normalisation import normalise_date, normalise_unit, normalise_value


class TestNormaliseValue:
    def test_plain_decimal(self):
        assert normalise_value("12.5") == 12.5

    def test_plain_integer(self):
        assert normalise_value("42") == 42.0

    def test_thousands_separator(self):
        assert normalise_value("12,500") == 12500.0

    def test_scientific_multiplier_notation(self):
        assert normalise_value("1.2 x 10^3") == 1200.0

    def test_scientific_multiplier_notation_uppercase_x(self):
        assert normalise_value("1.2 X 10^3") == 1200.0

    def test_comparator_less_than_preserved_verbatim(self):
        # Comparator changes the semantic meaning (a bound, not a point
        # value) -- must not be collapsed into a bare float.
        assert normalise_value("<0.5") == "<0.5"

    def test_comparator_greater_equal_preserved_verbatim(self):
        assert normalise_value(">=100") == ">=100"

    def test_range_as_value_preserved_verbatim(self):
        # A range appearing where a single value was expected -- must
        # not guess which end (or midpoint) was intended.
        assert normalise_value("0.8 - 1.2") == "0.8 - 1.2"

    def test_unparseable_text_preserved_verbatim(self):
        assert normalise_value("see note") == "see note"

    def test_never_raises_on_garbage_input(self):
        # Normaliser must degrade gracefully, never throw, on OCR noise.
        result = normalise_value("###@@@")
        assert result == "###@@@"


class TestNormaliseUnit:
    def test_known_alias_gm_dl_to_g_dl(self):
        assert normalise_unit("gm/dl") == "g/dl"

    def test_known_alias_case_insensitive(self):
        assert normalise_unit("GM/DL") == "g/dl"

    def test_already_canonical_unit_unchanged(self):
        assert normalise_unit("mg/dL") == "mg/dl"

    def test_scientific_notation_unit_alias(self):
        assert normalise_unit("10^3/µL") == "10^3/µl"

    def test_unknown_unit_lowercased_but_preserved(self):
        # Not in the alias table -- lowercase/strip only, never invent
        # a mapping we're not confident about.
        assert normalise_unit("Weird/Unit") == "weird/unit"

    def test_none_unit_stays_none(self):
        assert normalise_unit(None) is None


class TestNormaliseDate:
    def test_day_month_year_slash_format(self):
        assert normalise_date("15/01/2026") == "2026-01-15"

    def test_iso_format_passthrough(self):
        assert normalise_date("2026-01-15") == "2026-01-15"

    def test_day_month_name_year_format(self):
        assert normalise_date("15 Jan 2026") == "2026-01-15"

    def test_month_name_day_comma_year_format(self):
        assert normalise_date("January 15, 2026") == "2026-01-15"

    def test_unparseable_date_preserved_verbatim(self):
        assert normalise_date("sometime last week") == "sometime last week"

    def test_none_date_stays_none(self):
        assert normalise_date(None) is None