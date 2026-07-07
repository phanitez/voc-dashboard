"""
voc/formatters.py
Number and timestamp formatting helpers for display and export.

All functions are pure Python — no Streamlit or Pandas imports.
"""
from __future__ import annotations

from datetime import datetime


def format_pdd(value: int) -> str:
    """
    Format an integer PDD shipment count with thousands separators.

    Examples
    --------
    >>> format_pdd(24708)
    '24,708'
    >>> format_pdd(999)
    '999'
    >>> format_pdd(0)
    '0'

    Satisfies Property 21 (PDD clause).
    """
    return f"{value:,}"


def format_dea(fraction: float) -> str:
    """
    Format a DEA fraction [0.0, 1.0] as a percentage string with one decimal.

    Examples
    --------
    >>> format_dea(0.970)
    '97.0%'
    >>> format_dea(1.0)
    '100.0%'
    >>> format_dea(0.0)
    '0.0%'

    Satisfies Property 21 (DEA clause): result matches r'^\\d+\\.\\d%$'.
    """
    return f"{fraction * 100:.1f}%"


def format_timestamp(dt: datetime) -> str:
    """
    Format a datetime to "YYYY-MM-DD HH:MM:SS" using local time.

    Examples
    --------
    >>> from datetime import datetime
    >>> format_timestamp(datetime(2026, 6, 6, 14, 30, 0))
    '2026-06-06 14:30:00'
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def export_filename(dt: datetime) -> str:
    """
    Return an export filename in the pattern "VOC_Export_YYYYMMDD_HHMMSS.csv".

    Examples
    --------
    >>> export_filename(datetime(2026, 6, 6, 14, 30, 0))
    'VOC_Export_20260606_143000.csv'
    """
    return dt.strftime("VOC_Export_%Y%m%d_%H%M%S.csv")
