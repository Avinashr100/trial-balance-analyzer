
import streamlit as st
import pandas as pd
import numpy as np
from utils.shared_formatting import load_trial_balance, format_inr, format_percent, render_grouped_table
from cashflow_logic import compute_cash_flow_statement

st.set_page_config(page_title="📘 Yearly Summary", layout="wide")
st.title("📘 Yearly Financial Summary")

df = load_trial_balance()
df["Year"] = df["Date"].dt.year

years = sorted(df["Year"].unique(), reverse=True)
year_current = st.sidebar.selectbox("Select Current Year", years)
year_previous = st.sidebar.selectbox("Select Previous Year", [y for y in years if y < year_current])

def generate_grouped_summary(df, year_col, account_types):
    df_filtered = df[df["Account Type"].isin(account_types)]
    current = df_filtered[df_filtered[year_col] == year_current]
    previous = df_filtered[df_filtered[year_col] == year_previous]

    def agg(df_):
        g = df_.groupby(["Account Category", "Account Name"]).agg({"Debit": "sum", "Credit": "sum"}).reset_index()
        g["Amount"] = g["Debit"] - g["Credit"]
        return g[["Account Category", "Account Name", "Amount"]]

    curr_df = agg(current).rename(columns={"Amount": "Current"})
    prev_df = agg(previous).rename(columns={"Amount": "Previous"})

    merged = pd.merge(curr_df, prev_df, on=["Account Category", "Account Name"], how="outer").fillna(0)
    merged["₹ Change"] = merged["Current"] - merged["Previous"]
    merged["% Change"] = np.where(merged["Previous"] != 0, (merged["₹ Change"] / merged["Previous"]) * 100, 0)

    merged["Current"] = merged["Current"].apply(format_inr)
    merged["Previous"] = merged["Previous"].apply(format_inr)
    merged["₹ Change"] = merged["₹ Change"].apply(format_inr)
    merged["% Change"] = merged["% Change"].apply(format_percent)

    merged.rename(columns={
        "Current": f"Amount ({year_current})",
        "Previous": f"Amount ({year_previous})"
    }, inplace=True)

    return render_grouped_table(merged, f"{year_current} vs {year_previous}")

st.markdown("### 🧾 Balance Sheet")
generate_grouped_summary(df, "Year", ["Asset", "Liability", "Equity"])

st.markdown("### 📈 Income Statement")
generate_grouped_summary(df, "Year", ["Revenue", "Expense"])

st.markdown("### 💰 Cash Flow Statement")
cf_df = compute_cash_flow_statement(df, year_current, year_previous, by="Year")
st.markdown(cf_df, unsafe_allow_html=True)
