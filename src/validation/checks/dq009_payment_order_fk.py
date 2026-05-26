"""DQ009: payment order_id must exist in orders.

Foreign-key existence check from payments to orders. The valid
order-id set is built from orders AFTER drop_exact_duplicates so
byte-identical duplicates (O1018) do not affect membership -- the
surviving row still contributes order_id O1018 to the set.

Two flavours of violation, both under rule_id DQ009:

* Missing: payment's order_id is NULL.
* Unknown: order_id is non-NULL but not in the deduplicated order set.

This dataset triggers DQ009 exactly once: PMT029 references O9999,
which does not exist in orders.csv. PMT021 (O1021) is a valid FK;
its amount mismatch is DQ010, not DQ009.
"""

from __future__ import annotations

import pandas as pd

from src.preprocessing.deduplication import drop_exact_duplicates
from src.validation._helpers import (
    concat_exceptions,
    empty_exceptions,
    make_exception_rows,
)


def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Emit one exception per payment whose order_id is missing or unknown.

    Args:
        stg: Mapping of staged raw DataFrames; uses stg["payments"]
            AND stg["orders"].

    Returns:
        DataFrame in dq_exception_report shape. Missing-id rows are
        listed before unknown-id rows. Zero rows when every payment
        references a known order.
    """
    payments = stg["payments"]
    orders = stg["orders"]

    kept_orders, _dropped = drop_exact_duplicates(orders)
    valid_order_ids = set(kept_orders["order_id"].dropna().astype(str))

    order_id: pd.Series = payments["order_id"]
    null_mask = order_id.isna()
    unknown_mask = (~null_mask) & (~order_id.astype(str).isin(valid_order_ids))

    if not (null_mask | unknown_mask).any():
        return empty_exceptions()

    null_rows = payments[null_mask]
    unknown_rows = payments[unknown_mask]

    null_exc = make_exception_rows(
        "DQ009",
        record_keys=null_rows["payment_id"].tolist(),
        issue_template="payment_id={record_key}: payment order_id is missing.",
    )

    unknown_exc = make_exception_rows(
        "DQ009",
        record_keys=unknown_rows["payment_id"].tolist(),
        issue_template=(
            "Orphan payment: order_id={oid} not found in orders "
            "(payment_id={record_key})."
        ),
        fields={"oid": unknown_rows["order_id"].astype(str).tolist()},
    )

    return concat_exceptions(null_exc, unknown_exc)