"""Q5 analytics: negative tickets vs order/payment exceptions."""

from __future__ import annotations

import duckdb
import pandas as pd

from src.config import settings


_SQL_PATH = settings.SQL_DIR / "analytics" / "q5_sentiment_link.sql"

_DETAIL_SQL = """
WITH negative_customers AS (
    SELECT DISTINCT customer_key
    FROM fact_customer_issue
    WHERE lower(sentiment) = 'negative'
),
order_ex AS (
    SELECT record_key AS order_key
    FROM dq_exception_report
    WHERE dataset = 'orders'
    UNION
    SELECT fp.order_key
    FROM dq_exception_report pe
    INNER JOIN fact_payment fp
        ON pe.record_key = fp.payment_key
    WHERE pe.dataset = 'payments'
      AND fp.order_key IS NOT NULL
),
orders_flagged AS (
    SELECT
        o.customer_key,
        o.order_key,
        CASE WHEN e.order_key IS NOT NULL THEN 1 ELSE 0 END AS has_exception
    FROM fact_order o
    LEFT JOIN order_ex e
        ON o.order_key = e.order_key
),
per_customer AS (
    SELECT
        customer_key,
        COUNT(*) AS total_orders,
        SUM(has_exception) AS orders_with_exception
    FROM orders_flagged
    GROUP BY customer_key
)
SELECT
    c.customer_key,
    CASE
        WHEN nc.customer_key IS NOT NULL THEN 'has_negative_ticket'
        ELSE 'no_negative_ticket'
    END AS cohort,
    COALESCE(pc.total_orders, 0) AS total_orders,
    COALESCE(pc.orders_with_exception, 0) AS orders_with_exception,
    ROUND(
        100.0 * COALESCE(pc.orders_with_exception, 0)
        / NULLIF(COALESCE(pc.total_orders, 0), 0),
        2
    ) AS pct_orders_with_exception
FROM dim_customer c
LEFT JOIN negative_customers nc
    ON c.customer_key = nc.customer_key
LEFT JOIN per_customer pc
    ON c.customer_key = pc.customer_key
ORDER BY cohort, c.customer_key;
"""


def run(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Execute Q5 cohort summary SQL."""
    return con.execute(_SQL_PATH.read_text()).df()


def describe() -> str:
    """One-line business summary for reports/UI."""
    return (
        "Compares customers with negative support tickets vs those without, "
        "measuring the share of their orders that triggered exceptions."
    )


def per_customer_detail(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Per-customer breakdown for drill-down tables in the UI."""
    return con.execute(_DETAIL_SQL).df()