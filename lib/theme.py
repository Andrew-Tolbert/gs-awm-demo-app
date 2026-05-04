"""
GS AWM Design System
====================
Single source of truth for colors, typography, chart styling, and CSS.

Usage in every page:
    from lib.theme import banner, full_bleed, chart
    # setup() is called once in app.py — pages call banner() directly

    banner("Portfolio Insight")          # GS blue sub-banner with page title + time
    banner("Advisor 360", beta=True)     # same, with a Beta badge
    st.plotly_chart(chart(fig))          # apply GS chart defaults

To update:
    Brand color  → change PRIMARY
    Header color → change HEADER_COLOR
    App name     → change APP_NAME
"""

# ── App identity ──────────────────────────────────────────────────────────────

APP_NAME     = "Goldman Sachs AWM Pulse"
HEADER_COLOR = "#475b72"   # Dark navy — top Streamlit header bar


# ── Color tokens ──────────────────────────────────────────────────────────────

PRIMARY       = "#7297c5"   # Goldman Sachs blue — sub-banners, buttons, accents
PRIMARY_DARK  = "#5a7aad"   # Hover / pressed
PRIMARY_LIGHT = "#e8eef6"   # Tinted surface, chip backgrounds

BACKGROUND    = "#f0f1f5"   # App canvas (cool lavender near-white)
SURFACE       = "#ffffff"   # Cards and panels
SURFACE_ALT   = "#f7f8fb"   # Metric cards, alternate rows

BORDER        = "#dde2ec"   # Dividers and input outlines
BORDER_LIGHT  = "#eef0f5"   # Hairline separators

TEXT_PRIMARY   = "#1a1d2e"  # Headings and body copy
TEXT_SECONDARY = "#6673a0"  # Captions, axis labels, subtitles
TEXT_MUTED     = "#9aa5be"  # Placeholders, disabled states

SUCCESS = "#00a972"   # Positive P&L / return
DANGER  = "#e53e3e"   # Negative P&L / return


# ── Chart palette ─────────────────────────────────────────────────────────────

CHART_COLORS = [
    PRIMARY,     # GS Blue   — portfolio / primary series
    "#f5a623",   # Amber     — benchmark
    "#4caf8a",   # Teal      — alpha
    "#e57373",   # Rose
    "#9575cd",   # Lavender
    "#4db6ac",   # Teal-cyan
    "#ff8a65",   # Coral
    "#81c784",   # Sage green
]

CHART_PORTFOLIO = PRIMARY
CHART_BENCHMARK = "#f5a623"
CHART_ALPHA     = "#4caf8a"


# ── Plotly layout defaults ────────────────────────────────────────────────────

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
    """Apply GS AWM Plotly defaults. Returns fig for chaining."""
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

/* ── Header bar — app name centered via ::after, no JS required ──────────── */
[data-testid="stHeader"] {{
    background-color: {HEADER_COLOR};
    position: relative;
}}
[data-testid="stHeader"]::after {{
    content: "{APP_NAME}";
    position: absolute;
    left: 3.75rem;
    top: 50%;
    transform: translateY(-50%);
    color: #fff;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    white-space: nowrap;
    pointer-events: none;
}}
/* Tint the hamburger + deploy icons to match the header */
[data-testid="stHeader"] button svg,
[data-testid="stHeader"] [data-testid="stToolbar"] svg {{
    fill: rgba(255,255,255,0.8) !important;
    color: rgba(255,255,255,0.8) !important;
}}

/* ── Page padding — padding-top must clear the fixed ~60px header ────────── */
.main .block-container {{
    padding-top: 4.5rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    padding-bottom: 1rem !important;
    max-width: 100% !important;
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
h2 {{ font-weight: 600; color: {TEXT_PRIMARY}; }}
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
hr {{ border-top: 1px solid {BORDER_LIGHT} !important; }}

/* ── Chat messages ───────────────────────────────────────────────────────── */
[data-testid="stChatMessage"] {{
    border-radius: 10px;
    border: 1px solid {BORDER_LIGHT};
}}

/* ── Expander ────────────────────────────────────────────────────────────── */
[data-testid="stExpander"] summary {{
    font-size: 0.85rem;
    color: {TEXT_SECONDARY};
    font-weight: 500;
}}

/* ── Caption ─────────────────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] p {{
    color: {TEXT_MUTED};
    font-size: 0.78rem;
}}

/* ── Sub-banner (gs-banner) ──────────────────────────────────────────────── */
.gs-banner {{
    background: {PRIMARY};
    color: #fff;
    padding: 0.5rem 1.2rem;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: baseline;
    gap: 0.6rem;
}}
.gs-banner-time {{
    font-size: 0.75rem;
    font-weight: 400;
    opacity: 0.75;
    font-variant-numeric: tabular-nums;
}}
.gs-banner-beta {{
    font-size: 0.6rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    background: rgba(255,255,255,0.2);
    border: 1px solid rgba(255,255,255,0.4);
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    vertical-align: middle;
}}
</style>
"""

_FULL_BLEED_CSS = """
<style>
/* Iframe embed pages — minimal side/bottom padding, keep top header clearance */
.main .block-container {
    padding-top: 4.5rem !important;
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
    padding-bottom: 0 !important;
    max-width: 100% !important;
}
</style>
"""


# ── Public API ────────────────────────────────────────────────────────────────

def setup() -> None:
    """Inject global CSS. Called once in app.py before st.navigation()."""
    import streamlit as st
    st.markdown(_CSS, unsafe_allow_html=True)


def full_bleed() -> None:
    """Minimize page padding for iframe embed pages. Call after setup()."""
    import streamlit as st
    st.markdown(_FULL_BLEED_CSS, unsafe_allow_html=True)


def banner(page_title: str, beta: bool = False) -> None:
    """Render the GS blue page sub-banner with title and current UTC time.

    Args:
        page_title: Page label shown in the banner.
        beta:       Append a Beta badge.
    """
    from datetime import datetime, timezone
    import streamlit as st

    now          = datetime.now(timezone.utc)
    datetime_str = now.strftime("%d %b %Y  %H:%M UTC")
    beta_html    = '<span class="gs-banner-beta">Beta</span>' if beta else ""

    st.markdown(
        f'<div class="gs-banner">'
        f'{page_title} {beta_html}'
        f'<span class="gs-banner-time">{datetime_str}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
