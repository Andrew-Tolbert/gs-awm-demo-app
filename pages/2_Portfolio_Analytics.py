import streamlit as st
import streamlit.components.v1 as components
from lib.theme import setup, full_bleed, banner

st.set_page_config(
    page_title="Portfolio Analytics",
    page_icon="📈",
    layout="wide",
)
setup()
full_bleed()

DASHBOARD_URL = (
    "https://e2-demo-field-eng.cloud.databricks.com"
    "/embed/dashboardsv3/01f142dfebb71521b206239da8aa1d3d"
    "?o=1444828305810485"
)

banner("Portfolio Analytics")

components.iframe(DASHBOARD_URL, height=900, scrolling=True)
