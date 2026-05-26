from __future__ import annotations
from decimal import Decimal
import pandas as pd


from src.config import schemas, settings
from src.ingestion.csv_loader import load_csv
from src.ingestion.jsonl_loader import load_jsonl
from src.transformation.dim_customer import build as build_dim_customer
from src.transformation.dim_product import build as build_dim_product
from src.transformation.fact_order import build as build_fact_order
from src.transformation.fact_payment import build as build_fact_payment
from src.transformation.fact_customer_issue import build as build_fact_customer_issue



def test_dim_customer_row_count() -> None:
    """20 raw customers minus 1 PK loser (C006) => 19 dim rows."""
    customers = load_csv(settings.INPUT_DIR / "customers.csv", schemas.RAW_CUSTOMERS_DTYPES)
    dim = build_dim_customer({"customers": customers})
    assert len(dim) == 19



def test_dim_product_active_flag_for_P011_is_false() -> None:
    products = load_csv(settings.INPUT_DIR / "products.csv", schemas.RAW_PRODUCTS_DTYPES)
    dim = build_dim_product({"products": products})
    p011 = dim[dim["product_key"] == "P011"].iloc[0]
    assert bool(p011["active_flag"]) is False




def test_fact_order_row_count() -> None:
  """31 raw orders minus 1 byte-identical duplicate (O1018) => 30 fact rows."""
  orders = load_csv(settings.INPUT_DIR / "orders.csv", schemas.RAW_ORDERS_DTYPES)
  products = load_csv(settings.INPUT_DIR / "products.csv", schemas.RAW_PRODUCTS_DTYPES)
  fact = build_fact_order({"orders": orders, "products": products})
  assert len(fact) == 30

def test_fact_order_order_amount_variance_for_O1021() -> None:
    orders = load_csv(settings.INPUT_DIR / "orders.csv", schemas.RAW_ORDERS_DTYPES)
    products = load_csv(settings.INPUT_DIR / "products.csv", schemas.RAW_PRODUCTS_DTYPES)
    fact = build_fact_order({"orders": orders, "products": products})
    r = fact[fact["order_key"] == "O1021"].iloc[0]
    assert r["gross_order_amount"] == Decimal("50.00")
    assert r["calculated_order_amount"] == Decimal("44.00")
    assert r["order_amount_variance"] == Decimal("6.00")

def test_fact_order_keeps_invalid_fk_rows() -> None:
    orders = load_csv(settings.INPUT_DIR / "orders.csv", schemas.RAW_ORDERS_DTYPES)
    products = load_csv(settings.INPUT_DIR / "products.csv", schemas.RAW_PRODUCTS_DTYPES)
    fact = build_fact_order({"orders": orders, "products": products})
    keys = set(fact["order_key"].tolist())
    assert "O1019" in keys
    assert "O1020" in keys



def test_fact_payment_keeps_orphan_PMT029() -> None:
    payments = load_csv(settings.INPUT_DIR / "payments.csv", schemas.RAW_PAYMENTS_DTYPES)
    fact = build_fact_payment({"payments": payments})
    p29 = fact[fact["payment_key"] == "PMT029"].iloc[0]
    assert p29["order_key"] == "O9999"
    assert p29["payment_amount"] == Decimal("100.00")



def test_fact_customer_issue_T010_created_date_is_null() -> None:
    tickets = load_jsonl(settings.INPUT_DIR / "support_tickets.jsonl")
    fact = build_fact_customer_issue({"support_tickets": tickets})
    t010 = fact[fact["ticket_id"] == "T010"].iloc[0]
    assert pd.isna(t010["created_date"])