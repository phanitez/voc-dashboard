"""
app.py — VOC Command Center entry point.

Responsibilities:
  1. Initialise st.session_state keys with safe defaults.
  2. Render the sidebar: CSV file upload, parse summary, filter controls.
  3. Host the multi-page navigation for the pages/ directory.

Filter state written here persists across page navigation for the lifetime
of the browser session (until tab close or hard-refresh).
"""
from __future__ import annotations
import os

import streamlit as st

from voc.filters import validate_week_range
from voc.parser import parse_voc_csv, parse_voc_excel
from voc.ui import DARK_CSS

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="VOC Command Center",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS — dark-header / white-card / orange-accent theme
# Mirrors the design in the reference screenshot:
#   - Dark navy top bar  (#1E2A38)
#   - White content area with subtle card shadows
#   - Orange (#F6A623) primary accent: buttons, active tab underline, slider
#   - Clean input borders, rounded corners
# ---------------------------------------------------------------------------
st.markdown(DARK_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state initialisation (guarded — runs on every rerun)
# ---------------------------------------------------------------------------
_DEFAULTS: dict = {
    "raw_df": None,
    "parse_warnings": [],
    "filter_vendors": [],
    "filter_year": None,
    "filter_week_start": None,
    "filter_week_end": None,
    "latest_insight": None,
}
for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default
# ---------------------------------------------------------------------------
# Auto-load bundled data if no file has been uploaded yet
# ---------------------------------------------------------------------------
_AUTO_DATA_PATH = os.path.join(os.path.dirname(__file__), "VOC_data.xlsx")
if st.session_state["raw_df"] is None and os.path.exists(_AUTO_DATA_PATH):
    try:
        with open(_AUTO_DATA_PATH, "rb") as _f:
            _result = parse_voc_excel(_f.read())
        st.session_state["raw_df"] = _result.df
        st.session_state["parse_warnings"] = _result.warnings
    except Exception:
        pass  # Silently skip — user can upload manually



# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, #F6A623 0%, #E09615 100%);
            border-radius: 10px;
            padding: 14px 16px;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 10px;
        ">
            <span style="font-size:1.6rem;">📦</span>
            <div>
                <div style="color:#0A1628; font-weight:700; font-size:1rem; line-height:1.2;">
                    VOC Command Center
                </div>
                <div style="color:#3A2000; font-size:0.72rem; opacity:0.85;">
                    NA Direct Fulfillment
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ── File upload ──────────────────────────────────────────────────────
    st.subheader("📂 Data Source")
    uploaded = st.file_uploader(
        "Upload VOC Data (CSV or Excel)",
        type=["csv", "xlsx"],
        help="Upload a VOC performance file — CSV or SODA Excel (.xlsx) format accepted.",
    )

    if uploaded is not None:
        file_bytes = uploaded.read()
        try:
            if uploaded.name.lower().endswith(".xlsx"):
                result = parse_voc_excel(file_bytes)
            else:
                csv_text = file_bytes.decode("utf-8", errors="replace")
                result = parse_voc_csv(csv_text)
            st.session_state["raw_df"] = result.df
            st.session_state["parse_warnings"] = result.warnings
            # Reset all filters when a new file is loaded
            st.session_state["filter_vendors"] = []
            st.session_state["filter_year"] = None
            st.session_state["filter_week_start"] = None
            st.session_state["filter_week_end"] = None

            # Parse summary
            st.success(
                f"✅ Loaded **{result.total_ingested:,}** records"
                + (
                    f" | ⚠️ {result.total_skipped} row(s) skipped"
                    if result.total_skipped > 0
                    else ""
                )
            )
            if result.week_id_range:
                st.caption(
                    f"Week range: {result.week_id_range[0]} – {result.week_id_range[1]}"
                )
            if result.warnings:
                with st.expander(f"⚠️ {len(result.warnings)} parse warning(s)"):
                    for w in result.warnings:
                        st.text(w)

        except ValueError as exc:
            st.error(f"❌ Failed to load file: {exc}")
            st.session_state["raw_df"] = None
            st.session_state["parse_warnings"] = []

    raw_df = st.session_state["raw_df"]

    # ── Filters (only shown when data is loaded) ──────────────────────────
    st.markdown("---")
    st.subheader("🔍 Filters")

    if raw_df is not None and not raw_df.empty:
        # Vendor multi-select
        all_vendors = sorted(raw_df["vendor_code"].unique().tolist())
        vendor_labels = {
            vc: f"{vc} — {raw_df.loc[raw_df['vendor_code'] == vc, 'vendor_name'].iloc[0]}"
            for vc in all_vendors
        }
        selected_vendors = st.multiselect(
            "Vendors",
            options=all_vendors,
            default=st.session_state["filter_vendors"],
            format_func=lambda vc: vendor_labels.get(vc, vc),
            help="Leave empty to include all vendors.",
        )
        st.session_state["filter_vendors"] = selected_vendors

        # Year dropdown
        all_years = sorted(raw_df["year_id"].unique().tolist())
        year_options = ["All years"] + [str(y) for y in all_years]
        current_year_label = (
            str(st.session_state["filter_year"])
            if st.session_state["filter_year"] is not None
            else "All years"
        )
        selected_year_label = st.selectbox(
            "Year",
            options=year_options,
            index=year_options.index(current_year_label)
            if current_year_label in year_options
            else 0,
        )
        st.session_state["filter_year"] = (
            None
            if selected_year_label == "All years"
            else int(selected_year_label)
        )

        # Week range inputs
        all_weeks = sorted(raw_df["week_id"].unique().tolist())
        min_week = int(all_weeks[0])
        max_week = int(all_weeks[-1])

        col_start, col_end = st.columns(2)
        with col_start:
            week_start_input = st.number_input(
                "Week start",
                min_value=min_week,
                max_value=max_week,
                value=st.session_state["filter_week_start"] or min_week,
                step=1,
                format="%d",
            )
        with col_end:
            week_end_input = st.number_input(
                "Week end",
                min_value=min_week,
                max_value=max_week,
                value=st.session_state["filter_week_end"] or max_week,
                step=1,
                format="%d",
            )

        range_error = validate_week_range(int(week_start_input), int(week_end_input))
        if range_error:
            st.warning(f"⚠️ {range_error}")
        else:
            st.session_state["filter_week_start"] = int(week_start_input)
            st.session_state["filter_week_end"] = int(week_end_input)

        # Clear all filters
        if st.button("🗑️ Clear All Filters", use_container_width=True):
            st.session_state["filter_vendors"] = []
            st.session_state["filter_year"] = None
            st.session_state["filter_week_start"] = None
            st.session_state["filter_week_end"] = None
            st.rerun()

    else:
        st.info("Upload a CSV file above to enable filters.")

    st.markdown("---")
    st.caption("VOC Command Center · NA Direct Fulfillment")

# ---------------------------------------------------------------------------
# Main area — navigation landing
# ---------------------------------------------------------------------------
st.title("📦 VOC Command Center")

# Styled page-card grid
st.markdown(
    """
    <p style="color:#8892A4; font-size:0.95rem; margin-top:-0.5rem; margin-bottom:1.5rem;">
        Monitor DEA metrics, shipment volumes, and vendor concentration
        across the NA Direct Fulfillment VOC program.
    </p>
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap:1rem; margin-bottom:1.5rem;">
        <div style="background:#0F2040; border:1px solid #1E3A60; border-radius:10px;
                    padding:1rem 1.2rem; border-top:3px solid #F6A623;">
            <div style="font-size:1.4rem;">📊</div>
            <div style="font-weight:700; color:#E8EAF0; margin-top:4px;">Executive Summary</div>
            <div style="font-size:0.82rem; color:#8892A4; margin-top:4px;">
                KPI cards, top-3 concentration, insights
            </div>
        </div>
        <div style="background:#0F2040; border:1px solid #1E3A60; border-radius:10px;
                    padding:1rem 1.2rem; border-top:3px solid #F6A623;">
            <div style="font-size:1.4rem;">🏆</div>
            <div style="font-weight:700; color:#E8EAF0; margin-top:4px;">Vendor Performance</div>
            <div style="font-size:0.82rem; color:#8892A4; margin-top:4px;">
                Ranked table, search, drill-down
            </div>
        </div>
        <div style="background:#0F2040; border:1px solid #1E3A60; border-radius:10px;
                    padding:1rem 1.2rem; border-top:3px solid #F6A623;">
            <div style="font-size:1.4rem;">📈</div>
            <div style="font-weight:700; color:#E8EAF0; margin-top:4px;">Trend Analysis</div>
            <div style="font-size:0.82rem; color:#8892A4; margin-top:4px;">
                Weekly PDD volume &amp; DEA % charts
            </div>
        </div>
        <div style="background:#0F2040; border:1px solid #1E3A60; border-radius:10px;
                    padding:1rem 1.2rem; border-top:3px solid #E74C3C;">
            <div style="font-size:1.4rem;">⚠️</div>
            <div style="font-weight:700; color:#E8EAF0; margin-top:4px;">Risk Dashboard</div>
            <div style="font-size:0.82rem; color:#8892A4; margin-top:4px;">
                DEA threshold alerts, concentration risk
            </div>
        </div>
        <div style="background:#0F2040; border:1px solid #1E3A60; border-radius:10px;
                    padding:1rem 1.2rem; border-top:3px solid #4A90D9;">
            <div style="font-size:1.4rem;">💡</div>
            <div style="font-weight:700; color:#E8EAF0; margin-top:4px;">AI Insights</div>
            <div style="font-size:0.82rem; color:#8892A4; margin-top:4px;">
                Auto-generated observations &amp; CSV export
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="background:rgba(246,166,35,0.1); border:1px solid rgba(246,166,35,0.35); border-radius:8px;
                padding:0.75rem 1rem; margin-bottom:1rem; font-size:0.88rem; color:#F6A623;">
        <strong>Getting started:</strong>
        Upload your VOC performance CSV using the sidebar → apply filters → navigate to any page.
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state["raw_df"] is None:
    st.markdown(
        """
        <div style="background:#0F2040; border:2px dashed #F6A623; border-radius:10px;
                    padding:2rem; text-align:center; margin-top:1rem;">
            <div style="font-size:2.5rem;">📂</div>
            <div style="font-weight:600; color:#E8EAF0; font-size:1rem; margin-top:0.5rem;">
                No data loaded
            </div>
            <div style="color:#8892A4; font-size:0.88rem; margin-top:0.3rem;">
                Upload a VOC data CSV file using the sidebar to get started.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    raw_df = st.session_state["raw_df"]
    st.markdown(
        f"""
        <div style="background:rgba(46,204,113,0.08); border:1px solid rgba(46,204,113,0.3); border-radius:8px;
                    padding:0.75rem 1.2rem; display:flex; gap:2rem; flex-wrap:wrap;">
            <div>
                <span style="font-size:0.75rem; font-weight:600; color:#2ECC71;
                             text-transform:uppercase; letter-spacing:0.05em;">Records</span><br>
                <span style="font-size:1.4rem; font-weight:700; color:#E8EAF0;">
                    {len(raw_df):,}
                </span>
            </div>
            <div>
                <span style="font-size:0.75rem; font-weight:600; color:#2ECC71;
                             text-transform:uppercase; letter-spacing:0.05em;">Vendors</span><br>
                <span style="font-size:1.4rem; font-weight:700; color:#E8EAF0;">
                    {raw_df["vendor_code"].nunique()}
                </span>
            </div>
            <div>
                <span style="font-size:0.75rem; font-weight:600; color:#2ECC71;
                             text-transform:uppercase; letter-spacing:0.05em;">Weeks</span><br>
                <span style="font-size:1.4rem; font-weight:700; color:#E8EAF0;">
                    {raw_df["week_id"].nunique()}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
