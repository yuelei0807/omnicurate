"""Q3 analytics: orders with DQ / reconciliation exceptions."""

from __future__ import annotations

import duckdb
import pandas as pd

from src.config import settings


_SQL_PATH = settings.SQL_DIR / "analytics" / "q3_order_exceptions.sql"


def run(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Execute Q3 SQL and return results as a DataFrame."""
    sql = _SQL_PATH.read_text()
    return con.execute(sql).df()


def describe() -> str:
    """One-line business summary for reports/UI."""
    return (
        "Orders that triggered at least one data-quality or reconciliation "
        "exception (order-level or payment-mapped-to-order)."
    )


def summary(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Return total exception rows and per-rule counts for orders/payments datasets."""
    df = con.execute(
        """
        SELECT rule_id, COUNT(*) AS n
        FROM dq_exception_report
        WHERE dataset IN ('orders', 'payments')
        GROUP BY rule_id
        ORDER BY rule_id
        """
    ).df()
    per_rule = {str(row["rule_id"]): int(row["n"]) for _, row in df.iterrows()}
    return {
        "total_exceptions": int(df["n"].sum()) if len(df) else 0,
        "per_rule": per_rule,
    }