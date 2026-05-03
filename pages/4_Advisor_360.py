"""Advisor 360 dashboard — ported from AWM-Demo.lvdash.json, page 1."""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
from databricks import sql as dbsql
from databricks.sdk.core import Config
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="Advisor 360", page_icon="📋", layout="wide")

assert os.getenv("DATABRICKS_WAREHOUSE_ID"), "DATABRICKS_WAREHOUSE_ID must be set in app.yaml."

cfg = Config()
hostname = cfg.host.removeprefix("https://").removeprefix("http://")

S = "ahtsa.awm"  # catalog.schema prefix

BENCHMARKS = [
    "Dow Jones Industrial Average",
    "S&P 500",
    "NASDAQ Composite",
    "Russell 2000",
]


# ── Connection ────────────────────────────────────────────────────────────────

def _run(sql: str) -> pd.DataFrame:
    with dbsql.connect(
        server_hostname=hostname,
        http_path=f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID')}",
        credentials_provider=lambda: cfg.authenticate,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall_arrow().to_pandas()


# ── SQL helpers ───────────────────────────────────────────────────────────────

def _in_clause(col: str, vals: list) -> str:
    if not vals:
        return "1=1"
    quoted = ", ".join(f"'{v}'" for v in vals)
    return f"{col} IN ({quoted})"


def _holdings_sql(start_dt: str, end_dt: str, benchmark: str) -> str:
    return f"""
WITH
params AS (
  SELECT '{start_dt}' AS start_dt, '{end_dt}' AS end_dt
),
price_dates AS (
  SELECT
    MAX(CASE WHEN date <= (SELECT end_dt   FROM params) THEN date END) AS end_price_dt,
    MAX(CASE WHEN date <= (SELECT start_dt FROM params) THEN date END) AS start_price_dt
  FROM {S}.bronze_historical_prices
),
equity_positions AS (
  SELECT account_id, ticker, SUM(quantity) AS quantity, SUM(gross_amount) AS total_cost
  FROM {S}.transactions
  WHERE action IN ('BUY', 'DRIP') AND ticker != 'CASH'
    AND date <= (SELECT end_dt FROM params)
  GROUP BY account_id, ticker
),
cash_positions AS (
  SELECT
    account_id,
    GREATEST(0.0,
      SUM(CASE WHEN action='BUY'      AND ticker='CASH' THEN quantity   ELSE 0.0 END)
    + SUM(CASE WHEN action='DIVIDEND'                   THEN net_amount ELSE 0.0 END)
    + SUM(CASE WHEN action='DRIP'                       THEN net_amount ELSE 0.0 END)
    + SUM(CASE WHEN action='FEE'                        THEN net_amount ELSE 0.0 END)
    ) AS cash_balance
  FROM {S}.transactions
  WHERE date <= (SELECT end_dt FROM params)
  GROUP BY account_id
),
end_prices AS (
  SELECT symbol, adjClose AS end_price
  FROM {S}.bronze_historical_prices
  WHERE date = (SELECT end_price_dt FROM price_dates)
),
start_prices AS (
  SELECT symbol, adjClose AS start_price
  FROM {S}.bronze_historical_prices
  WHERE date = (SELECT start_price_dt FROM price_dates)
),
asset_class_ref AS (
  SELECT DISTINCT account_id, ticker, asset_class
  FROM {S}.holdings WHERE ticker != 'CASH'
),
pre_existing_positions AS (
  SELECT DISTINCT account_id, ticker FROM {S}.transactions
  WHERE action IN ('BUY','DRIP') AND ticker != 'CASH'
    AND date < (SELECT start_dt FROM params)
),
benchmark AS (
  SELECT
    v.symbol AS benchmark_symbol,
    '{benchmark}' AS benchmark,
    MAX_BY(v.close, CASE WHEN v.date <= pd.start_price_dt THEN v.date END) AS benchmark_start,
    MAX_BY(v.close, CASE WHEN v.date <= pd.end_price_dt   THEN v.date END) AS benchmark_end,
    (MAX_BY(v.close, CASE WHEN v.date <= pd.end_price_dt   THEN v.date END)
     - MAX_BY(v.close, CASE WHEN v.date <= pd.start_price_dt THEN v.date END))
    / NULLIF(MAX_BY(v.close, CASE WHEN v.date <= pd.start_price_dt THEN v.date END), 0)
      AS benchmark_return
  FROM {S}.bronze_indexes_and_vix v
  CROSS JOIN price_dates pd
  WHERE v.index = '{benchmark}'
  GROUP BY ALL
),
equity_rows AS (
  SELECT
    ep.account_id, ep.ticker,
    COALESCE(ac.asset_class,'Equity') AS asset_class,
    ep.quantity,
    epr.end_price AS price,
    ep.quantity * epr.end_price AS market_value,
    ep.total_cost / ep.quantity  AS cost_basis_per_share,
    ep.total_cost                AS total_cost_basis,
    ep.quantity * epr.end_price - ep.total_cost AS unrealized_gl,
    ROUND((ep.quantity*epr.end_price - ep.total_cost)/NULLIF(ep.total_cost,0)*100,2) AS unrealized_gl_pct,
    spr.start_price,
    ROUND((epr.end_price - spr.start_price)/NULLIF(spr.start_price,0)*100,2) AS period_return_pct,
    CASE WHEN pp.account_id IS NOT NULL THEN spr.start_price
         ELSE ep.total_cost / NULLIF(ep.quantity,0) END AS period_cost_basis_per_share
  FROM equity_positions ep
  JOIN end_prices   epr ON ep.ticker = epr.symbol
  LEFT JOIN start_prices spr ON ep.ticker = spr.symbol
  LEFT JOIN asset_class_ref ac ON ep.account_id=ac.account_id AND ep.ticker=ac.ticker
  LEFT JOIN pre_existing_positions pp ON ep.account_id=pp.account_id AND ep.ticker=pp.ticker
),
cash_rows AS (
  SELECT account_id,'CASH' AS ticker,'Cash' AS asset_class,cash_balance AS quantity,
    1.0 AS price, cash_balance AS market_value, 1.0 AS cost_basis_per_share,
    cash_balance AS total_cost_basis, 0.0 AS unrealized_gl, 0.0 AS unrealized_gl_pct,
    1.0 AS start_price, 0.0 AS period_return_pct, 1.0 AS period_cost_basis_per_share
  FROM cash_positions WHERE cash_balance > 0
),
all_holdings AS (SELECT * FROM equity_rows UNION ALL SELECT * FROM cash_rows),
period_fees AS (
  SELECT account_id, ABS(SUM(net_amount)) AS fees_paid
  FROM {S}.transactions
  WHERE action='FEE'
    AND date BETWEEN (SELECT start_dt FROM params) AND (SELECT end_dt FROM params)
  GROUP BY account_id
),
position_level AS (
SELECT
  (SELECT start_price_dt FROM price_dates) AS period_start_price_date,
  (SELECT end_price_dt   FROM price_dates) AS as_of_date,
  bm.benchmark_symbol, ROUND(bm.benchmark_return,6) AS benchmark_return,
  ROUND(bm.benchmark_return*100,4) AS benchmark_return_pct,
  c.client_id, c.client_name, c.advisor_id, c.tier, c.risk_profile,
  ah.account_id, a.account_name, a.account_type,
  ah.ticker, ah.asset_class,
  ROUND(ah.quantity,4) AS quantity, ROUND(ah.price,4) AS price,
  ROUND(ah.market_value,2) AS market_value,
  ROUND(ah.cost_basis_per_share,4) AS cost_basis_per_share,
  ROUND(ah.total_cost_basis,2) AS total_cost_basis,
  ROUND(ah.unrealized_gl,2) AS unrealized_gl, ah.unrealized_gl_pct,
  ROUND(ah.quantity*ah.start_price,2) AS market_value_at_period_start,
  ROUND(ah.period_cost_basis_per_share,4) AS period_cost_basis_per_share,
  ROUND(ah.quantity*ah.period_cost_basis_per_share,2) AS period_total_cost_basis,
  ROUND(ah.market_value - ah.quantity*ah.period_cost_basis_per_share,2) AS period_pl,
  ah.period_return_pct,
  ROUND(ah.market_value/NULLIF(SUM(ah.market_value) OVER (PARTITION BY ah.account_id),0)*100,2) AS pct_of_account,
  ROUND(ah.market_value/NULLIF(SUM(ah.market_value) OVER (PARTITION BY c.client_id),0)*100,2) AS pct_of_client_portfolio,
  ROUND(ah.market_value/NULLIF(SUM(ah.market_value) OVER (),0)*100,4) AS pct_of_total_aum,
  ROUND((ah.market_value - ah.quantity*ah.start_price)/NULLIF(SUM(ah.quantity*ah.start_price) OVER (PARTITION BY c.client_id),0),6) AS contribution_to_client_return,
  ROUND(COALESCE(pf.fees_paid,0)*ah.market_value/NULLIF(SUM(ah.market_value) OVER (PARTITION BY ah.account_id),0),2) AS fees_attributed
FROM all_holdings ah
JOIN {S}.accounts a ON ah.account_id=a.account_id
JOIN {S}.clients  c ON a.client_id=c.client_id
CROSS JOIN benchmark bm
LEFT JOIN period_fees pf ON ah.account_id=pf.account_id
)
SELECT
  pl.period_start_price_date, pl.as_of_date, pl.benchmark_symbol,
  pl.benchmark_return, pl.benchmark_return_pct,
  pl.client_id, pl.client_name, pl.advisor_id, pl.tier, pl.risk_profile,
  pl.account_id, pl.account_name, pl.account_type,
  pl.ticker, pl.asset_class,
  CASE WHEN pl.ticker='CASH' THEN 'Cash'
       WHEN es.etf_symbol IS NOT NULL THEN COALESCE(es.sector,'Unknown')
       ELSE COALESCE(cp.sector,'Unknown') END AS sector,
  CASE WHEN es.etf_symbol IS NULL AND pl.ticker!='CASH' THEN COALESCE(cp.industry,'Unknown') END AS industry,
  CASE WHEN es.etf_symbol IS NOT NULL THEN 'Indirect' ELSE 'Direct' END AS source_type,
  COALESCE(es.weightPercentage/100, 1.0) AS weight_in_source,
  pl.price, pl.cost_basis_per_share, pl.period_cost_basis_per_share,
  pl.period_return_pct, pl.unrealized_gl_pct,
  ROUND(pl.quantity             * COALESCE(es.weightPercentage/100,1.0),4) AS quantity,
  ROUND(pl.market_value         * COALESCE(es.weightPercentage/100,1.0),2) AS market_value,
  ROUND(pl.total_cost_basis     * COALESCE(es.weightPercentage/100,1.0),2) AS total_cost_basis,
  ROUND(pl.unrealized_gl        * COALESCE(es.weightPercentage/100,1.0),2) AS unrealized_gl,
  ROUND(pl.period_total_cost_basis * COALESCE(es.weightPercentage/100,1.0),2) AS period_total_cost_basis,
  ROUND(pl.period_pl            * COALESCE(es.weightPercentage/100,1.0),2) AS period_pl,
  ROUND(pl.pct_of_account       * COALESCE(es.weightPercentage/100,1.0),4) AS pct_of_account,
  ROUND(pl.pct_of_client_portfolio * COALESCE(es.weightPercentage/100,1.0),4) AS pct_of_client_portfolio,
  ROUND(pl.pct_of_total_aum     * COALESCE(es.weightPercentage/100,1.0),6) AS pct_of_total_aum,
  ROUND(pl.contribution_to_client_return * COALESCE(es.weightPercentage/100,1.0),6) AS contribution_to_client_return,
  ROUND(pl.fees_attributed      * COALESCE(es.weightPercentage/100,1.0),2) AS fees_attributed
FROM position_level pl
LEFT JOIN {S}.bronze_etf_sectors     es ON pl.ticker=es.etf_symbol
LEFT JOIN {S}.bronze_company_profiles cp ON pl.ticker=cp.symbol
ORDER BY pl.client_name, pl.account_id, pl.asset_class, pl.ticker, sector
"""


def _timeseries_sql(
    start_dt: str, end_dt: str, benchmark: str,
    advisor_ids: list, account_types: list, tickers: list,
) -> str:
    advisor_f = _in_clause("c.advisor_id", advisor_ids)
    account_f = _in_clause("a.account_type", account_types)
    ticker_f  = _in_clause("t.ticker", tickers)

    return f"""
WITH
params AS (SELECT '{start_dt}' AS start_dt, '{end_dt}' AS end_dt),
price_dates AS (
  SELECT
    MAX(CASE WHEN date <= (SELECT end_dt   FROM params) THEN date END) AS end_price_dt,
    MAX(CASE WHEN date <= (SELECT start_dt FROM params) THEN date END) AS start_price_dt
  FROM {S}.bronze_historical_prices
),
trading_days AS (
  SELECT DISTINCT date FROM {S}.bronze_historical_prices
  WHERE date >= (SELECT start_price_dt FROM price_dates)
    AND date <= (SELECT end_price_dt   FROM price_dates)
),
filtered_positions AS (
  SELECT t.account_id, t.ticker, SUM(t.quantity) AS quantity, SUM(t.gross_amount) AS total_cost
  FROM {S}.transactions t
  JOIN {S}.accounts a ON t.account_id=a.account_id
  JOIN {S}.clients  c ON a.client_id=c.client_id
  WHERE t.action IN ('BUY','DRIP') AND t.ticker!='CASH'
    AND t.date <= (SELECT end_dt FROM params)
    AND {advisor_f} AND {account_f} AND {ticker_f}
  GROUP BY t.account_id, t.ticker
),
pre_existing_positions AS (
  SELECT DISTINCT t.account_id, t.ticker
  FROM {S}.transactions t
  JOIN {S}.accounts a ON t.account_id=a.account_id
  JOIN {S}.clients  c ON a.client_id=c.client_id
  WHERE t.action IN ('BUY','DRIP') AND t.ticker!='CASH'
    AND t.date < (SELECT start_dt FROM params)
    AND {advisor_f} AND {account_f}
),
series_start_prices AS (
  SELECT symbol, adjClose AS start_price FROM {S}.bronze_historical_prices
  WHERE date=(SELECT start_price_dt FROM price_dates)
),
daily_portfolio AS (
  SELECT td.date, SUM(fp.quantity * hp.adjClose) AS portfolio_value
  FROM trading_days td
  CROSS JOIN filtered_positions fp
  JOIN {S}.bronze_historical_prices hp ON hp.symbol=fp.ticker AND hp.date=td.date
  GROUP BY td.date
),
portfolio_baseline AS (
  SELECT SUM(
    CASE WHEN pp.account_id IS NOT NULL THEN fp.quantity*sp.start_price ELSE fp.total_cost END
  ) AS base
  FROM filtered_positions fp
  LEFT JOIN series_start_prices    sp ON fp.ticker=sp.symbol
  LEFT JOIN pre_existing_positions pp ON fp.account_id=pp.account_id AND fp.ticker=pp.ticker
),
daily_benchmark AS (
  SELECT td.date, MAX_BY(v.close, v.date) AS benchmark_value
  FROM trading_days td
  LEFT JOIN {S}.bronze_indexes_and_vix v ON v.index='{benchmark}' AND v.date=td.date
  GROUP BY td.date
),
benchmark_baseline AS (
  SELECT benchmark_value AS base FROM daily_benchmark
  WHERE date=(SELECT start_price_dt FROM price_dates)
),
fees_by_day AS (
  SELECT td.date, COALESCE(SUM(ABS(f.net_amount)),0) AS cumulative_fees
  FROM trading_days td
  LEFT JOIN {S}.transactions f
    ON f.action='FEE'
    AND f.date >= (SELECT start_price_dt FROM price_dates) AND f.date <= td.date
    AND f.account_id IN (SELECT DISTINCT account_id FROM filtered_positions)
  GROUP BY td.date
)
SELECT
  dp.date,
  ROUND(dp.portfolio_value / NULLIF(pb.base,0) - 1, 6) AS portfolio_return_before_fees,
  ROUND((dp.portfolio_value - fd.cumulative_fees)/NULLIF(pb.base,0) - 1, 6) AS portfolio_return_after_fees,
  ROUND((dp.portfolio_value - fd.cumulative_fees)/NULLIF(pb.base,0) - 1, 6)
    - ROUND(db.benchmark_value/NULLIF(bb.base,0) - 1, 6) AS portfolio_alpha,
  ROUND(fd.cumulative_fees, 2) AS cumulative_fees,
  ROUND(db.benchmark_value/NULLIF(bb.base,0) - 1, 6) AS benchmark_return,
  '{benchmark}' AS benchmark
FROM daily_portfolio dp
LEFT JOIN daily_benchmark  db ON dp.date=db.date
LEFT JOIN fees_by_day      fd ON dp.date=fd.date
CROSS JOIN portfolio_baseline pb
CROSS JOIN benchmark_baseline bb
ORDER BY dp.date
"""


# ── Cached data loaders ───────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_holdings(start_dt: str, end_dt: str, benchmark: str) -> pd.DataFrame:
    return _run(_holdings_sql(start_dt, end_dt, benchmark))


@st.cache_data(ttl=300)
def load_timeseries(
    start_dt: str, end_dt: str, benchmark: str,
    advisor_tup: tuple, account_tup: tuple, ticker_tup: tuple,
) -> pd.DataFrame:
    return _run(_timeseries_sql(start_dt, end_dt, benchmark, list(advisor_tup), list(account_tup), list(ticker_tup)))


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Filters")
    today      = datetime.now(timezone.utc).date()
    date_range = st.date_input("Date Range", value=(today - timedelta(days=90), today))
    benchmark  = st.selectbox("Benchmark", BENCHMARKS)

if not isinstance(date_range, (list, tuple)) or len(date_range) < 2:
    st.info("Select a complete date range to load data.")
    st.stop()

start_str = str(date_range[0])
end_str   = str(date_range[1])

# Load holdings (unfiltered by multi-select) to populate filter options
with st.spinner("Loading portfolio data…"):
    df_all = load_holdings(start_str, end_str, benchmark)

advisor_options  = sorted(df_all["advisor_id"].dropna().unique().tolist())
account_options  = sorted(df_all["account_type"].dropna().unique().tolist())
ticker_options   = sorted(df_all["ticker"].dropna().unique().tolist())

with st.sidebar:
    advisors      = st.multiselect("Advisor", advisor_options)
    account_types = st.multiselect("Account Type", account_options)
    tickers       = st.multiselect("Ticker", ticker_options)

# Apply pandas filters to holdings
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

# Load timeseries with all filters applied in SQL
with st.spinner("Loading timeseries…"):
    df_ts = load_timeseries(
        start_str, end_str, benchmark,
        tuple(advisors), tuple(account_types), tuple(tickers),
    )

# Numeric coercions
for col in ["market_value", "period_pl", "period_total_cost_basis", "fees_attributed",
            "benchmark_return", "unrealized_gl"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

for col in ["portfolio_return_before_fees", "benchmark_return", "portfolio_alpha"]:
    if col in df_ts.columns:
        df_ts[col] = pd.to_numeric(df_ts[col], errors="coerce")

df_ts["date"] = pd.to_datetime(df_ts["date"])

# ── Portfolio-level computed measures ─────────────────────────────────────────

bm_return   = float(df["benchmark_return"].iloc[0]) if len(df) else 0.0
total_pnl   = df["period_pl"].sum()
total_cost  = df["period_total_cost_basis"].sum()
total_mv    = df["market_value"].sum()
total_fees  = df["fees_attributed"].sum()
pct_return  = total_pnl / total_cost if total_cost else 0.0
alpha       = pct_return - bm_return
fee_ratio   = total_fees / total_mv if total_mv else 0.0
as_of       = df["as_of_date"].max() if "as_of_date" in df.columns else end_str

# ── Layout ────────────────────────────────────────────────────────────────────

# Row 1: Title + KPIs
col_title, col_pnl, col_ret, col_fees = st.columns(4)

with col_title:
    st.markdown("### Advisor 360 Dashboard")
    st.caption(f"As of {as_of}")

with col_pnl:
    st.metric("Period P&L", f"${total_pnl:,.0f}")

with col_ret:
    st.metric(
        "% Return",
        f"{pct_return:.2%}",
        delta=f"{alpha:+.2%} vs {benchmark}",
        delta_color="normal",
    )

with col_fees:
    st.metric("Fees Paid", f"${total_fees:,.0f}", delta=f"{fee_ratio:.2%} of AUM", delta_color="off")

st.divider()

# Row 2: Asset class bar | Ticker bar | Pie
col_bar, col_ticker_bar, col_pie = st.columns([3, 6, 3])

with col_bar:
    st.subheader("Return by Asset Class")
    df_ac = (
        df.groupby("asset_class", as_index=False)
        .agg(period_pl=("period_pl", "sum"), period_total_cost_basis=("period_total_cost_basis", "sum"))
    )
    df_ac["pct_return"] = df_ac["period_pl"] / df_ac["period_total_cost_basis"].replace(0, float("nan"))
    df_ac = df_ac.sort_values("pct_return")
    fig_ac = px.bar(
        df_ac, x="pct_return", y="asset_class", orientation="h",
        color="pct_return", color_continuous_scale="RdYlGn",
        labels={"pct_return": "% Return", "asset_class": ""},
        text_auto=".1%",
    )
    fig_ac.update_layout(showlegend=False, coloraxis_showscale=False,
                         margin=dict(l=0, r=0, t=0, b=0))
    fig_ac.update_xaxes(tickformat=".0%")
    st.plotly_chart(fig_ac, use_container_width=True)

with col_ticker_bar:
    st.subheader("Return by Ticker")
    df_t = (
        df.groupby(["ticker", "asset_class"], as_index=False)
        .agg(period_pl=("period_pl", "sum"), period_total_cost_basis=("period_total_cost_basis", "sum"))
    )
    df_t["pct_return"] = df_t["period_pl"] / df_t["period_total_cost_basis"].replace(0, float("nan"))
    df_t = df_t.sort_values("pct_return", ascending=True)
    fig_t = px.bar(
        df_t, x="ticker", y="pct_return", color="asset_class",
        labels={"pct_return": "% Return", "ticker": "", "asset_class": "Asset Class"},
        barmode="group",
    )
    fig_t.update_yaxes(tickformat=".1%")
    fig_t.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_t, use_container_width=True)

with col_pie:
    st.subheader("AUM by Asset Class")
    df_pie = df.groupby("asset_class", as_index=False)["market_value"].sum()
    fig_pie = px.pie(
        df_pie, values="market_value", names="asset_class",
        hole=0.35,
    )
    fig_pie.update_traces(textinfo="percent+label")
    fig_pie.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_pie, use_container_width=True)

