"""Raw-layer CSV ingestion.

Two thin functions, intentionally separate so each can be unit-tested
in isolation:

- ``load_csv``     : CSV on disk -> typed pandas DataFrame.
- ``insert_dataframe`` : DataFrame -> a named raw_* table in DuckDB.

Design notes:

* We read every column as pandas StringDtype (the dtype map in
  ``src.config.schemas`` is all "string"). Numeric-looking values
  stay verbatim so the preprocessing layer can cast them explicitly
  and surface coercion failures as DQ exceptions.

* ``keep_default_na=False`` prevents pandas from inferring NA from
  strings like "NA" / "N/A" / "NULL" -- those are preserved verbatim.
  ``na_values=[""]`` does convert literal empty cells to ``pd.NA``
  (which DuckDB stores as SQL NULL on insert), matching the
  conventional interpretation of an empty CSV cell.

* SQL identifiers cannot be parameterised, so ``insert_dataframe``
  validates ``table_name`` against the ``RAW_TABLE_NAMES`` allow-list.
  Any other value raises ``ValueError`` before any SQL runs.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.config.schemas import RAW_TABLE_NAMES


def load_csv(path: Path, dtypes: dict[str, str]) -> pd.DataFrame:
    """Read a CSV into a typed DataFrame using ``dtypes`` from schemas.py."""
    return pd.read_csv(
        path,
        dtype=dtypes,
        keep_default_na=False,
        na_values=[""],
    )


def insert_dataframe(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    df: pd.DataFrame,
) -> int:
    """Insert ``df`` into ``table_name`` and return the number of rows inserted.

    ``table_name`` is validated against ``RAW_TABLE_NAMES`` because SQL
    identifiers cannot be parameterised via placeholders. DuckDB's
    ``register`` exposes the DataFrame as a zero-copy view, which is
    much faster than row-by-row INSERTs.
    """
    if table_name not in RAW_TABLE_NAMES:
        raise ValueError(
            f"Refusing to insert into unknown table {table_name!r}; "
            f"must be one of {RAW_TABLE_NAMES}"
        )

    con.register("_df_to_insert", df)
    try:
        con.execute(f"INSERT INTO {table_name} SELECT * FROM _df_to_insert")
    finally:
        con.unregister("_df_to_insert")

    return len(df)