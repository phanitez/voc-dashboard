"""
voc/ui.py — Dark-theme constants, CSS, and Plotly layout for VOC Command Center.

Import and use:
    from voc.ui import BG, CARD, ORANGE, TEXT, MUTED, DARK_CSS, PLOTLY_LAYOUT
    from voc.ui import inject_dark_css
"""
from __future__ import annotations

# ── Dark colour palette ────────────────────────────────────────────────────
BG      = "#0A1628"   # page background
CARD    = "#0F2040"   # card / container background
CARD2   = "#142850"   # slightly lighter alternate card
SIDE    = "#071220"   # sidebar background
BORDER  = "#1E3A60"   # borders / dividers
BORDER2 = "#2A4E7A"   # lighter border
ORANGE  = "#F6A623"   # primary accent
TEXT    = "#E8EAF0"   # primary text
MUTED   = "#8892A4"   # secondary / muted text
GREEN   = "#2ECC71"
YELLOW  = "#F39C12"
RED     = "#E74C3C"
BLUE    = "#4A90D9"
PURPLE  = "#9B59B6"

# Semantic risk colours (translucent for dark-bg cards)
RISK_BG   = {"on_track": "rgba(46,204,113,0.10)", "at_risk": "rgba(243,156,18,0.10)", "below_threshold": "rgba(231,76,60,0.10)"}
RISK_TEXT = {"on_track": GREEN,  "at_risk": YELLOW,  "below_threshold": RED}
RISK_BDR  = {"on_track": "rgba(46,204,113,0.40)", "at_risk": "rgba(243,156,18,0.40)", "below_threshold": "rgba(231,76,60,0.40)"}

# ── Shared Plotly layout defaults ──────────────────────────────────────────
PLOTLY_LAYOUT: dict = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=TEXT),
    margin=dict(l=0, r=0, t=36, b=0),
    hoverlabel=dict(bgcolor=CARD, bordercolor=BORDER2, font_size=13,
                    font_family="Inter, sans-serif"),
)

