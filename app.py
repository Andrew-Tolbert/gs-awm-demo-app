import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

st.set_page_config(
    page_title="GS AWM Demo",
    page_icon="📊",
    layout="wide",
)

st.title("GS Asset & Wealth Management — Databricks Demo")
st.caption("Powered by Databricks Lakehouse Platform")

# Sidebar
with st.sidebar:
    st.header("Portfolio Filters")
    asset_class = st.multiselect(
        "Asset Class",
        ["Equities", "Fixed Income", "Alternatives", "Cash"],
        default=["Equities", "Fixed Income"],
    )
    region = st.selectbox("Region", ["Global", "Americas", "EMEA", "APAC"])
    time_horizon = st.slider("Lookback (days)", 30, 365, 90)

# Generate sample data
random.seed(42)
dates = [datetime.today() - timedelta(days=i) for i in range(time_horizon, 0, -1)]

portfolio_value = 10_000_000
values = [portfolio_value]
for _ in range(len(dates) - 1):
    values.append(values[-1] * (1 + random.gauss(0.0003, 0.008)))

df_perf = pd.DataFrame({"Date": dates, "Portfolio Value ($)": values})

# Benchmark
benchmark_values = [portfolio_value]
for _ in range(len(dates) - 1):
    benchmark_values.append(benchmark_values[-1] * (1 + random.gauss(0.0002, 0.007)))
df_perf["Benchmark"] = benchmark_values

# KPI row
col1, col2, col3, col4 = st.columns(4)
total_return = (values[-1] - portfolio_value) / portfolio_value * 100
benchmark_return = (benchmark_values[-1] - portfolio_value) / portfolio_value * 100
alpha = total_return - benchmark_return

col1.metric("Portfolio Value", f"${values[-1]:,.0f}", f"{total_return:+.2f}%")
col2.metric("Total Return", f"{total_return:.2f}%", f"α {alpha:+.2f}%")
col3.metric("Sharpe Ratio", f"{random.uniform(0.8, 1.6):.2f}", "+0.12")
col4.metric("Active Positions", "47", "+3")

st.divider()

# Performance chart
fig = px.line(
    df_perf,
    x="Date",
    y=["Portfolio Value ($)", "Benchmark"],
    title="Portfolio vs Benchmark Performance",
    template="plotly_white",
)
fig.update_layout(legend_title_text="", hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# Allocation + Risk side by side
col_left, col_right = st.columns(2)

with col_left:
    allocation_data = {
        "Equities": 52,
        "Fixed Income": 28,
        "Alternatives": 15,
        "Cash": 5,
    }
    filtered = {k: v for k, v in allocation_data.items() if k in asset_class} if asset_class else allocation_data
    fig_pie = px.pie(
        values=list(filtered.values()),
        names=list(filtered.keys()),
        title="Asset Allocation",
        hole=0.4,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    risk_metrics = pd.DataFrame({
        "Metric": ["VaR (95%)", "CVaR (95%)", "Max Drawdown", "Beta", "Tracking Error"],
        "Portfolio": ["1.24%", "1.87%", "-8.3%", "0.92", "2.1%"],
        "Limit": ["2.00%", "3.00%", "-15.0%", "1.10", "4.0%"],
        "Status": ["✅ OK", "✅ OK", "✅ OK", "✅ OK", "✅ OK"],
    })
    st.subheader("Risk Dashboard")
    st.dataframe(risk_metrics, hide_index=True, use_container_width=True)

# Top holdings table
st.subheader("Top Holdings")
holdings = pd.DataFrame({
    "Security": ["AAPL US", "MSFT US", "AMZN US", "GOOGL US", "JPM US", "BRK/B US", "UNH US", "V US"],
    "Asset Class": ["Equities"] * 8,
    "Weight (%)": [5.2, 4.8, 3.9, 3.7, 2.8, 2.5, 2.3, 2.1],
    "1D Return (%)": [round(random.gauss(0.05, 0.8), 2) for _ in range(8)],
    "YTD Return (%)": [round(random.gauss(8, 12), 2) for _ in range(8)],
    "Market Value ($M)": [round(v * values[-1] / 100 / 1e6, 2) for v in [5.2, 4.8, 3.9, 3.7, 2.8, 2.5, 2.3, 2.1]],
})
st.dataframe(
    holdings.style.format({"Weight (%)": "{:.1f}", "Market Value ($M)": "${:.2f}"}),
    hide_index=True,
    use_container_width=True,
)

st.caption(f"Data refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | Region: {region}")
