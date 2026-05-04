import streamlit as st

st.set_page_config(
    page_title="GS AWM Demo",
    page_icon="🏦",
    layout="wide",
)

st.title("GS Asset & Wealth Management")
st.caption("Powered by Databricks Lakehouse")

st.divider()

col1, col2, col3 = st.columns(3, gap="large")

with col1:
    st.page_link(
        "pages/2_AI_BI_Dashboard.py",
        label="**📈 AI/BI Dashboard**",
        use_container_width=True,
    )
    st.markdown(
        "Embedded Databricks AI/BI Lakeview dashboard. "
        "Drag-and-drop analytics with natural language querying "
        "and auto-generated insights."
    )

with col2:
    st.page_link(
        "pages/3_Genie.py",
        label="**🧞 Ask Your Portfolio**",
        use_container_width=True,
    )
    st.markdown(
        "Natural language chat over `ahtsa.awm` powered by Databricks Genie. "
        "Ask questions, get answers with live data tables and suggested follow-ups."
    )

with col3:
    st.page_link(
        "pages/4_Advisor_360.py",
        label="**📋 Advisor 360**",
        use_container_width=True,
    )
    st.markdown(
        "Full Advisor 360 view ported from the Lakeview dashboard. "
        "Period P&L, alpha vs benchmark, fee attribution, holdings breakdown, "
        "and cumulative returns timeseries."
    )
