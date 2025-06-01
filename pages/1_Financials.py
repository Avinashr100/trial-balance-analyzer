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

# Read data
df = pd.read_excel(DATA_FILE, parse_dates=["Date"])
df["Month"] = df["Date"].dt.to_period("M")
df["Month Name"] = df["Date"].dt.strftime("%B %Y")

# Map categories
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

# Sidebar for period selection
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

# ---------------- BALANCE SHEET LOGIC ----------------
def generate_balance_statement(df, month_col, section_order):
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

# ---------------- INCOME STATEMENT LOGIC ----------------
def generate_income_statement(df, month_col):
    df_curr = df[df[month_col] == current_month]
    df_prev = df[df[month_col] == previous_month]

    curr = df_curr[df_curr["Account Type"].isin(["Revenue", "Expense"])]
    prev = df_prev[df_prev["Account Type"].isin(["Revenue", "Expense"])]

    curr = curr.groupby(["Account Category", "Account Name", "Account Type"]).agg({"Debit": "sum", "Credit": "sum"}).reset_index()
    prev = prev.groupby(["Account Category", "Account Name", "Account Type"]).agg({"Debit": "sum", "Credit": "sum"}).reset_index()

    curr["Amount"] = curr.apply(lambda row: row["Credit"] if row["Account Type"] == "Revenue" else -row["Debit"], axis=1)
    prev["Amount"] = prev.apply(lambda row: row["Credit"] if row["Account Type"] == "Revenue" else -row["Debit"], axis=1)

    curr_df = curr[["Account Category", "Account Name", "Amount"]].rename(columns={"Amount": "Current"})
    prev_df = prev[["Account Category", "Account Name", "Amount"]].rename(columns={"Amount": "Previous"})

    merged = pd.merge(curr_df, prev_df, on=["Account Category", "Account Name"], how="outer").fillna(0)
    merged["₹ Change"] = merged["Current"] - merged["Previous"]
    merged["% Change"] = np.where(merged["Previous"] != 0,
                                   merged["₹ Change"] / merged["Previous"] * 100, 0)

    rows = []
    totals = {}

    for section in ["Revenue", "Expenses"]:
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

        totals[section] = (total_current, total_previous)

        rows.append([
            f"<b>Total {section}</b>",
            f"<b>{format_inr(total_current)}</b>",
            f"<b>{format_inr(total_previous)}</b>",
            f"<b>{format_inr(total_current - total_previous)}</b>",
            f"<b>{(total_current - total_previous)/total_previous*100:.1f}%</b>" if total_previous else ""
        ])

    rev_curr, rev_prev = totals.get("Revenue", (0, 0))
    exp_curr, exp_prev = totals.get("Expenses", (0, 0))
    net_curr = rev_curr - exp_curr
    net_prev = rev_prev - exp_prev
    chg = net_curr - net_prev
    pct = (chg / net_prev * 100) if net_prev else 0

    rows.append([
        "<b>Net Income</b>",
        f"<b>{format_inr(net_curr)}</b>",
        f"<b>{format_inr(net_prev)}</b>",
        f"<b>{format_inr(chg)}</b>",
        f"<b>{pct:.1f}%</b>"
    ])

    return pd.DataFrame(rows, columns=["Account Name",
                                       f"Amount ({month_label_current})",
                                       f"Amount ({month_label_previous})",
                                       "₹ Change", "% Change"]), float(net_curr), float(net_prev)

# ---------------- RENDER TABLE ----------------
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
    html(styled, height=700, scrolling=True)

# ---------------- DISPLAY SECTIONS ----------------
render_statement("Balance Sheet", generate_balance_statement(df, "Month", ["Assets", "Liabilities", "Equity"]))

income_df, net_income_current, net_income_previous = generate_income_statement(df, "Month")
render_statement("Income Statement", income_df)

# ---------------- CASH FLOW ----------------
st.markdown("### Cash Flow Statement")
cf_df = compute_cash_flow_statement(df.copy(), current_month, previous_month, income_curr=net_income_current, income_prev=net_income_previous, is_annual=False)
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
html(cf_style, height=1500, scrolling=True)
