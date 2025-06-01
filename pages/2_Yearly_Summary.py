import streamlit as st
import pandas as pd
import numpy as np
import os
from streamlit.components.v1 import html
from utils.cashflow_logic import compute_cash_flow_statement

st.set_page_config(page_title="📘 Yearly Financial Summary", layout="wide")
st.markdown("## 📘 Yearly Financial Summary")

DATA_FILE = "trial_balance_cashflow.xlsx"
if not os.path.exists(DATA_FILE):
    st.error(f"❌ '{DATA_FILE}' not found in repo.")
    st.stop()

df = pd.read_excel(DATA_FILE, parse_dates=["Date"])
df["Year"] = df["Date"].dt.year

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

years = sorted(df["Year"].unique())
st.sidebar.header("📅 Select Years")
current_year = st.sidebar.selectbox("Current Year", years[::-1])
previous_year = st.sidebar.selectbox("Previous Year", [y for y in years if y < current_year][::-1])

def format_inr(x):
    try:
        return f"₹{int(x):,}"
    except:
        return ""

def generate_annual_statement(df, year_col, section_order):
    df_curr = df[df[year_col] == current_year]
    df_prev = df[df[year_col] == previous_year]

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
                                       f"Amount ({current_year})",
                                       f"Amount ({previous_year})",
                                       "₹ Change", "% Change"])

def render_annual_statement(title, sections):
    st.markdown(f"<h4 style='text-align:center'>{title}</h4>", unsafe_allow_html=True)
    df_table = generate_annual_statement(df, "Year", sections)

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
    html(styled, height=500, scrolling=True)

# ---- Render Statements ----
render_annual_statement("Balance Sheet", ["Assets", "Liabilities", "Equity"])
render_annual_statement("Income Statement", ["Revenue", "Expenses"])

# ---- Cash Flow ----
st.markdown("### Cash Flow Statement")
cf_df = compute_cash_flow_statement(df, current_year, previous_year, is_annual=True)
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
