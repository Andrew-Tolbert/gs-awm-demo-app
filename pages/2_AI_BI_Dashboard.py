import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="AI/BI Dashboard",
    page_icon="📈",
    layout="wide",
)

st.title("AI/BI Dashboard")
st.caption("Embedded Databricks AI/BI Lakeview Dashboard")

DASHBOARD_URL = (
    "https://e2-demo-field-eng.cloud.databricks.com"
    "/dashboardsv3/01f142dfebb71521b206239da8aa1d3d/published"
    "?o=1444828305810485"
)

components.iframe(DASHBOARD_URL, height=900, scrolling=True)
