
import pandas as pd
import numpy as np

def format_inr(x):
    try:
        return f"₹{int(x):,}"
    except:
        return ""

def compute_cash_flow_statement(df, current_month, previous_month):
    month_label_current = pd.Timestamp(current_month.start_time).strftime('%B %Y')
    month_label_previous = pd.Timestamp(previous_month.start_time).strftime('%B %Y')

    current = df[df["Month"] == current_month]
    previous = df[df["Month"] == previous_month]

    def get_group(month_df, cash_type):
        return month_df[month_df["Account Type"] == cash_type]             .groupby("Account Name").agg({"Debit": "sum", "Credit": "sum"})             .apply(lambda row: row["Debit"] - row["Credit"], axis=1)

    def add_rows(title, group_curr, group_prev):
        rows = [[f"<b>{title}</b>", "", "", "", ""]]
        total_curr = group_curr.sum()
        total_prev = group_prev.sum()
        for acc in sorted(set(group_curr.index).union(group_prev.index)):
            val_curr = group_curr.get(acc, 0)
            val_prev = group_prev.get(acc, 0)
            chg = val_curr - val_prev
            pct = (chg / val_prev * 100) if val_prev != 0 else 0
            rows.append([
                acc,
                format_inr(val_curr),
                format_inr(val_prev),
                format_inr(chg),
                f"{pct:.1f}%"
            ])
        chg_total = total_curr - total_prev
        pct_total = (chg_total / total_prev * 100) if total_prev != 0 else 0
        rows.append([
            f"<b>Total {title}</b>",
            f"<b>{format_inr(total_curr)}</b>",
            f"<b>{format_inr(total_prev)}</b>",
            f"<b>{format_inr(chg_total)}</b>",
            f"<b>{pct_total:.1f}%</b>"
        ])
        return rows, total_curr, total_prev

    # Get Net Income
    income_curr = current[current["Account Type"] == "Revenue"].Debit.sum() - current[current["Account Type"] == "Expense"].Debit.sum()
    income_prev = previous[previous["Account Type"] == "Revenue"].Debit.sum() - previous[previous["Account Type"] == "Expense"].Debit.sum()
    net_income_row = [["Net Income",
                       format_inr(income_curr),
                       format_inr(income_prev),
                       format_inr(income_curr - income_prev),
                       f"{((income_curr - income_prev) / income_prev * 100):.1f}%" if income_prev else ""]]

    # Cash Flow Sections
    ops_rows, ops_curr, ops_prev = add_rows("Operating Activities",
                                            get_group(current, "Cash Flow Operating"),
                                            get_group(previous, "Cash Flow Operating"))
    inv_rows, inv_curr, inv_prev = add_rows("Investing Activities",
                                            get_group(current, "Cash Flow Investing"),
                                            get_group(previous, "Cash Flow Investing"))
    fin_rows, fin_curr, fin_prev = add_rows("Financing Activities",
                                            get_group(current, "Cash Flow Financing"),
                                            get_group(previous, "Cash Flow Financing"))

    net_activities_curr = income_curr + ops_curr + inv_curr + fin_curr
    net_activities_prev = income_prev + ops_prev + inv_prev + fin_prev
    net_chg = net_activities_curr - net_activities_prev
    net_pct = (net_chg / net_activities_prev * 100) if net_activities_prev else 0

    net_row = [["Net Activities",
                format_inr(net_activities_curr),
                format_inr(net_activities_prev),
                format_inr(net_chg),
                f"{net_pct:.1f}%"]]

    begin_cash_curr = net_activities_curr + 60000
    begin_cash_prev = net_activities_prev + 60000
    end_cash_curr = 60000
    end_cash_prev = 60000

    end_rows = [
        ["Beginning Cash at Bank", format_inr(begin_cash_curr), format_inr(begin_cash_prev),
         format_inr(begin_cash_curr - begin_cash_prev),
         f"{((begin_cash_curr - begin_cash_prev)/begin_cash_prev*100):.1f}%" if begin_cash_prev else ""],
        ["Ending Cash at Bank", format_inr(end_cash_curr), format_inr(end_cash_prev),
         format_inr(end_cash_curr - end_cash_prev),
         f"{((end_cash_curr - end_cash_prev)/end_cash_prev*100):.1f}%" if end_cash_prev else ""]
    ]

    full_table = net_income_row + ops_rows + inv_rows + fin_rows + net_row + end_rows

    return pd.DataFrame(full_table, columns=["Account Name",
                                              f"Amount ({month_label_current})",
                                              f"Amount ({month_label_previous})",
                                              "₹ Change", "% Change"])
