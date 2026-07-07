"""
pages/2_Vendor_Performance.py
Vendor Performance — ranked table with search, sortable columns, DEA status
badges, volume-share bar sparklines, and a drill-down panel per vendor.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from voc.ui import inject_dark_css

from voc.aggregator import (
    compute_vendor_metrics,
    most_recent_week,
    risk_classification,
)
from voc.filters import apply_filters, filter_vendors_by_search
from voc.formatters import format_dea, format_pdd

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Vendor Performance | VOC Command Center",
    page_icon="🏆",
    layout="wide",
)


# ── Apply dark theme CSS ──
inject_dark_css()
from voc.ui import _ensure_data_loaded
_ensure_data_loaded()
# ── Theme palette ─────────────────────────────────────────────────────────
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
    margin=dict(l=0, r=0, t=28, b=0),
    hoverlabel=dict(bgcolor="#0F2040", bordercolor="#2A4E7A",
                    font_size=13, font_family="Inter, sans-serif"),
)

# ── Helpers ───────────────────────────────────────────────────────────────

def _risk_ui(rc: str) -> tuple[str, str, str, str]:
    """Return (bg, text_color, border, label) for a risk tier string."""
    return {
        "on_track":        ("rgba(46,204,113,0.1)", "#2ECC71", "rgba(46,204,113,0.4)", "✅ On Track"),
        "at_risk":         ("rgba(243,156,18,0.1)", "#F39C12", "rgba(243,156,18,0.4)", "⚠️ At Risk"),
        "below_threshold": ("rgba(231,76,60,0.1)", "#E74C3C", "rgba(231,76,60,0.4)", "🔴 Below Threshold"),
    }.get(rc, ("#0F2040", "#8892A4", "#1E3A60", "—"))


def _badge(text: str, bg: str, color: str, border: str) -> str:
    return (
        f'<span style="background:{bg}; color:{color}; border:1px solid {border}; '
        f'border-radius:10px; padding:2px 9px; font-size:0.72rem; font-weight:700; '
        f'white-space:nowrap;">{text}</span>'
    )


def _share_bar(share_pct: float, max_share: float) -> str:
    """Inline HTML mini-bar for volume share."""
    bar_w = int(share_pct / max(max_share, 1) * 80)  # max 80 px
    return (
        f'<div style="display:flex; align-items:center; gap:6px;">'
        f'<div style="width:{bar_w}px; height:8px; background:{_ORANGE}; '
        f'border-radius:4px; min-width:3px;"></div>'
        f'<span style="font-size:0.82rem; color:{_TEXT}; font-weight:600;">'
        f'{share_pct:.1f}%</span></div>'
    )


def _section_label(text: str) -> None:
    st.markdown(
        f'<p style="font-size:0.72rem; font-weight:700; color:{_MUTED}; '
        f'text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.6rem;">'
        f'{text}</p>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════
# Guard: require loaded data
# ══════════════════════════════════════════════════════════════════════════
raw_df: pd.DataFrame | None = st.session_state.get("raw_df")

if raw_df is None:
    st.markdown(
        f"""
        <div style="background:{_GREY}; border:2px dashed {_ORANGE}; border-radius:10px;
                    padding:2.5rem; text-align:center; margin-top:2rem;">
            <div style="font-size:2.5rem;">📂</div>
            <div style="font-weight:700; color:{_TEXT}; font-size:1.05rem; margin-top:0.5rem;">
                No data loaded
            </div>
            <div style="color:{_MUTED}; font-size:0.9rem; margin-top:0.4rem;">
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
    f'<h1 style="color:{_TEXT}; font-weight:700; font-size:1.7rem; '
    f'border-bottom:3px solid {_ORANGE}; padding-bottom:0.4rem; '
    f'margin-bottom:0.25rem;">🏆 Vendor Performance</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p style="color:{_MUTED}; font-size:0.9rem; margin-bottom:1.2rem;">'
    f'Ranked vendor metrics, DEA status, volume share, and week-by-week drill-down.</p>',
    unsafe_allow_html=True,
)

