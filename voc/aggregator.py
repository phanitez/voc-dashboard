"""
voc/aggregator.py
Volume-weighted DEA calculations, vendor metrics, weekly aggregates,
risk classification, and concentration helpers.

All functions are pure Python / Pandas — no Streamlit imports.
"""
from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# Core metric functions
# ---------------------------------------------------------------------------


def volume_weighted_dea(
    df: pd.DataFrame, col: str = "dea_pct"
) -> float | None:
    """
    Compute sum(pdd_shipments * col) / sum(pdd_shipments).

    Result is in fraction space [0.0, 1.0] — the same space as dea_pct.
    Returns None if *df* is empty or if sum(pdd_shipments) == 0.
    """
    if df.empty:
        return None
    denom = df["pdd_shipments"].sum()
    if denom == 0:
        return None
    return float((df["pdd_shipments"] * df[col]).sum() / denom)


def active_vendor_count(df: pd.DataFrame) -> int:
    """
    Count distinct vendor_code values where pdd_shipments > 0.

    Satisfies Property 6: active_vendor_count == nunique of vendor_code
    among rows with pdd_shipments > 0.
    """
    return int(df.loc[df["pdd_shipments"] > 0, "vendor_code"].nunique())


def most_recent_week(df: pd.DataFrame) -> int | None:
    """
    Return df["week_id"].max() as int, or None if *df* is empty.

    Satisfies Property 15: most_recent_week == df["week_id"].max().
    """
    if df.empty:
        return None
    return int(df["week_id"].max())


# ---------------------------------------------------------------------------
# Vendor-level aggregation
# ---------------------------------------------------------------------------


