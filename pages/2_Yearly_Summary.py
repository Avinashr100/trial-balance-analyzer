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

# Load and prepare data
df = load_trial_balance()
df["Year"] = df["Date"].dt.year

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

# Year selection
years = sorted(df["Year"].unique(), reverse=True)
if len(years) < 2:
    st.warning("Not enough years of data.")
    st.stop()

current_year = st.sidebar.selectbox("Current Year", years)
prev_year = st.sidebar.selectbox("Previous Year", [y for y in years if y < current_year])

# ==== Helper ====
def build_statement(sections):
    df_curr = df[df["Year"] == current_year]
    df_prev = df[df["Year"] == prev_year]

    def aggregate(subset, types):
        g = subset[subset["Account Category"].isin(types)]
        g = g.groupby(["Account Category", "Account Name"]).agg({"Debit": "sum", "Credit": "sum"}).reset_index()
        g["Amount"] = g["Debit"] - g["Credit"]
        return g[["Account Category", "Account Name", "Amount"]]

    curr = aggregate(df_curr, sections).rename(columns={"Amount": "Current"})
    prev = aggregate(df_prev, sections).rename(columns={"Amount": "Previous"})

    merged = pd.merge(curr, prev, on=["Account Category", "Account Name"], how="outer").fillna(0)
    merged["₹ Change"] = merged["Current"] - merged["Previous"]
    merged["% Change"] = np.where(
        merged["Previous"] != 0,
        merged["₹ Change"] / merged["Previous"] * 100,
        0
    )

    merged["Current"] = merged["Current"].apply(format_inr)
    merged["Previous"] = merged["Previous"].apply(format_inr)
    merged["₹ Change"] = merged["₹ Change"].apply(format_inr)
    merged["% Change"] = merged["% Change"].apply(format_percent)

    merged.rename(columns={
        "Current": f"Amount ({current_year})",
        "Previous": f"Amount ({prev_year})"
    }, inplace=True)

    rows = []
    for section in sections:
        sec_df = merged[merged["Account Category"] == section]
        if sec_df.empty:
            continue

        rows.append([f"<b>{section}</b>", "", "", "", ""])
        for _, r in sec_df.iterrows():
            rows.append([
                r["Account Name"],
                r[f"Amount ({current_year})"],
                r[f"Amount ({prev_year})"],
                r["₹ Change"],
                r["% Change"]
            ])

        def to_num(s):
            return int(s.replace("₹", "").replace(",", "")) if isinstance(s, str) and s.startswith("₹") else 0

        total_curr = sec_df[f"Amount ({current_year})"].apply(to_num).sum()
        total_prev = sec_df[f"Amount ({prev_year})"].apply(to_num).sum()
        diff = total_curr - total_prev
        pct = (diff / total_prev * 100) if total_prev != 0 else 0

        rows.append([
            f"<b>Total {section}</b>",
            f"<b>{format_inr(total_curr)}</b>",
            f"<b>{format_inr(total_prev)}</b>",
            f"<b>{format_inr(diff)}</b>",
            f"<b>{format_percent(pct)}</b>"
        ])

    return pd.DataFrame(rows, columns=[
        "Account Name",
        f"Amount ({current_year})",
        f"Amount ({prev_year})",
        "₹ Change",
        "% Change"
    ])

# ==== Display Sections ====
st.markdown("### 🧾 Balance Sheet")
st.markdown(styled_table_html(build_statement(["Asset", "Liability", "Equity"])), unsafe_allow_html=True)

st.markdown("### 📈 Income Statement")
st.markdown(styled_table_html(build_statement(["Revenue", "Expense"])), unsafe_allow_html=True)

# ==== Cash Flow Statement ====
st.markdown("### 💰 Cash Flow Statement")

def get_cash_flow_data(category, year):
    d = df[(df["Account Type"] == category) & (df["Year"] == year)]
    d = d.groupby("Account Name").agg({"Debit": "sum", "Credit": "sum"}).reset_index()
    d["Amount"] = d["Debit"] - d["Credit"]
    return d.set_index("Account Name")["Amount"].to_dict()

