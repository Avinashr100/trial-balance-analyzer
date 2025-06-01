def generate_statement(df, month_col, section_order):
    df_curr = df[df[month_col] == current_month]
    df_prev = df[df[month_col] == previous_month]

    # Defensive: show message if no data
    if df_curr.empty or df_prev.empty:
        return pd.DataFrame([["No data available", "", "", "", ""]],
                            columns=["Account Name",
                                     f"Amount ({month_label_current})",
                                     f"Amount ({month_label_previous})",
                                     "₹ Change", "% Change"])

    # Revenue = Credit; Expense = Debit
    rev_curr = df_curr[df_curr["Account Type"] == "Revenue"]["Credit"].sum()
    rev_prev = df_prev[df_prev["Account Type"] == "Revenue"]["Credit"].sum()
    exp_curr = df_curr[df_curr["Account Type"] == "Expense"]["Debit"].sum()
    exp_prev = df_prev[df_prev["Account Type"] == "Expense"]["Debit"].sum()

    net_curr = rev_curr - exp_curr
    net_prev = rev_prev - exp_prev
    chg = net_curr - net_prev
    pct = (chg / net_prev * 100) if net_prev else 0

    rows = [[
        "<b>Net Income</b>",
        f"<b>{format_inr(net_curr)}</b>",
        f"<b>{format_inr(net_prev)}</b>",
        f"<b>{format_inr(chg)}</b>",
        f"<b>{pct:.1f}%</b>"
    ]]

    return pd.DataFrame(rows, columns=["Account Name",
                                       f"Amount ({month_label_current})",
                                       f"Amount ({month_label_previous})",
                                       "₹ Change", "% Change"])
