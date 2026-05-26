"""Schema declarations for raw input files and canonical table-name registries.

This module is dependency-free (no pandas, no duckdb). 
Two purposes:
1. Tell ``pandas.read_csv`` what dtype to read each raw column as. We
   intentionally keep numeric-looking columns as ``"string"`` so the
   preprocessing layer can cast them explicitly and surface coercion
   failures as DQ exceptions instead of silently producing NaN.
2. Provide a single source of truth for raw and curated table names,
   used by the DDL runner, the ingestion loader (as an allow-list to
   defend against table-name injection), the transformation persist
   step, and the Streamlit Curated Model Explorer.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Pandas dtype maps for read_csv. One dict per CSV input file.
# Column names MUST match the source CSV header rows exactly.
# ---------------------------------------------------------------------------

RAW_CUSTOMERS_DTYPES: dict[str, str] = {
    "customer_id": "string",
    "first_name": "string",
    "last_name": "string",
    "email": "string",
    "phone": "string",
    "country": "string",
    "state": "string",
    "signup_date": "string",
    "loyalty_tier": "string",
}

RAW_PRODUCTS_DTYPES: dict[str, str] = {
    "product_id": "string",
    "product_name": "string",
    "category": "string",
    "unit_price": "string",
    "active_flag": "string",
}

RAW_ORDERS_DTYPES: dict[str, str] = {
    "order_id": "string",
    "customer_id": "string",
    "order_ts": "string",
    "product_id": "string",
    "quantity": "string",
    "order_status": "string",
    "shipping_state": "string",
    "order_total": "string",
}

RAW_PAYMENTS_DTYPES: dict[str, str] = {
    "payment_id": "string",
    "order_id": "string",
    "payment_ts": "string",
    "payment_method": "string",
    "payment_status": "string",
    "amount": "string",
}

# ---------------------------------------------------------------------------
# Canonical table-name registries.
# Order is for human-readable summary output; correctness does not depend on it.
# ---------------------------------------------------------------------------

RAW_TABLE_NAMES: list[str] = [
    "raw_customers",
    "raw_products",
    "raw_orders",
    "raw_payments",
    "raw_support_tickets",
]

CURATED_TABLE_NAMES: list[str] = [
    "dim_customer",
    "dim_product",
    "fact_order",
    "fact_payment",
    "fact_customer_issue",
    "dq_exception_report",
]
