import streamlit as st

st.set_page_config(page_title="📊 Financial Reports", layout="wide")

st.title("📊 Financial Analysis Dashboard")
st.markdown("Welcome! Use the sidebar to navigate:")

st.sidebar.header("Navigate")
st.sidebar.page_link("pages/1_Financials.py", label="📘 Monthly Financial Statements")
st.sidebar.page_link("pages/2_Yearly_Summary.py", label="📆 Yearly Summary")
st.sidebar.page_link("pages/3_Dashboard.py", label="📈 Dashboard")