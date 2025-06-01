
import streamlit as st
import pandas as pd
import numpy as np
from utils.cashflow_logic import compute_cash_flow_statement

st.markdown("<h2 style='text-align:center;'>📘 Monthly Financial Statements</h2>", unsafe_allow_html=True)

@st.cache_data
def load_data():
    return pd.read_excel("trial_balance_cashflow.xlsx", parse_dates=["Date"])

df = load_data()
df["Month"] = df["Date"].dt.to_period("M")

months = sorted(df["Month"].unique())
current_month = st.sidebar.selectbox("Select Current Month", months[::-1])
previous_month = st.sidebar.selectbox("Select Previous Month", [m for m in months if m < current_month][::-1])

month_label_current = pd.Timestamp(current_month.start_time).strftime('%b %Y')
month_label_previous = pd.Timestamp(previous_month.start_time).strftime('%b %Y')

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

def render_statement(title, section_order):
    st.markdown(f"<h3 style='text-align:center'>{title}</h3>", unsafe_allow_html=True)
    df_table = generate_statement(section_order)
    html_table = df_table.to_html(escape=False, index=False)

    styled_html = f"""
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
    st.markdown(styled_html, unsafe_allow_html=True)

render_statement("Balance Sheet", ["Asset", "Liability", "Equity"])
render_statement("Income Statement", ["Revenue", "Expense"])
render_statement("Cash Flow Statement", ["Cash Flow Operating", "Cash Flow Investing", "Cash Flow Financing"])