st.divider()

# Row 3: Summary Table
st.subheader("Advisor / Client / Account Summary")
df_summary = (
    df.groupby(["advisor_id", "client_name", "account_type"], as_index=False)
    .agg(
        market_value=("market_value", "sum"),
        period_pl=("period_pl", "sum"),
        period_total_cost_basis=("period_total_cost_basis", "sum"),
        fees_attributed=("fees_attributed", "sum"),
    )
)
df_summary["pct_return"] = (
    df_summary["period_pl"] / df_summary["period_total_cost_basis"].replace(0, float("nan"))
)
df_summary["fee_ratio"] = (
    df_summary["fees_attributed"] / df_summary["market_value"].replace(0, float("nan"))
)

st.dataframe(
    df_summary.rename(columns={
        "advisor_id": "Advisor",
        "client_name": "Client",
        "account_type": "Account",
        "market_value": "AUM",
        "period_pl": "P&L",
        "pct_return": "% Return",
        "fees_attributed": "$Fees",
        "fee_ratio": "Fee Ratio",
    }).style.format({
        "AUM": "${:,.0f}",
        "P&L": "${:,.0f}",
        "% Return": "{:.2%}",
        "$Fees": "${:,.0f}",
        "Fee Ratio": "{:.2%}",
    }),
    hide_index=True,
    use_container_width=True,
)

