"""DQ007: completed orders must have positive quantity.

Scope: only orders where order_status == 'completed'. Other statuses
(cancelled, returned) are out of scope -- a returned order may
legitimately carry a non-positive quantity as a reversal marker.

Three flavours of violation, all under rule_id DQ007:

* Missing: quantity is NULL. Fix: backfill from source.
* Unparseable: quantity is present but not a valid integer ('abc',
  '1.5'). Fix: correct the source value.
* Non-positive: quantity parses cleanly but is <= 0. Fix: investigate
  the source system; correct the sign or reverse the order.

Status matching is case-insensitive and whitespace-trimmed so
'Completed ' or 'COMPLETED' would still be in scope.

This dataset triggers DQ007 exactly once: O1030 has order_status=
'completed' AND quantity=-1 (falls into the non-positive bucket).
O1014 (quantity=1, status=returned) and O1005 (status=cancelled)
are out of scope.

The quantity coercion uses coerce_int_series from type_coercion so
DQ007's notion of 'valid integer' is identical to what the
transformation layer will use when populating fact_order.quantity.
"""

from __future__ import annotations

import pandas as pd

from src.preprocessing.type_coercion import coerce_int_series
from src.validation._helpers import (
    concat_exceptions,
    empty_exceptions,
    make_exception_rows,
)


def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Emit one exception per completed order with missing/invalid/non-positive quantity.

    Args:
        stg: Mapping of staged raw DataFrames; uses stg["orders"].

    Returns:
        DataFrame in dq_exception_report shape. Sub-buckets are
        emitted in order: missing, then unparseable, then non-positive
        -- so the report groups by root cause. Zero rows when every
        completed order has a positive integer quantity.
    """
    orders = stg["orders"]

    completed_mask = (
        orders["order_status"].astype(str).str.strip().str.lower() == "completed"
    )
    completed = orders[completed_mask]

    if completed.empty:
        return empty_exceptions()

    quantity: pd.Series = completed["quantity"]
    null_mask = quantity.isna()
    typed_qty, valid_qty = coerce_int_series(quantity)
    valid_bool = valid_qty.astype(bool)

    present_invalid_mask = (~null_mask) & (~valid_bool)
    non_positive_mask = valid_bool & (typed_qty <= 0).fillna(False).astype(bool)

    if not (null_mask | present_invalid_mask | non_positive_mask).any():
        return empty_exceptions()

    null_rows = completed[null_mask]
    invalid_rows = completed[present_invalid_mask]
    non_pos_rows = completed[non_positive_mask]
    non_pos_values = typed_qty[non_positive_mask].astype(str)

    null_exc = make_exception_rows(
        "DQ007",
        record_keys=null_rows["order_id"].tolist(),
        issue_template="order_id={record_key}: completed-order quantity is missing.",
    )

    invalid_exc = make_exception_rows(
        "DQ007",
        record_keys=invalid_rows["order_id"].tolist(),
        issue_template=(
            "order_id={record_key}: completed-order quantity '{raw}' "
            "is not a valid integer."
        ),
        fields={"raw": invalid_rows["quantity"].astype(str).tolist()},
    )

    non_pos_exc = make_exception_rows(
        "DQ007",
        record_keys=non_pos_rows["order_id"].tolist(),
        issue_template=(
            "order_id={record_key}: completed-order quantity {qty} is not positive."
        ),
        fields={"qty": non_pos_values.tolist()},
    )

    return concat_exceptions(null_exc, invalid_exc, non_pos_exc)