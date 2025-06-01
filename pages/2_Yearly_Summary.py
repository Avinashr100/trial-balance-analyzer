import streamlit as st
import pandas as pd
import numpy as np
from streamlit.components.v1 import html
from utils.cashflow_logic import compute_cash_flow_statement

st.set_page_config(page_title="📘 Yearly Summary", layout="wide")
st.markdown("## 📘 Yearly Summary")

# Load Data
DATA_FILE = "trial_balance_cashflow.xlsx"
try:
    df = pd.read_excel(DATA_FILE, parse_dates=["Date"])
except FileNotFoundError:
    st.error(f"'{DATA_FILE}' not found.")
    st.stop()

df["Year"] = df["Date"].dt.year

# Sidebar year selection
years = sorted(df["Year"].unique())
st.sidebar.header("🗓️ Select Years")
current_year = st.sidebar.selectbox("Current Year", years[::-1])
previous_year = st.sidebar.selectbox("Previous Year", [y for y in years if y < current_year][::-1])

label_current = str(current_year)
label_previous = str(previous_year)

# ---------- Helper Functions ----------
def format_inr(x):
    try:
        return f"₹{int(x):,}"
    except:
        return ""

def render_statement(title, df_table):
    st.markdown(f"<h4 style='text-align:center'>{title}</h4>", unsafe_allow_html=True)
    html_table = df_table.to_html(escape=False, index=False)
    styled = f"""
    <style>
        table {{
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
        }}
        th {{
            background-color: #003366;
            color: white;
            padding: 8px;
            text-align: center;
        }}
        td {{
            padding: 8px;
        }}
        td:first-child {{
            text-align: left;
        }}
        td:not(:first-child) {{
            text-align: center;
        }}
        tbody tr:nth-child(even) {{background-color: #f0f8ff;}}
        tbody tr:nth-child(odd) {{background-color: white;}}
    </style>
    {html_table}
    """
    html(styled, height=800, scrolling=True)

# ---------- Compute Statements ----------
income_df, cashflow_df = compute_cash_flow_statement(df, current_year, previous_year, is_annual=True)

# ---------- Render Statements ----------
render_statement("Income Statement", income_df)
render_statement("Cash Flow Statement", cashflow_df)
