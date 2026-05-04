import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone
from lib.db import run_query
from lib.queries import kpis_sql, performance_sql, allocation_sql, top_holdings_sql

st.set_page_config(page_title="Streamlit Dashboard", page_icon="📊", layout="wide")


# ── Cached data loaders ───────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_kpis() -> pd.DataFrame:
    return run_query(kpis_sql())


@st.cache_data(ttl=300)
def load_performance() -> pd.DataFrame:
    return run_query(performance_sql())


@st.cache_data(ttl=300)
def load_allocation() -> pd.DataFrame:
    return run_query(allocation_sql())


@st.cache_data(ttl=300)
def load_top_holdings() -> pd.DataFrame:
    return run_query(top_holdings_sql())


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Filters")
    df_alloc_raw  = load_allocation()
    asset_classes = df_alloc_raw["asset_class"].tolist()
    selected_classes = st.multiselect("Asset Class", asset_classes, default=asset_classes)
    lookback = st.slider("Performance Lookback (days)", 30, 90, 90)


# ── Header ────────────────────────────────────────────────────────────────────

st.title("GS Asset & Wealth Management")
st.caption("Powered by Databricks Lakehouse · Data from `ahtsa.awm`")


# ── KPIs ──────────────────────────────────────────────────────────────────────

kpis      = load_kpis().iloc[0]
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


# ── Market Performance Chart ──────────────────────────────────────────────────

df_perf = load_performance()
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


# ── Asset Allocation + Top Holdings ──────────────────────────────────────────

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
    df_holdings = load_top_holdings()
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
