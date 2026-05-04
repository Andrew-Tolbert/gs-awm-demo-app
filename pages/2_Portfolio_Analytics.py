import streamlit as st
import streamlit.components.v1 as components
from lib.theme import setup, banner

st.set_page_config(
    page_title="AI/BI Dashboard",
    page_icon="📈",
    layout="wide",
)
setup()

banner("AI/BI Dashboard")
st.caption("Embedded Databricks AI/BI Lakeview Dashboard")

DASHBOARD_URL = (
    "https://e2-demo-field-eng.cloud.databricks.com"
    "/embed/dashboardsv3/01f142dfebb71521b206239da8aa1d3d"
    "?o=1444828305810485"
)

components.iframe(DASHBOARD_URL, height=900, scrolling=True)
