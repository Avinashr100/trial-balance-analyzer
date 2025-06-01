def generate_statement(df, month_col, section_order):
    df_curr = df[df[month_col] == current_month]
    df_prev = df[df[month_col] == previous_month]

    curr = df_curr.groupby(["Account Category", "Account Name"]).agg({"Debit": "sum", "Credit": "sum"}).reset_index()
    curr["Current"] = curr["Debit"] - curr["Credit"]

    prev = df_prev.groupby(["Account Category", "Account Name"]).agg({"Debit": "sum", "Credit": "sum"}).reset_index()
    prev["Previous"] = prev["Debit"] - prev["Credit"]

    merged = pd.merge(curr[["Account Category", "Account Name", "Current"]],
                      prev[["Account Category", "Account Name", "Previous"]],
                      on=["Account Category", "Account Name"], how="outer").fillna(0)
    merged["₹ Change"] = merged["Current"] - merged["Previous"]
    merged["% Change"] = np.where(merged["Previous"] != 0,
                                   merged["₹ Change"] / merged["Previous"] * 100, 0)

    rows = []
    totals = {}

    for section in section_order:
        section_df = merged[merged["Account Category"] == section]
        if section_df.empty:
            continue

        rows.append([f"<b>{section}</b>", "", "", "", ""])
        total_current = total_previous = 0

        for _, row in section_df.iterrows():
            rows.append([
                row["Account Name"],
                format_inr(row["Current"]),
                format_inr(row["Previous"]),
                format_inr(row["₹ Change"]),
                f"{row['% Change']:.1f}%"
            ])
            total_current += row["Current"]
            total_previous += row["Previous"]

        totals[section] = (total_current, total_previous)

        rows.append([
            f"<b>Total {section}</b>",
            f"<b>{format_inr(total_current)}</b>",
            f"<b>{format_inr(total_previous)}</b>",
            f"<b>{format_inr(total_current - total_previous)}</b>",
            f"<b>{(total_current - total_previous)/total_previous*100:.1f}%</b>" if total_previous else ""
        ])

    # Add Net Income row if both Revenue and Expenses exist
    if "Revenue" in totals and "Expenses" in totals:
        rev_curr, rev_prev = totals["Revenue"]
        exp_curr, exp_prev = totals["Expenses"]
        net_curr = rev_curr - exp_curr
        net_prev = rev_prev - exp_prev
        chg = net_curr - net_prev
        pct = (chg / net_prev * 100) if net_prev else 0
        rows.append([
            "<b>Net Income</b>",
            f"<b>{format_inr(net_curr)}</b>",
            f"<b>{format_inr(net_prev)}</b>",
            f"<b>{format_inr(chg)}</b>",
            f"<b>{pct:.1f}%</b>"
        ])

    return pd.DataFrame(rows, columns=["Account Name",
                                       f"Amount ({month_label_current})",
                                       f"Amount ({month_label_previous})",
                                       "₹ Change", "% Change"])
