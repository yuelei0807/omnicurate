"""DuckDB connection management.

This is the only module in the project that imports duckdb directly.
Every other module receives a connection object opened here, so the
dependency surface stays tiny and easy to mock in tests.

Usage:

    from src.database.connection import duckdb_connection

    with duckdb_connection() as con:           # read+write
        con.execute("CREATE TABLE t (x INT)")

    with duckdb_connection(read_only=True) as con:  # Streamlit / tests
        con.execute("SELECT * FROM t").fetchall()

    reset_database()                            # nuke the file
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import duckdb

from src.config import settings


@contextmanager
def duckdb_connection(read_only: bool = False) -> Iterator[duckdb.DuckDBPyConnection]:
    """Yield a DuckDB connection to the project's curated.duckdb file.

    Ensures the output directory exists before connecting (so the very
    first pipeline run on a fresh checkout works without manual mkdir).
    The connection is always closed in the finally block, even when the
    caller raises an exception.

    Parameters
    ----------
    read_only:
        Open the database in read-only mode. The file must already
        exist; callers (e.g. Streamlit pages) are responsible for
        showing a friendly "run the pipeline first" message when it
        does not.
    """
    settings.ensure_output_dir()
    con = duckdb.connect(str(settings.DUCKDB_PATH), read_only=read_only)
    try:
        yield con
    finally:
        con.close()


def reset_database() -> None:
    """Delete the DuckDB file if it exists.

    Called at the start of a pipeline run so every rebuild is from a
    clean slate and there is no risk of stale rows surviving a schema
    change. Safe to call when the file does not exist.
    """
    if settings.DUCKDB_PATH.exists():
        settings.DUCKDB_PATH.unlink()