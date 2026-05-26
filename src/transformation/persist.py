"""Persist curated tables into DuckDB.

This is the transformation-layer analogue of src/ingestion/csv_loader.
It writes pandas DataFrames into the DuckDB curated schema using an
allow-list pattern so dynamic table names cannot be abused.
"""

from __future__ import annotations

from typing import Iterator

import duckdb
import pandas as pd

from src.config.schemas import CURATED_TABLE_NAMES


def _iter_persist_targets() -> Iterator[str]:
    """Yield curated tables to persist (exclude dq_exception_report)."""
    for name in CURATED_TABLE_NAMES:
        if name == "dq_exception_report":
            continue
        yield name


def persist_curated(
    con: duckdb.DuckDBPyConnection,
    frames: dict[str, pd.DataFrame],
) -> None:
    """Truncate and insert curated frames into DuckDB.

    Idempotent: DELETE all rows for each target table then insert the new
    DataFrame batch.
    """
    for table_name in _iter_persist_targets():
        if table_name not in frames:
            # Allow partial frames in dev/debug; pipeline can choose
            # to build only what it needs.
            continue
        if table_name not in CURATED_TABLE_NAMES:
            raise ValueError(f"Refusing to persist into unknown table {table_name!r}")

        df = frames[table_name]
        con.register("_df_to_insert", df)
        try:
            con.execute(f"DELETE FROM {table_name}")
            con.execute(f"INSERT INTO {table_name} SELECT * FROM _df_to_insert")
        finally:
            con.unregister("_df_to_insert")