if filtered_df.empty:
    st.info("No data matches the current filters. Adjust the sidebar filters to see results.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════
# Pre-compute
# ══════════════════════════════════════════════════════════════════════════
vendor_metrics = compute_vendor_metrics(filtered_df)
mrw            = most_recent_week(filtered_df)
max_share      = float(vendor_metrics["volume_share_pct"].max()) if not vendor_metrics.empty else 1.0

# ══════════════════════════════════════════════════════════════════════════
# Summary bar — quick stats
# ══════════════════════════════════════════════════════════════════════════
n_total   = len(vendor_metrics)
n_on      = int((vendor_metrics["most_recent_week_dea"].dropna() > 0.95).sum()) if not vendor_metrics.empty else 0
n_atrisk  = int(((vendor_metrics["most_recent_week_dea"].dropna() >= 0.90) &
                 (vendor_metrics["most_recent_week_dea"].dropna() <= 0.95)).sum()) if not vendor_metrics.empty else 0
n_below   = int((vendor_metrics["most_recent_week_dea"].dropna() < 0.90).sum())  if not vendor_metrics.empty else 0

st.markdown(
    f"""
    <div style="display:flex; gap:1rem; flex-wrap:wrap; margin-bottom:1.2rem;">
        <div style="background:#0F2040; border:1px solid {_BORDER}; border-radius:8px;
                    padding:0.6rem 1.1rem; display:flex; align-items:center; gap:8px;
                    box-shadow:0 1px 4px rgba(0,0,0,0.05);">
            <span style="font-size:1.1rem;">🏭</span>
            <div>
                <div style="font-size:1.3rem; font-weight:800; color:{_TEXT};">{n_total}</div>
                <div style="font-size:0.72rem; color:{_MUTED}; font-weight:600;">Total Vendors</div>
            </div>
        </div>
        <div style="background:rgba(46,204,113,0.1); border:1px solid rgba(46,204,113,0.4); border-radius:8px;
                    padding:0.6rem 1.1rem; display:flex; align-items:center; gap:8px;">
            <span style="font-size:1.1rem;">✅</span>
            <div>
                <div style="font-size:1.3rem; font-weight:800; color:#2ECC71;">{n_on}</div>
                <div style="font-size:0.72rem; color:#2ECC71; font-weight:600;">On Track (&gt;95%)</div>
            </div>
        </div>
        <div style="background:rgba(243,156,18,0.1); border:1px solid rgba(243,156,18,0.4); border-radius:8px;
                    padding:0.6rem 1.1rem; display:flex; align-items:center; gap:8px;">
            <span style="font-size:1.1rem;">⚠️</span>
            <div>
                <div style="font-size:1.3rem; font-weight:800; color:#F39C12;">{n_atrisk}</div>
                <div style="font-size:0.72rem; color:#F39C12; font-weight:600;">At Risk (90–95%)</div>
            </div>
        </div>
        <div style="background:rgba(231,76,60,0.1); border:1px solid rgba(231,76,60,0.4); border-radius:8px;
                    padding:0.6rem 1.1rem; display:flex; align-items:center; gap:8px;">
            <span style="font-size:1.1rem;">🔴</span>
            <div>
                <div style="font-size:1.3rem; font-weight:800; color:#E74C3C;">{n_below}</div>
                <div style="font-size:0.72rem; color:#E74C3C; font-weight:600;">Below Threshold (&lt;90%)</div>
            </div>
        </div>
        <div style="background:#0F2040; border:1px solid {_BORDER}; border-radius:8px;
                    padding:0.6rem 1.1rem; display:flex; align-items:center; gap:8px;">
            <span style="font-size:1.1rem;">📅</span>
            <div>
                <div style="font-size:1.3rem; font-weight:800; color:{_TEXT};">{mrw}</div>
                <div style="font-size:0.72rem; color:{_MUTED}; font-weight:600;">Most Recent Week</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════
# Controls row: search + sort
# ══════════════════════════════════════════════════════════════════════════
_section_label("VENDOR RANKING TABLE")

ctrl_search, ctrl_sort, ctrl_filter = st.columns([2.5, 1.5, 1.5])

with ctrl_search:
    search_str = st.text_input(
        "🔍 Search vendors",
        placeholder="Type vendor code or name…",
        label_visibility="collapsed",
    )

with ctrl_sort:
    sort_col = st.selectbox(
        "Sort by",
        options=[
            "Total PDD Shipments",
            "Volume Share %",
            "Avg DEA %",
            "Avg Unpadded DEA %",
            "Weeks Active",
            "Vendor Code",
        ],
        index=0,
        label_visibility="visible",
    )

with ctrl_filter:
    status_filter = st.selectbox(
        "DEA Status filter",
        options=["All", "On Track", "At Risk", "Below Threshold"],
        index=0,
        label_visibility="visible",
    )

# ── Apply search ───────────────────────────────────────────────────────────
display_metrics = filter_vendors_by_search(vendor_metrics, search_str)

# ── Apply status filter ────────────────────────────────────────────────────
if status_filter != "All" and not display_metrics.empty:
    tier_map = {"On Track": "on_track", "At Risk": "at_risk", "Below Threshold": "below_threshold"}
    target_tier = tier_map[status_filter]
    display_metrics = display_metrics[
        display_metrics["most_recent_week_dea"].apply(
            lambda v: risk_classification(v) == target_tier if pd.notna(v) else False
        )
    ].reset_index(drop=True)

# ── Apply sort ─────────────────────────────────────────────────────────────
_sort_map = {
    "Total PDD Shipments": ("total_pdd", False),
    "Volume Share %":      ("volume_share_pct", False),
    "Avg DEA %":           ("weighted_dea_pct", False),
    "Avg Unpadded DEA %":  ("weighted_unpadded_dea_pct", False),
    "Weeks Active":        ("weeks_active", False),
    "Vendor Code":         ("vendor_code", True),
}
sort_field, sort_asc = _sort_map[sort_col]
if not display_metrics.empty:
    display_metrics = display_metrics.sort_values(sort_field, ascending=sort_asc).reset_index(drop=True)

# ── Result count badge ─────────────────────────────────────────────────────
total_shown = len(display_metrics)
st.markdown(
    f'<div style="font-size:0.8rem; color:{_MUTED}; margin-bottom:0.6rem;">'
    f'Showing <strong>{total_shown}</strong> of {n_total} vendors'
    + (f' · filtered by <em>{status_filter}</em>' if status_filter != "All" else "")
    + (f' · search: "<em>{search_str}</em>"' if search_str else "")
    + "</div>",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════
# Vendor ranking table
# ══════════════════════════════════════════════════════════════════════════
if display_metrics.empty:
    st.markdown(
        f"""
        <div style="background:{_GREY}; border:1px solid {_BORDER}; border-radius:8px;
                    padding:2rem; text-align:center; color:{_MUTED};">
            No vendors match the search criteria.
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    # Build HTML table
    header_cells = [
        ("Rank",              "center", "50px"),
        ("Vendor Code",       "left",   "90px"),
        ("Vendor Name",       "left",   "220px"),
        ("PDD Shipments",     "right",  "120px"),
        ("Volume Share",      "left",   "130px"),
        ("Avg DEA %",         "right",  "100px"),
        ("Avg Unpad DEA %",   "right",  "110px"),
        ("Weeks Active",      "center", "90px"),
        ("DEA Status",        "center", "140px"),
    ]

    th_style = (
        f"background:#142850; color:{_TEXT}; font-size:0.73rem; font-weight:700; "
        f"text-transform:uppercase; letter-spacing:0.06em; padding:9px 10px; "
        f"border-bottom:2px solid {_ORANGE}; white-space:nowrap;"
    )

    header_html = "".join(
        f'<th style="{th_style} text-align:{align}; min-width:{w};">{label}</th>'
        for label, align, w in header_cells
    )

    rows_html = ""
    for i, row in display_metrics.iterrows():
        rank = i + 1
        dea_val  = row["weighted_dea_pct"]
        udea_val = row["weighted_unpadded_dea_pct"]
        mrw_dea  = row["most_recent_week_dea"]

        dea_str  = format_dea(dea_val)  if pd.notna(dea_val)  else "—"
        udea_str = format_dea(udea_val) if pd.notna(udea_val) else "—"

        # DEA colour for the avg DEA cell
        dea_color = (
            _GREEN  if pd.notna(dea_val) and dea_val > 0.95 else
            _YELLOW if pd.notna(dea_val) and dea_val >= 0.90 else
            _RED    if pd.notna(dea_val) else _MUTED
        )

        # Status badge from most-recent-week DEA
        if pd.notna(mrw_dea):
            rc  = risk_classification(mrw_dea)
            bg, tc, bd, lb = _risk_ui(rc)
            status_html = _badge(lb, bg, tc, bd)
        else:
            status_html = _badge("No recent data", _GREY, _MUTED, _BORDER)

        # Alternating row background
        row_bg = "#142850" if rank % 2 == 1 else _GREY

        # Rank medal for top-3
        rank_display = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))

        td = (
            f"font-size:0.85rem; padding:9px 10px; border-bottom:1px solid {_BORDER}; "
            f"vertical-align:middle;"
        )

        rows_html += (
            f'<tr style="background:{row_bg};">'
            f'<td style="{td} text-align:center; font-weight:700; color:{_MUTED};">{rank_display}</td>'
            f'<td style="{td} font-weight:700; color:{_ORANGE};">{row["vendor_code"]}</td>'
            f'<td style="{td} color:{_TEXT};">{row["vendor_name"]}</td>'
            f'<td style="{td} text-align:right; font-weight:600; color:{_TEXT};">'
            f'{format_pdd(int(row["total_pdd"]))}</td>'
            f'<td style="{td}">{_share_bar(row["volume_share_pct"], max_share)}</td>'
            f'<td style="{td} text-align:right; font-weight:700; color:{dea_color};">'
            f'{dea_str}</td>'
            f'<td style="{td} text-align:right; color:{_MUTED};">{udea_str}</td>'
            f'<td style="{td} text-align:center; color:{_TEXT};">{int(row["weeks_active"])}</td>'
            f'<td style="{td} text-align:center;">{status_html}</td>'
            f'</tr>'
        )

    table_html = (
        f'<div style="overflow-x:auto; border-radius:10px; border:1px solid {_BORDER}; '
        f'box-shadow:0 2px 8px rgba(0,0,0,0.05);">'
        f'<table style="width:100%; border-collapse:collapse;">'
        f'<thead><tr>{header_html}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>'
    )
    st.markdown(table_html, unsafe_allow_html=True)

