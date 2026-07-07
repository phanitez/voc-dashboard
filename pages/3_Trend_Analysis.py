"""
pages/3_Trend_Analysis.py
Trend Analysis — weekly PDD volume trend, DEA % trend with thresholds,
per-vendor DEA sparklines, and week-over-week change table.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from voc.ui import inject_dark_css

from voc.aggregator import compute_weekly_aggregates, most_recent_week, risk_classification
from voc.filters import apply_filters
from voc.formatters import format_dea, format_pdd

st.set_page_config(
    page_title="Trend Analysis | VOC Command Center",
    page_icon="📈",
    layout="wide",
)


# ── Apply dark theme CSS ──
inject_dark_css()
from voc.ui import _ensure_data_loaded
_ensure_data_loaded()
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

_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=_TEXT),
    margin=dict(l=0, r=0, t=36, b=0),
    hoverlabel=dict(bgcolor="#0F2040", bordercolor="#2A4E7A",
                    font_size=13, font_family="Inter, sans-serif"),
)

# Vendor colour palette for multi-line chart
_PALETTE = ["#F6A623","#2A3548","#4A90D9","#2ECC71","#9B59B6",
            "#E74C3C","#1ABC9C","#E67E22","#3498DB","#8E44AD","#27AE60"]

def _section(text: str) -> None:
    st.markdown(
        f'<p style="font-size:0.72rem; font-weight:700; color:{_MUTED}; '
        f'text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.5rem;">'
        f'{text}</p>',
        unsafe_allow_html=True,
    )

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
    f'📈 Trend Analysis</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p style="color:{_MUTED}; font-size:0.9rem; margin-bottom:1.2rem;">'
    f'Week-over-week PDD volume and DEA % trajectory for all active vendors.</p>',
    unsafe_allow_html=True,
)

if filtered_df.empty:
    st.info("No data matches the current filters. Adjust the sidebar filters.")
    st.stop()

weekly_agg = compute_weekly_aggregates(filtered_df)
mrw        = most_recent_week(filtered_df)
all_vendors = sorted(filtered_df["vendor_code"].unique())

# ══════════════════════════════════════════════════════════════════════════
# Section 1 — Fleet-Level Trends (PDD + DEA side by side)
# ══════════════════════════════════════════════════════════════════════════
_section("FLEET-LEVEL WEEKLY TRENDS")

col_vol, col_dea = st.columns(2, gap="large")

# ── PDD Volume Trend ───────────────────────────────────────────────────
with col_vol:
    st.markdown(
        f'<div style="font-weight:700; color:{_TEXT}; font-size:0.97rem; '
        f'margin-bottom:0.4rem;">Weekly PDD Shipment Volume</div>',
        unsafe_allow_html=True,
    )
    if len(weekly_agg) < 2:
        st.info("Need at least 2 weeks for trend.")
    else:
        wa = weekly_agg.copy()
        wa["week_label"] = wa["week_id"].astype(int)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=wa["week_label"],
            y=wa["total_pdd"],
            mode="lines+markers",
            name="PDD Shipments",
            line=dict(color=_ORANGE, width=2.5),
            marker=dict(size=5, color=_ORANGE, line=dict(width=1.5, color="#FFF")),
            fill="tozeroy",
            fillcolor="rgba(246,166,35,0.12)",
            hovertemplate="Week %{x}<br>PDD: <b>%{y:,}</b><extra></extra>",
        ))

        # Rolling 4-week avg if enough data
        if len(wa) >= 4:
            wa["rolling4"] = wa["total_pdd"].rolling(4, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=wa["week_label"],
                y=wa["rolling4"],
                mode="lines",
                name="4-Wk Avg",
                line=dict(color="#4A90D9", width=1.5, dash="dot"),
                hovertemplate="Week %{x}<br>4-Wk Avg: <b>%{y:,.0f}</b><extra></extra>",
            ))

        fig.update_layout(
            **_PLOTLY_LAYOUT,
            height=300,
            xaxis=dict(
tickangle=-45, tickfont=dict(size=9), showgrid=False, title="Week", tickformat="d"),
            yaxis=dict(showgrid=True, gridcolor=_BORDER, zeroline=False, tickformat=","),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Fleet DEA % Trend ─────────────────────────────────────────────────
with col_dea:
    st.markdown(
        f'<div style="font-weight:700; color:{_TEXT}; font-size:0.97rem; '
        f'margin-bottom:0.4rem;">Fleet-Wide Weighted DEA %</div>',
        unsafe_allow_html=True,
    )
    if len(weekly_agg) < 2:
        st.info("Need at least 2 weeks for trend.")
    else:
        wa = weekly_agg.copy()
        wa["week_label"] = wa["week_id"].astype(int)
        dea_pct = wa["weighted_dea_pct"] * 100

        # Colour markers by risk tier
        point_colors = [
            (_GREEN if v > 95 else _YELLOW if v >= 90 else _RED)
            for v in dea_pct.fillna(0)
        ]

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=wa["week_label"],
            y=dea_pct,
            mode="lines+markers",
            name="Weighted DEA %",
            line=dict(color=_ORANGE, width=2.5),
            marker=dict(size=7, color=point_colors, line=dict(width=1.5, color="#FFF")),
            hovertemplate="Week %{x}<br>DEA: <b>%{y:.1f}%</b><extra></extra>",
        ))
        fig2.add_hline(y=90, line_dash="dash", line_color=_RED,
                       annotation_text="90% min", annotation_position="bottom right",
                       annotation_font_size=10)
        fig2.add_hline(y=95, line_dash="dash", line_color=_YELLOW,
                       annotation_text="95% on-track", annotation_position="top right",
                       annotation_font_size=10)

        fig2.update_layout(
            **_PLOTLY_LAYOUT,
            height=300,
            xaxis=dict(
tickangle=-45, tickfont=dict(size=9), showgrid=False, title="Week", tickformat="d"),
            yaxis=dict(range=[
                max(0, float(dea_pct.min()) - 5) if not dea_pct.isna().all() else 0,
                102
            ], showgrid=True, gridcolor=_BORDER, zeroline=False, ticksuffix="%"),
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Section 2 — Per-Vendor DEA Trend
# ══════════════════════════════════════════════════════════════════════════
_section("PER-VENDOR DEA % TREND")

# Vendor selector
vendor_labels = {
    vc: f"{vc} — {filtered_df.loc[filtered_df['vendor_code']==vc,'vendor_name'].iloc[0]}"
    for vc in all_vendors
}
selected_vendors = st.multiselect(
    "Select vendors to compare (leave empty = all)",
    options=all_vendors,
    format_func=lambda v: vendor_labels.get(v, v),
    default=[],
    key="trend_vendor_select",
)
vendors_to_plot = selected_vendors if selected_vendors else all_vendors

fig3 = go.Figure()
for i, vc in enumerate(vendors_to_plot):
    vdata = (
        filtered_df[filtered_df["vendor_code"] == vc]
        .sort_values("week_id")
    )
    if vdata.empty:
        continue
    label = vendor_labels.get(vc, vc)
    color = _PALETTE[i % len(_PALETTE)]
    fig3.add_trace(go.Scatter(
        x=vdata["week_id"].astype(int),
        y=vdata["dea_pct"] * 100,
        mode="lines+markers",
        name=vc,
        line=dict(color=color, width=2),
        marker=dict(size=5),
        hovertemplate=f"<b>{label}</b><br>Week %{{x}}<br>DEA: <b>%{{y:.1f}}%</b><extra></extra>",
    ))

fig3.add_hline(y=90, line_dash="dash", line_color=_RED,
               annotation_text="90%", annotation_position="bottom right",
               annotation_font_size=10)
fig3.add_hline(y=95, line_dash="dot", line_color=_YELLOW,
               annotation_text="95%", annotation_position="top right",
               annotation_font_size=10)

fig3.update_layout(
    **_PLOTLY_LAYOUT,
    height=380,
    xaxis=dict(
tickangle=-45, tickfont=dict(size=9), showgrid=False, title="Week ID", tickformat="d"),
    yaxis=dict(range=[0, 105], showgrid=True, gridcolor=_BORDER, zeroline=False,
               ticksuffix="%", title="DEA %"),
    legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5,
                font=dict(size=10)),
)
st.plotly_chart(fig3, use_container_width=True)

st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Section 3 — Week-over-Week Change Table
# ══════════════════════════════════════════════════════════════════════════
_section("WEEK-OVER-WEEK SUMMARY TABLE")

if len(weekly_agg) >= 2:
    wa_sorted = weekly_agg.sort_values("week_id").reset_index(drop=True)
    wa_sorted["prev_pdd"]  = wa_sorted["total_pdd"].shift(1)
    wa_sorted["prev_dea"]  = wa_sorted["weighted_dea_pct"].shift(1)

    wa_sorted["pdd_chg"]  = wa_sorted.apply(
        lambda r: f'{((r.total_pdd - r.prev_pdd) / r.prev_pdd * 100):+.1f}%'
        if pd.notna(r.prev_pdd) and r.prev_pdd > 0 else "—", axis=1
    )
    wa_sorted["dea_chg"]  = wa_sorted.apply(
        lambda r: f'{((r.weighted_dea_pct - r.prev_dea) * 100):+.2f} pp'
        if pd.notna(r.prev_dea) else "—", axis=1
    )
    wa_sorted["dea_fmt"]  = wa_sorted["weighted_dea_pct"].apply(
        lambda v: format_dea(v) if pd.notna(v) else "—"
    )
    wa_sorted["pdd_fmt"]  = wa_sorted["total_pdd"].apply(lambda v: format_pdd(int(v)))

    # Status badge
    def _status_html(v: float) -> str:
        if pd.isna(v):
            return "—"
        rc = risk_classification(v)
        return {"on_track":"✅ On Track","at_risk":"⚠️ At Risk","below_threshold":"🔴 Below Thr."}[rc]

    wa_sorted["status"] = wa_sorted["weighted_dea_pct"].apply(_status_html)

    display_table = wa_sorted[["week_id","pdd_fmt","pdd_chg","dea_fmt","dea_chg","status"]].copy()
    display_table.columns = ["Week ID","PDD Shipments","PDD Δ vs Prior","Wtd DEA %","DEA Δ vs Prior","Status"]
    display_table = display_table.sort_values("Week ID", ascending=False).reset_index(drop=True)

    st.dataframe(display_table, use_container_width=True, hide_index=True)
else:
    st.info("Week-over-week comparison requires at least 2 weeks of data.")

# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="text-align:right; font-size:0.75rem; color:{_MUTED}; '
    f'border-top:1px solid {_BORDER}; padding-top:0.6rem; margin-top:1rem;">'
    f'VOC Command Center · NA Direct Fulfillment · Most recent week: <strong>{mrw}</strong>'
    f'</div>',
    unsafe_allow_html=True,
)