def compute_vendor_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate per-vendor metrics from a filtered record DataFrame.

    Returns a DataFrame with columns:
        vendor_code, vendor_name, total_pdd, volume_share_pct,
        weighted_dea_pct, weighted_unpadded_dea_pct,
        weeks_active, most_recent_week_dea

    Sorted by total_pdd descending (Property 10).

    Notes
    -----
    * weighted_dea_pct and weighted_unpadded_dea_pct are fractions [0, 1].
    * most_recent_week_dea is the dea_pct (fraction) for the highest
      week_id in *df*, or NaN if no record exists for that vendor.
    * volume_share_pct is 0.0 when grand total PDD is 0.
    """
    if df.empty:
        return pd.DataFrame(
            columns=[
                "vendor_code",
                "vendor_name",
                "total_pdd",
                "volume_share_pct",
                "weighted_dea_pct",
                "weighted_unpadded_dea_pct",
                "weeks_active",
                "most_recent_week_dea",
            ]
        )

    # --- total_pdd per vendor ---
    totals = (
        df.groupby(["vendor_code", "vendor_name"], as_index=False)["pdd_shipments"]
        .sum()
        .rename(columns={"pdd_shipments": "total_pdd"})
    )

    # --- weighted DEA per vendor ---
    def _wdea(group: pd.DataFrame, col: str) -> float:
        denom = group["pdd_shipments"].sum()
        if denom == 0:
            return float("nan")
        return float((group["pdd_shipments"] * group[col]).sum() / denom)

    wdea_map = (
        df.groupby("vendor_code")
        .apply(lambda g: _wdea(g, "dea_pct"))
        .reset_index(name="weighted_dea_pct")
    )
    wudea_map = (
        df.groupby("vendor_code")
        .apply(lambda g: _wdea(g, "unpadded_dea_pct"))
        .reset_index(name="weighted_unpadded_dea_pct")
    )

    # --- weeks_active (distinct week_id where pdd_shipments > 0) ---
    weeks_active_map = (
        df[df["pdd_shipments"] > 0]
        .groupby("vendor_code")["week_id"]
        .nunique()
        .reset_index(name="weeks_active")
    )

    # --- most_recent_week_dea ---
    mrw = most_recent_week(df)
    if mrw is not None:
        mrw_rows = df[df["week_id"] == mrw][["vendor_code", "dea_pct"]].rename(
            columns={"dea_pct": "most_recent_week_dea"}
        )
        # If a vendor has multiple rows for the most recent week (shouldn't
        # happen after dedup, but be safe), take the first.
        mrw_rows = mrw_rows.drop_duplicates(subset=["vendor_code"])
    else:
        mrw_rows = pd.DataFrame(columns=["vendor_code", "most_recent_week_dea"])

    # --- merge everything ---
    result = totals.copy()
    result = result.merge(wdea_map, on="vendor_code", how="left")
    result = result.merge(wudea_map, on="vendor_code", how="left")
    result = result.merge(weeks_active_map, on="vendor_code", how="left")
    result = result.merge(mrw_rows, on="vendor_code", how="left")

    # Fill NaN weeks_active (vendors with all-zero PDD)
    result["weeks_active"] = result["weeks_active"].fillna(0).astype("int64")

    # --- volume_share_pct ---
    grand_total = int(result["total_pdd"].sum())
    if grand_total > 0:
        result["volume_share_pct"] = result["total_pdd"] / grand_total * 100.0
    else:
        result["volume_share_pct"] = 0.0

    # --- sort by total_pdd descending ---
    result = result.sort_values("total_pdd", ascending=False).reset_index(drop=True)

    return result


# ---------------------------------------------------------------------------
# Weekly aggregation
# ---------------------------------------------------------------------------


def compute_weekly_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate weekly totals across all vendors.

    Returns a DataFrame with columns:
        week_id  (int64, sorted ascending)
        total_pdd  (int64)
        weighted_dea_pct  (float64, fraction 0–1)

    Returns an empty DataFrame with the correct schema if *df* is empty.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["week_id", "total_pdd", "weighted_dea_pct"]
        ).astype({"week_id": "int64", "total_pdd": "int64", "weighted_dea_pct": "float64"})

    def _week_agg(group: pd.DataFrame) -> pd.Series:
        denom = group["pdd_shipments"].sum()
        wdea = (
            float((group["pdd_shipments"] * group["dea_pct"]).sum() / denom)
            if denom > 0
            else float("nan")
        )
        return pd.Series(
            {"total_pdd": int(denom), "weighted_dea_pct": wdea}
        )

    weekly = (
        df.groupby("week_id")
        .apply(_week_agg)
        .reset_index()
        .sort_values("week_id")
        .reset_index(drop=True)
    )
    weekly["week_id"] = weekly["week_id"].astype("int64")
    weekly["total_pdd"] = weekly["total_pdd"].astype("int64")
    return weekly


# ---------------------------------------------------------------------------
# Concentration helpers
# ---------------------------------------------------------------------------


def top_vendors_by_pdd(
    vendor_metrics_df: pd.DataFrame, n: int = 3
) -> pd.DataFrame:
    """
    Return the top-N rows by total_pdd.

    Ties are broken by vendor_code lexicographic ascending (Property 7).
    Returns an empty DataFrame (with correct columns) when input has < n rows.
    """
    if vendor_metrics_df.empty:
        return vendor_metrics_df.copy()

    sorted_df = vendor_metrics_df.sort_values(
        ["total_pdd", "vendor_code"], ascending=[False, True]
    )
    return sorted_df.head(n).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------


def risk_classification(dea_fraction: float) -> str:
    """
    Classify a DEA fraction [0.0, 1.0] into one of three risk tiers.

    Returns
    -------
    "below_threshold"  when dea_fraction < 0.90
    "at_risk"          when 0.90 <= dea_fraction <= 0.95
    "on_track"         when dea_fraction > 0.95

    Satisfies Property 16: exhaustive and mutually exclusive over [0, 1].
    """
    if dea_fraction < 0.90:
        return "below_threshold"
    if dea_fraction <= 0.95:
        return "at_risk"
    return "on_track"
