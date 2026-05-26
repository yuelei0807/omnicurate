"""Generate outputs/business_answers.md from curated analytics queries."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.analytics import (
    q1_revenue_by_month,
    q2_top_customers,
    q3_order_exceptions,
    q4_revenue_by_state,
    q5_sentiment_link,
)
from src.config import settings


def _df_to_md(df: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub-flavoured markdown table."""
    if df.empty:
        return "_No rows returned._"
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = [
        "| " + " | ".join(str(row[c]) for c in df.columns) + " |"
        for _, row in df.iterrows()
    ]
    return "\n".join([header, sep, *rows])


def _sql_block(path: Path) -> str:
    return f"```sql\n{path.read_text().strip()}\n```"


def _finding_q1(df: pd.DataFrame) -> str:
    if df.empty:
        return "No completed orders with valid order dates were found."
    total = float(df["completed_revenue"].sum())
    peak = df.loc[df["completed_revenue"].idxmax()]
    month = str(peak["month"])[:7]
    return (
        f"Total completed revenue is ${total:,.2f} across {int(df['completed_orders'].sum())} "
        f"orders. Peak month is {month} with ${float(peak['completed_revenue']):,.2f} "
        f"from {int(peak['completed_orders'])} orders."
    )


def _finding_q2(df: pd.DataFrame) -> str:
    if df.empty:
        return "No completed orders linked to valid customers were found."
    top = df.iloc[0]
    return (
        f"Top customer is {top['customer_key']} ({top['full_name']}, {top['standard_state']}) "
        f"with ${float(top['completed_value']):,.2f} across {int(top['completed_orders'])} "
        f"completed orders."
    )


def _finding_q3(df: pd.DataFrame) -> str:
    if df.empty:
        return "No orders triggered data-quality or reconciliation exceptions."
    keys = ", ".join(sorted(df["order_key"].astype(str).tolist()))
    return (
        f"{len(df)} distinct orders triggered at least one exception. "
        f"Affected order keys: {keys}."
    )


def _finding_q4(df: pd.DataFrame) -> str:
    if df.empty:
        return "No completed orders with a standardized shipping state were found."
    top = df.iloc[0]
    return (
        f"Top revenue state is {top['state']} with ${float(top['completed_revenue']):,.2f} "
        f"from {int(top['completed_orders'])} completed orders."
    )


def _finding_q5(df: pd.DataFrame) -> str:
    if df.empty:
        return "No customer cohort comparison could be computed."
    neg = df[df["cohort"] == "has_negative_ticket"]
    pos = df[df["cohort"] == "no_negative_ticket"]
    if len(neg) == 0:
        neg_pct, neg_n = 0.0, 0
    else:
        neg_row = neg.iloc[0]
        neg_pct = float(neg_row["pct_orders_with_exception"])
        neg_n = int(neg_row["customer_count"])
    pos_pct = (
        float(pos.iloc[0]["pct_orders_with_exception"]) if len(pos) else 0.0
    )
    return (
        f"Among {neg_n} customers with negative support tickets, "
        f"{neg_pct:.1f}% of their orders triggered exceptions, versus "
        f"{pos_pct:.1f}% for customers without negative tickets."
    )


def render(con: duckdb.DuckDBPyConnection) -> str:
    """Build markdown answers for Q1–Q5."""
    sections: list[tuple[str, str, Path, pd.DataFrame, str]] = [
        (
            "Q1 — Completed revenue by month",
            q1_revenue_by_month.describe(),
            settings.SQL_DIR / "analytics" / "q1_revenue_by_month.sql",
            q1_revenue_by_month.run(con),
            "",
        ),
        (
            "Q2 — Top customers by completed order value",
            q2_top_customers.describe(),
            settings.SQL_DIR / "analytics" / "q2_top_customers.sql",
            q2_top_customers.run(con),
            "",
        ),
        (
            "Q3 — Orders with data-quality exceptions",
            q3_order_exceptions.describe(),
            settings.SQL_DIR / "analytics" / "q3_order_exceptions.sql",
            q3_order_exceptions.run(con),
            "",
        ),
        (
            "Q4 — Completed revenue by shipping state",
            q4_revenue_by_state.describe(),
            settings.SQL_DIR / "analytics" / "q4_revenue_by_state.sql",
            q4_revenue_by_state.run(con),
            "",
        ),
        (
            "Q5 — Negative tickets vs order exceptions",
            q5_sentiment_link.describe(),
            settings.SQL_DIR / "analytics" / "q5_sentiment_link.sql",
            q5_sentiment_link.run(con),
            "",
        ),
    ]

    finders = [_finding_q1, _finding_q2, _finding_q3, _finding_q4, _finding_q5]

    lines: list[str] = ["# Business Answers", ""]
    for i, (title, desc, sql_path, df, _) in enumerate(sections):
        lines.extend(
            [
                f"## {title}",
                "",
                desc,
                "",
                "### SQL",
                "",
                _sql_block(sql_path),
                "",
                "### Results",
                "",
                _df_to_md(df),
                "",
                "### Finding",
                "",
                finders[i](df),
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def write(con: duckdb.DuckDBPyConnection) -> Path:
    """Render answers and write to settings.ANSWERS_MD; return path."""
    settings.ensure_output_dir()
    path = settings.ANSWERS_MD
    path.write_text(render(con), encoding="utf-8")
    return path