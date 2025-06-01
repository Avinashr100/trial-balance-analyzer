import pandas as pd
import streamlit as st
import numpy as np

def load_trial_balance():
    return pd.read_excel("trial_balance_cashflow.xlsx", parse_dates=["Date"])

def format_inr(x):
    try:
        return f"₹{int(x):,}"
    except:
        return ""

def format_percent(x):
    try:
        return f"{x:.1f}%"
    except:
        return ""

def styled_table_html(df):
    html = df.to_html(escape=False, index=False)
    style = """
    <style>
        table {
            width: 100%;
            border-collapse: collapse;
            font-family: sans-serif;
        }
        th {
            background-color: #003366;
            color: white;
            padding: 8px;
            text-align: center;
        }
        td {
            padding: 8px;
        }
        td:first-child {
            text-align: left;
        }
        td:not(:first-child) {
            text-align: center;
        }
        tbody tr:nth-child(even) {background-color: #f0f8ff;}
        tbody tr:nth-child(odd) {background-color: white;}
    </style>
    """
    return style + html

def render_grouped_table(df, title):
    st.markdown(f"<h4 style='text-align:center'>{title}</h4>", unsafe_allow_html=True)
    st.markdown(styled_table_html(df), unsafe_allow_html=True)

def print_js_button(text):
    st.markdown(f"<button onclick='window.print()'>{text}</button>", unsafe_allow_html=True)

def generate_statement(df, current_period, previous_period, sections):
    df["Month"] = df["Date"].dt.to_period("M")
    df_curr = df[df["Month"] == current_period]
    df_prev = df[df["Month"] == previous_period]

    curr = df_curr.groupby(["Account Category", "Account Name"]).agg({"Debit": "sum", "Credit": "sum"}).reset_index()
    prev = df_prev.groupby(["Account Category", "Account Name"]).agg({"Debit": "sum", "Credit": "sum"}).reset_index()

    curr["Amount"] = curr["Credit"] - curr["Debit"]  # Revenue = positive, Expenses = negative
    prev["Amount"] = prev["Credit"] - prev["Debit"]

    merged = pd.merge(curr[["Account Category", "Account Name", "Amount"]],
                      prev[["Account Category", "Account Name", "Amount"]],
                      on=["Account Category", "Account Name"],
                      how="outer", suffixes=("_Current", "_Previous")).fillna(0)

    merged["₹ Change"] = merged["Amount_Current"] - merged["Amount_Previous"]
    merged["% Change"] = np.where(
        merged["Amount_Previous"] != 0,
        merged["₹ Change"] / merged["Amount_Previous"] * 100,
        0
    )

    rows = []
    net_income_current = net_income_previous = 0

    for section in sections:
        section_df = merged[merged["Account Category"] == section]
        if section_df.empty:
            continue

        rows.append([f"<b>{section}</b>", "", "", "", ""])
        total_current = total_previous = 0

        for _, row in section_df.iterrows():
            rows.append([
                row["Account Name"],
                format_inr(row["Amount_Current"]),
                format_inr(row["Amount_Previous"]),
                format_inr(row["₹ Change"]),
                format_percent(row["% Change"])
            ])
            total_current += row["Amount_Current"]
            total_previous += row["Amount_Previous"]

        rows.append([
            f"<b>Total {section}</b>",
            f"<b>{format_inr(total_current)}</b>",
            f"<b>{format_inr(total_previous)}</b>",
            f"<b>{format_inr(total_current - total_previous)}</b>",
            f"<b>{format_percent((total_current - total_previous)/total_previous*100) if total_previous else ''}</b>"
        ])

        if section == "Revenue":
            net_income_current += total_current
            net_income_previous += total_previous
        elif section == "Expenses":
            net_income_current -= total_current
            net_income_previous -= total_previous

    rows.append([
        "<b>Net Income</b>",
        f"<b>{format_inr(net_income_current)}</b>",
        f"<b>{format_inr(net_income_previous)}</b>",
        f"<b>{format_inr(net_income_current - net_income_previous)}</b>",
        f"<b>{format_percent((net_income_current - net_income_previous)/net_income_previous) if net_income_previous else ''}</b>"
    ])

    df_result = pd.DataFrame(rows, columns=[
        "Account Name",
        f"Amount ({current_period.strftime('%b %Y')})",
        f"Amount ({previous_period.strftime('%b %Y')})",
        "₹ Change",
        "% Change"
    ])
    return df_result, net_income_current, net_income_previous
