"""DDL runner: executes the raw and curated CREATE statements.

Thin wrapper over duckdb.execute() that reads SQL files from sql/ddl/
and runs them against an open connection. The two named helpers
(create_raw_tables, create_curated_tables) exist so callers can run
just one half — useful for tests that need only the raw schema or
only the curated schema.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from src.config import settings

_RAW_DDL_PATH: Path = settings.SQL_DIR / "ddl" / "001_raw_tables.sql"
_CURATED_DDL_PATH: Path = settings.SQL_DIR / "ddl" / "002_curated_tables.sql"


def execute_sql_file(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    """Execute every statement in the given SQL file against ``con``."""
    con.execute(path.read_text())


def create_raw_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Create the five raw_* landing tables (idempotent)."""
    execute_sql_file(con, _RAW_DDL_PATH)


def create_curated_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Create the six curated tables: dim_*, fact_*, dq_exception_report (idempotent)."""
    execute_sql_file(con, _CURATED_DDL_PATH)