import os
import streamlit as st
import pandas as pd
import plotly.express as px
from databricks import sql as dbsql
from databricks.sdk.core import Config
from datetime import datetime, timezone

assert os.getenv('DATABRICKS_WAREHOUSE_ID'), "DATABRICKS_WAREHOUSE_ID must be set in app.yaml."

st.set_page_config(
    page_title="Streamlit Dashboard",
    page_icon="📊",
    layout="wide",
)

cfg = Config()

def query_as_user(sql: str, user_token: str) -> pd.DataFrame:
    with dbsql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{cfg.warehouse_id}",
        access_token=user_token,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall_arrow().to_pandas()

def query_as_sp(sql: str) -> pd.DataFrame:
    with dbsql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{cfg.warehouse_id}",
        credentials_provider=lambda: cfg.authenticate,
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall_arrow().to_pandas()

user_token = st.context.headers.get("X-Forwarded-Access-Token")

@st.cache_data(ttl=300)
def load_kpis(token):
    return query_as_user("""
        SELECT
            (SELECT SUM(total_aum)     FROM ahtsa.awm.clients)   AS total_aum,
            (SELECT COUNT(*)           FROM ahtsa.awm.clients)   AS num_clients,
            (SELECT COUNT(*)           FROM ahtsa.awm.accounts)  AS num_accounts,
            (SELECT SUM(unrealized_gl) FROM ahtsa.awm.holdings)  AS total_gl,
            (SELECT SUM(market_value)  FROM ahtsa.awm.holdings)  AS total_mv
    """, token)

@st.cache_data(ttl=300)
def load_performance(token):
    return query_as_user("""
        SELECT symbol, date, adjClose
        FROM ahtsa.awm.bronze_historical_prices
        WHERE symbol IN ('SPY', 'AGG')
          AND date >= DATEADD(DAY, -90, CURRENT_DATE)
        ORDER BY date
    """, token)

@st.cache_data(ttl=300)
def load_allocation(token):
    return query_as_user("""
        SELECT asset_class, SUM(market_value) AS market_value
        FROM ahtsa.awm.holdings
        GROUP BY asset_class
        ORDER BY market_value DESC
    """, token)

@st.cache_data(ttl=300)
def load_top_holdings(token):
    return query_as_user("""
        SELECT
            ticker,
            company_name,
            sector,
            ROUND(SUM(market_value) / 1e6, 1)      AS market_value_m,
            ROUND(SUM(unrealized_gl) / 1e6, 1)     AS unrealized_gl_m,
            ROUND(AVG(unrealized_gl_pct), 1)        AS gl_pct,
            ROUND(AVG(pct_of_total_aum) * 100, 2)  AS weight_pct,
            MAX(analyst_consensus)                  AS analyst_view
        FROM ahtsa.awm.gold_portfolio_fundamentals
        WHERE holdings_date = (SELECT MAX(holdings_date) FROM ahtsa.awm.gold_portfolio_fundamentals)
          AND is_etf = false
          AND sector IS NOT NULL
        GROUP BY ticker, company_name, sector
        ORDER BY SUM(market_value) DESC
        LIMIT 10
    """, token)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Filters")
    df_alloc_raw = load_allocation(user_token)
    asset_classes = df_alloc_raw["asset_class"].tolist()
    selected_classes = st.multiselect("Asset Class", asset_classes, default=asset_classes)
    lookback = st.slider("Performance Lookback (days)", 30, 90, 90)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("GS Asset & Wealth Management")
st.caption("Powered by Databricks Lakehouse · Data from `ahtsa.awm`")

# ── KPIs ──────────────────────────────────────────────────────────────────────

kpis = load_kpis(user_token).iloc[0]
total_aum = float(kpis["total_aum"])
total_gl  = float(kpis["total_gl"])
total_mv  = float(kpis["total_mv"])
gl_pct    = total_gl / (total_mv - total_gl) * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total AUM",      f"${total_aum / 1e9:.1f}B")
col2.metric("Clients",        f"{int(kpis['num_clients']):,}")
col3.metric("Accounts",       f"{int(kpis['num_accounts']):,}")
col4.metric("Unrealized G/L", f"${total_gl / 1e9:.1f}B", f"{gl_pct:+.1f}%")

st.divider()

# ── Performance Chart ─────────────────────────────────────────────────────────

df_perf = load_performance(user_token)
df_perf["date"]     = pd.to_datetime(df_perf["date"])
df_perf["adjClose"] = df_perf["adjClose"].astype(float)
df_perf = df_perf[df_perf["date"] >= df_perf["date"].max() - pd.Timedelta(days=lookback)]
df_perf["indexed"] = df_perf.groupby("symbol")["adjClose"].transform(lambda x: x / x.iloc[0] * 100)
df_perf["label"]   = df_perf["symbol"].map({"SPY": "Equities (SPY)", "AGG": "Fixed Income (AGG)"})

fig_perf = px.line(
    df_perf, x="date", y="indexed", color="label",
    title="Market Performance (Indexed to 100)",
    labels={"indexed": "Index Value", "date": "", "label": ""},
    template="plotly_white",
)
fig_perf.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.12))
st.plotly_chart(fig_perf, use_container_width=True)

# ── Allocation + Top Holdings ─────────────────────────────────────────────────

col_left, col_right = st.columns(2)

with col_left:
    df_alloc = df_alloc_raw[df_alloc_raw["asset_class"].isin(selected_classes)].copy()
    df_alloc["market_value"] = df_alloc["market_value"].astype(float)
    fig_pie = px.pie(
        df_alloc, values="market_value", names="asset_class",
        title="Asset Allocation by Market Value",
        hole=0.4,
    )
    fig_pie.update_traces(textinfo="percent+label")
    st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    df_holdings = load_top_holdings(user_token)
    for col in ("market_value_m", "unrealized_gl_m", "gl_pct", "weight_pct"):
        df_holdings[col] = pd.to_numeric(df_holdings[col], errors="coerce")
    st.subheader("Top Holdings")
    st.dataframe(
        df_holdings.rename(columns={
            "ticker":          "Ticker",
            "company_name":    "Company",
            "sector":          "Sector",
            "market_value_m":  "MV ($M)",
            "unrealized_gl_m": "Unreal. G/L ($M)",
            "gl_pct":          "G/L %",
            "weight_pct":      "Weight %",
            "analyst_view":    "Analyst",
        }).style.format({
            "MV ($M)":          "${:,.1f}",
            "Unreal. G/L ($M)": "${:,.1f}",
            "G/L %":            "{:+.1f}%",
            "Weight %":         "{:.2f}%",
        }),
        hide_index=True,
        use_container_width=True,
    )

st.caption(f"Refreshed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
