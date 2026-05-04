import streamlit as st
from lib.theme import setup, banner

st.set_page_config(
    page_title="Ask Your Portfolio (Embedded)",
    page_icon="🧞",
    layout="wide",
)
setup()

GENIE_URL = (
    "https://e2-demo-field-eng.cloud.databricks.com"
    "/genie/rooms/01f147207fdd153cb94327ebddc171fe"
)

banner("Ask Your Portfolio")
st.caption(
    "Native Databricks Genie Space — sign in with your Databricks credentials to interact."
)

# allow="clipboard-write" enables CSV export and conversation link copying per Databricks docs.
st.markdown(
    f"""
    <iframe
        src="{GENIE_URL}"
        allow="clipboard-write"
        width="100%"
        height="880"
        style="border:none; border-radius:8px; display:block;"
    ></iframe>
    """,
    unsafe_allow_html=True,
)
