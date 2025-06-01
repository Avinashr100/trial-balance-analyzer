import pandas as pd
import streamlit as st

def load_trial_balance():
    return pd.read_excel("trial_balance_cashflow.xlsx", parse_dates=["Date"])

def format_inr(x):
    try:
        return f"₹{int(x):,}"
    except:
        return ""

def format_percent(x):
    try:
        return f"{x:.1f}%"
    except:
        return ""

def styled_table_html(df):
    html = df.to_html(escape=False, index=False)
    style = """
    <style>
        table {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
        }
        th {
            background-color: #003366;
            color: white;
            padding: 8px;
            text-align: center;
        }
        td {
            padding: 8px;
        }
        td:first-child {
            text-align: left;
        }
        td:not(:first-child) {
            text-align: center;
        }
        tbody tr:nth-child(even) {background-color: #f0f8ff;}
        tbody tr:nth-child(odd) {background-color: white;}
    </style>
    """
    return style + html

def render_grouped_table(df, title):
    st.markdown(f"<h4 style='text-align:center'>{title}</h4>", unsafe_allow_html=True)
    st.markdown(styled_table_html(df), unsafe_allow_html=True)

def print_js_button(text):
    st.markdown(f"<button onclick='window.print()'>{text}</button>", unsafe_allow_html=True)