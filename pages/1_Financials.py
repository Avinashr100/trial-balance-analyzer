
import streamlit as st
import pandas as pd
import numpy as np
import os
from utils.cashflow_logic import compute_cash_flow_statement
from streamlit.components.v1 import html

st.set_page_config(page_title="📘 Monthly Financial Statements", layout="wide")
st.title("📘 Monthly Financial Statements")

DEFAULT_FILE = "trial_balance_cashflow.xlsx"
if not os.path.exists(DEFAULT_FILE):
    st.error("❌ 'trial_balance_cashflow.xlsx' not found.")
    st.stop()

df = pd.read_excel(DEFAULT_FILE, parse_dates=["Date"])
df["Month"] = df["Date"].dt.to_period("M")
df["Month Name"] = df["Date"].dt.strftime('%b %Y')

category_map = {
    "Asset": "Asset",
    "Liability": "Liability",
    "Equity": "Equity",
    "Revenue": "Revenue",
    "Expense": "Expense",
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

def generate_statement(section_order):
    current = df[df["Month"] == current_month]
    previous = df[df["Month"] == previous_month]

    curr = current.groupby(["Account Category", "Account Name"]).agg({"Debit": "sum", "Credit": "sum"}).reset_index()
    curr["Current"] = curr["Debit"] - curr["Credit"]
    prev = previous.groupby(["Account Category", "Account Name"]).agg({"Debit": "sum", "Credit": "sum"}).reset_index()
    prev["Previous"] = prev["Debit"] - prev["Credit"]

    merged = pd.merge(curr[["Account Category", "Account Name", "Current"]],
                      prev[["Account Category", "Account Name", "Previous"]],
                      on=["Account Category", "Account Name"], how="outer").fillna(0)
    merged["₹ Change"] = merged["Current"] - merged["Previous"]
    merged["% Change"] = np.where(merged["Previous"] != 0,
                                   merged["₹ Change"] / merged["Previous"] * 100, 0)

    result_rows = []

    for section in section_order:
        section_df = merged[merged["Account Category"] == section].copy()
        if section_df.empty:
            continue

        result_rows.append([f"<b>{section}</b>", "", "", "", ""])
        total_current = total_previous = 0

        for _, row in section_df.iterrows():
            total_current += row["Current"]
            total_previous += row["Previous"]
            result_rows.append([
                row["Account Name"],
                format_inr(row["Current"]),
                format_inr(row["Previous"]),
                format_inr(row["₹ Change"]),
                f"{row['% Change']:.1f}%"
            ])

        result_rows.append([
            f"<b>Total {section}</b>",
            f"<b>{format_inr(total_current)}</b>",
            f"<b>{format_inr(total_previous)}</b>",
            f"<b>{format_inr(total_current - total_previous)}</b>",
            f"<b>{(total_current - total_previous) / total_previous * 100:.1f}%</b>" if total_previous != 0 else ""
        ])

    return pd.DataFrame(result_rows, columns=["Account Name",
                                              f"Amount ({month_label_current})",
                                              f"Amount ({month_label_previous})",
                                              "₹ Change", "% Change"])

def render_html_table(df_table, title):
    html_table = df_table.to_html(escape=False, index=False)
    styled_html = f"""
    <h3 style='text-align:center'>{title}</h3>
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
        td:first-child strong {{
            text-align: left;
            display: block;
        }}
        td:not(:first-child) {{
            text-align: center;
        }}
        tbody tr:nth-child(even) {{background-color: #f0f8ff;}}
        tbody tr:nth-child(odd) {{background-color: white;}}
    </style>
    {html_table}
    """
    html(styled_html, height=600, scrolling=True)

# Render all 3 statements
render_html_table(generate_statement(["Asset", "Liability", "Equity"]), "Balance Sheet")
render_html_table(generate_statement(["Revenue", "Expense"]), "Income Statement")

cf_df = compute_cash_flow_statement(df, current_month, previous_month)
render_html_table(cf_df, "Cash Flow Statement")
