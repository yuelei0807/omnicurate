"""End-to-end reconciliation: full pipeline vs independent pandas checks."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from src.config import schemas, settings
from src.database.connection import duckdb_connection
from src.ingestion.csv_loader import load_csv
from src.pipeline import run
from src.preprocessing.deduplication import drop_exact_duplicates
from src.preprocessing.type_coercion import coerce_decimal_series


def _completed_order_total_from_csv() -> Decimal:
    """Sum order_total for completed orders, dropping byte-identical dup rows."""
    orders = load_csv(settings.INPUT_DIR / "orders.csv", schemas.RAW_ORDERS_DTYPES)
    kept, _dropped = drop_exact_duplicates(orders)
    completed = kept[kept["order_status"] == "completed"]
    typed, valid = coerce_decimal_series(completed["order_total"])
    total = Decimal("0")
    for val, ok in zip(typed, valid):
        if ok and val is not None:
            total += val
    return total


def _settled_payment_total_from_csv() -> Decimal:
    """Sum payment amount for settled payments."""
    payments = load_csv(settings.INPUT_DIR / "payments.csv", schemas.RAW_PAYMENTS_DTYPES)
    settled = payments[payments["payment_status"] == "settled"]
    typed, valid = coerce_decimal_series(settled["amount"])
    total = Decimal("0")
    for val, ok in zip(typed, valid):
        if ok and val is not None:
            total += val
    return total


def test_full_pipeline_reconciles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """pipeline.run() produces expected counts and reconciles money totals."""
    db_path = tmp_path / "curated.duckdb"
    exceptions_csv = tmp_path / "exceptions.csv"
    dq_report = tmp_path / "data_quality_report.md"
    answers_md = tmp_path / "business_answers.md"

    monkeypatch.setattr(settings, "DUCKDB_PATH", db_path)
    monkeypatch.setattr(settings, "EXCEPTIONS_CSV", exceptions_csv)
    monkeypatch.setattr(settings, "DQ_REPORT_MD", dq_report)
    monkeypatch.setattr(settings, "ANSWERS_MD", answers_md)
    monkeypatch.setattr(settings, "OUTPUT_DIR", tmp_path)

    run()

    expected_order_total = _completed_order_total_from_csv()
    expected_payment_total = _settled_payment_total_from_csv()

    with duckdb_connection(read_only=True) as con:
        raw_total = int(
            con.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM raw_customers)
                  + (SELECT COUNT(*) FROM raw_products)
                  + (SELECT COUNT(*) FROM raw_orders)
                  + (SELECT COUNT(*) FROM raw_payments)
                  + (SELECT COUNT(*) FROM raw_support_tickets)
                AS n
                """
            ).fetchdf().iloc[0]["n"]
        )
        dim_customers = int(
            con.execute("SELECT COUNT(*) AS n FROM dim_customer").fetchdf().iloc[0]["n"]
        )
        fact_order_total = con.execute(
            """
            SELECT COALESCE(SUM(gross_order_amount), 0) AS total
            FROM fact_order
            WHERE order_status = 'completed'
            """
        ).fetchdf().iloc[0]["total"]
        fact_payment_total = con.execute(
            """
            SELECT COALESCE(SUM(payment_amount), 0) AS total
            FROM fact_payment
            WHERE payment_status = 'settled'
            """
        ).fetchdf().iloc[0]["total"]
        dq_count = int(
            con.execute("SELECT COUNT(*) AS n FROM dq_exception_report").fetchdf().iloc[0]["n"]
        )

    assert raw_total == 103
    assert dim_customers == 19
    assert Decimal(str(fact_order_total)) == expected_order_total
    assert Decimal(str(fact_payment_total)) == expected_payment_total
    assert dq_count > 0

    assert exceptions_csv.exists() and exceptions_csv.stat().st_size > 0
    assert dq_report.exists() and dq_report.stat().st_size > 0
    assert answers_md.exists() and answers_md.stat().st_size > 0