st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Drill-down panel
# ══════════════════════════════════════════════════════════════════════════
_section_label("VENDOR DRILL-DOWN")

if display_metrics.empty:
    st.info("Apply a search or filter above, then select a vendor to drill down.")
else:
    vendor_options = [
        f"{row['vendor_code']} — {row['vendor_name']}"
        for _, row in display_metrics.iterrows()
    ]
    selected_label = st.selectbox(
        "Select a vendor to inspect",
        options=vendor_options,
        index=0,
        label_visibility="visible",
    )
    selected_code = selected_label.split(" — ")[0].strip()

    # Pull the vendor's weekly data from the filtered dataset
    vendor_weekly = (
        filtered_df[filtered_df["vendor_code"] == selected_code]
        .sort_values("week_id")
        .reset_index(drop=True)
    )

    vendor_row = display_metrics[display_metrics["vendor_code"] == selected_code]
    if vendor_row.empty or vendor_weekly.empty:
        st.info("No data available for the selected vendor.")
    else:
        vr = vendor_row.iloc[0]
        mrw_dea_v = vr["most_recent_week_dea"]
        rc_v      = risk_classification(mrw_dea_v) if pd.notna(mrw_dea_v) else "below_threshold"
        bg_v, tc_v, bd_v, lb_v = _risk_ui(rc_v)

        # ── Vendor header card ─────────────────────────────────────────
        st.markdown(
            f"""
            <div style="background:#0F2040; border:1px solid {_BORDER}; border-radius:12px;
                        padding:1.1rem 1.4rem; box-shadow:0 2px 8px rgba(0,0,0,0.05);
                        border-left:6px solid {_ORANGE}; margin-bottom:1rem;
                        display:flex; align-items:center; justify-content:space-between;
                        flex-wrap:wrap; gap:1rem;">
                <div>
                    <div style="font-size:1.2rem; font-weight:800; color:{_TEXT};">
                        {vr['vendor_code']}
                    </div>
                    <div style="font-size:0.88rem; color:{_MUTED}; margin-top:2px;">
                        {vr['vendor_name']}
                    </div>
                </div>
                <div style="display:flex; gap:1.5rem; flex-wrap:wrap;">
                    <div style="text-align:center;">
                        <div style="font-size:1.4rem; font-weight:800; color:{_TEXT};">
                            {format_pdd(int(vr['total_pdd']))}
                        </div>
                        <div style="font-size:0.7rem; color:{_MUTED}; font-weight:600;
                                    text-transform:uppercase;">Total PDD</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:1.4rem; font-weight:800; color:{_TEXT};">
                            {vr['volume_share_pct']:.1f}%
                        </div>
                        <div style="font-size:0.7rem; color:{_MUTED}; font-weight:600;
                                    text-transform:uppercase;">Volume Share</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:1.4rem; font-weight:800; color:{_TEXT};">
                            {format_dea(vr['weighted_dea_pct']) if pd.notna(vr['weighted_dea_pct']) else '—'}
                        </div>
                        <div style="font-size:0.7rem; color:{_MUTED}; font-weight:600;
                                    text-transform:uppercase;">Avg DEA</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:1.4rem; font-weight:800; color:{_TEXT};">
                            {int(vr['weeks_active'])}
                        </div>
                        <div style="font-size:0.7rem; color:{_MUTED}; font-weight:600;
                                    text-transform:uppercase;">Weeks Active</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="background:{bg_v}; color:{tc_v}; border:1px solid {bd_v};
                                    border-radius:10px; padding:4px 12px; font-size:0.78rem;
                                    font-weight:700; margin-top:2px;">{lb_v}</div>
                        <div style="font-size:0.7rem; color:{_MUTED}; font-weight:600;
                                    text-transform:uppercase; margin-top:4px;">
                            Latest Week DEA: {format_dea(mrw_dea_v) if pd.notna(mrw_dea_v) else '—'}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Two charts side by side ────────────────────────────────────
        ch_left, ch_right = st.columns(2, gap="large")

        # Weekly PDD volume trend
        with ch_left:
            st.markdown(
                f'<div style="font-weight:700; color:{_TEXT}; font-size:0.95rem; '
                f'margin-bottom:0.4rem;">Weekly PDD Shipments</div>',
                unsafe_allow_html=True,
            )
            fig_pdd = go.Figure(
                go.Bar(
                    x=vendor_weekly["week_id"].astype(int),
                    y=vendor_weekly["pdd_shipments"],
                    marker_color=_ORANGE,
                    text=vendor_weekly["pdd_shipments"].apply(
                        lambda v: format_pdd(int(v))
                    ),
                    textposition="outside",
                    textfont=dict(size=10),
                    hovertemplate="Week %{x}<br>PDD: <b>%{y:,}</b><extra></extra>",
                )
            )
            fig_pdd.update_layout(
                **_PLOTLY_LAYOUT,
                height=280,
                xaxis=dict(
tickangle=-45, tickfont=dict(size=9), showgrid=False,
                           title="Week ID", tickformat="d"),
                yaxis=dict(showgrid=True, gridcolor=_BORDER, zeroline=False,
                           tickformat=",", title="PDD Shipments"),
                showlegend=False,
            )
            st.plotly_chart(fig_pdd, use_container_width=True)

        # Weekly DEA trend with threshold lines
        with ch_right:
            st.markdown(
                f'<div style="font-weight:700; color:{_TEXT}; font-size:0.95rem; '
                f'margin-bottom:0.4rem;">Weekly DEA % vs Threshold</div>',
                unsafe_allow_html=True,
            )
            dea_pct_series  = vendor_weekly["dea_pct"]  * 100
            udea_pct_series = vendor_weekly["unpadded_dea_pct"] * 100

            fig_dea = go.Figure()
            fig_dea.add_trace(go.Scatter(
                x=vendor_weekly["week_id"].astype(int),
                y=dea_pct_series,
                mode="lines+markers",
                name="DEA %",
                line=dict(color=_ORANGE, width=2.5),
                marker=dict(size=6, color=_ORANGE,
                            line=dict(width=1.5, color="#0A1628")),
                hovertemplate="Week %{x}<br>DEA: <b>%{y:.1f}%</b><extra></extra>",
            ))
            fig_dea.add_trace(go.Scatter(
                x=vendor_weekly["week_id"].astype(int),
                y=udea_pct_series,
                mode="lines+markers",
                name="Unpadded DEA %",
                line=dict(color="#4A90D9", width=2, dash="dot"),
                marker=dict(size=5, color="#4A90D9"),
                hovertemplate="Week %{x}<br>Unpadded DEA: <b>%{y:.1f}%</b><extra></extra>",
            ))
            # Threshold reference lines
            fig_dea.add_hline(y=90, line_dash="dash", line_color=_RED,
                              annotation_text="90% threshold",
                              annotation_position="bottom right",
                              annotation_font_size=10)
            fig_dea.add_hline(y=95, line_dash="dash", line_color=_YELLOW,
                              annotation_text="95% on-track",
                              annotation_position="top right",
                              annotation_font_size=10)
            fig_dea.update_layout(
                **_PLOTLY_LAYOUT,
                height=280,
                xaxis=dict(
tickangle=-45, tickfont=dict(size=9), showgrid=False,
                           title="Week ID", tickformat="d"),
                yaxis=dict(range=[0, 105], showgrid=True, gridcolor=_BORDER,
                           ticksuffix="%", title="DEA %"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02,
                            xanchor="right", x=1, font=dict(size=11)),
            )
            st.plotly_chart(fig_dea, use_container_width=True)

        # ── Week-by-week detail table ──────────────────────────────────
        with st.expander("📋 Week-by-week data table", expanded=False):
            detail = vendor_weekly[[
                "week_id", "pdd_shipments", "dea_pct", "unpadded_dea_pct"
            ]].copy()

            detail["DEA %"]          = detail["dea_pct"].apply(format_dea)
            detail["Unpadded DEA %"] = detail["unpadded_dea_pct"].apply(format_dea)
            detail["PDD Shipments"]  = detail["pdd_shipments"].apply(
                lambda v: format_pdd(int(v))
            )
            detail["DEA Status"] = detail["dea_pct"].apply(
                lambda v: risk_classification(v) if pd.notna(v) else "—"
            ).map({
                "on_track": "✅ On Track",
                "at_risk": "⚠️ At Risk",
                "below_threshold": "🔴 Below Threshold",
            })

            detail_display = detail.rename(columns={"week_id": "Week ID"})[[
                "Week ID", "PDD Shipments", "DEA %", "Unpadded DEA %", "DEA Status"
            ]]

            st.dataframe(
                detail_display,
                use_container_width=True,
                hide_index=True,
            )

# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="text-align:right; font-size:0.75rem; color:{_MUTED}; '
    f'border-top:1px solid {_BORDER}; padding-top:0.6rem; margin-top:1rem;">'
    f'VOC Command Center · NA Direct Fulfillment · Most recent week: <strong>{mrw}</strong>'
    f'</div>',
    unsafe_allow_html=True,
)
