import streamlit as st
import streamlit.components.v1 as components
from lib.theme import setup, banner

st.set_page_config(
    page_title="Ask Your Portfolio (Embedded)",
    page_icon="🧞",
    layout="wide",
)
setup()

# /embed/ prefix + ?o= org ID mirrors the working dashboard embed pattern.
GENIE_URL = (
    "https://e2-demo-field-eng.cloud.databricks.com"
    "/embed/genie/rooms/01f147207fdd153cb94327ebddc171fe"
    "?o=1444828305810485"
)

banner("Ask Your Portfolio")
st.caption(
    "Native Databricks Genie Space — sign in with your Databricks credentials to interact."
)

components.iframe(GENIE_URL, height=880, scrolling=True)
