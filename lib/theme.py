"""
GS AWM Design System
====================
Single source of truth for colors, typography, chart styling, and CSS.

Usage in every page (after st.set_page_config):
    from lib.theme import setup, chart, banner

    setup()                          # injects CSS
    banner("Page Title")             # full-width branded header with date/time
    banner("Page Title", beta=True)  # same but with a Beta badge
    fig = px.line(...)
    st.plotly_chart(chart(fig))      # applies GS chart defaults

To update the brand color, change PRIMARY below — everything else follows.
To rename the app, change APP_NAME below.
"""

# ── App identity ──────────────────────────────────────────────────────────────

APP_NAME = "Goldman Sachs AWM Pulse"


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
# Merged into every figure via chart(fig). Change here to affect all charts.

_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
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
    """Apply GS AWM Plotly defaults to a figure. Returns fig for chaining.

        st.plotly_chart(theme.chart(fig, showlegend=False))
    """
    fig.update_layout(**_PLOTLY_LAYOUT)
    if extra_layout:
        fig.update_layout(**extra_layout)
    return fig


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = f"""
<style>
/* ── Inter font ──────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {{
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif !important;
}}

/* ── Reduce default page padding ─────────────────────────────────────────── */
.main .block-container {{
    padding-top: 1rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
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

/* ── Banner component ────────────────────────────────────────────────────── */
.gs-banner {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: {PRIMARY};
    color: {SURFACE};
    padding: 0.6rem 1.4rem;
    border-radius: 8px;
    margin-bottom: 0.4rem;
    line-height: 1;
}}
.gs-banner-left {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
}}
.gs-banner-appname {{
    font-weight: 700;
    font-size: 1rem;
    letter-spacing: 0.01em;
    white-space: nowrap;
}}
.gs-banner-divider {{
    opacity: 0.4;
    font-weight: 300;
    font-size: 1.1rem;
}}
.gs-banner-pagetitle {{
    font-weight: 400;
    font-size: 1rem;
    opacity: 0.9;
}}
.gs-banner-beta {{
    background: rgba(255,255,255,0.18);
    border: 1px solid rgba(255,255,255,0.45);
    color: #fff;
    font-size: 0.58rem;
    font-weight: 700;
    padding: 0.12rem 0.4rem;
    border-radius: 3px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    vertical-align: middle;
}}
.gs-banner-right {{
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.8rem;
    opacity: 0.8;
    font-variant-numeric: tabular-nums;
    font-weight: 400;
    white-space: nowrap;
}}
.gs-banner-sep {{
    opacity: 0.45;
}}
</style>
"""

_FULL_BLEED_CSS = """
<style>
.main .block-container {
    padding-top: 0.5rem !important;
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
    padding-bottom: 0 !important;
    max-width: 100% !important;
}
</style>
"""


# ── Public API ────────────────────────────────────────────────────────────────

def setup() -> None:
    """Apply the GS AWM theme. Call once per page, after st.set_page_config()."""
    import streamlit as st
    st.markdown(_CSS, unsafe_allow_html=True)


def full_bleed() -> None:
    """Remove page padding — call on iframe embed pages after setup()."""
    import streamlit as st
    st.markdown(_FULL_BLEED_CSS, unsafe_allow_html=True)


def banner(page_title: str = "", beta: bool = False) -> None:
    """Render the branded app banner with app name, page title, and live date/time.

    Args:
        page_title: Sub-page label shown after the app name. Omit on the home page.
        beta:       Show a Beta badge next to the page title.
    """
    from datetime import datetime, timezone
    import streamlit as st

    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%d %b %Y")
    time_str = now.strftime("%H:%M UTC")

    page_section = ""
    if page_title:
        beta_badge = (
            ' <span class="gs-banner-beta">Beta</span>' if beta else ""
        )
        page_section = (
            f'<span class="gs-banner-divider">|</span>'
            f'<span class="gs-banner-pagetitle">{page_title}{beta_badge}</span>'
        )

    st.markdown(
        f"""
        <div class="gs-banner">
          <div class="gs-banner-left">
            <span class="gs-banner-appname">{APP_NAME}</span>
            {page_section}
          </div>
          <div class="gs-banner-right">
            <span>{date_str}</span>
            <span class="gs-banner-sep">·</span>
            <span>{time_str}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
