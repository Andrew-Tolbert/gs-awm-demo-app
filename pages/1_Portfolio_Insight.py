import streamlit as st
import streamlit.components.v1 as components
from lib.theme import full_bleed, banner

full_bleed()

# /embed/ prefix + ?o= org ID is required for iframe embedding.
GENIE_URL = (
    "https://e2-demo-field-eng.cloud.databricks.com"
    "/embed/genie/rooms/01f147207fdd153cb94327ebddc171fe"
    "?o=1444828305810485"
)

banner("Portfolio Insight")

components.iframe(GENIE_URL, height=900, scrolling=True)
