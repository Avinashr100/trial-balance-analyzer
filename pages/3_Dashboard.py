
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils.shared_formatting import load_trial_balance

st.set_page_config(page_title="📊 Dashboard", layout="wide")
st.title("📊 Financial Dashboard")

df = load_trial_balance()
df["Month"] = df["Date"].dt.to_period("M")
df["Month Label"] = df["Date"].dt.strftime('%b-%y')

metrics = {
    "Cash": ["Cash", "Cash at Bank"],
    "Revenue": ["Service Revenue"],
    "Expenses": ["Salaries Expense"],
    "Net Assets": ["Asset", "Liability"],
    "Investments": ["Investments"]
}

df["Amount"] = df["Debit"] - df["Credit"]

month_range = sorted(df["Month"].unique())[-15:]
df = df[df["Month"].isin(month_range)]

for metric, accounts in metrics.items():
    fig, ax = plt.subplots(figsize=(6, 4))
    plot_df = df[df["Account Name"].isin(accounts)]
    plot_df = plot_df.groupby("Month Label")["Amount"].sum().reset_index()
    ax.plot(plot_df["Month Label"], plot_df["Amount"])
    ax.set_title(metric)
    ax.tick_params(axis='x', rotation=45)
    st.pyplot(fig)
