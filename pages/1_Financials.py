import streamlit as st
import pandas as pd
import numpy as np
from utils.cashflow_logic import compute_cash_flow_statement

st.set_page_config(page_title="📘 Monthly Financial Statements", layout="wide")
st.title("📘 Monthly Financial Statements")

# Load trial balance
@st.cache_data
def load_data():
    return pd.read_excel("trial_balance_cashflow.xlsx", parse_dates=["Date"])

df = load_data()
df["Month"] = df["Date"].dt.to_period("M")

months = sorted(df["Month"].unique())
current_month = st.sidebar.selectbox("Select Current Month", months[::-1])
previous_month = st.sidebar.selectbox("Select Previous Month", [m for m in months if m < current_month][::-1])

def format_inr(x):
    try:
        return f"₹{int(x):,}"
    except:
        return x

def generate_statement(df, month_col, sections):
    df_curr = df[df["Month"] == current_month]
    df_prev = df[df["Month"] == previous_month]

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

    result_rows = []
    for section in sections:
        section_df = merged[merged["Account Category"] == section]
        if section_df.empty:
            continue
        result_rows.append([f"<b>{section}</b>", "", "", "", ""])
        total_current = total_previous = 0
        for _, row in section_df.iterrows():
            result_rows.append([row["Account Name"],
                                format_inr(row["Current"]),
                                format_inr(row["Previous"]),
                                format_inr(row["₹ Change"]),
                                f"{row['% Change']:.1f}%"])
            total_current += row["Current"]
            total_previous += row["Previous"]
        total_change = total_current - total_previous
        pct_change = f"{(total_change / total_previous * 100):.1f}%" if total_previous != 0 else ""
        result_rows.append([f"<b>Total {section}</b>",
                            f"<b>{format_inr(total_current)}</b>",
                            f"<b>{format_inr(total_previous)}</b>",
                            f"<b>{format_inr(total_change)}</b>",
                            f"<b>{pct_change}</b>"])
    return pd.DataFrame(result_rows, columns=["Account Name",
                                              f"Amount ({current_month})",
                                              f"Amount ({previous_month})",
                                              "₹ Change", "% Change"])

def render_statement(title, sections):
    st.subheader(title)
    df_table = generate_statement(df, "Month", sections)
    html_table = df_table.to_html(escape=False, index=False)
    st.markdown(f"""
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
    """, unsafe_allow_html=True)

# Render Statements
render_statement("Balance Sheet", ["Asset", "Liability", "Equity"])
render_statement("Income Statement", ["Revenue", "Expense"])

# Cash Flow
st.subheader("Cash Flow Statement")
cf_df = compute_cash_flow_statement(df, current_month, previous_month)
cf_html = cf_df.to_html(escape=False, index=False)
st.markdown(f"""
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
{cf_html}
""", unsafe_allow_html=True)