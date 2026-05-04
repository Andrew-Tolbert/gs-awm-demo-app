"""
GS AWM Design System
====================
Single source of truth for colors, typography, chart styling, and CSS.

Usage in every page (after st.set_page_config):
    from lib.theme import setup, chart

    setup()                        # injects CSS + registers Plotly template
    fig = px.line(...)
    st.plotly_chart(chart(fig))    # applies GS chart defaults

To update the brand color, change PRIMARY below; everything else follows.
"""

# ── Color tokens ──────────────────────────────────────────────────────────────

PRIMARY       = "#7297c5"   # Goldman Sachs blue — banners, buttons, accents
PRIMARY_DARK  = "#5a7aad"   # Hover / pressed state
PRIMARY_LIGHT = "#e8eef6"   # Tinted surface, selected rows, chip backgrounds

BACKGROUND    = "#f0f1f5"   # App canvas (cool lavender near-white)
SURFACE       = "#ffffff"   # Cards and panels
SURFACE_ALT   = "#f7f8fb"   # Metric cards, alternate rows, subtle insets

BORDER        = "#dde2ec"   # Dividers and input outlines
BORDER_LIGHT  = "#eef0f5"   # Hairline separators, hover outlines

TEXT_PRIMARY   = "#1a1d2e"  # Headings and body copy
TEXT_SECONDARY = "#6673a0"  # Captions, axis labels, subtitles
TEXT_MUTED     = "#9aa5be"  # Placeholders, disabled states

SUCCESS = "#00a972"   # Positive P&L / return (green)
DANGER  = "#e53e3e"   # Negative P&L / return (red)


# ── Chart palette ─────────────────────────────────────────────────────────────
# Ordered so the first color is always GS blue (portfolio), second is benchmark.

CHART_COLORS = [
    PRIMARY,     # GS Blue   — portfolio / primary series
    "#f5a623",   # Amber     — benchmark / secondary series
    "#4caf8a",   # Teal      — alpha / tertiary
    "#e57373",   # Rose
    "#9575cd",   # Lavender
    "#4db6ac",   # Teal-cyan
    "#ff8a65",   # Coral
    "#81c784",   # Sage green
]

CHART_PORTFOLIO = PRIMARY       # Portfolio return line
CHART_BENCHMARK = "#f5a623"    # Benchmark line
CHART_ALPHA     = "#4caf8a"    # Cumulative alpha area


# ── Plotly layout defaults ────────────────────────────────────────────────────
# These are merged into every figure via chart(fig). Add or override keys here
# to change how all charts look at once.

_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",   # transparent — inherits card/page bg
    plot_bgcolor="rgba(0,0,0,0)",
    colorway=CHART_COLORS,
    margin=dict(l=0, r=0, t=4, b=0),
    font=dict(
        family="Inter, Helvetica Neue, Arial, sans-serif",
        size=12,
        color=TEXT_SECONDARY,
    ),
    xaxis=dict(
        gridcolor=BORDER_LIGHT,
        linecolor=BORDER,
        tickcolor=BORDER,
        tickfont=dict(color=TEXT_SECONDARY),
    ),
    yaxis=dict(
        gridcolor=BORDER_LIGHT,
        linecolor=BORDER,
        tickcolor=BORDER,
        tickfont=dict(color=TEXT_SECONDARY),
    ),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_SECONDARY),
    ),
)


def chart(fig, **extra_layout):
    """Apply GS AWM Plotly defaults to a figure.

    Returns the figure so calls can be chained:
        st.plotly_chart(theme.chart(fig, showlegend=False))
    """
    fig.update_layout(**_PLOTLY_LAYOUT)
    if extra_layout:
        fig.update_layout(**extra_layout)
    return fig


# ── CSS ───────────────────────────────────────────────────────────────────────
# Targets Streamlit elements that config.toml cannot reach.
# All color references use the tokens above so a single change propagates.

