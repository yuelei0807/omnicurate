"""Q2 analytics: top customers by completed order value."""

from __future__ import annotations

import duckdb
import pandas as pd

from src.config import settings


_SQL_PATH = settings.SQL_DIR / "analytics" / "q2_top_customers.sql"


def run(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Execute Q2 SQL and return results as a DataFrame."""
    sql = _SQL_PATH.read_text()
    return con.execute(sql).df()


def describe() -> str:
    """One-line business summary for reports/UI."""
    return (
        "Top customers ranked by total completed order value "
        "(gross_order_amount), excluding orders with invalid customer_key."
    )