st.divider()

# Row 4: Line chart — Portfolio Returns vs Benchmark
if not df_ts.empty:
    st.subheader("Portfolio Returns vs Benchmark")
    fig_line = px.line(
        df_ts, x="date",
        y=["portfolio_return_before_fees", "benchmark_return"],
        color_discrete_map={
            "portfolio_return_before_fees": "#1f77b4",
            "benchmark_return": "#ff7f0e",
        },
        labels={"value": "Cumulative Return", "date": "", "variable": ""},
    )
    fig_line.for_each_trace(lambda t: t.update(name={
        "portfolio_return_before_fees": "% Return",
        "benchmark_return": benchmark,
    }.get(t.name, t.name)))
    fig_line.update_yaxes(tickformat=".1%")
    fig_line.update_layout(legend=dict(orientation="h", y=1.12), margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_line, use_container_width=True)

    st.divider()

# Row 5: Pivot / Holdings Breakdown
st.subheader("Holdings Breakdown")
df_pivot = (
    df.groupby(["account_type", "client_name", "ticker"], as_index=False)
    .agg(
        cost_basis=("period_cost_basis_per_share", "mean"),
        period_pl=("period_pl", "sum"),
        period_total_cost_basis=("period_total_cost_basis", "sum"),
    )
)
df_pivot["% Return"] = df_pivot["period_pl"] / df_pivot["period_total_cost_basis"].replace(0, float("nan"))
df_pivot["% Alpha"]  = df_pivot["% Return"] - bm_return
df_pivot["$ Alpha"]  = df_pivot["% Alpha"] * df_pivot["period_total_cost_basis"]

