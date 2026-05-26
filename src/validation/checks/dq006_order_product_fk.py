"""DQ006: orders.product_id must exist in products.

Mirror of DQ005 but on the product FK. The valid product-id set is
built from raw products. products.csv has no PK duplicates in this
dataset, so dedup is not relevant here.

Each physical row in raw orders gets its own check. If the byte-id
duplicate O1018 referenced an orphan product, BOTH copies would
emit DQ006.

Two flavours of violation, both under rule_id DQ006:

* Missing: product_id is NULL. Fix: backfill from source.
* Unknown: product_id is non-NULL but not in products. Fix: correct
  the reference or stub the missing product.

This dataset triggers DQ006 exactly once: O1020 references P999 (no
such product). All other 30 orders reference valid product_ids in
P001..P012.
"""

from __future__ import annotations

import pandas as pd

from src.validation._helpers import (
    concat_exceptions,
    empty_exceptions,
    make_exception_rows,
)


def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Emit one exception per order whose product_id is missing or unknown.

    Args:
        stg: Mapping of staged raw DataFrames; uses stg["orders"]
            AND stg["products"].

    Returns:
        DataFrame in dq_exception_report shape. Missing-id rows are
        listed before unknown-id rows so the report groups by root
        cause. Zero rows when every order has a valid product FK.
    """
    orders = stg["orders"]
    products = stg["products"]

    valid_ids = set(products["product_id"].dropna().astype(str))

    null_mask = orders["product_id"].isna()
    unknown_mask = (~null_mask) & (
        ~orders["product_id"].astype(str).isin(valid_ids)
    )

    if not (null_mask | unknown_mask).any():
        return empty_exceptions()

    null_rows = orders[null_mask]
    unknown_rows = orders[unknown_mask]

    null_exc = make_exception_rows(
        "DQ006",
        record_keys=null_rows["order_id"].tolist(),
        issue_template="order_id={record_key}: product_id is missing.",
    )

    unknown_exc = make_exception_rows(
        "DQ006",
        record_keys=unknown_rows["order_id"].tolist(),
        issue_template=(
            "order_id={record_key}: product_id '{pid}' not found in products."
        ),
        fields={"pid": unknown_rows["product_id"].astype(str).tolist()},
    )

    return concat_exceptions(null_exc, unknown_exc)