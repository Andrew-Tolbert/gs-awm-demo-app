import streamlit as st
from lib.theme import setup

st.set_page_config(
    page_title="Goldman Sachs AWM Pulse",
    page_icon="🏦",
    layout="wide",
)
setup()

pages = st.navigation([
    st.Page("pages/0_Home.py",                  title="Home",                  icon="🏠"),
    st.Page("pages/1_Portfolio_Insight.py",      title="Portfolio Insight",     icon="🧞"),
    st.Page("pages/2_Portfolio_Analytics.py",    title="Portfolio Analytics",   icon="📊"),
    st.Page("pages/3_Ask_Your_Portfolio.py",     title="Ask Your Portfolio",    icon="💬"),
    st.Page("pages/4_Advisor_360.py",            title="Advisor 360",           icon="📋"),
])
pages.run()
