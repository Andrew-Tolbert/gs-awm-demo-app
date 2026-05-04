import streamlit as st
from lib.theme import banner

banner("Home")

st.markdown("#### Powered by Databricks Lakehouse")
st.divider()

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("### 🧞 Portfolio Insight")
    st.page_link(
        "pages/1_Portfolio_Insight.py",
        label="Open Portfolio Insight →",
        use_container_width=True,
    )
    st.markdown(
        "Natural language Q&A over your portfolio data powered by the native "
        "Databricks Genie Space. Ask questions in plain English — Genie queries "
        "live data, explains its reasoning, and surfaces follow-up suggestions. "
        "Full conversation history with CSV export."
    )

with col2:
    st.markdown("### 📊 Portfolio Analytics")
    st.page_link(
        "pages/2_Portfolio_Analytics.py",
        label="Open Portfolio Analytics →",
        use_container_width=True,
    )
    st.markdown(
        "Embedded Databricks AI/BI Lakeview dashboard with drag-and-drop "
        "analytics, auto-generated insights, and natural language chart "
        "creation. Real-time views across AUM, P&L, allocation, and "
        "performance benchmarks — no code required."
    )
