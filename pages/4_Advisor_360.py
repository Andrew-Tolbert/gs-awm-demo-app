import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone, timedelta
from lib.db import run_query, BENCHMARKS
from lib.queries import advisor_holdings_sql, advisor_timeseries_sql
from lib import theme


# ── Cached data loaders ───────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_holdings(start_dt: str, end_dt: str, benchmark: str) -> pd.DataFrame:
    return run_query(advisor_holdings_sql(start_dt, end_dt, benchmark))


@st.cache_data(ttl=300)
def load_timeseries(
    start_dt: str, end_dt: str, benchmark: str,
    advisor_tup: tuple, account_tup: tuple, ticker_tup: tuple,
) -> pd.DataFrame:
    return run_query(advisor_timeseries_sql(
        start_dt, end_dt, benchmark,
        list(advisor_tup), list(account_tup), list(ticker_tup),
    ))


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Filters")
    today      = datetime.now(timezone.utc).date()
    date_range = st.date_input("Date Range", value=(today - timedelta(days=90), today))
    benchmark  = st.selectbox("Benchmark", BENCHMARKS)

if not isinstance(date_range, (list, tuple)) or len(date_range) < 2:
    st.info("Select a complete date range to load data.")
    st.stop()

start_str, end_str = str(date_range[0]), str(date_range[1])

# Load unfiltered holdings first so we can populate the multi-select options.
with st.spinner("Loading portfolio data…"):
    df_all = load_holdings(start_str, end_str, benchmark)

with st.sidebar:
    advisors      = st.multiselect("Advisor",       sorted(df_all["advisor_id"].dropna().unique()))
    account_types = st.multiselect("Account Type",  sorted(df_all["account_type"].dropna().unique()))
    tickers       = st.multiselect("Ticker",        sorted(df_all["ticker"].dropna().unique()))

# Apply multi-select filters in pandas (holdings SQL has no advisor/account/ticker clauses).
df = df_all.copy()
if advisors:
    df = df[df["advisor_id"].isin(advisors)]
if account_types:
    df = df[df["account_type"].isin(account_types)]
if tickers:
    df = df[df["ticker"].isin(tickers)]

if df.empty:
    st.warning("No data for the selected filters.")
    st.stop()

# Load timeseries with all filters in SQL (they affect portfolio composition).
with st.spinner("Loading timeseries…"):
    df_ts = load_timeseries(
        start_str, end_str, benchmark,
        tuple(advisors), tuple(account_types), tuple(tickers),
    )

# Numeric coercions
_numeric_holdings   = ["market_value", "period_pl", "period_total_cost_basis",
                        "fees_attributed", "benchmark_return", "unrealized_gl"]
_numeric_timeseries = ["portfolio_return_before_fees", "benchmark_return", "portfolio_alpha"]

for col in _numeric_holdings:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
for col in _numeric_timeseries:
    if col in df_ts.columns:
        df_ts[col] = pd.to_numeric(df_ts[col], errors="coerce")

df_ts["date"] = pd.to_datetime(df_ts["date"])


# ── Portfolio-level aggregates ────────────────────────────────────────────────

bm_return  = float(df["benchmark_return"].iloc[0]) if len(df) else 0.0
total_pnl  = df["period_pl"].sum()
total_cost = df["period_total_cost_basis"].sum()
total_mv   = df["market_value"].sum()
total_fees = df["fees_attributed"].sum()
pct_return = total_pnl / total_cost if total_cost else 0.0
alpha      = pct_return - bm_return
fee_ratio  = total_fees / total_mv if total_mv else 0.0
as_of      = df["as_of_date"].max() if "as_of_date" in df.columns else end_str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _add_return_measures(grp: pd.DataFrame) -> pd.DataFrame:
    """Attach pct_return, pct_alpha, dollar_alpha, fee_ratio to a grouped DataFrame."""
    grp = grp.copy()
    grp["pct_return"]   = grp["period_pl"] / grp["period_total_cost_basis"].replace(0, float("nan"))
    grp["pct_alpha"]    = grp["pct_return"] - bm_return
    grp["dollar_alpha"] = grp["pct_alpha"] * grp["period_total_cost_basis"]
    if "fees_attributed" in grp.columns and "market_value" in grp.columns:
        grp["fee_ratio"] = grp["fees_attributed"] / grp["market_value"].replace(0, float("nan"))
    return grp


def _color_signed(val) -> str:
    try:
        f = float(val)
        if f > 0:
            return f"color: {theme.SUCCESS}"
        if f < 0:
            return f"color: {theme.DANGER}"
    except (TypeError, ValueError):
        pass
    return ""


# ── Layout ────────────────────────────────────────────────────────────────────

theme.banner("Advisor 360", beta=True)
st.caption(f"As of {as_of}")

# Row 1 — KPIs
col_pnl, col_ret, col_fees_kpi = st.columns(3)

with col_pnl:
    st.metric("Period P&L", f"${total_pnl:,.0f}")

with col_ret:
    st.metric(
        "% Return", f"{pct_return:.2%}",
        delta=f"{alpha:+.2%} vs {benchmark}",
        delta_color="normal",
    )

with col_fees_kpi:
    st.metric("Fees Paid", f"${total_fees:,.0f}",
              delta=f"{fee_ratio:.2%} of AUM", delta_color="off")

st.divider()

# Row 2 — Charts: asset-class bar | ticker bar | pie
col_bar, col_ticker_bar, col_pie = st.columns([3, 6, 3])

