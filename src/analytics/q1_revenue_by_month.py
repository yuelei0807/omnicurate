"""Q1 analytics: completed revenue by month."""

from __future__ import annotations

import duckdb
import pandas as pd

from src.config import settings


_SQL_PATH = settings.SQL_DIR / "analytics" / "q1_revenue_by_month.sql"


def run(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Execute Q1 SQL and return results as a DataFrame."""
    sql = _SQL_PATH.read_text()
    return con.execute(sql).df()


def describe() -> str:
    """One-line business summary for reports/UI."""
    return (
        "Completed revenue by calendar month, using gross_order_amount "
        "for orders with status 'completed'."
    )