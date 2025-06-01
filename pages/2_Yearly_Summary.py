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

st.set_page_config(page_title="📘 Yearly Summary", layout="wide")
st.title("📘 Yearly Financial Summary")

# 1. Load trial balance and assign Year
df = load_trial_balance()
df["Year"] = df["Date"].dt.year

# 2. Map Account Type → Account Category (must match exactly your trial_balance_cashflow.xlsx)
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

# 3. Sidebar: choose Current Year & Previous Year
years = sorted(df["Year"].unique(), reverse=True)
if len(years) < 2:
    st.warning("Not enough distinct years of data to compare.")
    st.stop()

year_current = st.sidebar.selectbox("Select Current Year", years)
prev_options = [y for y in years if y < year_current]
if not prev_options:
    st.warning("No earlier year available for comparison.")
    st.stop()
year_previous = st.sidebar.selectbox("Select Previous Year", prev_options)

# Helper to generate grouped summary for Balance Sheet & P/L
def generate_grouped_summary(df, year_col, sections):
    """
    Builds a DataFrame with these columns:
      Account Name | Amount (CurrentYear) | Amount (PreviousYear) | ₹ Change | % Change
    Sections appear as bold headers, followed by each line item, followed by "Total Section".
    """
    df_curr = df[df[year_col] == year_current]
    df_prev = df[df[year_col] == year_previous]

    # Aggregate function: group by Category+Name, sum Debit-Credit
    def aggregate_subset(df_subset, types):
        g = (
            df_subset[df_subset["Account Category"].isin(types)]
            .groupby(["Account Category", "Account Name"])
            .agg({"Debit": "sum", "Credit": "sum"})
            .reset_index()
        )
        g["Amount"] = g["Debit"] - g["Credit"]
        return g[["Account Category", "Account Name", "Amount"]]

    curr_df = aggregate_subset(df_curr, sections).rename(columns={"Amount": "Current"})
    prev_df = aggregate_subset(df_prev, sections).rename(columns={"Amount": "Previous"})

    merged = (
        pd.merge(curr_df, prev_df,
                 on=["Account Category", "Account Name"],
                 how="outer")
        .fillna(0)
    )
    merged["₹ Change"] = merged["Current"] - merged["Previous"]
    merged["% Change"] = np.where(
        merged["Previous"] != 0,
        merged["₹ Change"] / merged["Previous"] * 100,
        0
    )

    # Format columns
    merged["Current"]   = merged["Current"].apply(format_inr)
    merged["Previous"]  = merged["Previous"].apply(format_inr)
    merged["₹ Change"]  = merged["₹ Change"].apply(format_inr)
    merged["% Change"]  = merged["% Change"].apply(format_percent)

    # Rename to Year labels
    merged.rename(columns={
        "Current":  f"Amount ({year_current})",
        "Previous": f"Amount ({year_previous})"
    }, inplace=True)

    # Build ordered rows: section header, line items, total row
    rows = []
    for section in sections:
        sec_df = merged[merged["Account Category"] == section]
        if sec_df.empty:
            continue

        # Bold section header
        rows.append([f"<b>{section}</b>", "", "", "", ""])

        # Line items
        for _, r in sec_df.iterrows():
            rows.append([
                r["Account Name"],
                r[f"Amount ({year_current})"],
                r[f"Amount ({year_previous})"],
                r["₹ Change"],
                r["% Change"]
            ])

        # Subtotals (strip ₹,+commas to sum numerically)
        def to_num(s):
            return int(s.replace("₹", "").replace(",", "")) if isinstance(s, str) and s.startswith("₹") else 0

        total_curr = sec_df[f"Amount ({year_current})"].apply(to_num).sum()
        total_prev = sec_df[f"Amount ({year_previous})"].apply(to_num).sum()
        diff       = total_curr - total_prev
        pct        = (diff / total_prev * 100) if total_prev != 0 else 0

        rows.append([
            f"<b>Total {section}</b>",
            f"<b>{format_inr(total_curr)}</b>",
            f"<b>{format_inr(total_prev)}</b>",
            f"<b>{format_inr(diff)}</b>",
            f"<b>{format_percent(pct)}</b>"
        ])

    return pd.DataFrame(
        rows,
        columns=[
            "Account Name",
            f"Amount ({year_current})",
            f"Amount ({year_previous})",
            "₹ Change",
            "% Change"
        ]
    )

