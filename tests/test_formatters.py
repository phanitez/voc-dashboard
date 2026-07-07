"""
tests/test_formatters.py
Unit tests for voc/formatters.py.  Property-based test in Task 8.2.
"""
import re
from datetime import datetime

import pytest

from voc.formatters import export_filename, format_dea, format_pdd, format_timestamp


class TestFormatPdd:
    def test_zero(self):
        assert format_pdd(0) == "0"

    def test_below_thousand(self):
        assert format_pdd(999) == "999"

    def test_exactly_thousand(self):
        assert format_pdd(1000) == "1,000"

    def test_large_number(self):
        assert format_pdd(1000000) == "1,000,000"

    def test_24708(self):
        assert format_pdd(24708) == "24,708"

    def test_no_decimal_point(self):
        assert "." not in format_pdd(24708)


class TestFormatDea:
    def test_zero(self):
        assert format_dea(0.0) == "0.0%"

    def test_97_percent(self):
        assert format_dea(0.97) == "97.0%"

    def test_100_percent(self):
        assert format_dea(1.0) == "100.0%"

    def test_one_decimal_place(self):
        # 0.9683 → 96.8%
        result = format_dea(0.9683)
        assert result == "96.8%"

    def test_matches_regex(self):
        pattern = re.compile(r"^\d+\.\d%$")
        for val in [0.0, 0.5, 0.9, 1.0, 0.123]:
            assert pattern.match(format_dea(val)), f"format_dea({val}) = {format_dea(val)!r}"


class TestFormatTimestamp:
    def test_format(self):
        dt = datetime(2026, 6, 6, 14, 30, 0)
        assert format_timestamp(dt) == "2026-06-06 14:30:00"

    def test_zero_seconds(self):
        dt = datetime(2026, 1, 1, 0, 0, 0)
        assert format_timestamp(dt) == "2026-01-01 00:00:00"


class TestExportFilename:
    def test_format(self):
        dt = datetime(2026, 6, 6, 14, 30, 0)
        assert export_filename(dt) == "VOC_Export_20260606_143000.csv"

    def test_ends_with_csv(self):
        dt = datetime(2026, 1, 1, 0, 0, 0)
        assert export_filename(dt).endswith(".csv")
