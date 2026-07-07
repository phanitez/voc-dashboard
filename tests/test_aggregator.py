"""
tests/test_aggregator.py
Unit tests for voc/aggregator.py.  Property-based tests in Tasks 4.2–4.13.
"""
import pandas as pd
import pytest

from voc.aggregator import (
    active_vendor_count,
    compute_vendor_metrics,
    compute_weekly_aggregates,
    most_recent_week,
    risk_classification,
    top_vendors_by_pdd,
    volume_weighted_dea,
)


def _df(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# volume_weighted_dea
# ---------------------------------------------------------------------------


class TestVolumeWeightedDea:
    def test_empty_returns_none(self):
        assert volume_weighted_dea(pd.DataFrame(columns=["pdd_shipments", "dea_pct"])) is None

    def test_all_zero_pdd_returns_none(self):
        df = _df([{"pdd_shipments": 0, "dea_pct": 0.9}])
        assert volume_weighted_dea(df) is None

    def test_single_row_returns_that_dea(self):
        df = _df([{"pdd_shipments": 100, "dea_pct": 0.97}])
        assert volume_weighted_dea(df) == pytest.approx(0.97)

    def test_weighted_average(self):
        df = _df([
            {"pdd_shipments": 100, "dea_pct": 0.90},
            {"pdd_shipments": 900, "dea_pct": 1.00},
        ])
        expected = (100 * 0.90 + 900 * 1.00) / 1000
        assert volume_weighted_dea(df) == pytest.approx(expected, abs=1e-9)

    def test_unpadded_column(self):
        df = _df([{"pdd_shipments": 200, "dea_pct": 0.95, "unpadded_dea_pct": 0.85}])
        assert volume_weighted_dea(df, col="unpadded_dea_pct") == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# active_vendor_count
# ---------------------------------------------------------------------------


class TestActiveVendorCount:
    def test_empty_returns_zero(self):
        assert active_vendor_count(pd.DataFrame(columns=["pdd_shipments", "vendor_code"])) == 0

    def test_all_zero_pdd_returns_zero(self):
        df = _df([{"pdd_shipments": 0, "vendor_code": "A"}])
        assert active_vendor_count(df) == 0

    def test_mixed_zero_nonzero(self):
        df = _df([
            {"pdd_shipments": 100, "vendor_code": "A"},
            {"pdd_shipments": 0, "vendor_code": "B"},
            {"pdd_shipments": 50, "vendor_code": "A"},  # duplicate vendor, nonzero
        ])
        assert active_vendor_count(df) == 1  # only "A" is active

    def test_counts_distinct_vendors(self):
        df = _df([
            {"pdd_shipments": 10, "vendor_code": "A"},
            {"pdd_shipments": 20, "vendor_code": "B"},
        ])
        assert active_vendor_count(df) == 2


# ---------------------------------------------------------------------------
# most_recent_week
# ---------------------------------------------------------------------------


class TestMostRecentWeek:
    def test_empty_returns_none(self):
        assert most_recent_week(pd.DataFrame(columns=["week_id"])) is None

    def test_single_row(self):
        df = _df([{"week_id": 202617}])
        assert most_recent_week(df) == 202617

    def test_returns_max(self):
        df = _df([{"week_id": 202601}, {"week_id": 202624}])
        assert most_recent_week(df) == 202624


# ---------------------------------------------------------------------------
# compute_vendor_metrics
# ---------------------------------------------------------------------------


class TestComputeVendorMetrics:
    def _sample_df(self):
        return _df([
            {"vendor_code": "A", "vendor_name": "Alpha", "week_id": 1,
             "pdd_shipments": 100, "dea_pct": 0.90, "unpadded_dea_pct": 0.88, "year_id": 2026},
            {"vendor_code": "B", "vendor_name": "Beta", "week_id": 1,
             "pdd_shipments": 400, "dea_pct": 0.95, "unpadded_dea_pct": 0.93, "year_id": 2026},
        ])

    def test_returns_required_columns(self):
        required = {
            "vendor_code", "vendor_name", "total_pdd", "volume_share_pct",
            "weighted_dea_pct", "weighted_unpadded_dea_pct",
            "weeks_active", "most_recent_week_dea",
        }
        result = compute_vendor_metrics(self._sample_df())
        assert required.issubset(set(result.columns))

    def test_sorted_by_total_pdd_descending(self):
        result = compute_vendor_metrics(self._sample_df())
        assert list(result["vendor_code"]) == ["B", "A"]

    def test_volume_share_sums_to_100(self):
        result = compute_vendor_metrics(self._sample_df())
        assert result["volume_share_pct"].sum() == pytest.approx(100.0, abs=0.1)

    def test_empty_input_returns_empty_with_schema(self):
        df = pd.DataFrame(columns=[
            "vendor_code", "vendor_name", "week_id",
            "pdd_shipments", "dea_pct", "unpadded_dea_pct", "year_id",
        ])
        result = compute_vendor_metrics(df)
        assert result.empty
        assert "vendor_code" in result.columns


# ---------------------------------------------------------------------------
# compute_weekly_aggregates
# ---------------------------------------------------------------------------


class TestComputeWeeklyAggregates:
    def test_empty_returns_correct_schema(self):
        df = pd.DataFrame(columns=["week_id", "pdd_shipments", "dea_pct"])
        result = compute_weekly_aggregates(df)
        assert set(result.columns) == {"week_id", "total_pdd", "weighted_dea_pct"}
        assert result.empty

    def test_sorted_by_week_id_ascending(self):
        df = _df([
            {"week_id": 202603, "pdd_shipments": 100, "dea_pct": 0.90},
            {"week_id": 202601, "pdd_shipments": 50, "dea_pct": 0.95},
        ])
        result = compute_weekly_aggregates(df)
        assert list(result["week_id"]) == [202601, 202603]

    def test_total_pdd_is_sum(self):
        df = _df([
            {"week_id": 1, "pdd_shipments": 200, "dea_pct": 0.9},
            {"week_id": 1, "pdd_shipments": 300, "dea_pct": 0.8},
        ])
        result = compute_weekly_aggregates(df)
        assert int(result.iloc[0]["total_pdd"]) == 500


# ---------------------------------------------------------------------------
# top_vendors_by_pdd
# ---------------------------------------------------------------------------


class TestTopVendorsByPdd:
    def _metrics(self):
        return pd.DataFrame([
            {"vendor_code": "C", "total_pdd": 50, "volume_share_pct": 10},
            {"vendor_code": "A", "total_pdd": 500, "volume_share_pct": 50},
            {"vendor_code": "B", "total_pdd": 200, "volume_share_pct": 40},
        ])

    def test_top_3_correct_order(self):
        result = top_vendors_by_pdd(self._metrics(), n=3)
        assert list(result["vendor_code"]) == ["A", "B", "C"]

    def test_top_2(self):
        result = top_vendors_by_pdd(self._metrics(), n=2)
        assert len(result) == 2
        assert list(result["vendor_code"]) == ["A", "B"]

    def test_empty_input(self):
        result = top_vendors_by_pdd(pd.DataFrame(columns=["vendor_code", "total_pdd"]))
        assert result.empty


# ---------------------------------------------------------------------------
# risk_classification
# ---------------------------------------------------------------------------


class TestRiskClassification:
    def test_below_90_is_below_threshold(self):
        assert risk_classification(0.899) == "below_threshold"
        assert risk_classification(0.0) == "below_threshold"

    def test_90_is_at_risk(self):
        assert risk_classification(0.90) == "at_risk"

    def test_95_is_at_risk(self):
        assert risk_classification(0.95) == "at_risk"

    def test_above_95_is_on_track(self):
        assert risk_classification(0.951) == "on_track"
        assert risk_classification(1.0) == "on_track"