# 4. Render Balance Sheet
st.markdown("### 🧾 Balance Sheet")
df_bs = generate_grouped_summary(df, "Year", ["Asset", "Liability", "Equity"])
st.markdown(styled_table_html(df_bs), unsafe_allow_html=True)

# 5. Render Income Statement
st.markdown("### 📈 Income Statement")
df_pl = generate_grouped_summary(df, "Year", ["Revenue", "Expense"])
st.markdown(styled_table_html(df_pl), unsafe_allow_html=True)

# 6. Render Cash Flow Statement (inline logic)
st.markdown("### 💰 Cash Flow Statement")

# a) Compute Net Income per year:
df_revenue = df[df["Account Type"] == "Revenue"].groupby("Year").agg({"Debit":"sum", "Credit":"sum"}).reset_index()
df_revenue["NetRev"] = df_revenue["Debit"] - df_revenue["Credit"]
df_expense = df[df["Account Type"] == "Expense"].groupby("Year").agg({"Debit":"sum", "Credit":"sum"}).reset_index()
df_expense["NetExp"] = df_expense["Debit"] - df_expense["Credit"]

# Merge to get Net Income = Revenue (debit-credit) - Expense (debit-credit)
ni = pd.merge(
    df_revenue[["Year", "NetRev"]],
    df_expense[["Year", "NetExp"]],
    on="Year", how="outer"
).fillna(0)
ni["Net Income"] = ni["NetRev"] - ni["NetExp"]

# b) Helper: get sum of (Debit - Credit) by Account Name for Cash Flow categories
def yearly_flow(year, flow_type):
    subset = df[
        (df["Year"] == year) &
        (df["Account Type"] == flow_type)
    ].copy()
    grouped = subset.groupby("Account Name").agg({"Debit":"sum","Credit":"sum"}).reset_index()
    grouped["Amount"] = grouped["Debit"] - grouped["Credit"]
    return grouped.set_index("Account Name")["Amount"].to_dict()

# Build sections: Operating, Investing, Financing
flow_sections = []
# Net Income row
curr_ni = ni.loc[ni["Year"] == year_current, "Net Income"].sum()
prev_ni = ni.loc[ni["Year"] == year_previous, "Net Income"].sum()
flow_sections.append({
    "header": "Net Income",
    "rows": [("Net Income", curr_ni, prev_ni)]
})

# Operating Activities
curr_ops = yearly_flow(year_current, "Cash Flow Operating")
prev_ops = yearly_flow(year_previous, "Cash Flow Operating")
operating_rows = []
for acct in sorted(set(curr_ops.keys()).union(prev_ops.keys())):
    av = curr_ops.get(acct, 0)
    pv = prev_ops.get(acct, 0)
    operating_rows.append((acct, av, pv))
flow_sections.append({
    "header": "Operating Activities",
    "rows": operating_rows
})

# Investing Activities
curr_inv = yearly_flow(year_current, "Cash Flow Investing")
prev_inv = yearly_flow(year_previous, "Cash Flow Investing")
investing_rows = []
for acct in sorted(set(curr_inv.keys()).union(prev_inv.keys())):
    iv = curr_inv.get(acct, 0)
    pv = prev_inv.get(acct, 0)
    investing_rows.append((acct, iv, pv))
flow_sections.append({
    "header": "Investing Activities",
    "rows": investing_rows
})

# Financing Activities
curr_fin = yearly_flow(year_current, "Cash Flow Financing")
prev_fin = yearly_flow(year_previous, "Cash Flow Financing")
financing_rows = []
for acct in sorted(set(curr_fin.keys()).union(prev_fin.keys())):
    fv = curr_fin.get(acct, 0)
    pv = prev_fin.get(acct, 0)
    financing_rows.append((acct, fv, pv))
flow_sections.append({
    "header": "Financing Activities",
    "rows": financing_rows
})

# Assemble Cash Flow DataFrame
cf_rows = []
#  a) Net Income row
ni_diff = curr_ni - prev_ni
ni_pct  = (ni_diff / prev_ni * 100) if prev_ni != 0 else 0.0
cf_rows.append([
    "Net Income",
    format_inr(curr_ni),
    format_inr(prev_ni),
    format_inr(ni_diff),
    format_percent(ni_pct)
])

