import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils.shared_formatting import load_trial_balance

st.set_page_config(page_title="📊 Dashboard", layout="wide")
st.title("📊 Rolling 15-Month Financial Dashboard")

df = load_trial_balance()
df["Month"] = df["Date"].dt.to_period("M")
df["Month Label"] = df["Date"].dt.strftime("%b-%y")
df["Amount"] = df["Debit"] - df["Credit"]

month_range = sorted(df["Month"].unique())[-15:]
df_subset = df[df["Month"].isin(month_range)]

metrics = {
    "Cash": ["Cash", "Cash at Bank"],
    "Revenue": ["Service Revenue"],
    "Expenses": ["Salaries Expense"],
    "Net Assets": ["Cash", "Accounts Receivable", "Investments", "Accounts Payable"],
    "Investments": ["Investments"]
}

# Arrange charts two per row
rows = list(metrics.items())
for i in range(0, len(rows), 2):
    cols = st.columns(2)
    for idx, (metric, accounts) in enumerate(rows[i:i+2]):
        subset = df_subset[df_subset["Account Name"].isin(accounts)]
        chart_data = subset.groupby("Month Label")["Amount"].sum().reset_index()
        with cols[idx]:
            plt.figure(figsize=(5, 3))
            plt.plot(chart_data["Month Label"], chart_data["Amount"], marker="o")
            plt.title(metric)
            plt.xticks(rotation=45)
            st.pyplot(plt)