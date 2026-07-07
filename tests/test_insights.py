"""
tests/test_insights.py
Unit tests for voc/insights.py.  Property-based tests in Tasks 10.3, 10.5, 10.7.
"""
import pandas as pd
import pytest

from voc.insights import (
    dea_decliners,
    generate_insights,
    preceding_week,
    rank_vendors_by_dea,
    volume_changers,
)


def _week_df(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# preceding_week
# ---------------------------------------------------------------------------


class TestPrecedingWeek:
    def test_returns_max_strictly_less_than_target(self):
        assert preceding_week([202601, 202603, 202605], 202605) == 202603

    def test_two_weeks_gap(self):
        assert preceding_week([202601, 202603], 202603) == 202601

    def test_single_element_equal_to_target_returns_none(self):
        assert preceding_week([202601], 202601) is None

    def test_empty_list_returns_none(self):
        assert preceding_week([], 202601) is None

    def test_no_week_less_than_target_returns_none(self):
        assert preceding_week([202605, 202610], 202601) is None


# ---------------------------------------------------------------------------
# rank_vendors_by_dea
# ---------------------------------------------------------------------------


class TestRankVendorsByDea:
    def test_sorted_by_dea_descending(self):
        df = _week_df([
            {"vendor_code": "A", "vendor_name": "Alpha", "dea_pct": 0.90, "pdd_shipments": 100},
            {"vendor_code": "B", "vendor_name": "Beta", "dea_pct": 0.95, "pdd_shipments": 50},
        ])
        result = rank_vendors_by_dea(df)
        assert list(result["vendor_code"]) == ["B", "A"]

    def test_tiebreaker_is_pdd_descending(self):
        df = _week_df([
            {"vendor_code": "A", "vendor_name": "Alpha", "dea_pct": 0.97, "pdd_shipments": 50},
            {"vendor_code": "B", "vendor_name": "Beta", "dea_pct": 0.97, "pdd_shipments": 200},
        ])
        result = rank_vendors_by_dea(df)
        assert result.iloc[0]["vendor_code"] == "B"  # higher PDD wins tie


# ---------------------------------------------------------------------------
# dea_decliners
# ---------------------------------------------------------------------------


class TestDeaDecliners:
    def _make_week(self, vendor_code, dea):
        return _week_df([
            {"vendor_code": vendor_code, "vendor_name": f"Vendor {vendor_code}",
             "dea_pct": dea, "pdd_shipments": 100}
        ])

    def test_delta_exactly_005_not_included(self):
        # Strictly > 0.05 required; exactly 0.05 must NOT be included
        current = self._make_week("A", 0.90)  # prior 0.95, delta = 0.05
        prior = self._make_week("A", 0.95)
        result = dea_decliners(current, prior)
        assert len(result) == 0

    def test_delta_over_005_is_included(self):
        current = self._make_week("A", 0.899)  # prior 0.95, delta ≈ 0.051
        prior = self._make_week("A", 0.95)
        result = dea_decliners(current, prior)
        assert len(result) == 1
        assert result[0]["vendor_code"] == "A"

    def test_empty_prior_returns_empty(self):
        current = self._make_week("A", 0.80)
        result = dea_decliners(current, pd.DataFrame())
        assert result == []

    def test_vendor_only_in_current_excluded(self):
        current = _week_df([
            {"vendor_code": "A", "vendor_name": "Alpha", "dea_pct": 0.80, "pdd_shipments": 100},
            {"vendor_code": "B", "vendor_name": "Beta", "dea_pct": 0.70, "pdd_shipments": 50},
        ])
        prior = self._make_week("A", 0.95)  # only A in prior
        result = dea_decliners(current, prior)
        # B is not in prior, so B is excluded
        assert all(d["vendor_code"] == "A" for d in result)


# ---------------------------------------------------------------------------
# volume_changers
# ---------------------------------------------------------------------------


class TestVolumeChangers:
    def test_prior_zero_pdd_excluded(self):
        current = _week_df([{"vendor_code": "A", "vendor_name": "Alpha", "pdd_shipments": 100}])
        prior = _week_df([{"vendor_code": "A", "pdd_shipments": 0}])
        result = volume_changers(current, prior)
        assert result == []

    def test_increase_over_20_percent(self):
        current = _week_df([{"vendor_code": "A", "vendor_name": "Alpha", "pdd_shipments": 130}])
        prior = _week_df([{"vendor_code": "A", "pdd_shipments": 100}])
        result = volume_changers(current, prior)
        assert len(result) == 1
        assert result[0]["direction"] == "increase"
        assert result[0]["change_pct"] == 30.0

    def test_decrease_over_20_percent(self):
        current = _week_df([{"vendor_code": "A", "vendor_name": "Alpha", "pdd_shipments": 70}])
        prior = _week_df([{"vendor_code": "A", "pdd_shipments": 100}])
        result = volume_changers(current, prior)
        assert len(result) == 1
        assert result[0]["direction"] == "decrease"

    def test_exactly_20_percent_not_included(self):
        current = _week_df([{"vendor_code": "A", "vendor_name": "Alpha", "pdd_shipments": 120}])
        prior = _week_df([{"vendor_code": "A", "pdd_shipments": 100}])
        result = volume_changers(current, prior)
        assert len(result) == 0  # exactly 20% is not > 20%

    def test_empty_prior_returns_empty(self):
        current = _week_df([{"vendor_code": "A", "vendor_name": "Alpha", "pdd_shipments": 500}])
        result = volume_changers(current, pd.DataFrame())
        assert result == []


# ---------------------------------------------------------------------------
# generate_insights
# ---------------------------------------------------------------------------


class TestGenerateInsights:
    def _sample_df(self):
        return pd.DataFrame([
            {"vendor_code": "A", "vendor_name": "Alpha", "week_id": 202601,
             "pdd_shipments": 100, "dea_pct": 0.97, "unpadded_dea_pct": 0.97},
            {"vendor_code": "B", "vendor_name": "Beta", "week_id": 202601,
             "pdd_shipments": 50, "dea_pct": 0.80, "unpadded_dea_pct": 0.80},
            {"vendor_code": "A", "vendor_name": "Alpha", "week_id": 202602,
             "pdd_shipments": 90, "dea_pct": 0.75, "unpadded_dea_pct": 0.75},
        ])

    def test_raises_for_missing_week(self):
        df = self._sample_df()
        with pytest.raises(ValueError):
            generate_insights(df, week_id=202699)

    def test_returns_three_paragraphs(self):
        df = self._sample_df()
        result = generate_insights(df, week_id=202602)
        assert len(result.paragraphs) == 3

    def test_has_prior_week_note_false_when_prior_exists(self):
        df = self._sample_df()
        result = generate_insights(df, week_id=202602)
        # paragraph indices: 1 = dea-decline, 2 = volume-change
        assert result.paragraphs[1].has_prior_week_note is False

    def test_has_prior_week_note_true_when_no_prior(self):
        df = self._sample_df()
        result = generate_insights(df, week_id=202601)
        # No week before 202601 → prior week note
        assert result.paragraphs[1].has_prior_week_note is True
        assert result.paragraphs[2].has_prior_week_note is True

    def test_week_id_in_result(self):
        df = self._sample_df()
        result = generate_insights(df, week_id=202602)
        assert result.week_id == 202602

    def test_generated_at_is_formatted(self):
        import re
        df = self._sample_df()
        result = generate_insights(df, week_id=202601)
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result.generated_at)
