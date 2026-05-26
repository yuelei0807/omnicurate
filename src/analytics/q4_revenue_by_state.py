"""Q4 analytics: completed revenue by shipping state."""

from __future__ import annotations

import duckdb
import pandas as pd

from src.config import settings


_SQL_PATH = settings.SQL_DIR / "analytics" / "q4_revenue_by_state.sql"


def run(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Execute Q4 SQL and return results as a DataFrame."""
    sql = _SQL_PATH.read_text()
    return con.execute(sql).df()


def describe() -> str:
    """One-line business summary for reports/UI."""
    return (
        "Completed revenue aggregated by standardized shipping_state "
        "(USPS 2-letter codes)."
    )