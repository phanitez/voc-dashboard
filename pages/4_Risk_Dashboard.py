"""
pages/4_Risk_Dashboard.py
Risk Dashboard — DEA threshold alerts, at-risk vendor table,
concentration risk panel, and volume share chart.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from voc.ui import inject_dark_css

from voc.aggregator import (
    compute_vendor_metrics,
    compute_weekly_aggregates,
    most_recent_week,
    risk_classification,
    top_vendors_by_pdd,
)
from voc.filters import apply_filters
from voc.formatters import format_dea, format_pdd

st.set_page_config(
    page_title="Risk Dashboard | VOC Command Center",
    page_icon="⚠️",
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

_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=_TEXT),
    margin=dict(l=0, r=0, t=36, b=0),
    hoverlabel=dict(bgcolor="#0F2040", bordercolor="#2A4E7A",
                    font_size=13, font_family="Inter, sans-serif"),
)

def _section(text: str) -> None:
    st.markdown(
        f'<p style="font-size:0.72rem; font-weight:700; color:{_MUTED}; '
        f'text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.5rem;">'
        f'{text}</p>',
        unsafe_allow_html=True,
    )

def _badge(label: str, bg: str, color: str, border: str) -> str:
    return (
        f'<span style="background:{bg}; color:{color}; border:1px solid {border}; '
        f'border-radius:10px; padding:2px 9px; font-size:0.72rem; font-weight:700; '
        f'white-space:nowrap;">{label}</span>'
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

# ── Page header ────────────────────────────────────────────────────────────
st.markdown(
    f'<h1 style="color:{_TEXT}; font-weight:700; font-size:1.7rem; '
    f'border-bottom:3px solid {_ORANGE}; padding-bottom:0.4rem; margin-bottom:0.25rem;">'
    f'⚠️ Risk Dashboard</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p style="color:{_MUTED}; font-size:0.9rem; margin-bottom:1.2rem;">'
    f'DEA threshold alerts, at-risk vendor prioritisation, and concentration risk analysis.</p>',
    unsafe_allow_html=True,
)

if filtered_df.empty:
    st.info("No data matches the current filters. Adjust the sidebar filters.")
    st.stop()

# ── Pre-compute ────────────────────────────────────────────────────────────
vendor_metrics = compute_vendor_metrics(filtered_df)
weekly_agg     = compute_weekly_aggregates(filtered_df)
mrw            = most_recent_week(filtered_df)

# Most-recent-week snapshot
mrw_df = filtered_df[filtered_df["week_id"] == mrw] if mrw else pd.DataFrame()

# Risk tiers (by most_recent_week_dea)
def _tier(v):
    if pd.isna(v): return "no_data"
    return risk_classification(v)

vm = vendor_metrics.copy()
vm["risk_tier"] = vm["most_recent_week_dea"].apply(_tier)

below_df = vm[vm["risk_tier"] == "below_threshold"]
atrisk_df = vm[vm["risk_tier"] == "at_risk"]
ontrack_df = vm[vm["risk_tier"] == "on_track"]
nodata_df  = vm[vm["risk_tier"] == "no_data"]

n_total  = len(vm)
n_below  = len(below_df)
n_atrisk = len(atrisk_df)
n_on     = len(ontrack_df)

# Concentration
top3 = top_vendors_by_pdd(vendor_metrics, n=3)
top3_share = float(top3["volume_share_pct"].sum()) if not top3.empty else 0.0
conc_risk = top3_share > 80.0

# ══════════════════════════════════════════════════════════════════════════
# Section 1 — Risk KPI Cards
# ══════════════════════════════════════════════════════════════════════════
_section("RISK SUMMARY — MOST RECENT WEEK")

c1, c2, c3, c4 = st.columns(4)

def _risk_kpi(col, icon, label, value, bg, border_color, text_color, sub=""):
    with col:
        st.markdown(
            f'<div style="background:{bg}; border:1px solid {border_color}; '
            f'border-top:4px solid {border_color}; border-radius:12px; '
            f'padding:1rem 1.2rem; box-shadow:0 2px 8px rgba(0,0,0,0.05);">'
            f'<div style="font-size:1.4rem;">{icon}</div>'
            f'<div style="font-size:0.73rem; font-weight:700; color:{text_color}; '
            f'text-transform:uppercase; letter-spacing:0.07em; margin-top:4px;">{label}</div>'
            f'<div style="font-size:2rem; font-weight:800; color:{text_color}; '
            f'line-height:1.15; margin-top:2px;">{value}</div>'
            f'<div style="font-size:0.78rem; color:{text_color}; opacity:0.7; '
            f'margin-top:2px;">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

_risk_kpi(c1, "🔴", "Below Threshold", n_below,
          "rgba(231,76,60,0.12)", "#E74C3C", "#E74C3C", sub="DEA < 90%")
_risk_kpi(c2, "⚠️", "At Risk", n_atrisk,
          "rgba(243,156,18,0.12)", "rgba(243,156,18,0.4)", "#F39C12", sub="DEA 90–95%")
_risk_kpi(c3, "✅", "On Track", n_on,
          "rgba(46,204,113,0.12)", "rgba(46,204,113,0.4)", "#2ECC71", sub="DEA > 95%")
_risk_kpi(c4, "📊", "Concentration",
          f"{top3_share:.0f}%",
          "rgba(231,76,60,0.12)" if conc_risk else "rgba(46,204,113,0.12)",
          "rgba(231,76,60,0.4)" if conc_risk else "rgba(46,204,113,0.4)",
          "#E74C3C" if conc_risk else "#2ECC71",
          sub="Top-3 volume share" + (" ⚠️ High" if conc_risk else " ✅ Normal"))

st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Section 2 — Alert Table (Below Threshold + At Risk)
# ══════════════════════════════════════════════════════════════════════════
_section("DEA ALERT TABLE — VENDORS REQUIRING ATTENTION")

alert_df = pd.concat([below_df, atrisk_df], ignore_index=True)

if alert_df.empty:
    st.markdown(
        f'<div style="background:rgba(46,204,113,0.1); border:1px solid rgba(46,204,113,0.4); border-radius:10px; '
        f'padding:1.2rem; text-align:center; color:#2ECC71; font-weight:700;">'
        f'✅ No vendors are below threshold or at risk in the most recent week (Week {mrw}). '
        f'All vendors are On Track.</div>',
        unsafe_allow_html=True,
    )
else:
    # Build styled HTML table
    th = (
        f"background:#142850; color:{_TEXT}; font-size:0.73rem; font-weight:700; "
        f"text-transform:uppercase; letter-spacing:0.06em; padding:9px 10px; "
        f"border-bottom:2px solid {_ORANGE}; white-space:nowrap;"
    )
    headers = [
        ("Risk Level","center","120px"),("Vendor Code","left","90px"),
        ("Vendor Name","left","220px"),("Latest DEA %","right","110px"),
        ("Avg DEA %","right","100px"),("Weeks Active","center","90px"),
        ("Vol Share","right","90px"),("Total PDD","right","110px"),
    ]
    hrow = "".join(
        f'<th style="{th} text-align:{a}; min-width:{w};">{h}</th>'
        for h,a,w in headers
    )

    rows_html = ""
    for i, row in alert_df.sort_values(
        ["risk_tier","most_recent_week_dea"], ascending=[True, True]
    ).reset_index(drop=True).iterrows():
        rc = row["risk_tier"]
        if rc == "below_threshold":
            badge = _badge("🔴 Below Threshold","rgba(231,76,60,0.1)","#E74C3C","rgba(231,76,60,0.4)")
            row_bg = "rgba(231,76,60,0.08)" if i % 2 == 0 else "rgba(231,76,60,0.12)"
        else:
            badge = _badge("⚠️ At Risk","rgba(243,156,18,0.1)","#F39C12","rgba(243,156,18,0.4)")
            row_bg = "rgba(243,156,18,0.08)" if i % 2 == 0 else "rgba(243,156,18,0.12)"

        mrw_dea = row["most_recent_week_dea"]
        mrw_str = format_dea(mrw_dea) if pd.notna(mrw_dea) else "—"
        avg_str = format_dea(row["weighted_dea_pct"]) if pd.notna(row["weighted_dea_pct"]) else "—"

        td = f"font-size:0.85rem; padding:9px 10px; border-bottom:1px solid {_BORDER}; vertical-align:middle;"
        rows_html += (
            f'<tr style="background:{row_bg};">'
            f'<td style="{td} text-align:center;">{badge}</td>'
            f'<td style="{td} font-weight:700; color:{_ORANGE};">{row["vendor_code"]}</td>'
            f'<td style="{td}">{row["vendor_name"]}</td>'
            f'<td style="{td} text-align:right; font-weight:700; color:{_RED};">{mrw_str}</td>'
            f'<td style="{td} text-align:right; color:{_MUTED};">{avg_str}</td>'
            f'<td style="{td} text-align:center;">{int(row["weeks_active"])}</td>'
            f'<td style="{td} text-align:right;">{row["volume_share_pct"]:.1f}%</td>'
            f'<td style="{td} text-align:right; font-weight:600;">'
            f'{format_pdd(int(row["total_pdd"]))}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<div style="overflow-x:auto; border-radius:10px; border:1px solid {_BORDER}; '
        f'box-shadow:0 2px 8px rgba(0,0,0,0.05);">'
        f'<table style="width:100%; border-collapse:collapse;">'
        f'<thead><tr>{hrow}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>',
        unsafe_allow_html=True,
    )

    # Week history for alerted vendors — sparkline heatmap
    with st.expander(f"📋 Historical DEA for {len(alert_df)} alerted vendor(s)", expanded=False):
        alert_codes = alert_df["vendor_code"].tolist()
        hist = filtered_df[filtered_df["vendor_code"].isin(alert_codes)].copy()
        if not hist.empty:
            pivot = hist.pivot_table(
                index="vendor_code", columns="week_id", values="dea_pct", aggfunc="first"
            ) * 100
            pivot.columns = [int(c) for c in pivot.columns]

            colorscale = [[0,"#E74C3C"],[0.5,"#F39C12"],[1,"#2ECC71"]]
            fig_heat = go.Figure(go.Heatmap(
                z=pivot.values,
                x=list(pivot.columns),
                y=list(pivot.index),
                colorscale=colorscale,
                zmin=0, zmax=100,
                text=[[f"{v:.1f}%" if pd.notna(v) else "—" for v in row]
                      for row in pivot.values],
                texttemplate="%{text}",
                textfont=dict(size=9),
                hovertemplate="Vendor: %{y}<br>Week: %{x}<br>DEA: %{z:.1f}%<extra></extra>",
                colorbar=dict(title="DEA %", ticksuffix="%"),
            ))
            fig_heat.update_layout(
                **_PLOTLY_LAYOUT,
                height=max(200, len(alert_codes) * 55 + 60),
                xaxis=dict(
tickangle=-45, tickfont=dict(size=9), title="Week ID", tickformat="d"),
                yaxis=dict(tickfont=dict(size=10)),
            )
            st.plotly_chart(fig_heat, use_container_width=True)

st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Section 3 — Concentration Risk + Volume Distribution
# ══════════════════════════════════════════════════════════════════════════
_section("VENDOR CONCENTRATION RISK")

conc_left, conc_right = st.columns([1, 1.4], gap="large")

with conc_left:
    risk_bg = "rgba(231,76,60,0.1)" if conc_risk else "rgba(46,204,113,0.1)"
    risk_bd = "#E74C3C" if conc_risk else "#2ECC71"
    risk_tc = "#E74C3C" if conc_risk else "#2ECC71"
    risk_lbl = "⚠️ High Concentration Risk" if conc_risk else "✅ Concentration Normal"

    st.markdown(
        f'<div style="background:{risk_bg}; border:1px solid {risk_bd}; '
        f'border-radius:12px; padding:1.1rem 1.4rem; margin-bottom:1rem;">'
        f'<div style="font-weight:700; color:{risk_tc}; font-size:0.95rem;">{risk_lbl}</div>'
        f'<div style="font-size:2rem; font-weight:800; color:{risk_tc}; margin:4px 0;">'
        f'{top3_share:.1f}%</div>'
        f'<div style="font-size:0.82rem; color:{risk_tc}; opacity:0.85;">'
        f'Top-3 vendors\' combined volume share'
        f'{"— exceeds 80% threshold" if conc_risk else "— within 80% threshold"}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # Top-5 vendor concentration rows
    top5_conc = vendor_metrics.head(5)
    for i, row in top5_conc.iterrows():
        dea_v = row["weighted_dea_pct"]
        rc = risk_classification(dea_v) if pd.notna(dea_v) else "below_threshold"
        bg_m  = {"on_track":"rgba(46,204,113,0.1)","at_risk":"rgba(243,156,18,0.1)","below_threshold":"rgba(231,76,60,0.1)"}[rc]
        tc_m  = {"on_track":"#2ECC71","at_risk":"#F39C12","below_threshold":"#E74C3C"}[rc]
        bd_m  = {"on_track":"rgba(46,204,113,0.4)","at_risk":"rgba(243,156,18,0.4)","below_threshold":"rgba(231,76,60,0.4)"}[rc]
        lb_m  = {"on_track":"On Track","at_risk":"At Risk","below_threshold":"Below Thr."}[rc]

        bar_w = int(row["volume_share_pct"] / max(float(top5_conc["volume_share_pct"].max()), 1) * 120)
        st.markdown(
            f'<div style="background:#0F2040; border:1px solid {_BORDER}; border-radius:8px; '
            f'padding:0.55rem 1rem; margin-bottom:0.5rem;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<div><div style="font-weight:700; color:{_TEXT}; font-size:0.88rem;">#{i+1} {row["vendor_code"]}</div>'
            f'<div style="font-size:0.74rem; color:{_MUTED};">{row["vendor_name"][:38]}</div></div>'
            f'<div style="text-align:right;">'
            f'<div style="font-weight:700; color:{_TEXT};">{row["volume_share_pct"]:.1f}%</div>'
            f'<div style="background:{bg_m}; color:{tc_m}; border:1px solid {bd_m}; '
            f'border-radius:8px; padding:1px 7px; font-size:0.7rem; font-weight:700; display:inline-block;">'
            f'{format_dea(dea_v) if pd.notna(dea_v) else "—"} · {lb_m}</div></div></div>'
            f'<div style="margin-top:5px; height:5px; background:#1E3A60; border-radius:3px;">'
            f'<div style="width:{bar_w}px; height:5px; background:{_ORANGE}; border-radius:3px;"></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

with conc_right:
    if not vendor_metrics.empty:
        top5c = vendor_metrics.head(5).copy()
        others = max(0.0, 100.0 - top5c["volume_share_pct"].sum())
        labels = list(top5c["vendor_code"]) + (["Others"] if others > 0.01 else [])
        values = list(top5c["volume_share_pct"]) + ([others] if others > 0.01 else [])
        colors = ["#F6A623","#2A3548","#4A90D9","#2ECC71","#9B59B6","#8892A4"][:len(labels)]

        fig_pie = go.Figure(go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker=dict(colors=colors, line=dict(color="#0A1628", width=2)),
            textinfo="label+percent",
            textfont=dict(size=11),
            hovertemplate="<b>%{label}</b><br>Share: %{value:.1f}%<extra></extra>",
        ))
        fig_pie.update_layout(
            **_PLOTLY_LAYOUT,
            height=340,
            showlegend=False,
            annotations=[dict(
                text=f'<b>{top3_share:.0f}%</b><br><span style="font-size:10px">Top 3</span>',
                x=0.5, y=0.5, font=dict(size=16, color="#E8EAF0"), showarrow=False,
            )],
        )
        st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# Section 4 — DEA Distribution Bar Chart (all vendors, latest week)
# ══════════════════════════════════════════════════════════════════════════
_section(f"DEA % DISTRIBUTION — WEEK {mrw}")

if mrw_df.empty:
    st.info("No data for most recent week.")
else:
    mrw_sorted = mrw_df.sort_values("dea_pct", ascending=True)
    bar_colors = [
        (_GREEN if v > 0.95 else _YELLOW if v >= 0.90 else _RED)
        for v in mrw_sorted["dea_pct"]
    ]

    fig_dist = go.Figure(go.Bar(
        x=mrw_sorted["dea_pct"] * 100,
        y=mrw_sorted["vendor_code"],
        orientation="h",
        marker_color=bar_colors,
        text=[f"{v*100:.1f}%" for v in mrw_sorted["dea_pct"]],
        textposition="outside",
        textfont=dict(size=10, color="#E8EAF0"),
        customdata=mrw_sorted[["vendor_name","pdd_shipments"]].values,
        hovertemplate=(
            "<b>%{y}</b> — %{customdata[0]}<br>"
            "DEA: <b>%{x:.1f}%</b><br>"
            "PDD: %{customdata[1]:,}<extra></extra>"
        ),
    ))
    fig_dist.add_vline(x=90, line_dash="dash", line_color=_RED,
                       annotation_text="90%", annotation_position="bottom",
                       annotation_font_size=10)
    fig_dist.add_vline(x=95, line_dash="dot", line_color=_YELLOW,
                       annotation_text="95%", annotation_position="top",
                       annotation_font_size=10)
    fig_dist.update_layout(
        **_PLOTLY_LAYOUT,
        height=max(280, len(mrw_sorted) * 32 + 60),
        xaxis=dict(range=[0, 107], ticksuffix="%", showgrid=True, gridcolor=_BORDER,
                   title="DEA %"),
        yaxis=dict(showgrid=False, tickfont=dict(size=10)),
        showlegend=False,
    )
    st.plotly_chart(fig_dist, use_container_width=True)

    # Colour legend
    st.markdown(
        f'<div style="display:flex; gap:14px; font-size:0.76rem; color:{_MUTED}; margin-top:-0.4rem;">'
        f'<span>🟢 &gt;95% On Track</span>'
        f'<span>🟡 90–95% At Risk</span>'
        f'<span>🔴 &lt;90% Below Threshold</span>'
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
