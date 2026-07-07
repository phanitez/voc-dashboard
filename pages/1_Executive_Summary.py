"""
pages/1_Executive_Summary.py
Executive Summary — KPI cards, top-5 volume chart, weekly trend, vendor
concentration section, and executive insights bullet box.

Uses the orange-accent / dark-navy theme defined in app.py and config.toml.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from voc.ui import inject_dark_css

from voc.aggregator import (
    active_vendor_count,
    compute_vendor_metrics,
    compute_weekly_aggregates,
    most_recent_week,
    risk_classification,
    top_vendors_by_pdd,
    volume_weighted_dea,
)
from voc.filters import apply_filters
from voc.formatters import format_dea, format_pdd

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Executive Summary | VOC Command Center",
    page_icon="📊",
    layout="wide",
)


# ── Apply dark theme CSS ──
inject_dark_css()
from voc.ui import _ensure_data_loaded
_ensure_data_loaded()
# ── Theme palette (mirrors config.toml + app.py CSS) ──────────────────────
_ORANGE = "#F6A623"
_NAVY   = "#0A1628"
_GREY   = "#0F2040"
_BORDER = "#1E3A60"
_TEXT   = "#E8EAF0"
_MUTED  = "#8892A4"
_RED    = "#E74C3C"
_YELLOW = "#F39C12"
_GREEN  = "#2ECC71"

# ── Shared Plotly layout defaults ──────────────────────────────────────────
_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=_TEXT),
    margin=dict(l=0, r=0, t=36, b=0),
    hoverlabel=dict(
        bgcolor="#0F2040",
        bordercolor=_BORDER,
        font_size=13,
        font_family="Inter, sans-serif",
    ),
)

# ══════════════════════════════════════════════════════════════════════════
# Guard: require loaded data
# ══════════════════════════════════════════════════════════════════════════
raw_df: pd.DataFrame | None = st.session_state.get("raw_df")

if raw_df is None:
    st.markdown(
        """
        <div style="background:#0F2040; border:2px dashed #F6A623; border-radius:10px;
                    padding:2.5rem; text-align:center; margin-top:2rem;">
            <div style="font-size:2.5rem;">📂</div>
            <div style="font-weight:700; color:#E8EAF0; font-size:1.05rem; margin-top:0.5rem;">
                No data loaded
            </div>
            <div style="color:#8892A4; font-size:0.9rem; margin-top:0.4rem;">
                Upload a VOC data CSV file using the sidebar to view this page.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ══════════════════════════════════════════════════════════════════════════
# Apply sidebar filters
# ══════════════════════════════════════════════════════════════════════════
filtered_df = apply_filters(
    raw_df,
    vendors=st.session_state.get("filter_vendors", []),
    year=st.session_state.get("filter_year"),
    week_start=st.session_state.get("filter_week_start"),
    week_end=st.session_state.get("filter_week_end"),
)

# ══════════════════════════════════════════════════════════════════════════
# Page header
# ══════════════════════════════════════════════════════════════════════════
st.markdown(
    """
    <h1 style="color:#E8EAF0; font-weight:700; font-size:1.7rem;
               border-bottom:3px solid #F6A623; padding-bottom:0.4rem;
               margin-bottom:0.25rem;">
        📊 Executive Summary
    </h1>
    """,
    unsafe_allow_html=True,
)

# Active filter badge
_active = []
if st.session_state.get("filter_vendors"):
    _active.append(f"{len(st.session_state['filter_vendors'])} vendor(s)")
if st.session_state.get("filter_year"):
    _active.append(f"Year {st.session_state['filter_year']}")
if st.session_state.get("filter_week_start") or st.session_state.get("filter_week_end"):
    _active.append(
        f"Weeks {st.session_state.get('filter_week_start', '–')} → "
        f"{st.session_state.get('filter_week_end', '–')}"
    )

