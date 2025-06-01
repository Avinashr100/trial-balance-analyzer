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
        label_current = pd.Timestamp(current_period.start_time).strftime('%b %Y')
        label_previous = pd.Timestamp(previous_period.start_time).strftime('%b %Y')

    current = df[df["Period"] == current_period]
    previous = df[df["Period"] == previous_period]

    # --- Calculate Net Income from Income Statement Logic ---
    def calc_net_income(period_df):
        revenue = period_df[period_df["Account Type"] == "Revenue"]["Credit"].sum()
        expenses = period_df[period_df["Account Type"] == "Expense"]["Debit"].sum()
        return revenue - expenses

    income_curr = calc_net_income(current)
    income_prev = calc_net_income(previous)

    # --- Create Income Statement Table ---
    def generate_income_statement():
        rows = []
        totals = {}
        for section in ["Revenue", "Expense"]:
            rows.append([f"<b>{section}</b>", "", "", "", ""])
            curr_section = current[current["Account Type"] == section]
            prev_section = previous[previous["Account Type"] == section]
            names = sorted(set(curr_section["Account Name"]).union(set(prev_section["Account Name"])))
            total_curr = total_prev = 0
            for name in names:
                curr_val = curr_section[curr_section["Account Name"] == name]
                prev_val = prev_section[prev_section["Account Name"] == name]
                curr_amt = curr_val["Credit"].sum() if section == "Revenue" else -curr_val["Debit"].sum()
                prev_amt = prev_val["Credit"].sum() if section == "Revenue" else -prev_val["Debit"].sum()
                change = curr_amt - prev_amt
                pct = (change / prev_amt * 100) if prev_amt else 0
                rows.append([
                    name,
                    format_inr(curr_amt),
                    format_inr(prev_amt),
                    format_inr(change),
                    f"{pct:.1f}%"
                ])
                total_curr += curr_amt
                total_prev += prev_amt
            totals[section] = (total_curr, total_prev)
            rows.append([
                f"<b>Total {section}</b>",
                f"<b>{format_inr(total_curr)}</b>",
                f"<b>{format_inr(total_prev)}</b>",
                f"<b>{format_inr(total_curr - total_prev)}</b>",
                f"<b>{((total_curr - total_prev) / total_prev * 100):.1f}%</b>" if total_prev else ""
            ])

        net_curr = totals.get("Revenue", (0, 0))[0] - totals.get("Expense", (0, 0))[0]
        net_prev = totals.get("Revenue", (0, 0))[1] - totals.get("Expense", (0, 0))[1]
        chg = net_curr - net_prev
        pct = (chg / net_prev * 100) if net_prev else 0

        rows.append([
            "<b>Net Income</b>",
            f"<b>{format_inr(net_curr)}</b>",
            f"<b>{format_inr(net_prev)}</b>",
            f"<b>{format_inr(chg)}</b>",
            f"<b>{pct:.1f}%</b>"
        ])
        return pd.DataFrame(rows, columns=[
            "Account Name",
            f"Amount ({label_current})",
            f"Amount ({label_previous})",
            "₹ Change",
            "% Change"
        ]), net_curr, net_prev

    def get_group(period_df, cash_type):
        filtered = period_df[(period_df["Account Type"] == cash_type) & (~period_df["Account Name"].str.contains("Net Income", case=False, na=False))]
        grouped = (
            filtered.groupby("Account Name")
            .agg({"Debit": "sum", "Credit": "sum"})
            .apply(lambda row: row["Debit"] - row["Credit"], axis=1)
        )
        return grouped

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

    income_statement_df, income_curr, income_prev = generate_income_statement()

    net_income_row = [[
        "Net Income",
        format_inr(income_curr),
        format_inr(income_prev),
        format_inr(income_curr - income_prev),
        f"{((income_curr - income_prev) / income_prev * 100):.1f}%" if income_prev else ""
    ]]

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

    net_row = [[
        "Net Activities",
        format_inr(net_activities_curr),
        format_inr(net_activities_prev),
        format_inr(net_chg),
        f"{net_pct:.1f}%"
    ]]

    def get_cash_balance(df_period):
        cash_row = df_period[df_period["Account Name"] == "Cash at Bank"]
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

    cash_flow_df = pd.DataFrame(net_income_row + ops_rows + inv_rows + fin_rows + net_row + end_rows,
        columns=[
            "Account Name",
            f"Amount ({label_current})",
            f"Amount ({label_previous})",
            "₹ Change",
            "% Change"]
    )

    return income_statement_df, cash_flow_df
