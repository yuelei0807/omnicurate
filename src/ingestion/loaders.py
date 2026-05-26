"""Raw-layer ingestion orchestrator.

One public function: ``load_all(con)``. It creates the raw tables
(idempotent), truncates each one, loads its source file via the
matching loader, and returns a ``{table_name: row_count}`` dict for
the pipeline to log.

Truncating before insert (rather than relying solely on
``CREATE OR REPLACE TABLE`` in the DDL) makes the function safe to
call against an already-populated database without doubling rows.
This matters for some tests that share a DuckDB across cases.

The ``_SOURCE_MAP`` is the single source of truth that ties each raw
table to its source file and dtype map. Adding a new raw source is
one line here plus one line in ``schemas.RAW_TABLE_NAMES``.
"""

from __future__ import annotations

import duckdb

from src.config import schemas, settings
from src.database import ddl
from src.ingestion.csv_loader import insert_dataframe, load_csv
from src.ingestion.jsonl_loader import load_jsonl

# (raw_table_name, source_filename, dtypes_or_None_for_jsonl)
_SOURCE_MAP: tuple[tuple[str, str, dict[str, str] | None], ...] = (
    ("raw_customers",       "customers.csv",         schemas.RAW_CUSTOMERS_DTYPES),
    ("raw_products",        "products.csv",          schemas.RAW_PRODUCTS_DTYPES),
    ("raw_orders",          "orders.csv",            schemas.RAW_ORDERS_DTYPES),
    ("raw_payments",        "payments.csv",          schemas.RAW_PAYMENTS_DTYPES),
    ("raw_support_tickets", "support_tickets.jsonl", None),
)


def load_all(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Load every raw source file into its matching ``raw_*`` table.

    Idempotent: re-running on the same connection does not double rows
    because each table is truncated before insert. Returns a dict of
    final row counts keyed by table name, in the order declared by
    ``_SOURCE_MAP`` (matches ``schemas.RAW_TABLE_NAMES``).
    """
    ddl.create_raw_tables(con)

    counts: dict[str, int] = {}
    for table_name, filename, dtypes in _SOURCE_MAP:
        path = settings.INPUT_DIR / filename
        if dtypes is None:
            df = load_jsonl(path)
        else:
            df = load_csv(path, dtypes)

        # Safe: table_name is from a module-private constant, not user input.
        con.execute(f"DELETE FROM {table_name}")
        inserted = insert_dataframe(con, table_name, df)
        counts[table_name] = inserted
        print(f"[ingest] {table_name:22s} <- {filename:24s}  rows={inserted}")

    return counts