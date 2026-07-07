"""
tests/test_filters.py
Unit tests for voc/filters.py.  Property-based tests in Tasks 6.2–6.7.
"""
import pandas as pd
import pytest

from voc.filters import apply_filters, filter_vendors_by_search, validate_week_range


def _raw_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"vendor_code": "BICFA", "vendor_name": "BIC Corp", "year_id": 2026, "week_id": 202601, "pdd_shipments": 100, "dea_pct": 0.97},
        {"vendor_code": "YX74K", "vendor_name": "Geneva Supply", "year_id": 2026, "week_id": 202601, "pdd_shipments": 50, "dea_pct": 0.90},
        {"vendor_code": "BICFA", "vendor_name": "BIC Corp", "year_id": 2026, "week_id": 202602, "pdd_shipments": 80, "dea_pct": 0.95},
    ])


# ---------------------------------------------------------------------------
# validate_week_range
# ---------------------------------------------------------------------------


class TestValidateWeekRange:
    def test_none_none_returns_none(self):
        assert validate_week_range(None, None) is None

    def test_none_end_returns_none(self):
        assert validate_week_range(None, 202610) is None

    def test_start_none_returns_none(self):
        assert validate_week_range(202601, None) is None

    def test_start_equal_end_returns_none(self):
        assert validate_week_range(202605, 202605) is None

    def test_start_less_than_end_returns_none(self):
        assert validate_week_range(202601, 202624) is None

    def test_start_greater_than_end_returns_error_string(self):
        result = validate_week_range(202610, 202605)
        assert result is not None
        assert len(result) > 0

    def test_error_message_is_descriptive(self):
        result = validate_week_range(5, 3)
        assert "week" in result.lower() or "start" in result.lower()


# ---------------------------------------------------------------------------
# apply_filters
# ---------------------------------------------------------------------------


class TestApplyFilters:
    def test_all_none_returns_full_dataset(self):
        df = _raw_df()
        result = apply_filters(df, vendors=[], year=None, week_start=None, week_end=None)
        assert len(result) == len(df)

    def test_vendor_filter_single(self):
        df = _raw_df()
        result = apply_filters(df, vendors=["BICFA"], year=None, week_start=None, week_end=None)
        assert all(result["vendor_code"] == "BICFA")
        assert len(result) == 2

    def test_year_filter(self):
        df = _raw_df()
        result = apply_filters(df, vendors=[], year=2026, week_start=None, week_end=None)
        assert len(result) == 3  # all rows are 2026

    def test_week_start_filter(self):
        df = _raw_df()
        result = apply_filters(df, vendors=[], year=None, week_start=202602, week_end=None)
        assert all(result["week_id"] >= 202602)

    def test_week_end_filter(self):
        df = _raw_df()
        result = apply_filters(df, vendors=[], year=None, week_start=None, week_end=202601)
        assert all(result["week_id"] <= 202601)

    def test_week_range_start_equals_end(self):
        df = _raw_df()
        result = apply_filters(df, vendors=[], year=None, week_start=202601, week_end=202601)
        assert all(result["week_id"] == 202601)
        assert len(result) == 2

    def test_combined_vendor_and_week_filter(self):
        df = _raw_df()
        result = apply_filters(df, vendors=["BICFA"], year=None, week_start=202602, week_end=202602)
        assert len(result) == 1
        assert result.iloc[0]["vendor_code"] == "BICFA"
        assert result.iloc[0]["week_id"] == 202602

    def test_does_not_mutate_original(self):
        df = _raw_df()
        original_len = len(df)
        apply_filters(df, vendors=["BICFA"], year=None, week_start=None, week_end=None)
        assert len(df) == original_len

    def test_no_matching_rows_returns_empty(self):
        df = _raw_df()
        result = apply_filters(df, vendors=["NONEXISTENT"], year=None, week_start=None, week_end=None)
        assert result.empty


# ---------------------------------------------------------------------------
# filter_vendors_by_search
# ---------------------------------------------------------------------------


class TestFilterVendorsBySearch:
    def _vendor_metrics(self):
        return pd.DataFrame([
            {"vendor_code": "BICFA", "vendor_name": "BIC Corporation -- Dropship"},
            {"vendor_code": "YX74K", "vendor_name": "Geneva Supply Inc. -- Dropship"},
        ])

    def test_empty_search_returns_all(self):
        df = self._vendor_metrics()
        result = filter_vendors_by_search(df, "")
        assert len(result) == 2

    def test_case_insensitive_match_on_code(self):
        df = self._vendor_metrics()
        result = filter_vendors_by_search(df, "bicfa")
        assert len(result) == 1
        assert result.iloc[0]["vendor_code"] == "BICFA"

    def test_case_insensitive_match_on_name(self):
        df = self._vendor_metrics()
        result = filter_vendors_by_search(df, "geneva")
        assert len(result) == 1
        assert result.iloc[0]["vendor_code"] == "YX74K"

    def test_no_match_returns_empty(self):
        df = self._vendor_metrics()
        result = filter_vendors_by_search(df, "zzznomatch")
        assert result.empty

    def test_partial_match(self):
        df = self._vendor_metrics()
        result = filter_vendors_by_search(df, "dropship")
        assert len(result) == 2  # both have "Dropship" in vendor_name
