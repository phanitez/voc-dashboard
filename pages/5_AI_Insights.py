"""
pages/5_AI_Insights.py
AI Insights — rule-based weekly narrative observations and filtered CSV export.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from voc.ui import inject_dark_css

from voc.aggregator import most_recent_week
from voc.export import export_filename, generate_export_bytes
from voc.filters import apply_filters
from voc.formatters import format_dea, format_pdd
from voc.insights import generate_insights

# ── WBR Narrative Generator ────────────────────────────────────────────────
def _wbr_narrative(df: pd.DataFrame, week_id: int, total_df_shipments: int = 0) -> tuple[str, str]:
    """
    Generate the two-paragraph WBR volume narrative for a given week.
    Returns (paragraph1, paragraph2) as plain strings.
    """
    wk_num = week_id % 100

    all_weeks = sorted(df["week_id"].unique().tolist())
    prior_candidates = [w for w in all_weeks if w < week_id]
    prior_id   = max(prior_candidates) if prior_candidates else None
    prior_wk   = prior_id % 100 if prior_id else None

    curr_df    = df[df["week_id"] == week_id]
    prior_df   = df[df["week_id"] == prior_id] if prior_id is not None else pd.DataFrame()

    curr_total = int(curr_df["pdd_shipments"].sum())
    prior_total= int(prior_df["pdd_shipments"].sum()) if not prior_df.empty else 0

    def _k(v: int) -> str:
        return f"{v/1000:.1f}K" if v >= 1000 else str(v)

    # ── DF share ──────────────────────────────────────────────────────────
    if total_df_shipments > 0:
        df_share = f"{curr_total / total_df_shipments * 100:.1f}%"
    else:
        df_share = "less than 1%"

    # ── WoW deltas ────────────────────────────────────────────────────────
    if prior_id and prior_total > 0:
        delta     = curr_total - prior_total
        delta_pct = delta / prior_total * 100
        sign      = "+" if delta >= 0 else ""
        direction = "increase" if delta >= 0 else "decrease"

        # Driver: top 2 vendors by absolute volume change
        merged = (
            curr_df[["vendor_code", "vendor_name", "pdd_shipments"]]
            .merge(
                prior_df[["vendor_code", "pdd_shipments"]]
                .rename(columns={"pdd_shipments": "prior_pdd"}),
                on="vendor_code", how="outer",
            )
            .fillna(0)
        )
        merged["delta_vol"] = merged["pdd_shipments"] - merged["prior_pdd"]

        def _display_name(n: str) -> str:
            return n.split("--")[0].strip()

        def _short_name(n: str) -> str:
            clean = _display_name(n)
            for sfx in [" Inc.", " Inc", " LLC", " Corporation", " Corp.", " Corp", " Co."]:
                clean = clean.replace(sfx, "")
            return clean.strip().split()[0]  # first word only

        if delta >= 0:
            top_movers = merged.nlargest(2, "delta_vol")
            parts = []
            for _, r in top_movers.iterrows():
                if r["delta_vol"] > 0:
                    verb = "a rebound in" if r["prior_pdd"] > 0 else "new volume from"
                    parts.append(f"{verb} {_display_name(r['vendor_name'])} shipments")
            driver = " and ".join(parts) if parts else "broad fleet volume recovery"
        else:
            top_movers = merged.nsmallest(2, "delta_vol")
            parts = []
            for _, r in top_movers.iterrows():
                if r["delta_vol"] < 0:
                    parts.append(f"a decline in {_display_name(r['vendor_name'])} shipments")
            driver = " and ".join(parts) if parts else "broad fleet volume reduction"

        p1 = (
            f"In WK-{wk_num:02d}, VOC shipped {_k(curr_total)} shipments "
            f"(Approx {sign}{_k(abs(delta))} or {sign}{abs(delta_pct):.1f}%) "
            f"versus WK-{prior_wk:02d} ({_k(prior_total)}), representing approximately "
            f"{df_share} of total DF volume. "
            f"The WoW {direction} reflects {driver}. "
            f"VOC continues to remain a tightly governed capability-gap solution, "
            f"contributing to less than 1% of overall DF volume."
        )
    else:
        p1 = (
            f"In WK-{wk_num:02d}, VOC shipped {_k(curr_total)} shipments. "
            f"No prior week is available for comparison. "
            f"VOC continues to remain a tightly governed capability-gap solution, "
            f"contributing to less than 1% of overall DF volume."
        )

    # ── Vendor concentration ──────────────────────────────────────────────
    curr_v = curr_df.copy()
    curr_v["share"] = (curr_v["pdd_shipments"] / curr_total * 100).round(0).astype(int)
    top2_curr = curr_v.nlargest(2, "pdd_shipments").reset_index(drop=True)

    if len(top2_curr) < 2:
        return p1, ""

    t1_name  = _display_name(top2_curr.loc[0, "vendor_name"])
    t2_name  = _display_name(top2_curr.loc[1, "vendor_name"])
    t1_short = _short_name(top2_curr.loc[0, "vendor_name"])
    t2_short = _short_name(top2_curr.loc[1, "vendor_name"])
    t1_pct   = int(top2_curr.loc[0, "share"])
    t2_pct   = int(top2_curr.loc[1, "share"])
    combined = t1_pct + t2_pct

    if not prior_df.empty and prior_total > 0:
        prior_v = prior_df.copy()
        prior_v["share"] = (prior_v["pdd_shipments"] / prior_total * 100).round(0).astype(int)
        top2_prior = prior_v.nlargest(2, "pdd_shipments").reset_index(drop=True)
        pt1_pct  = int(top2_prior.loc[0, "share"]) if len(top2_prior) > 0 else 0
        pt2_pct  = int(top2_prior.loc[1, "share"]) if len(top2_prior) > 1 else 0
        pt1_short = _short_name(top2_prior.loc[0, "vendor_name"]) if len(top2_prior) > 0 else ""
        pt2_short = _short_name(top2_prior.loc[1, "vendor_name"]) if len(top2_prior) > 1 else ""
        prior_combined = pt1_pct + pt2_pct
        shift = abs(combined - prior_combined)
        conc_word  = "largely stable"  if shift < 3 else ("slightly shifted" if shift < 8 else "notably shifted")
        shift_word = "a marginal shift" if shift < 3 else ("a moderate shift"  if shift < 8 else "a notable shift")
        p2 = (
            f"Vendor concentration remained {conc_word}, with {t1_name} ({t1_pct}%) "
            f"and {t2_name} ({t2_pct}%) accounting for {combined}% of total VOC shipments, "
            f"{shift_word} from WK-{prior_wk:02d}\u2019s {prior_combined}% "
            f"({t1_short}- {pt1_pct}%, {t2_short}- {pt2_pct}%)."
        )
    else:
        p2 = (
            f"Vendor concentration: {t1_name} ({t1_pct}%) and {t2_name} ({t2_pct}%) "
            f"accounted for {combined}% of total VOC shipments this week."
        )

    return p1, p2


st.set_page_config(
    page_title="AI Insights | VOC Command Center",
    page_icon="💡",
    layout="wide",
)


# ── Apply dark theme CSS ──
inject_dark_css()
# ── Theme ──────────────────────────────────────────────────────────────────
_ORANGE = "#F6A623"
_NAVY   = "#0A1628"
_GREY   = "#0F2040"
_BORDER = "#1E3A60"
_TEXT   = "#E8EAF0"
_MUTED  = "#8892A4"
_RED    = "#E74C3C"
_YELLOW = "#F39C12"
_GREEN  = "#2ECC71"

def _section(text: str) -> None:
    st.markdown(
        f'<p style="font-size:0.72rem; font-weight:700; color:{_MUTED}; '
        f'text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.5rem;">'
        f'{text}</p>',
        unsafe_allow_html=True,
    )

# Insight type → visual style map
_INSIGHT_STYLE = {
    "top-performers": {
        "icon": "🏆", "label": "Top Performers",
        "bg": "rgba(46,204,113,0.1)", "border": "rgba(46,204,113,0.4)", "text": "#2ECC71",
    },
    "dea-decline": {
        "icon": "📉", "label": "DEA Decline Alert",
        "bg": "rgba(231,76,60,0.1)", "border": "rgba(231,76,60,0.4)", "text": "#E74C3C",
    },
    "volume-change": {
        "icon": "📦", "label": "Volume Change",
        "bg": "rgba(74,144,217,0.1)", "border": "rgba(74,144,217,0.4)", "text": "#4A90D9",
    },
}

# ── Guard ──────────────────────────────────────────────────────────────────
raw_df: pd.DataFrame | None = st.session_state.get("raw_df")
if raw_df is None:
    st.markdown(
        f'<div style="background:{_GREY}; border:2px dashed {_ORANGE}; border-radius:10px;'
        f'padding:2.5rem; text-align:center; margin-top:2rem;">'
        f'<div style="font-size:2.5rem;">📂</div>'
        f'<div style="font-weight:700; color:{_TEXT}; font-size:1.05rem; margin-top:0.5rem;">'
        f'No data loaded</div>'
        f'<div style="color:{_MUTED}; font-size:0.9rem; margin-top:0.4rem;">'
        f'Upload a VOC data CSV file using the sidebar.</div></div>',
        unsafe_allow_html=True,
    )
    st.stop()

filtered_df = apply_filters(
    raw_df,
    vendors=st.session_state.get("filter_vendors", []),
    year=st.session_state.get("filter_year"),
    week_start=st.session_state.get("filter_week_start"),
    week_end=st.session_state.get("filter_week_end"),
)

# ── Header ─────────────────────────────────────────────────────────────────
st.markdown(
    f'<h1 style="color:{_TEXT}; font-weight:700; font-size:1.7rem; '
    f'border-bottom:3px solid {_ORANGE}; padding-bottom:0.4rem; margin-bottom:0.25rem;">'
    f'💡 AI Insights</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p style="color:{_MUTED}; font-size:0.9rem; margin-bottom:1.2rem;">'
    f'Rule-based weekly narrative observations: top performers, DEA declines, '
    f'and volume shifts. Export filtered data as CSV.</p>',
    unsafe_allow_html=True,
)

if filtered_df.empty:
    st.info("No data matches the current filters. Adjust the sidebar filters.")
    st.stop()

mrw = most_recent_week(filtered_df)
all_weeks = sorted(filtered_df["week_id"].unique().tolist(), reverse=True)

# ══════════════════════════════════════════════════════════════════════════
# Section 1 — Week Selector + Generate Button
# ══════════════════════════════════════════════════════════════════════════
_section("GENERATE WEEKLY INSIGHTS")

ctrl_col, btn_col = st.columns([2, 1], gap="medium")

with ctrl_col:
    selected_week = st.selectbox(
        "Select week to analyse",
        options=all_weeks,
        index=0,
        format_func=lambda w: f"Week {w}" + (" (most recent)" if w == mrw else ""),
        help="Insights compare selected week vs. the immediately preceding week in the dataset.",
    )

with btn_col:
    st.markdown("<div style='margin-top:1.75rem;'></div>", unsafe_allow_html=True)
    generate_clicked = st.button(
        "🔍 Generate Insights",
        use_container_width=True,
        type="primary",
    )

# Optional: total DF volume for exact % calculation in WBR narrative
with st.expander("⚙️ WBR Narrative — Optional Input", expanded=False):
    st.markdown(
        f'<div style="font-size:0.8rem; color:{_MUTED}; margin-bottom:0.4rem;">'
        f'Enter total DF weekly shipments to compute the exact "X% of total DF volume" figure. '
        f'Leave at 0 to show "less than 1%" (always accurate for VOC).</div>',
        unsafe_allow_html=True,
    )
    total_df_input = st.number_input(
        "Total DF shipments this week",
        min_value=0,
        value=0,
        step=100000,
        help="Used only for the WBR narrative % calculation. Does not affect any other insights.",
    )

# ── Generate / cache insights ──────────────────────────────────────────────
if generate_clicked:
    try:
        result = generate_insights(filtered_df, int(selected_week))
        st.session_state["insights_result"] = result
        st.session_state["insights_week"]   = int(selected_week)
    except Exception:
        st.error("Insights could not be generated. Please try again.")
        st.session_state.pop("insights_result", None)

# ── Render cached insights ─────────────────────────────────────────────────
insight_result = st.session_state.get("insights_result")
cached_week    = st.session_state.get("insights_week")

if insight_result is not None:
    # Warn if cached insights are for a different week
    if cached_week != selected_week:
        st.warning(
            f"Showing insights for Week {cached_week}. "
            f"Click **Generate Insights** to refresh for Week {selected_week}."
        )

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    _section(f"INSIGHTS — WEEK {insight_result.week_id}")

    for para in insight_result.paragraphs:
        style = _INSIGHT_STYLE.get(para.type, {
            "icon": "ℹ️", "label": para.type,
            "bg": _GREY, "border": _BORDER, "text": _TEXT,
        })

        # Strip the [Week X | Generated: ...] prefix from text for clean display
        raw_text = para.text
        if raw_text.startswith("[Week"):
            bracket_end = raw_text.find("]\n")
            body = raw_text[bracket_end + 2:].strip() if bracket_end != -1 else raw_text
        else:
            body = raw_text

        prior_note_html = ""
        if para.has_prior_week_note:
            prior_note_html = (
                f'<div style="margin-top:6px; font-size:0.78rem; '
                f'color:{_MUTED}; font-style:italic;">'
                f'ℹ️ Prior-week comparison data is unavailable.</div>'
            )

        # For volume-change: replace body with the WBR narrative
        if para.type == "volume-change":
            p1, p2 = _wbr_narrative(
                filtered_df,
                int(insight_result.week_id),
                int(total_df_input) if "total_df_input" in dir() else 0,
            )
            body = (
                f'<p style="margin:0 0 0.8rem 0;">{p1}</p>'
                + (f'<p style="margin:0;">{p2}</p>' if p2 else "")
            )

        st.markdown(
            f'<div style="background:{style["bg"]}; border:1px solid {style["border"]}; '
            f'border-left:5px solid {style["border"]}; border-radius:10px; '
            f'padding:0.9rem 1.2rem; margin-bottom:0.75rem;">'
            f'<div style="font-size:0.73rem; font-weight:700; color:{style["text"]}; '
            f'text-transform:uppercase; letter-spacing:0.07em; margin-bottom:4px;">'
            f'{style["icon"]} {style["label"]}</div>'
            f'<div style="font-size:0.88rem; color:{_TEXT}; line-height:1.75;">{body}</div>'
            f'{prior_note_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Generated-at footer
    st.markdown(
        f'<div style="font-size:0.76rem; color:{_MUTED}; margin-top:0.2rem; '
        f'margin-bottom:1.5rem;">'
        f'Generated: {insight_result.generated_at} · '
        f'Week {insight_result.week_id} · '
        f'{len(filtered_df[filtered_df["week_id"]==insight_result.week_id]):,} records analysed'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div style="background:#0F2040; border:1px solid {_BORDER}; border-radius:10px; '
        f'padding:2rem; text-align:center; color:{_MUTED}; margin-top:0.5rem;">'
        f'<div style="font-size:2rem; margin-bottom:0.5rem;">💡</div>'
        f'Select a week above and click <strong>Generate Insights</strong> to see '
        f'data-driven observations.'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Section 2 — CSV Export
# ══════════════════════════════════════════════════════════════════════════
_section("EXPORT FILTERED DATA")

export_empty = filtered_df.empty
filename     = export_filename(datetime.now())

export_col, info_col = st.columns([1, 2], gap="medium")

with export_col:
    if export_empty:
        st.download_button(
            label="⬇️ Download CSV",
            data=b"",
            file_name=filename,
            mime="text/csv",
            disabled=True,
            use_container_width=True,
        )
        st.caption("No data available to export.")
    else:
        export_bytes = generate_export_bytes(filtered_df)
        st.download_button(
            label="⬇️ Download Filtered Data (CSV)",
            data=export_bytes,
            file_name=filename,
            mime="text/csv",
            use_container_width=True,
        )

with info_col:
    if not export_empty:
        n_records = len(filtered_df)
        n_vendors = filtered_df["vendor_code"].nunique()
        n_weeks   = filtered_df["week_id"].nunique()
        wk_min    = int(filtered_df["week_id"].min())
        wk_max    = int(filtered_df["week_id"].max())
        st.markdown(
            f'<div style="background:#0F2040; border:1px solid {_BORDER}; border-radius:8px; '
            f'padding:0.7rem 1rem; font-size:0.85rem; color:{_TEXT};">'
            f'<strong>{n_records:,}</strong> records · '
            f'<strong>{n_vendors}</strong> vendors · '
            f'<strong>{n_weeks}</strong> weeks '
            f'(WK{wk_min} – WK{wk_max})'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="text-align:right; font-size:0.75rem; color:{_MUTED}; '
    f'border-top:1px solid {_BORDER}; padding-top:0.6rem; margin-top:1.5rem;">'
    f'VOC Command Center · NA Direct Fulfillment · Most recent week: <strong>{mrw}</strong>'
    f'</div>',
    unsafe_allow_html=True,
)
