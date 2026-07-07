"""
tests/test_parser.py
Unit and property-based tests for voc/parser.py.

Tasks 2.2, 2.5, 2.6, 2.7, 2.8
"""
import pytest
from voc.parser import (
    REQUIRED_COLUMNS,
    ParseResult,
    parse_dea,
    parse_pdd,
    parse_voc_csv,
    validate_header,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_HEADER = ",".join([""] + REQUIRED_COLUMNS)  # leading index column


def _make_csv(*data_rows: str) -> str:
    """Build a minimal valid CSV string from data row strings."""
    return _VALID_HEADER + "\n" + "\n".join(data_rows)


_VALID_ROW = '1,VOC,2026,BICFA,BIC Corporation -- Dropship,202617,"24,708",97.0%,97.0%'


# ---------------------------------------------------------------------------
# validate_header
# ---------------------------------------------------------------------------


class TestValidateHeader:
    def test_all_required_columns_present_returns_empty(self):
        assert validate_header(REQUIRED_COLUMNS) == []

    def test_all_required_plus_extra_column_returns_empty(self):
        assert validate_header(REQUIRED_COLUMNS + ["Extra Column"]) == []

    def test_missing_one_column_returns_that_column(self):
        headers = [c for c in REQUIRED_COLUMNS if c != "DEA %"]
        missing = validate_header(headers)
        assert missing == ["DEA %"]

    def test_missing_two_columns_returns_both_sorted(self):
        headers = [c for c in REQUIRED_COLUMNS if c not in ("DEA %", "Year ID")]
        missing = validate_header(headers)
        assert missing == sorted(["DEA %", "Year ID"])

    def test_empty_header_returns_all_required(self):
        missing = validate_header([])
        assert set(missing) == set(REQUIRED_COLUMNS)

    def test_leading_index_column_accepted(self):
        headers = [""] + REQUIRED_COLUMNS
        assert validate_header(headers) == []


# ---------------------------------------------------------------------------
# parse_pdd
# ---------------------------------------------------------------------------


class TestParsePdd:
    def test_plain_integer(self):
        assert parse_pdd("912") == 912

    def test_comma_formatted(self):
        assert parse_pdd("24,708") == 24708

    def test_zero(self):
        assert parse_pdd("0") == 0

    def test_empty_string_returns_none(self):
        assert parse_pdd("") is None

    def test_whitespace_only_returns_none(self):
        assert parse_pdd("   ") is None

    def test_non_numeric_returns_none(self):
        assert parse_pdd("abc") is None

    def test_decimal_returns_none(self):
        assert parse_pdd("1.5") is None

    def test_negative_returns_none(self):
        assert parse_pdd("-1") is None

    def test_strips_whitespace(self):
        assert parse_pdd("  1,000  ") == 1000


# ---------------------------------------------------------------------------
# parse_dea
# ---------------------------------------------------------------------------


class TestParseDea:
    def test_standard_percentage(self):
        assert parse_dea("97.0%") == pytest.approx(0.97)

    def test_100_percent(self):
        assert parse_dea("100.0%") == pytest.approx(1.0)

    def test_zero_percent(self):
        assert parse_dea("0.0%") == pytest.approx(0.0)

    def test_no_percent_suffix_returns_none(self):
        assert parse_dea("97.0") is None

    def test_non_numeric_returns_none(self):
        assert parse_dea("abc%") is None

    def test_above_100_returns_none(self):
        assert parse_dea("105.0%") is None

    def test_negative_returns_none(self):
        assert parse_dea("-1.0%") is None

    def test_strips_whitespace(self):
        assert parse_dea("  96.8%  ") == pytest.approx(0.968)


# ---------------------------------------------------------------------------
# parse_voc_csv — integration
# ---------------------------------------------------------------------------


class TestParseVocCsv:
    def test_valid_csv_ingests_all_rows(self):
        csv = _make_csv(_VALID_ROW, _VALID_ROW.replace("202617", "202618"))
        result = parse_voc_csv(csv)
        assert result.total_ingested == 2
        assert result.total_skipped == 0
        assert len(result.df) == 2

    def test_missing_columns_raises_value_error(self):
        # CSV missing "DEA %" and "Year ID"
        bad_header = ",".join(
            [c for c in REQUIRED_COLUMNS if c not in ("DEA %", "Year ID")]
        )
        csv = bad_header + "\nBICFA,row\n"
        with pytest.raises(ValueError) as exc_info:
            parse_voc_csv(csv)
        msg = str(exc_info.value)
        assert "DEA %" in msg
        assert "Year ID" in msg

    def test_invalid_pdd_row_is_skipped_with_warning(self):
        bad_row = "2,VOC,2026,BICFA,BIC Corporation -- Dropship,202618,abc,97.0%,97.0%"
        csv = _make_csv(_VALID_ROW, bad_row)
        result = parse_voc_csv(csv)
        assert result.total_ingested == 1
        assert result.total_skipped == 1
        assert any("abc" in w for w in result.warnings)
        assert any("3" in w for w in result.warnings)  # 1-based row 3

    def test_out_of_range_dea_row_is_skipped_with_warning(self):
        bad_row = "2,VOC,2026,BICFA,BIC Corporation -- Dropship,202618,100,105.0%,97.0%"
        csv = _make_csv(_VALID_ROW, bad_row)
        result = parse_voc_csv(csv)
        assert result.total_ingested == 1
        assert result.total_skipped == 1
        assert any("105.0%" in w for w in result.warnings)

    def test_duplicate_vendor_week_keeps_first_warns_rest(self):
        row2 = _VALID_ROW.replace("1,VOC", "2,VOC").replace('"24,708"', "500")
        row3 = _VALID_ROW.replace("1,VOC", "3,VOC").replace('"24,708"', "300")
        csv = _make_csv(_VALID_ROW, row2, row3)
        result = parse_voc_csv(csv)
        assert result.total_ingested == 1
        assert result.total_skipped == 2
        # First row's pdd_shipments should be retained
        assert int(result.df.iloc[0]["pdd_shipments"]) == 24708

    def test_empty_csv_returns_empty_dataframe(self):
        csv = _VALID_HEADER + "\n"
        result = parse_voc_csv(csv)
        assert result.total_ingested == 0
        assert result.week_id_range is None
        assert result.df.empty

    def test_week_id_range_is_correct(self):
        row2 = '2,VOC,2026,BICFA,BIC Corporation -- Dropship,202601,100,95.0%,95.0%'
        row3 = '3,VOC,2026,BICFA,BIC Corporation -- Dropship,202650,200,96.0%,96.0%'
        csv = _make_csv(row2, row3)
        result = parse_voc_csv(csv)
        assert result.week_id_range == (202601, 202650)