with col_bar:
    st.subheader("Return by Asset Class")
    df_ac = (
        df.groupby("asset_class", as_index=False)
        .agg(period_pl=("period_pl", "sum"),
             period_total_cost_basis=("period_total_cost_basis", "sum"))
        .pipe(_add_return_measures)
        .sort_values("pct_return")
    )
    fig = px.bar(
        df_ac, x="pct_return", y="asset_class", orientation="h",
        color="pct_return", color_continuous_scale="RdYlGn",
        labels={"pct_return": "% Return", "asset_class": ""},
        text_auto=".1%",
    )
    fig.update_xaxes(tickformat=".0%")
    st.plotly_chart(
        theme.chart(fig, showlegend=False, coloraxis_showscale=False),
        use_container_width=True,
    )

with col_ticker_bar:
    st.subheader("Return by Ticker")
    df_t = (
        df.groupby(["ticker", "asset_class"], as_index=False)
        .agg(period_pl=("period_pl", "sum"),
             period_total_cost_basis=("period_total_cost_basis", "sum"))
        .pipe(_add_return_measures)
        .sort_values("pct_return")
    )
    fig = px.bar(
        df_t, x="ticker", y="pct_return", color="asset_class", barmode="group",
        labels={"pct_return": "% Return", "ticker": "", "asset_class": "Asset Class"},
    )
    fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(theme.chart(fig), use_container_width=True)

with col_pie:
    st.subheader("AUM by Asset Class")
    df_pie = df.groupby("asset_class", as_index=False)["market_value"].sum()
    fig = px.pie(df_pie, values="market_value", names="asset_class", hole=0.35)
    fig.update_traces(textinfo="percent+label")
    st.plotly_chart(
        theme.chart(fig, showlegend=False),
        use_container_width=True,
    )

st.divider()

# Row 3 — Summary table
st.subheader("Advisor / Client / Account Summary")
df_summary = (
    df.groupby(["advisor_id", "client_name", "account_type"], as_index=False)
    .agg(market_value=("market_value", "sum"),
         period_pl=("period_pl", "sum"),
         period_total_cost_basis=("period_total_cost_basis", "sum"),
         fees_attributed=("fees_attributed", "sum"))
    .pipe(_add_return_measures)
)
st.dataframe(
    df_summary.rename(columns={
        "advisor_id":   "Advisor",
        "client_name":  "Client",
        "account_type": "Account",
        "market_value": "AUM",
        "period_pl":    "P&L",
        "pct_return":   "% Return",
        "fees_attributed": "$Fees",
        "fee_ratio":    "Fee Ratio",
    }).drop(columns=["period_total_cost_basis", "pct_alpha", "dollar_alpha"])
    .style.format({
        "AUM":       "${:,.0f}",
        "P&L":       "${:,.0f}",
        "% Return":  "{:.2%}",
        "$Fees":     "${:,.0f}",
        "Fee Ratio": "{:.2%}",
    }),
    hide_index=True,
    use_container_width=True,
)

st.divider()

# Row 4 — Portfolio returns vs benchmark (line)
if not df_ts.empty:
    st.subheader("Portfolio Returns vs Benchmark")
    fig = px.line(
        df_ts, x="date",
        y=["portfolio_return_before_fees", "benchmark_return"],
        color_discrete_map={
            "portfolio_return_before_fees": theme.CHART_PORTFOLIO,
            "benchmark_return":             theme.CHART_BENCHMARK,
        },
        labels={"value": "Cumulative Return", "date": "", "variable": ""},
    )
    fig.for_each_trace(lambda t: t.update(name={
        "portfolio_return_before_fees": "% Return",
        "benchmark_return": benchmark,
    }.get(t.name, t.name)))
    fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(
        theme.chart(fig, legend=dict(orientation="h", y=1.12)),
        use_container_width=True,
    )

    st.divider()

# Row 5 — Holdings breakdown (pivot)
st.subheader("Holdings Breakdown")
df_pivot = (
    df.groupby(["account_type", "client_name", "ticker"], as_index=False)
    .agg(cost_basis=("period_cost_basis_per_share", "mean"),
         period_pl=("period_pl", "sum"),
         period_total_cost_basis=("period_total_cost_basis", "sum"),
         fees_attributed=("fees_attributed", "sum"),
         market_value=("market_value", "sum"))
    .pipe(_add_return_measures)
    .rename(columns={
        "account_type": "Account",
        "client_name":  "Client",
        "ticker":       "Ticker",
        "cost_basis":   "Cost Basis",
        "pct_return":   "% Return",
        "pct_alpha":    "% Alpha",
        "dollar_alpha": "$ Alpha",
    })
    .drop(columns=["period_pl", "period_total_cost_basis", "fees_attributed",
                   "market_value", "fee_ratio"])
)
st.dataframe(
    df_pivot.style
    .format({"Cost Basis": "${:,.2f}", "% Return": "{:.2%}",
             "% Alpha": "{:.2%}", "$ Alpha": "${:,.0f}"})
    .applymap(_color_signed, subset=["% Alpha", "$ Alpha"]),
    hide_index=True,
    use_container_width=True,
)

st.divider()

# Row 6 — Cumulative alpha (area)
if not df_ts.empty and "portfolio_alpha" in df_ts.columns:
    st.subheader("Cumulative Portfolio Alpha")
    fig = px.area(
        df_ts, x="date", y="portfolio_alpha",
        labels={"portfolio_alpha": "", "date": ""},
        color_discrete_sequence=[theme.CHART_ALPHA],
    )
    fig.update_yaxes(tickformat=".1%")
    st.plotly_chart(theme.chart(fig), use_container_width=True)

st.caption(f"Refreshed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
