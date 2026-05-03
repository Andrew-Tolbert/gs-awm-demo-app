import streamlit as st

st.set_page_config(
    page_title="GS AWM Demo",
    page_icon="🏦",
    layout="wide",
)

st.title("GS Asset & Wealth Management")
st.caption("Powered by Databricks Lakehouse")

st.divider()

col1, col2 = st.columns(2, gap="large")

with col1:
    st.page_link(
        "pages/1_Streamlit_Dashboard.py",
        label="**📊 Streamlit Dashboard**",
        use_container_width=True,
    )
    st.markdown(
        "Live portfolio analytics built with Streamlit. "
        "Includes AUM KPIs, market performance charts, asset allocation, "
        "and top holdings with fundamentals — all powered by `ahtsa.awm`."
    )

with col2:
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
