
import streamlit as st
import pandas as pd
import numpy as np

from utils.shared_formatting import (
    load_trial_balance,
    format_inr,
    format_percent,
    styled_table_html,
    print_js_button
)
from utils.cashflow_logic import compute_cash_flow_statement

st.set_page_config(page_title="📘 Yearly Summary", layout="wide")
st.title("📘 Yearly Financial Summary")

# Load and preprocess
df = load_trial_balance()
df["Year"] = df["Date"].dt.year

# Map Account Type to Account Category
category_map = {
    "Asset": "Asset",
    "Liability": "Liability",
    "Equity": "Equity",
    "Revenue": "Revenue",
    "Expense": "Expense",
    "Cash Flow Operating": "Cash Flow Operating",
    "Cash Flow Investing": "Cash Flow Investing",
    "Cash Flow Financing": "Cash Flow Financing"
}
df["Account Category"] = df["Account Type"].map(category_map)

years = sorted(df["Year"].unique(), reverse=True)
if len(years) < 2:
    st.warning("Not enough years of data for comparison.")
    st.stop()

year_current = st.sidebar.selectbox("Select Current Year", years)
years_prev_options = [y for y in years if y < year_current]
if not years_prev_options:
    st.warning("No earlier year available for comparison.")
    st.stop()
year_previous = st.sidebar.selectbox("Select Previous Year", years_prev_options)

def generate_grouped_summary(df, year_col, section_order):
    df_curr = df[df[year_col] == year_current]
    df_prev = df[df[year_col] == year_previous]

    def aggregate(df_subset, types):
        g = (
            df_subset[df_subset["Account Category"].isin(types)]
            .groupby(["Account Category", "Account Name"])
            .agg({"Debit": "sum", "Credit": "sum"})
            .reset_index()
        )
        g["Amount"] = g["Debit"] - g["Credit"]
        return g[["Account Category", "Account Name", "Amount"]]

    curr_df = aggregate(df_curr, section_order).rename(columns={"Amount": "Current"})
    prev_df = aggregate(df_prev, section_order).rename(columns={"Amount": "Previous"})

    merged = (
        pd.merge(curr_df, prev_df, on=["Account Category", "Account Name"], how="outer")
        .fillna(0)
    )
    merged["₹ Change"] = merged["Current"] - merged["Previous"]
    merged["% Change"] = np.where(
        merged["Previous"] != 0,
        merged["₹ Change"] / merged["Previous"] * 100,
        0
    )

    # Format currency and percent
    merged["Current"] = merged["Current"].apply(format_inr)
    merged["Previous"] = merged["Previous"].apply(format_inr)
    merged["₹ Change"] = merged["₹ Change"].apply(format_inr)
    merged["% Change"] = merged["% Change"].apply(format_percent)

    # Rename columns to include year labels
    merged.rename(columns={
        "Current": f"Amount ({year_current})",
        "Previous": f"Amount ({year_previous})"
    }, inplace=True)

    ordered_rows = []
    for section in section_order:
        section_df = merged[merged["Account Category"] == section]
        if section_df.empty:
            continue

        # Section header
        ordered_rows.append([f"<b>{section}</b>", "", "", "", ""])
        # Line items
        for _, row in section_df.iterrows():
            ordered_rows.append([
                row["Account Name"],
                row[f"Amount ({year_current})"],
                row[f"Amount ({year_previous})"],
                row["₹ Change"],
                row["% Change"]
            ])
        # Subtotal
        def to_num(s):
            return int(s.replace("₹", "").replace(",", "")) if isinstance(s, str) and s.startswith("₹") else 0

        total_curr = sum(section_df[f"Amount ({year_current})"].apply(to_num))
        total_prev = sum(section_df[f"Amount ({year_previous})"].apply(to_num))
        diff = total_curr - total_prev
        pct = (diff / total_prev * 100) if total_prev != 0 else 0
        ordered_rows.append([
            f"<b>Total {section}</b>",
            f"<b>{format_inr(total_curr)}</b>",
            f"<b>{format_inr(total_prev)}</b>",
            f"<b>{format_inr(diff)}</b>",
            f"<b>{format_percent(pct)}</b>"
        ])

    return pd.DataFrame(
        ordered_rows,
        columns=["Account Name",
                 f"Amount ({year_current})",
                 f"Amount ({year_previous})",
                 "₹ Change", "% Change"]
    )

# Render Balance Sheet
st.markdown("### 🧾 Balance Sheet")
df_bs = generate_grouped_summary(df, "Year", ["Asset", "Liability", "Equity"])
st.markdown(styled_table_html(df_bs), unsafe_allow_html=True)

# Render Income Statement
st.markdown("### 📈 Income Statement")
df_pl = generate_grouped_summary(df, "Year", ["Revenue", "Expense"])
st.markdown(styled_table_html(df_pl), unsafe_allow_html=True)

# Render Cash Flow Statement
st.markdown("### 💰 Cash Flow Statement")
cf_df = compute_cash_flow_statement(df, year_current, year_previous, by="Year")
st.markdown(styled_table_html(cf_df), unsafe_allow_html=True)

# Print button at bottom
print_js_button("Print Yearly Summary")
