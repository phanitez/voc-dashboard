"""
voc/insights.py
Rule-based narrative insight generation for weekly VOC performance.

All functions are pure Python / Pandas — no Streamlit imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class InsightParagraph:
    """A single narrative paragraph in an InsightResult."""

    type: str  # 'top-performers' | 'dea-decline' | 'volume-change'
    text: str
    has_prior_week_note: bool = False


@dataclass
class InsightResult:
    """The full set of narrative insights for one selected week."""

    week_id: int
    generated_at: str  # "YYYY-MM-DD HH:MM:SS" local time
    paragraphs: list[InsightParagraph] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def preceding_week(
    all_week_ids: list[int], target_week_id: int
) -> int | None:
    """
    Return the largest value in *all_week_ids* that is strictly less than
    *target_week_id*.  Returns None if no such value exists.
    """
    candidates = [w for w in all_week_ids if w < target_week_id]
    return max(candidates) if candidates else None


def rank_vendors_by_dea(week_df: pd.DataFrame) -> pd.DataFrame:
    """
    Sort *week_df* by dea_pct descending, then pdd_shipments descending
    as a stable tiebreaker.

    Satisfies Property 19.
    """
    return week_df.sort_values(
        ["dea_pct", "pdd_shipments"], ascending=[False, False], kind="stable"
    ).reset_index(drop=True)


def dea_decliners(
    current_week_df: pd.DataFrame,
    prior_week_df: pd.DataFrame,
) -> list[dict]:
    """
    Return vendors whose DEA % declined by more than 5 percentage points
    compared to the prior week.

    Each result dict contains:
        vendor_code, vendor_name, current_dea, prior_dea, delta

    where delta = prior_dea - current_dea (both fractions; > 0.05 to qualify).

    Vendors present in only one of the two weeks are excluded.
    Satisfies Property 17 (strictly greater than 0.05).
    """
    if prior_week_df.empty:
        return []

    merged = current_week_df[["vendor_code", "vendor_name", "dea_pct"]].merge(
        prior_week_df[["vendor_code", "dea_pct"]].rename(
            columns={"dea_pct": "prior_dea_pct"}
        ),
        on="vendor_code",
        how="inner",
    )

    results = []
    for row in merged.itertuples(index=False):
        delta = row.prior_dea_pct - row.dea_pct  # both fractions
        if delta > 0.05:  # strictly greater than 5 pp
            results.append(
                {
                    "vendor_code": row.vendor_code,
                    "vendor_name": row.vendor_name,
                    "current_dea": row.dea_pct,
                    "prior_dea": row.prior_dea_pct,
                    "delta": delta,
                }
            )
    return results


def volume_changers(
    current_week_df: pd.DataFrame,
    prior_week_df: pd.DataFrame,
) -> list[dict]:
    """
    Return vendors whose PDD shipment count changed by more than 20%
    compared to the prior week.

    Each result dict contains:
        vendor_code, vendor_name, direction ('increase'|'decrease'), change_pct

    Vendors with pdd_prior == 0 are excluded (no baseline).
    Satisfies Property 18.
    """
    if prior_week_df.empty:
        return []

    merged = current_week_df[["vendor_code", "vendor_name", "pdd_shipments"]].merge(
        prior_week_df[["vendor_code", "pdd_shipments"]].rename(
            columns={"pdd_shipments": "prior_pdd"}
        ),
        on="vendor_code",
        how="inner",
    )

    results = []
    for row in merged.itertuples(index=False):
        if row.prior_pdd == 0:
            continue
        ratio = abs(row.pdd_shipments - row.prior_pdd) / row.prior_pdd
        if ratio > 0.20:
            direction = "increase" if row.pdd_shipments > row.prior_pdd else "decrease"
            change_pct = round(ratio * 100, 1)
            results.append(
                {
                    "vendor_code": row.vendor_code,
                    "vendor_name": row.vendor_name,
                    "direction": direction,
                    "change_pct": change_pct,
                }
            )
    return results


# ---------------------------------------------------------------------------
# Main insight generator
# ---------------------------------------------------------------------------


def generate_insights(df: pd.DataFrame, week_id: int) -> InsightResult:
    """
    Generate narrative InsightResult for *week_id* within *df*.

    Paragraphs produced:
      1. Top-3 performing vendors by DEA % (ties broken by PDD descending).
      2. Vendors with DEA decline > 5 pp vs. prior week.
      3. Vendors with PDD volume change > 20% vs. prior week.

    Paragraphs 2 and 3 include a prior-week note when no preceding week
    exists in the dataset.

    Raises
    ------
    ValueError
        If *week_id* is not present in *df*.
    """
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    label = f"[Week {week_id} | Generated: {generated_at}]"

    current = df[df["week_id"] == week_id]
    if current.empty:
        raise ValueError(f"No data found for week_id {week_id}.")

    all_week_ids = sorted(df["week_id"].unique().tolist())
    prior_id = preceding_week(all_week_ids, week_id)
    prior = df[df["week_id"] == prior_id] if prior_id is not None else pd.DataFrame()
    has_prior_note = prior_id is None

    paragraphs: list[InsightParagraph] = []

    # --- Paragraph 1: Top 3 performers ---
    ranked = rank_vendors_by_dea(current).head(3)
    if ranked.empty:
        top_text = f"{label}\nNo vendor data available for this week."
    else:
        names = ", ".join(
            f"{r.vendor_name} ({r.dea_pct * 100:.1f}%)"
            for r in ranked.itertuples(index=False)
        )
        top_text = (
            f"{label}\n"
            f"Top performing vendors by DEA % in Week {week_id}: {names}."
        )
    paragraphs.append(
        InsightParagraph(type="top-performers", text=top_text, has_prior_week_note=False)
    )

    # --- Paragraph 2: DEA decliners ---
    decliners = dea_decliners(current, prior)
    if has_prior_note:
        decline_text = (
            f"{label}\n"
            f"DEA % week-over-week comparison: Prior-week comparison data is unavailable."
        )
    elif not decliners:
        decline_text = (
            f"{label}\n"
            f"No vendors experienced a DEA % decline of more than 5 percentage points "
            f"compared to Week {prior_id}."
        )
    else:
        parts = ", ".join(
            f"{d['vendor_name']} (−{d['delta'] * 100:.1f} pp)"
            for d in decliners
        )
        decline_text = (
            f"{label}\n"
            f"Vendors with DEA % decline > 5 pp vs. Week {prior_id}: {parts}."
        )
    paragraphs.append(
        InsightParagraph(
            type="dea-decline",
            text=decline_text,
            has_prior_week_note=has_prior_note,
        )
    )

    # --- Paragraph 3: Volume changers ---
    changers = volume_changers(current, prior)
    if has_prior_note:
        volume_text = (
            f"{label}\n"
            f"PDD volume week-over-week comparison: Prior-week comparison data is unavailable."
        )
    elif not changers:
        volume_text = (
            f"{label}\n"
            f"No vendors experienced a PDD shipment volume change of more than 20% "
            f"compared to Week {prior_id}."
        )
    else:
        parts = ", ".join(
            f"{c['vendor_name']} ({c['direction']} {c['change_pct']}%)"
            for c in changers
        )
        volume_text = (
            f"{label}\n"
            f"Vendors with PDD volume change > 20% vs. Week {prior_id}: {parts}."
        )
    paragraphs.append(
        InsightParagraph(
            type="volume-change",
            text=volume_text,
            has_prior_week_note=has_prior_note,
        )
    )

    return InsightResult(
        week_id=week_id,
        generated_at=generated_at,
        paragraphs=paragraphs,
    )
