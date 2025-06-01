
import streamlit as st
import pandas as pd
import numpy as np
import os
from streamlit.components.v1 import html
from utils.cashflow_logic import compute_cash_flow_statement

st.set_page_config(page_title="📘 Monthly Financial Statements", layout="wide")
st.markdown("## 📘 Monthly Financial Statements")

# Load file
DATA_FILE = "trial_balance_cashflow.xlsx"
if not os.path.exists(DATA_FILE):
    st.error(f"❌ '{DATA_FILE}' not found in repo.")
    st.stop()

df = pd.read_excel(DATA_FILE, parse_dates=["Date"])
df["Month"] = df["Date"].dt.to_period("M")
df["Month Name"] = df["Date"].dt.strftime("%B %Y")

# Map to categories
category_map = {
    "Asset": "Assets",
    "Liability": "Liabilities",
    "Equity": "Equity",
    "Revenue": "Revenue",
    "Expense": "Expenses",
    "Cash Flow Operating": "Operating Activities",
    "Cash Flow Investing": "Investing Activities",
    "Cash Flow Financing": "Financing Activities"
}
df["Account Category"] = df["Account Type"].map(category_map)

months = sorted(df["Month"].unique())
st.sidebar.header("🗓️ Select Periods")
current_month = st.sidebar.selectbox("Current Month", months[::-1])
previous_month = st.sidebar.selectbox("Previous Month", [m for m in months if m < current_month][::-1])

month_label_current = pd.Timestamp(current_month.start_time).strftime('%b %Y')
month_label_previous = pd.Timestamp(previous_month.start_time).strftime('%b %Y')

def format_inr(x):
    try:
        return f"₹{int(x):,}"
    except:
        return ""

def generate_statement(df, month_col, section_order):
    df_curr = df[df[month_col] == current_month]
    df_prev = df[df[month_col] == previous_month]

    curr = df_curr.groupby(["Account Category", "Account Name"]).agg({"Debit": "sum", "Credit": "sum"}).reset_index()
    curr["Current"] = curr["Debit"] - curr["Credit"]

    prev = df_prev.groupby(["Account Category", "Account Name"]).agg({"Debit": "sum", "Credit": "sum"}).reset_index()
    prev["Previous"] = prev["Debit"] - prev["Credit"]

    merged = pd.merge(curr[["Account Category", "Account Name", "Current"]],
                      prev[["Account Category", "Account Name", "Previous"]],
                      on=["Account Category", "Account Name"], how="outer").fillna(0)
    merged["₹ Change"] = merged["Current"] - merged["Previous"]
    merged["% Change"] = np.where(merged["Previous"] != 0,
                                   merged["₹ Change"] / merged["Previous"] * 100, 0)

    rows = []
    for section in section_order:
        section_df = merged[merged["Account Category"] == section]
        if section_df.empty:
            continue

        rows.append([f"<b>{section}</b>", "", "", "", ""])
        total_current = total_previous = 0

        for _, row in section_df.iterrows():
            rows.append([
                row["Account Name"],
                format_inr(row["Current"]),
                format_inr(row["Previous"]),
                format_inr(row["₹ Change"]),
                f"{row['% Change']:.1f}%"
            ])
            total_current += row["Current"]
            total_previous += row["Previous"]

        rows.append([
            f"<b>Total {section}</b>",
            f"<b>{format_inr(total_current)}</b>",
            f"<b>{format_inr(total_previous)}</b>",
            f"<b>{format_inr(total_current - total_previous)}</b>",
            f"<b>{(total_current - total_previous)/total_previous*100:.1f}%</b>" if total_previous else ""
        ])

    return pd.DataFrame(rows, columns=["Account Name",
                                       f"Amount ({month_label_current})",
                                       f"Amount ({month_label_previous})",
                                       "₹ Change", "% Change"])

def render_statement(title, sections):
    st.markdown(f"<h4 style='text-align:center'>{title}</h4>", unsafe_allow_html=True)
    df_table = generate_statement(df, "Month", sections)

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
    html(styled, height=600, scrolling=True)

# ---- Render Statements ----
render_statement("Balance Sheet", ["Assets", "Liabilities", "Equity"])
render_statement("Income Statement", ["Revenue", "Expenses"])

# ---- Cash Flow ----
st.markdown("### Cash Flow Statement")
cf_df = compute_cash_flow_statement(df, current_month, previous_month)
cf_html = cf_df.to_html(escape=False, index=False)
cf_style = f"""
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
{cf_html}
"""
html(cf_style, height=600, scrolling=True)
