
import streamlit as st
import pandas as pd
import numpy as np
from utils.shared_formatting import (
    load_trial_balance, format_inr, get_year_options,
    compute_cash_flow_statement
)

st.set_page_config(page_title="📆 Yearly Summary", layout="wide")
st.title("📆 Yearly Summary: Financial Statements")

df = load_trial_balance()
df["Year"] = df["Date"].dt.year

available_years = sorted(df["Year"].unique())
year_current = st.sidebar.selectbox("Select Current Year", available_years[::-1])
year_previous = st.sidebar.selectbox("Select Previous Year", [y for y in available_years if y < year_current][::-1])

def generate_statement(df, year_col, section_order):
    df_curr = df[df[year_col] == year_current]
    df_prev = df[df[year_col] == year_previous]

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

    for section in section_order:
        section_df = merged[merged["Account Category"] == section].copy()
        if section_df.empty:
            continue
        result_rows.append([f"<b>{section}</b>", "", "", "", ""])
        total_current, total_previous = 0, 0
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
    return pd.DataFrame(result_rows, columns=["Account Name", f"Amount ({year_current})", f"Amount ({year_previous})", "₹ Change", "% Change"])

def render_statement(title, sections, df):
    st.markdown(f"### {title}")
    table_df = generate_statement(df, "Year", sections)
    html_table = table_df.to_html(escape=False, index=False)
    styled_html = f'''
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
    '''
    st.markdown(styled_html, unsafe_allow_html=True)

render_statement("🧾 Balance Sheet", ["Asset", "Liability", "Equity"], df)
render_statement("📈 Income Statement", ["Revenue", "Expense"], df)

st.markdown("### 💰 Cash Flow Statement")
cf_df = compute_cash_flow_statement(df, year_current, year_previous, by="Year")
cf_html = cf_df.to_html(escape=False, index=False)
styled_cf = f'''
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
'''
st.markdown(styled_cf, unsafe_allow_html=True)
