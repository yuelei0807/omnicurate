"""End-to-end pipeline orchestrator.

Runs all layers in order on a fresh DuckDB file:
  reset -> DDL -> ingest -> stage -> validate -> transform -> report
"""

from __future__ import annotations

import pandas as pd

from src.config import schemas
from src.database import ddl
from src.database.connection import duckdb_connection, reset_database
from src.ingestion.loaders import load_all
from src.preprocessing.deduplication import drop_exact_duplicates, resolve_pk_duplicates
from src.reporting import business_answers, dq_report
from src.transformation.dim_customer import build as build_dim_customer
from src.transformation.dim_product import build as build_dim_product
from src.transformation.fact_customer_issue import build as build_fact_customer_issue
from src.transformation.fact_order import build as build_fact_order
from src.transformation.fact_payment import build as build_fact_payment
from src.transformation.persist import persist_curated
from src.validation.exception_writer import persist_exceptions, write_exceptions_csv
from src.validation.runner import apply_all


def _read_raw_frames(con) -> dict[str, pd.DataFrame]:
    """Load raw_* tables from DuckDB into pandas (string-like landing data)."""
    return {
        "customers": con.execute("SELECT * FROM raw_customers").fetchdf(),
        "products": con.execute("SELECT * FROM raw_products").fetchdf(),
        "orders": con.execute("SELECT * FROM raw_orders").fetchdf(),
        "payments": con.execute("SELECT * FROM raw_payments").fetchdf(),
        "support_tickets": con.execute("SELECT * FROM raw_support_tickets").fetchdf(),
    }


def _build_stg(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Assemble staging dict; include dropped duplicate rows for traceability."""
    customers = raw["customers"]
    orders = raw["orders"]

    _cust_winners, customers_duplicates = resolve_pk_duplicates(
        customers, ["customer_id"]
    )
    orders_kept, orders_exact_dup = drop_exact_duplicates(orders)
    _orders_kept, orders_pk_dup = resolve_pk_duplicates(orders_kept, ["order_id"])
    orders_duplicates = pd.concat(
        [orders_exact_dup, orders_pk_dup], ignore_index=True
    )

    return {
        "customers": customers,
        "customers_duplicates": customers_duplicates,
        "products": raw["products"],
        "orders": orders,
        "orders_duplicates": orders_duplicates,
        "payments": raw["payments"],
        "support_tickets": raw["support_tickets"],
    }


def _print_curated_summary(con) -> None:
    """Print row counts for every curated table."""
    print("[phase 8] curated table row counts")
    for table_name in schemas.CURATED_TABLE_NAMES:
        n = int(
            con.execute(f"SELECT COUNT(*) AS n FROM {table_name}").fetchdf().iloc[0]["n"]
        )
        print(f"  {table_name:22s} {n:>6}")


def run() -> None:
    """Execute the full pipeline once (idempotent per run via reset_database)."""
    print("[phase 1] reset database")
    reset_database()

    with duckdb_connection() as con:
        print("[phase 2] create raw and curated tables")
        ddl.create_raw_tables(con)
        ddl.create_curated_tables(con)

        print("[phase 3] ingest raw sources")
        ingest_counts = load_all(con)
        raw_rows = sum(ingest_counts.values())
        print(f"  raw rows ingested (total): {raw_rows}")

        print("[phase 4] stage raw frames for validation/transformation")
        raw = _read_raw_frames(con)
        stg = _build_stg(raw)
        print(f"  customers_duplicates: {len(stg['customers_duplicates'])}")
        print(f"  orders_duplicates:    {len(stg['orders_duplicates'])}")

        print("[phase 5] validate and persist exceptions")
        exceptions = apply_all(stg)
        csv_path = write_exceptions_csv(exceptions)
        persist_exceptions(con, exceptions)
        print(f"  exceptions: {len(exceptions)} rows -> {csv_path}")

        print("[phase 6] transform and persist curated tables")
        frames = {
            "dim_customer": build_dim_customer(stg),
            "dim_product": build_dim_product(stg),
            "fact_order": build_fact_order(stg),
            "fact_payment": build_fact_payment(stg),
            "fact_customer_issue": build_fact_customer_issue(stg),
        }
        persist_curated(con, frames)

        print("[phase 7] write reports")
        dq_path = dq_report.write(con)
        answers_path = business_answers.write(con)
        print(f"  dq report:       {dq_path}")
        print(f"  business answers:{answers_path}")

        _print_curated_summary(con)


if __name__ == "__main__":
    run()