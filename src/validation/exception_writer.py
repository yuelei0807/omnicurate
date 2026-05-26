"""Persist DQ exceptions to DuckDB and CSV.

Two idempotent writers used by the pipeline orchestrator:

* write_exceptions_csv  -> outputs/exceptions.csv (human review)
* persist_exceptions    -> dq_exception_report table in curated.duckdb

Both are safe to call on every pipeline run (truncate/delete-then-insert).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.config import settings
from src.validation._helpers import EXCEPTION_COLUMNS


def write_exceptions_csv(exceptions_df: pd.DataFrame) -> Path:
    """Write exceptions to settings.EXCEPTIONS_CSV; return the path.

  Idempotent: overwrites the file each run. Ensures OUTPUT_DIR exists.
  Empty input still writes a header-only CSV with canonical columns.
    """
    settings.ensure_output_dir()
    out = settings.EXCEPTIONS_CSV

    if exceptions_df.empty:
        pd.DataFrame({col: pd.Series(dtype="object") for col in EXCEPTION_COLUMNS}).to_csv(
            out, index=False
        )
        return out

    exceptions_df[list(EXCEPTION_COLUMNS)].to_csv(out, index=False)
    return out


def persist_exceptions(
    con: duckdb.DuckDBPyConnection,
    exceptions_df: pd.DataFrame,
) -> None:
    """Replace dq_exception_report contents with exceptions_df.

    Idempotent: DELETE all rows, then INSERT the new batch. Uses the
    same register/INSERT pattern as ingestion for consistency.
    """
    con.execute("DELETE FROM dq_exception_report")

    if exceptions_df.empty:
        return

    df = exceptions_df[list(EXCEPTION_COLUMNS)].copy()
    con.register("_exceptions_to_insert", df)
    try:
        con.execute(
            "INSERT INTO dq_exception_report SELECT * FROM _exceptions_to_insert"
        )
    finally:
        con.unregister("_exceptions_to_insert")