display_pivot = df_pivot.rename(columns={
    "account_type": "Account", "client_name": "Client", "ticker": "Ticker",
    "cost_basis": "Cost Basis",
}).drop(columns=["period_pl", "period_total_cost_basis"])


def _color_signed(val):
    try:
        if float(val) > 0:
            return "color: #00a972"
        if float(val) < 0:
            return "color: #e53e3e"
    except (TypeError, ValueError):
        pass
    return ""


st.dataframe(
    display_pivot.style.format({
        "Cost Basis": "${:,.2f}",
        "% Return": "{:.2%}",
        "% Alpha": "{:.2%}",
        "$ Alpha": "${:,.0f}",
    }).applymap(_color_signed, subset=["% Alpha", "$ Alpha"]),
    hide_index=True,
    use_container_width=True,
)

st.divider()

# Row 6: Area chart — Portfolio Alpha
if not df_ts.empty and "portfolio_alpha" in df_ts.columns:
    st.subheader("Cumulative Portfolio Alpha")
    fig_area = px.area(
        df_ts, x="date", y="portfolio_alpha",
        labels={"portfolio_alpha": "", "date": ""},
        color_discrete_sequence=["#2ecc71"],
    )
    fig_area.update_yaxes(tickformat=".1%")
    fig_area.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_area, use_container_width=True)

st.caption(f"Refreshed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
