"""DQ005: orders.customer_id must exist in customers.

Foreign-key existence check. The valid customer-id set is built from
the raw customers DataFrame -- we don't dedup first because both
copies of a PK-duplicated customer_id contribute the same value to
the set, so dedup is a no-op for membership.

Each physical row in raw orders gets its own check. If O1018 (the
byte-id duplicate) referenced an orphan customer, BOTH copies would
emit DQ005 -- the correct semantic, since raw data really does
contain two bad references. In this dataset O1018 references C018
which is valid, so the duplication is irrelevant here.

Two flavours of violation, both under rule_id DQ005:

* Missing: order's customer_id is NULL. Fix: backfill from source.
* Unknown: order's customer_id is non-NULL but not in customers.
  Fix: correct the reference or stub the missing customer.

This dataset triggers DQ005 exactly once: O1019 references C999
(no such customer). All other 30 orders reference valid customer_ids.
"""

from __future__ import annotations

import pandas as pd

from src.validation._helpers import (
    concat_exceptions,
    empty_exceptions,
    make_exception_rows,
)


def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Emit one exception per order whose customer_id is missing or unknown.

    Args:
        stg: Mapping of staged raw DataFrames; uses stg["orders"]
            AND stg["customers"].

    Returns:
        DataFrame in dq_exception_report shape. Missing-id rows are
        listed before unknown-id rows so the report groups by root
        cause. Zero rows when every order has a valid customer FK.
    """
    orders = stg["orders"]
    customers = stg["customers"]

    valid_ids = set(customers["customer_id"].dropna().astype(str))

    null_mask = orders["customer_id"].isna()
    unknown_mask = (~null_mask) & (
        ~orders["customer_id"].astype(str).isin(valid_ids)
    )

    if not (null_mask | unknown_mask).any():
        return empty_exceptions()

    null_rows = orders[null_mask]
    unknown_rows = orders[unknown_mask]

    null_exc = make_exception_rows(
        "DQ005",
        record_keys=null_rows["order_id"].tolist(),
        issue_template="order_id={record_key}: customer_id is missing.",
    )

    unknown_exc = make_exception_rows(
        "DQ005",
        record_keys=unknown_rows["order_id"].tolist(),
        issue_template=(
            "order_id={record_key}: customer_id '{cid}' not found in customers."
        ),
        fields={"cid": unknown_rows["customer_id"].astype(str).tolist()},
    )

    return concat_exceptions(null_exc, unknown_exc)