# ── Full dark CSS injected once per page ───────────────────────────────────
DARK_CSS = f"""
<style>
/* ── Base ─────────────────────────────────────────────────────────────── */
html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}
.stApp, .main {{
    background-color: {BG} !important;
}}
.main .block-container {{
    background-color: {BG};
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1440px;
}}

/* ── Header ────────────────────────────────────────────────────────────── */
header[data-testid="stHeader"] {{
    background-color: {BG} !important;
    border-bottom: 1px solid {BORDER} !important;
}}
header[data-testid="stHeader"] button svg,
header[data-testid="stHeader"] a svg {{
    fill: {TEXT} !important;
    stroke: {TEXT} !important;
}}

/* ── Sidebar ────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background-color: {SIDE} !important;
    border-right: 1px solid {BORDER} !important;
}}
section[data-testid="stSidebar"] * {{
    color: {TEXT} !important;
}}
section[data-testid="stSidebar"] hr {{
    border-color: {BORDER} !important;
}}
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] .stMultiSelect > div,
section[data-testid="stSidebar"] .stSelectbox > div {{
    background-color: {CARD} !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT} !important;
    border-radius: 6px !important;
}}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] {{
    background-color: {CARD} !important;
    border: 1px dashed {ORANGE} !important;
    border-radius: 8px !important;
}}

/* ── Headings ───────────────────────────────────────────────────────────── */
h1 {{
    color: {TEXT} !important;
    font-weight: 700 !important;
    font-size: 1.75rem !important;
    border-bottom: 3px solid {ORANGE};
    padding-bottom: 0.4rem;
    margin-bottom: 1.2rem !important;
}}
h2 {{
    color: {TEXT} !important;
    font-weight: 600 !important;
    font-size: 1.25rem !important;
}}
h3 {{
    color: {MUTED} !important;
    font-weight: 600 !important;
}}

/* ── Metric widget ──────────────────────────────────────────────────────── */
[data-testid="stMetric"] {{
    background-color: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 1rem 1.25rem !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}}
[data-testid="stMetricLabel"] {{
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: {MUTED} !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    color: {TEXT} !important;
}}

/* ── Buttons ────────────────────────────────────────────────────────────── */
.stButton > button {{
    background-color: {ORANGE} !important;
    color: #0A1628 !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.5rem 1.25rem !important;
    transition: background-color 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0 2px 6px rgba(246,166,35,0.35);
}}
.stButton > button:hover {{
    background-color: #E09615 !important;
    box-shadow: 0 4px 12px rgba(246,166,35,0.45);
}}
.stDownloadButton > button {{
    background-color: {ORANGE} !important;
    color: #0A1628 !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
}}

/* ── Tabs ───────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    border-bottom: 2px solid {BORDER};
    gap: 0;
    background: transparent;
}}
.stTabs [data-baseweb="tab"] {{
    font-weight: 500 !important;
    font-size: 0.95rem !important;
    color: {MUTED} !important;
    padding: 0.6rem 1.4rem !important;
    border-bottom: 3px solid transparent;
    margin-bottom: -2px;
    background: transparent !important;
}}
.stTabs [aria-selected="true"] {{
    color: {ORANGE} !important;
    border-bottom: 3px solid {ORANGE} !important;
    font-weight: 600 !important;
}}

/* ── Inputs ─────────────────────────────────────────────────────────────── */
input[type="number"], input[type="text"], textarea,
.stTextInput > div > div > input,
.stNumberInput > div > div > input {{
    border: 1px solid {BORDER} !important;
    border-radius: 6px !important;
    background-color: {CARD} !important;
    color: {TEXT} !important;
    font-size: 0.9rem !important;
    padding: 0.45rem 0.75rem !important;
}}
input:focus, textarea:focus {{
    border-color: {ORANGE} !important;
    box-shadow: 0 0 0 3px rgba(246,166,35,0.15) !important;
    outline: none !important;
}}

/* ── Select boxes ───────────────────────────────────────────────────────── */
[data-baseweb="select"] > div {{
    background-color: {CARD} !important;
    border-color: {BORDER} !important;
    color: {TEXT} !important;
}}
[data-baseweb="popover"] {{
    background-color: {CARD} !important;
}}
li[role="option"] {{
    background-color: {CARD} !important;
    color: {TEXT} !important;
}}
li[role="option"]:hover, li[aria-selected="true"][role="option"] {{
    background-color: {BORDER} !important;
}}

/* ── Slider ─────────────────────────────────────────────────────────────── */
.stSlider [data-baseweb="slider"] [role="slider"] {{
    background-color: {ORANGE} !important;
    border-color: {ORANGE} !important;
}}
.stSlider [data-baseweb="slider"] [data-testid="stSliderTrackFill"] {{
    background-color: {ORANGE} !important;
}}

/* ── Multiselect tags ───────────────────────────────────────────────────── */
.stMultiSelect span[data-baseweb="tag"] {{
    background-color: {ORANGE} !important;
    color: #0A1628 !important;
    border-radius: 4px !important;
    font-weight: 600 !important;
}}

/* ── DataFrames ─────────────────────────────────────────────────────────── */
.stDataFrame {{
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    overflow: hidden;
}}
.stDataFrame th {{
    background-color: {CARD2} !important;
    color: {MUTED} !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
.stDataFrame td {{
    color: {TEXT} !important;
    background-color: {CARD} !important;
    border-color: {BORDER} !important;
}}

/* ── Expanders ──────────────────────────────────────────────────────────── */
.stExpander {{
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    background-color: {CARD} !important;
}}
.stExpander summary {{
    font-weight: 600 !important;
    color: {TEXT} !important;
}}

/* ── Alerts ─────────────────────────────────────────────────────────────── */
.stAlert {{ border-radius: 8px !important; }}

/* ── Risk badges ────────────────────────────────────────────────────────── */
.badge-below-threshold {{
    background-color: rgba(231,76,60,0.12);
    color: {RED};
    border: 1px solid rgba(231,76,60,0.4);
    padding: 2px 10px; border-radius: 12px;
    font-size: 0.78rem; font-weight: 600;
}}
.badge-at-risk {{
    background-color: rgba(243,156,18,0.12);
    color: {YELLOW};
    border: 1px solid rgba(243,156,18,0.4);
    padding: 2px 10px; border-radius: 12px;
    font-size: 0.78rem; font-weight: 600;
}}
.badge-on-track {{
    background-color: rgba(46,204,113,0.12);
    color: {GREEN};
    border: 1px solid rgba(46,204,113,0.4);
    padding: 2px 10px; border-radius: 12px;
    font-size: 0.78rem; font-weight: 600;
}}

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: {CARD}; }}
::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: {ORANGE}; }}

/* ── Hide Streamlit branding ────────────────────────────────────────────── */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
</style>
"""


def inject_dark_css() -> None:
    """Call once per page — injects the full dark theme CSS."""
    import streamlit as st
    st.markdown(DARK_CSS, unsafe_allow_html=True)