# b) Each section with items + subtotal
grand_curr = curr_ni
grand_prev = prev_ni

for section in flow_sections[1:]:  # skip Net Income section, iterate Operating/Investing/Financing
    header = section["header"]
    cf_rows.append([f"<b>{header}</b>", "", "", "", ""])
    sec_curr_sum = sec_prev_sum = 0

    for acct, av, pv in section["rows"]:
        diff = av - pv
        pct  = (diff / pv * 100) if pv != 0 else 0
        cf_rows.append([
            acct,
            format_inr(av),
            format_inr(pv),
            format_inr(diff),
            format_percent(pct)
        ])
        sec_curr_sum += av
        sec_prev_sum += pv

    # Subtotal row
    diff_sec = sec_curr_sum - sec_prev_sum
    pct_sec  = (diff_sec / sec_prev_sum * 100) if sec_prev_sum != 0 else 0
    cf_rows.append([
        f"<b>Total {header}</b>",
        f"<b>{format_inr(sec_curr_sum)}</b>",
        f"<b>{format_inr(sec_prev_sum)}</b>",
        f"<b>{format_inr(diff_sec)}</b>",
        f"<b>{format_percent(pct_sec)}</b>"
    ])
    grand_curr += sec_curr_sum
    grand_prev += sec_prev_sum

# c) Net Activities row
net_diff = grand_curr - grand_prev
net_pct  = (net_diff / grand_prev * 100) if grand_prev != 0 else 0
cf_rows.append([
    "<b>Net Activities</b>",
    f"<b>{format_inr(grand_curr)}</b>",
    f"<b>{format_inr(grand_prev)}</b>",
    f"<b>{format_inr(net_diff)}</b>",
    f"<b>{format_percent(net_pct)}</b>"
])

# d) Beginning Cash at Bank & Ending Cash at Bank
#   For Yearly, we assume Ending Cash at Bank is existing “Cash at Bank” balance for each year, 
# or you can customize as needed. Here, for demonstration, we pull “Cash at Bank” from df:
def get_cash_balance(df_subset):
    cbalance = df_subset[df_subset["Account Name"] == "Cash at Bank"]
    if not cbalance.empty:
        return (cbalance["Debit"].sum() - cbalance["Credit"].sum())
    return 0

beg_curr = get_cash_balance(df[df["Year"] == year_current]) - (grand_curr - curr_ni)
beg_prev = get_cash_balance(df[df["Year"] == year_previous]) - (grand_prev - prev_ni)
end_curr = get_cash_balance(df[df["Year"] == year_current])
end_prev = get_cash_balance(df[df["Year"] == year_previous])

# Beginning Cash row
beg_diff = beg_curr - beg_prev
beg_pct  = (beg_diff / beg_prev * 100) if beg_prev != 0 else 0
cf_rows.append([
    "<b>Beginning Cash at Bank</b>",
    f"<b>{format_inr(beg_curr)}</b>",
    f"<b>{format_inr(beg_prev)}</b>",
    f"<b>{format_inr(beg_diff)}</b>",
    f"<b>{format_percent(beg_pct)}</b>"
])

# Ending Cash row
end_diff = end_curr - end_prev
end_pct  = (end_diff / end_prev * 100) if end_prev != 0 else 0
cf_rows.append([
    "<b>Ending Cash at Bank</b>",
    f"<b>{format_inr(end_curr)}</b>",
    f"<b>{format_inr(end_prev)}</b>",
    f"<b>{format_inr(end_diff)}</b>",
    f"<b>{format_percent(end_pct)}</b>"
])

cf_df = pd.DataFrame(
    cf_rows,
    columns=["Account Name",
             f"Amount ({year_current})",
             f"Amount ({year_previous})",
             "₹ Change", "% Change"]
)

st.markdown(styled_table_html(cf_df), unsafe_allow_html=True)

# 7. Print button
print_js_button("Print Yearly Summary")
"""

# Write to pages/2_Yearly_Summary.py
out_path = Path("pages/2_Yearly_Summary.py")
out_path.parent.mkdir(exist_ok=True, parents=True)
out_path.write_text(yearly_summary_corrected)