if _active:
    st.markdown(
        f'<span style="background:rgba(243,156,18,0.1); border:1px solid rgba(243,156,18,0.4); border-radius:6px; '
        f'padding:3px 10px; font-size:0.8rem; color:#F6A623; font-weight:600;">'
        f'🔍 Filtered: {" · ".join(_active)}</span>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Empty-state guard (after filtering)
# ══════════════════════════════════════════════════════════════════════════
if filtered_df.empty:
    st.info("No data matches the current filters. Adjust the sidebar filters to see metrics.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════
# Pre-compute metrics
# ══════════════════════════════════════════════════════════════════════════
total_pdd      = int(filtered_df["pdd_shipments"].sum())
active_vendors = active_vendor_count(filtered_df)
wdea           = volume_weighted_dea(filtered_df, col="dea_pct")
wudea          = volume_weighted_dea(filtered_df, col="unpadded_dea_pct")
mrw            = most_recent_week(filtered_df)
vendor_metrics = compute_vendor_metrics(filtered_df)
weekly_agg     = compute_weekly_aggregates(filtered_df)

# Format for display
total_pdd_fmt  = format_pdd(total_pdd)
wdea_fmt       = format_dea(wdea)   if wdea  is not None else "—"
wudea_fmt      = format_dea(wudea)  if wudea is not None else "—"

# DEA as float % for delta calculations
wdea_pct  = wdea  * 100 if wdea  is not None else None
wudea_pct = wudea * 100 if wudea is not None else None

# ══════════════════════════════════════════════════════════════════════════
# Section 1 — KPI Cards
# ══════════════════════════════════════════════════════════════════════════
st.markdown(
    '<p style="font-size:0.72rem; font-weight:700; color:#8892A4; '
    'text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.5rem;">'
    'KEY PERFORMANCE INDICATORS</p>',
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)

def _kpi_card(col, icon: str, label: str, value: str, sub: str = "",
              value_color: str = _TEXT) -> None:
    """Render a styled KPI card inside a Streamlit column."""
    with col:
        st.markdown(
            f"""
            <div style="background:#0F2040; border:1px solid {_BORDER};
                        border-radius:12px; padding:1.1rem 1.3rem;
                        box-shadow:0 2px 8px rgba(0,0,0,0.06);
                        border-top:4px solid {_ORANGE}; height:100%;">
                <div style="font-size:1.5rem; margin-bottom:4px;">{icon}</div>
                <div style="font-size:0.73rem; font-weight:700; color:{_MUTED};
                            text-transform:uppercase; letter-spacing:0.07em;">
                    {label}
                </div>
                <div style="font-size:2rem; font-weight:800; color:{value_color};
                            line-height:1.15; margin-top:2px;">
                    {value}
                </div>
                <div style="font-size:0.78rem; color:{_MUTED}; margin-top:4px;">
                    {sub}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

_wdea_color = (
    _GREEN  if wdea_pct is not None and wdea_pct >= 95 else
    _YELLOW if wdea_pct is not None and wdea_pct >= 90 else
    _RED    if wdea_pct is not None else _TEXT
)
_wudea_color = (
    _GREEN  if wudea_pct is not None and wudea_pct >= 95 else
    _YELLOW if wudea_pct is not None and wudea_pct >= 90 else
    _RED    if wudea_pct is not None else _TEXT
)

_kpi_card(k1, "📦", "Total PDD Shipments", total_pdd_fmt,
          sub=f"across {filtered_df['week_id'].nunique()} weeks")
_kpi_card(k2, "🏭", "Active Vendors", str(active_vendors),
          sub=f"of {filtered_df['vendor_code'].nunique()} total vendors")
_kpi_card(k3, "🎯", "Weighted DEA %", wdea_fmt,
          sub="Volume-weighted delivery accuracy",
          value_color=_wdea_color)
_kpi_card(k4, "📐", "Weighted Unpadded DEA %", wudea_fmt,
          sub="Raw delivery accuracy (no padding)",
          value_color=_wudea_color)

st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Section 2 — Charts row: Top-5 Volume Bar  +  Weekly Trend Line
# ══════════════════════════════════════════════════════════════════════════
st.markdown(
    '<p style="font-size:0.72rem; font-weight:700; color:#8892A4; '
    'text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.75rem;">'
    'VOLUME ANALYSIS</p>',
    unsafe_allow_html=True,
)

# (no card borders on charts)

col_bar, col_line = st.columns([1, 1.4], gap="large")

# ── Top-5 vendors by PDD volume ────────────────────────────────────────
with col_bar:

    top5 = top_vendors_by_pdd(vendor_metrics, n=5)

    if top5.empty:
        st.info("No vendor data available.")
    else:
        # Shorten long vendor names for display
        top5 = top5.copy()
        top5["label"] = top5["vendor_name"].apply(
            lambda n: (n[:28] + "…") if len(n) > 30 else n
        )
        top5["dea_display"] = top5["weighted_dea_pct"].apply(
            lambda v: format_dea(v) if pd.notna(v) else "—"
        )
        top5["share_display"] = top5["volume_share_pct"].apply(
            lambda v: f"{v:.1f}%" if pd.notna(v) else "—"
        )

        # Colour bars by DEA tier
        bar_colors = [
            (_GREEN  if v >= 0.95 else _YELLOW if v >= 0.90 else _RED)
            for v in top5["weighted_dea_pct"].fillna(0)
        ]

        fig_bar = go.Figure(
            go.Bar(
                x=top5["total_pdd"],
                y=top5["label"],
                orientation="h",
                marker_color=bar_colors,
                text=[
                    f"{p/1000:.1f}K  ({s})" if p >= 1000 else f"{int(p)}  ({s})"
                    for p, s in zip(top5["total_pdd"], top5["share_display"])
                ],
                textposition=[
                    "inside" if p >= max(top5["total_pdd"]) * 0.25 else "outside"
                    for p in top5["total_pdd"]
                ],
                insidetextanchor="middle",
                cliponaxis=False,
                textfont=dict(size=11, color=_TEXT),
                customdata=top5[["vendor_code", "dea_display", "share_display"]].values,
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Vendor Code: %{customdata[0]}<br>"
                    "PDD Shipments: %{x:,}<br>"
                    "Volume Share: %{customdata[2]}<br>"
                    "Weighted DEA: %{customdata[1]}"
                    "<extra></extra>"
                ),
            )
        )
        fig_bar.update_layout(
            **_PLOTLY_LAYOUT,
            title=dict(text="<b>Top 5 Vendors by PDD Volume</b>",
                       font=dict(color=_TEXT, size=14), x=0.02, xanchor="left",
                       pad=dict(t=10, l=8)),
            height=340,
            xaxis=dict(
                showgrid=True, gridcolor=_BORDER, zeroline=False,
                title="PDD Shipments", tickformat=".2s",
                showticklabels=True,
                automargin=True,
            ),
            yaxis=dict(
                autorange="reversed",
                showgrid=False,
                tickfont=dict(size=11),
            ),
            showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # DEA colour legend
        st.markdown(
            f'<div style="display:flex; gap:12px; font-size:0.75rem; color:{_MUTED}; '
            f'margin-top:-0.5rem; padding-left:4px;">'
            f'<span>🟢 ≥ 95% On Track</span>'
            f'<span>🟡 90–95% At Risk</span>'
            f'<span>🔴 &lt; 90% Below Threshold</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Weekly shipment trend ───────────────────────────────────────────────
with col_line:

    if weekly_agg.empty or len(weekly_agg) < 2:
        st.info("Trend analysis requires at least 2 weeks of data.")
    else:
        weekly_agg = weekly_agg.copy()
        weekly_agg["week_label"] = weekly_agg["week_id"].astype(int)
        weekly_agg["dea_display"] = weekly_agg["weighted_dea_pct"].apply(
            lambda v: format_dea(v) if pd.notna(v) else "—"
        )

        fig_line = go.Figure()

        # Build abbreviated labels: 28,400 → "28.4K"
        def _fmt(v):
            return f"{v/1000:.1f}K" if v >= 1000 else str(int(v))
        pdd_labels = weekly_agg["total_pdd"].apply(lambda v: _fmt(int(v)))

        # Volume trend (area + line + labels)
        fig_line.add_trace(
            go.Scatter(
                x=weekly_agg["week_label"],
                y=weekly_agg["total_pdd"],
                mode="lines+markers+text",
                name="PDD Shipments",
                line=dict(color=_ORANGE, width=2.5),
                marker=dict(size=5, color=_ORANGE, line=dict(width=1.5, color="#0F2040")),
                fill="tozeroy",
                fillcolor="rgba(246,166,35,0.12)",
                text=pdd_labels,
                textposition="top center",
                textfont=dict(size=9, color=_TEXT),
                customdata=weekly_agg[["week_id", "dea_display"]].values,
                hovertemplate=(
                    "Week %{customdata[0]}<br>"
                    "PDD Shipments: <b>%{y:,}</b><br>"
                    "Weighted DEA: %{customdata[1]}"
                    "<extra></extra>"
                ),
            )
        )

        # Week-over-week delta annotation on last point
        if len(weekly_agg) >= 2:
            last  = int(weekly_agg.iloc[-1]["total_pdd"])
            prev  = int(weekly_agg.iloc[-2]["total_pdd"])
            delta = last - prev
            delta_pct = delta / prev * 100 if prev > 0 else 0
            arrow = "▲" if delta >= 0 else "▼"
            delta_color = _GREEN if delta >= 0 else _RED
            fig_line.add_annotation(
                x=weekly_agg.iloc[-1]["week_label"],
                y=last,
                text=f'<span style="color:{delta_color}">{arrow} {abs(delta_pct):.1f}%</span>',
                showarrow=False,
                yshift=18,
                font=dict(size=11),
            )

        fig_line.update_layout(
            **_PLOTLY_LAYOUT,
            title=dict(text="<b>Weekly PDD Shipment Trend</b>",
                       font=dict(color=_TEXT, size=14), x=0.02, xanchor="left",
                       pad=dict(t=10, l=8)),
            height=380,
            xaxis=dict(
                showgrid=False,
                tickangle=-45,
                tickfont=dict(size=10),
                tickformat="d",
                title="Week",
                nticks=16,
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor=_BORDER,
                zeroline=False,
                title="PDD Shipments",
                tickformat=",",
            ),
            showlegend=False,
        )
        st.plotly_chart(fig_line, use_container_width=True)

st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Section 3 — Vendor Concentration
# ══════════════════════════════════════════════════════════════════════════
st.markdown(
    '<p style="font-size:0.72rem; font-weight:700; color:#8892A4; '
    'text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.75rem;">'
    'VENDOR CONCENTRATION</p>',
    unsafe_allow_html=True,
)

top3 = top_vendors_by_pdd(vendor_metrics, n=3)
combined_share = float(top3["volume_share_pct"].sum()) if not top3.empty else 0.0
high_risk = combined_share > 80.0

conc_col1, conc_col2 = st.columns([1, 1.2], gap="large")

with conc_col1:
    # Risk indicator card
    risk_bg    = "rgba(231,76,60,0.12)" if high_risk else "rgba(46,204,113,0.1)"
    risk_border= "#E74C3C" if high_risk else "#2ECC71"
    risk_label = "⚠️ High Concentration Risk" if high_risk else "✅ Concentration Normal"
    risk_txt   = "#E74C3C" if high_risk else "#2ECC71"

    st.markdown(
        f"""
        <div style="background:{risk_bg}; border:1px solid {risk_border};
                    border-radius:10px; padding:1rem 1.3rem; margin-bottom:1rem;">
            <div style="font-weight:700; color:{risk_txt}; font-size:0.95rem;">
                {risk_label}
            </div>
            <div style="font-size:2rem; font-weight:800; color:{risk_txt}; margin:4px 0;">
                {combined_share:.1f}%
            </div>
            <div style="font-size:0.82rem; color:{risk_txt}; opacity:0.85;">
                Top-3 vendors' combined volume share
                {"— exceeds 80% threshold" if high_risk else "— within 80% threshold"}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top-3 vendor rows
    if not top3.empty:
        for i, row in top3.iterrows():
            dea_val  = row["weighted_dea_pct"]
            dea_str  = format_dea(dea_val) if pd.notna(dea_val) else "—"
            rc       = risk_classification(dea_val) if pd.notna(dea_val) else "below_threshold"
            badge_bg = {"on_track": "rgba(46,204,113,0.1)", "at_risk": "rgba(243,156,18,0.1)", "below_threshold": "rgba(231,76,60,0.1)"}[rc]
            badge_cl = {"on_track": "#2ECC71", "at_risk": "#F39C12", "below_threshold": "#E74C3C"}[rc]
            badge_bd = {"on_track": "rgba(46,204,113,0.4)", "at_risk": "rgba(243,156,18,0.4)", "below_threshold": "rgba(231,76,60,0.4)"}[rc]
            badge_lb = {"on_track": "On Track", "at_risk": "At Risk", "below_threshold": "Below Threshold"}[rc]

            st.markdown(
                f"""
                <div style="background:#0F2040; border:1px solid {_BORDER};
                            border-radius:8px; padding:0.6rem 1rem;
                            margin-bottom:0.5rem; display:flex;
                            align-items:center; justify-content:space-between;">
                    <div>
                        <div style="font-weight:700; color:{_TEXT}; font-size:0.88rem;">
                            #{i+1} {row['vendor_code']}
                        </div>
                        <div style="font-size:0.75rem; color:{_MUTED};">
                            {(row['vendor_name'][:35] + '…') if len(row['vendor_name']) > 37 else row['vendor_name']}
                        </div>
                    </div>
                    <div style="text-align:right; min-width:110px;">
                        <div style="font-weight:700; color:{_TEXT}; font-size:0.95rem;">
                            {row['volume_share_pct']:.1f}%
                        </div>
                        <div style="background:{badge_bg}; color:{badge_cl}; border:1px solid {badge_bd};
                                    border-radius:10px; padding:1px 8px; font-size:0.7rem;
                                    font-weight:700; display:inline-block; margin-top:2px;">
                            {dea_str} · {badge_lb}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No vendor data available.")

with conc_col2:
    # Donut / pie chart of top-5 + Others
    if not vendor_metrics.empty:
        top5c = vendor_metrics.head(5).copy()
        others_share = max(0.0, 100.0 - top5c["volume_share_pct"].sum())
        pie_labels = list(top5c["vendor_code"]) + (["Others"] if others_share > 0.01 else [])
        pie_values = list(top5c["volume_share_pct"]) + ([others_share] if others_share > 0.01 else [])
        pie_colors = [_ORANGE, "#2A3548", "#4A90D9", "#2ECC71", "#9B59B6", "#BDC3C7"][:len(pie_labels)]

        fig_pie = go.Figure(
            go.Pie(
                labels=pie_labels,
                values=pie_values,
                hole=0.55,
                marker=dict(colors=pie_colors, line=dict(color="#0A1628", width=2)),
                textinfo="label+percent",
                textfont=dict(size=11),
                hovertemplate="<b>%{label}</b><br>Share: %{value:.1f}%<extra></extra>",
            )
        )
        fig_pie.update_layout(
            **_PLOTLY_LAYOUT,
            height=320,
            showlegend=False,
            annotations=[
                dict(
                    text=f"<b>{combined_share:.0f}%</b><br><span style='font-size:10px'>Top 3</span>",
                    x=0.5, y=0.5,
                    font=dict(size=16, color="#E8EAF0"),
                    showarrow=False,
                )
            ],
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No data for concentration chart.")

st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Section 4 — Executive Insights
# ══════════════════════════════════════════════════════════════════════════
st.markdown(
    '<p style="font-size:0.72rem; font-weight:700; color:#8892A4; '
    'text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.75rem;">'
    'EXECUTIVE INSIGHTS</p>',
    unsafe_allow_html=True,
)

# Build 3 data-driven bullet observations
bullets: list[tuple[str, str, str]] = []  # (icon, headline, detail)

# --- Observation 1: overall DEA health ---
if wdea_pct is not None:
    if wdea_pct >= 95:
        bullets.append((
            "🟢",
            f"Strong delivery accuracy at {wdea_fmt}",
            f"The volume-weighted DEA across all {active_vendors} active vendors "
            f"exceeds the 95% on-track threshold, indicating healthy carrier performance.",
        ))
    elif wdea_pct >= 90:
        bullets.append((
            "🟡",
            f"DEA at {wdea_fmt} — approaching threshold",
            f"Volume-weighted DEA is between 90% and 95%, placing the program in the "
            f"'At Risk' tier. Monitor closely for further declines.",
        ))
    else:
        bullets.append((
            "🔴",
            f"DEA at {wdea_fmt} — below 90% threshold",
            f"Volume-weighted DEA is below the 90% minimum threshold. "
            f"Immediate vendor reviews are recommended.",
        ))

# --- Observation 2: concentration risk ---
if not top3.empty:
    top1 = vendor_metrics.iloc[0]
    if high_risk:
        bullets.append((
            "⚠️",
            f"High concentration risk — top 3 hold {combined_share:.1f}% of volume",
            f"{top1['vendor_code']} alone accounts for {top1['volume_share_pct']:.1f}% "
            f"of total PDD shipments. Diversification should be explored to reduce "
            f"single-vendor dependency.",
        ))
    else:
        bullets.append((
            "✅",
            f"Concentration within bounds — top 3 hold {combined_share:.1f}% of volume",
            f"No single vendor dominates volume excessively. "
            f"{top1['vendor_code']} leads with {top1['volume_share_pct']:.1f}%, "
            f"within acceptable concentration limits.",
        ))

# --- Observation 3: recent week trend or below-threshold vendors ---
below_thresh = (
    vendor_metrics[vendor_metrics["most_recent_week_dea"].notna() &
                   (vendor_metrics["most_recent_week_dea"] < 0.90)]
    if not vendor_metrics.empty else pd.DataFrame()
)

if not below_thresh.empty:
    names_list = ", ".join(below_thresh["vendor_code"].head(3).tolist())
    extra = f" (+{len(below_thresh) - 3} more)" if len(below_thresh) > 3 else ""
    bullets.append((
        "🔴",
        f"{len(below_thresh)} vendor(s) below DEA threshold in the most recent week",
        f"Vendor(s) {names_list}{extra} recorded DEA below 90% in "
        f"Week {mrw}. These vendors require escalation or corrective action.",
    ))
elif len(weekly_agg) >= 2:
    last_pdd  = int(weekly_agg.iloc[-1]["total_pdd"])
    prev_pdd  = int(weekly_agg.iloc[-2]["total_pdd"])
    last_week = int(weekly_agg.iloc[-1]["week_id"])
    prev_week = int(weekly_agg.iloc[-2]["week_id"])
    vol_chg   = (last_pdd - prev_pdd) / prev_pdd * 100 if prev_pdd > 0 else 0
    direction = "increased" if vol_chg >= 0 else "decreased"
    icon      = "📈" if vol_chg >= 0 else "📉"
    bullets.append((
        icon,
        f"Shipment volume {direction} {abs(vol_chg):.1f}% week-over-week",
        f"Total PDD shipments moved from {format_pdd(prev_pdd)} (Week {prev_week}) "
        f"to {format_pdd(last_pdd)} (Week {last_week}), "
        f"a change of {format_pdd(abs(last_pdd - prev_pdd))} units.",
    ))
else:
    bullets.append((
        "ℹ️",
        "All vendors are meeting DEA targets in the most recent week",
        f"No vendors fell below the 90% DEA threshold in Week {mrw}.",
    ))

# Render insight box
bullet_html = "".join(
    f"""
    <div style="display:flex; gap:12px; align-items:flex-start;
                padding:0.85rem 1rem; border-bottom:1px solid {_BORDER};
                {'border-bottom:none;' if i == len(bullets)-1 else ''}">
        <div style="font-size:1.3rem; line-height:1.4; min-width:24px;">{icon}</div>
        <div>
            <div style="font-weight:700; color:{_TEXT}; font-size:0.92rem; margin-bottom:3px;">
                {headline}
            </div>
            <div style="font-size:0.83rem; color:{_MUTED}; line-height:1.55;">
                {detail}
            </div>
        </div>
    </div>
    """
    for i, (icon, headline, detail) in enumerate(bullets)
)

st.markdown(
    f"""
    <div style="background:#0F2040; border:1px solid {_BORDER}; border-radius:12px;
                box-shadow:0 2px 8px rgba(0,0,0,0.05); overflow:hidden;
                border-top:4px solid {_ORANGE};">
        <div style="background:{_GREY}; padding:0.6rem 1rem;
                    border-bottom:1px solid {_BORDER};">
            <span style="font-weight:700; color:{_TEXT}; font-size:0.9rem;">
                💡 Auto-Generated Observations
            </span>
            <span style="font-size:0.75rem; color:{_MUTED}; margin-left:8px;">
                Week range: {filtered_df['week_id'].min()} – {filtered_df['week_id'].max()}
                · {len(filtered_df):,} records · {active_vendors} active vendors
            </span>
        </div>
        {bullet_html}
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Footer
# ══════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div style="text-align:right; font-size:0.75rem; color:{_MUTED}; '
    f'border-top:1px solid {_BORDER}; padding-top:0.6rem;">'
    f'VOC Command Center · NA Direct Fulfillment · '
    f'Most recent week in view: <strong>Week {mrw}</strong>'
    f'</div>',
    unsafe_allow_html=True,
)