def get_net_income(year):
    rev = df[(df["Year"] == year) & (df["Account Type"] == "Revenue")]
    exp = df[(df["Year"] == year) & (df["Account Type"] == "Expense")]
    r_total = (rev["Debit"].sum() - rev["Credit"].sum())
    e_total = (exp["Debit"].sum() - exp["Credit"].sum())
    return r_total - e_total

cf_rows = []

# Net Income
ni_curr = get_net_income(current_year)
ni_prev = get_net_income(prev_year)
ni_diff = ni_curr - ni_prev
ni_pct = (ni_diff / ni_prev * 100) if ni_prev != 0 else 0
cf_rows.append(["Net Income", format_inr(ni_curr), format_inr(ni_prev), format_inr(ni_diff), format_percent(ni_pct)])

def add_cf_section(label, type_name):
    cf_rows.append([f"<b>{label}</b>", "", "", "", ""])
    c_curr = get_cash_flow_data(type_name, current_year)
    c_prev = get_cash_flow_data(type_name, prev_year)
    all_keys = set(c_curr.keys()).union(set(c_prev.keys()))
    total_curr = total_prev = 0
    for k in sorted(all_keys):
        v1 = c_curr.get(k, 0)
        v2 = c_prev.get(k, 0)
        total_curr += v1
        total_prev += v2
        diff = v1 - v2
        pct = (diff / v2 * 100) if v2 != 0 else 0
        cf_rows.append([k, format_inr(v1), format_inr(v2), format_inr(diff), format_percent(pct)])
    diff = total_curr - total_prev
    pct = (diff / total_prev * 100) if total_prev != 0 else 0
    cf_rows.append([f"<b>Total {label}</b>", f"<b>{format_inr(total_curr)}</b>", f"<b>{format_inr(total_prev)}</b>",
                    f"<b>{format_inr(diff)}</b>", f"<b>{format_percent(pct)}</b>"])
    return total_curr, total_prev

op_curr, op_prev = add_cf_section("Operating Activities", "Cash Flow Operating")
inv_curr, inv_prev = add_cf_section("Investing Activities", "Cash Flow Investing")
fin_curr, fin_prev = add_cf_section("Financing Activities", "Cash Flow Financing")

# Net Activities
net_curr = ni_curr + op_curr + inv_curr + fin_curr
net_prev = ni_prev + op_prev + inv_prev + fin_prev
net_diff = net_curr - net_prev
net_pct = (net_diff / net_prev * 100) if net_prev != 0 else 0
cf_rows.append(["<b>Net Activities</b>", f"<b>{format_inr(net_curr)}</b>", f"<b>{format_inr(net_prev)}</b>",
                f"<b>{format_inr(net_diff)}</b>", f"<b>{format_percent(net_pct)}</b>"])

# Beginning & Ending Cash
def get_cash(year):
    subset = df[(df["Year"] == year) & (df["Account Name"] == "Cash at Bank")]
    return (subset["Debit"].sum() - subset["Credit"].sum())

end_curr = get_cash(current_year)
end_prev = get_cash(prev_year)
beg_curr = end_curr - net_curr
beg_prev = end_prev - net_prev

for label, val1, val2 in [("Beginning Cash at Bank", beg_curr, beg_prev), ("Ending Cash at Bank", end_curr, end_prev)]:
    diff = val1 - val2
    pct = (diff / val2 * 100) if val2 != 0 else 0
    cf_rows.append([
        f"<b>{label}</b>",
        f"<b>{format_inr(val1)}</b>",
        f"<b>{format_inr(val2)}</b>",
        f"<b>{format_inr(diff)}</b>",
        f"<b>{format_percent(pct)}</b>"
    ])

cf_df = pd.DataFrame(cf_rows, columns=[
    "Account Name", f"Amount ({current_year})", f"Amount ({prev_year})", "₹ Change", "% Change"
])
st.markdown(styled_table_html(cf_df), unsafe_allow_html=True)

# Print
print_js_button("Print Yearly Summary")
