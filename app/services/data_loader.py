"""Cached DuckDB access for Streamlit pages."""

from __future__ import annotations

from datetime import datetime

import duckdb
import pandas as pd
import streamlit as st

from src.config import schemas, settings


def require_database() -> None:
    """Stop the page if the pipeline has not produced curated.duckdb yet."""
    if not settings.DUCKDB_PATH.exists():
        st.warning(
            "Pipeline has not been run yet — run "
            "`python -m src.pipeline` from the project root."
        )
        st.stop()


@st.cache_resource
def get_con() -> duckdb.DuckDBPyConnection:
    """Return a read-only DuckDB connection (one per Streamlit session)."""
    require_database()
    return duckdb.connect(str(settings.DUCKDB_PATH), read_only=True)


@st.cache_data(ttl=60)
def query(sql: str) -> pd.DataFrame:
    """Run a SQL query and return a DataFrame (cached 60s)."""
    require_database()
    return get_con().execute(sql).fetchdf()


def list_tables() -> list[str]:
    """Return curated table names for the model explorer."""
    require_database()
    return list(schemas.CURATED_TABLE_NAMES)


def table_preview(name: str, limit: int = 100) -> pd.DataFrame:
    """Return up to ``limit`` rows from an allow-listed curated table."""
    if name not in schemas.CURATED_TABLE_NAMES:
        raise ValueError(f"Unknown curated table: {name!r}")
    return query(f"SELECT * FROM {name} LIMIT {int(limit)}")


def kpi_metrics() -> dict[str, str]:
    """Home-page KPI values from the curated database."""
    require_database()
    con = get_con()

    customers = int(
        con.execute("SELECT COUNT(*) AS n FROM dim_customer").fetchdf().iloc[0]["n"]
    )
    revenue = con.execute(
        """
        SELECT COALESCE(ROUND(SUM(gross_order_amount), 2), 0) AS total
        FROM fact_order
        WHERE order_status = 'completed'
        """
    ).fetchdf().iloc[0]["total"]
    exceptions = int(
        con.execute("SELECT COUNT(*) AS n FROM dq_exception_report").fetchdf().iloc[0]["n"]
    )
    mtime = datetime.fromtimestamp(settings.DUCKDB_PATH.stat().st_mtime)
    last_run = mtime.strftime("%Y-%m-%d %H:%M")

    return {
        "total_customers": f"{customers:,}",
        "completed_revenue": f"${float(revenue):,.2f}",
        "total_exceptions": f"{exceptions:,}",
        "last_pipeline_run": last_run,
    }