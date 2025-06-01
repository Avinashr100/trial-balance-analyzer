import pandas as pd
import numpy as np

def format_inr(x):
    try:
        return f"₹{int(x):,}"
    except:
        return "₹0"

def compute_cash_flow_statement(df, current_period, previous_period, is_annual=False):
    if is_annual:
        df["Period"] = df["Date"].dt.year
        label_current = str(current_period)
        label_previous = str(previous_period)
    else:
        df["Period"] = df["Date"].dt.to_period("M")
        label_current = pd.Timestamp(current_period.start_time).strftime('%B %Y')
        label_previous = pd.Timestamp(previous_period.start_time).strftime('%B %Y')

    current = df[df["Period"] == current_period].copy()
    previous = df[df["Period"] == previous_period].copy()

    # ----------------- Helper Functions -----------------
    def get_group(period_df, cash_type):
        return (
            period_df[
                (period_df["Account Type"] == cash_type) &
                (~period_df["Account Name"].str.lower().str.contains("net income"))
            ]
            .groupby("Account Name")
            .agg({"Debit": "sum", "Credit": "sum"})
            .apply(lambda row: row["Debit"] - row["Credit"], axis=1)
        )

    def add_rows(title, group_curr, group_prev):
        rows = [[f"<b>{title}</b>", "", "", "", ""]]
        total_curr = group_curr.sum()
        total_prev = group_prev.sum()
        for acc in sorted(set(group_curr.index).union(group_prev.index)):
            val_curr = group_curr.get(acc, 0)
            val_prev = group_prev.get(acc, 0)
            chg = val_curr - val_prev
            pct = (chg / val_prev * 100) if val_prev else 0
            rows.append([
                acc,
                format_inr(val_curr),
                format_inr(val_prev),
                format_inr(chg),
                f"{pct:.1f}%"
            ])
        chg_total = total_curr - total_prev
        pct_total = (chg_total / total_prev * 100) if total_prev else 0
        rows.append([
            f"<b>Total {title}</b>",
            f"<b>{format_inr(total_curr)}</b>",
            f"<b>{format_inr(total_prev)}</b>",
            f"<b>{format_inr(chg_total)}</b>",
            f"<b>{pct_total:.1f}%</b>"
        ])
        return rows, total_curr, total_prev

    # ----------------- Net Income -----------------
    revenue_curr = current[current["Account Type"] == "Revenue"].Credit.sum()
    expense_curr = current[current["Account Type"] == "Expense"].Debit.sum()
    income_curr = revenue_curr - expense_curr

    revenue_prev = previous[previous["Account Type"] == "Revenue"].Credit.sum()
    expense_prev = previous[previous["Account Type"] == "Expense"].Debit.sum()
    income_prev = revenue_prev - expense_prev

    income_chg = income_curr - income_prev
    income_pct = (income_chg / income_prev * 100) if income_prev else 0

    net_income_row = [[
        "<b>Net Income</b>",
        f"<b>{format_inr(income_curr)}</b>",
        f"<b>{format_inr(income_prev)}</b>",
        f"<b>{format_inr(income_chg)}</b>",
        f"<b>{income_pct:.1f}%</b>"
    ]]

    # ----------------- Cash Flow Sections -----------------
    ops_rows, ops_curr, ops_prev = add_rows("Operating Activities",
                                            get_group(current, "Cash Flow Operating"),
                                            get_group(previous, "Cash Flow Operating"))
    inv_rows, inv_curr, inv_prev = add_rows("Investing Activities",
                                            get_group(current, "Cash Flow Investing"),
                                            get_group(previous, "Cash Flow Investing"))
    fin_rows, fin_curr, fin_prev = add_rows("Financing Activities",
                                            get_group(current, "Cash Flow Financing"),
                                            get_group(previous, "Cash Flow Financing"))

    # ----------------- Net Activities -----------------
    net_activities_curr = income_curr + ops_curr + inv_curr + fin_curr
    net_activities_prev = income_prev + ops_prev + inv_prev + fin_prev
    net_chg = net_activities_curr - net_activities_prev
    net_pct = (net_chg / net_activities_prev * 100) if net_activities_prev else 0

    net_row = [[
        "<b>Net Activities</b>",
        f"<b>{format_inr(net_activities_curr)}</b>",
        f"<b>{format_inr(net_activities_prev)}</b>",
        f"<b>{format_inr(net_chg)}</b>",
        f"<b>{net_pct:.1f}%</b>"
    ]]

    # ----------------- Beginning & Ending Cash -----------------
    def get_cash_balance(df_period):
        cash_row = df_period[df_period["Account Name"].str.lower() == "cash at bank"]
        debit = cash_row["Debit"].sum()
        credit = cash_row["Credit"].sum()
        return debit - credit

    begin_cash_curr = get_cash_balance(previous)
    begin_cash_prev = get_cash_balance(df[df["Period"] == (previous_period - 1 if is_annual else previous_period - 1)])

    end_cash_curr = begin_cash_curr + net_activities_curr
    end_cash_prev = begin_cash_prev + net_activities_prev

    end_rows = [
        ["Beginning Cash at Bank", format_inr(begin_cash_curr), format_inr(begin_cash_prev),
         format_inr(begin_cash_curr - begin_cash_prev),
         f"{((begin_cash_curr - begin_cash_prev)/begin_cash_prev*100):.1f}%" if begin_cash_prev else ""],
        ["Ending Cash at Bank", format_inr(end_cash_curr), format_inr(end_cash_prev),
         format_inr(end_cash_curr - end_cash_prev),
         f"{((end_cash_curr - end_cash_prev)/end_cash_prev*100):.1f}%" if end_cash_prev else ""]
    ]

    # ----------------- Final Output -----------------
    full_table = net_income_row + ops_rows + inv_rows + fin_rows + net_row + end_rows

    return pd.DataFrame(full_table, columns=[
        "Account Name",
        f"Amount ({label_current})",
        f"Amount ({label_previous})",
        "₹ Change",
        "% Change"
    ])
