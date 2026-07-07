"""
voc/filters.py
Filter engine: apply active filter state to a raw DataFrame,
validate week ranges, and search vendor metrics tables.

All functions are pure Python / Pandas — no Streamlit imports.
"""
from __future__ import annotations

import pandas as pd


def validate_week_range(
    week_start: int | None, week_end: int | None
) -> str | None:
    """
    Validate a Week ID range.

    Returns an error message string when both arguments are non-None and
    week_start > week_end.  Returns None in all other cases (valid or
    unconstrained range).

    Satisfies Property 14: rejects start > end, accepts start <= end or None.
    """
    if week_start is not None and week_end is not None:
        if week_start > week_end:
            return "Start week must be less than or equal to end week."
    return None


def apply_filters(
    df: pd.DataFrame,
    vendors: list[str],
    year: int | None,
    week_start: int | None,
    week_end: int | None,
) -> pd.DataFrame:
    """
    Apply all active filters to *df*.

    Returns a filtered copy (never mutates the input DataFrame).

    Filter logic (all conditions are AND-combined):
    1. vendors: if non-empty, keep only rows where vendor_code is in vendors.
    2. year:    if not None, keep only rows where year_id == year.
    3. week_start: if not None, keep only rows where week_id >= week_start.
    4. week_end:   if not None, keep only rows where week_id <= week_end.

    Satisfies Properties 12 (compositional correctness) and 13 (clear = full set).
    """
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    mask = pd.Series(True, index=df.index)

    if vendors:
        mask &= df["vendor_code"].isin(vendors)
    if year is not None:
        mask &= df["year_id"] == year
    if week_start is not None:
        mask &= df["week_id"] >= week_start
    if week_end is not None:
        mask &= df["week_id"] <= week_end

    return df[mask].copy()


def filter_vendors_by_search(
    vendor_metrics_df: pd.DataFrame, search: str
) -> pd.DataFrame:
    """
    Return rows from *vendor_metrics_df* where vendor_code or vendor_name
    contains *search* (case-insensitive substring match).

    An empty search string returns all rows unchanged.

    Satisfies Property 11: strict subset with case-insensitive containment.
    """
    if not search:
        return vendor_metrics_df.copy()

    s = search.lower()
    mask = vendor_metrics_df["vendor_code"].str.lower().str.contains(
        s, na=False, regex=False
    ) | vendor_metrics_df["vendor_name"].str.lower().str.contains(
        s, na=False, regex=False
    )
    return vendor_metrics_df[mask].reset_index(drop=True)