_CSS = f"""
<style>
/* ── Inter font ──────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {{
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif !important;
}}

/* ── Top toolbar border ──────────────────────────────────────────────────── */
[data-testid="stHeader"] {{
    background-color: {SURFACE};
    border-bottom: 2px solid {PRIMARY};
}}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {{
    border-right: 1px solid {BORDER};
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: {PRIMARY};
}}
[data-testid="stSidebarNavItems"] [aria-selected="true"] {{
    background-color: {PRIMARY_LIGHT};
    border-radius: 6px;
}}
[data-testid="stSidebarNavItems"] [aria-selected="true"] span {{
    color: {PRIMARY} !important;
}}

/* ── Heading typography ──────────────────────────────────────────────────── */
h1 {{
    font-weight: 700;
    letter-spacing: -0.02em;
    color: {TEXT_PRIMARY};
}}
h2 {{
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}
h3 {{
    font-weight: 600;
    color: {TEXT_PRIMARY};
    padding-left: 0.65rem;
    border-left: 3px solid {PRIMARY};
}}

/* ── Metric cards ────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {{
    background-color: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-left: 3px solid {PRIMARY};
    border-radius: 8px;
    padding: 0.75rem 1rem !important;
}}
[data-testid="stMetricLabel"] p {{
    font-size: 0.72rem !important;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {TEXT_SECONDARY} !important;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.55rem !important;
    font-weight: 700 !important;
    color: {TEXT_PRIMARY} !important;
}}

/* ── Page links (home screen nav tiles) ──────────────────────────────────── */
[data-testid="stPageLink"] a {{
    background-color: {PRIMARY} !important;
    color: {SURFACE} !important;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 0.65rem 1.2rem;
    border-radius: 8px;
    text-decoration: none !important;
    text-align: center;
    display: block;
    transition: background-color 0.15s ease;
}}
[data-testid="stPageLink"] a:hover {{
    background-color: {PRIMARY_DARK} !important;
}}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton > button {{
    font-weight: 600;
    border-radius: 6px;
    font-size: 0.875rem;
    transition: background-color 0.15s ease, border-color 0.15s ease;
}}
/* Suggested-question chips (Genie page) */
[data-testid="stHorizontalBlock"] .stButton > button {{
    background-color: {PRIMARY_LIGHT};
    color: {PRIMARY};
    border: 1px solid {BORDER};
    font-size: 0.82rem;
    padding: 0.3rem 0.75rem;
    white-space: normal;
    height: auto;
    line-height: 1.4;
}}
[data-testid="stHorizontalBlock"] .stButton > button:hover {{
    background-color: #d0def2;
    border-color: {PRIMARY};
}}

/* ── Dataframe ───────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] > div {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    overflow: hidden;
}}

/* ── Divider ─────────────────────────────────────────────────────────────── */
hr {{
    border-top: 1px solid {BORDER_LIGHT} !important;
}}

/* ── Chat messages ───────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {{
    border-radius: 10px;
    border: 1px solid {BORDER_LIGHT};
}}

/* ── Expander label ──────────────────────────────────────────────────────── */
[data-testid="stExpander"] summary {{
    font-size: 0.85rem;
    color: {TEXT_SECONDARY};
    font-weight: 500;
}}

/* ── Caption text ────────────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] p {{
    color: {TEXT_MUTED};
    font-size: 0.78rem;
}}

/* ─────────────────────────────────────────────────────────────────────────── */
/* Utility classes — use via st.markdown(..., unsafe_allow_html=True)          */
/* ─────────────────────────────────────────────────────────────────────────── */

/* Full-width GS blue banner */
.gs-banner {{
    background: {PRIMARY};
    color: {SURFACE};
    padding: 0.55rem 1.2rem;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    margin-bottom: 0.25rem;
}}
</style>
"""


# ── Public API ────────────────────────────────────────────────────────────────

def setup() -> None:
    """Apply the GS AWM theme to the current page.

    Call once per page, immediately after st.set_page_config().
    """
    import streamlit as st
    st.markdown(_CSS, unsafe_allow_html=True)


def banner(text: str) -> None:
    """Render a full-width GS blue banner heading via st.markdown."""
    import streamlit as st
    st.markdown(f'<div class="gs-banner">{text}</div>', unsafe_allow_html=True)
