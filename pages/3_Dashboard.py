
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils.shared_formatting import load_trial_balance

st.set_page_config(page_title="📊 Dashboard", layout="wide")
st.title("📊 Rolling 15-Month Financial Dashboard")

df = load_trial_balance()
df["Month"] = df["Date"].dt.to_period("M").astype(str)
df["YearMonth"] = pd.to_datetime(df["Date"]).dt.strftime("%b-%y")

metrics = {
    "Cash": ["Cash"],
    "Revenue": ["Service Revenue"],
    "Expenses": ["Salaries Expense"],
    "Net Assets": ["Cash", "Accounts Receivable", "Investments", "Accounts Payable"],
    "Investments": ["Investments"]
}

month_range = df["YearMonth"].unique()[-15:]  # last 15 months

for i, (title, accounts) in enumerate(metrics.items()):
    subset = df[df["Account Name"].isin(accounts)].copy()
    grouped = subset.groupby("YearMonth").apply(lambda x: x["Debit"].sum() - x["Credit"].sum()).reindex(month_range).fillna(0)
    plt.figure(figsize=(6, 3))
    plt.plot(grouped.index, grouped.values, marker="o")
    plt.title(f"{title} Over Time")
    plt.xticks(rotation=45)
    st.pyplot(plt)
    if i % 2 == 1:
        st.markdown("---")
