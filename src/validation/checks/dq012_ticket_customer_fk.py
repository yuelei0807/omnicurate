"""DQ012: support_tickets.customer_id should exist in customers.

Foreign-key existence check from tickets to the customer master.
The valid customer-id set includes every customer_id present in raw
customers (both C006 PK rows contribute C006 once).

Two flavours of violation, both under rule_id DQ012:

* Missing: ticket's customer_id is NULL.
* Unknown: customer_id is non-NULL but not in customers.

This dataset triggers DQ012 exactly once: T005 references C999,
which does not exist in customers.csv (same orphan id as O1019 in
DQ005).
"""

from __future__ import annotations

import pandas as pd

from src.validation._helpers import (
    concat_exceptions,
    empty_exceptions,
    make_exception_rows,
)


def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Emit one exception per ticket whose customer_id is missing or unknown.

    Args:
        stg: Mapping of staged raw DataFrames; uses stg["support_tickets"]
            AND stg["customers"].

    Returns:
        DataFrame in dq_exception_report shape. Missing-id rows are
        listed before unknown-id rows. Zero rows when every ticket
        references a known customer.
    """
    tickets = stg["support_tickets"]
    customers = stg["customers"]

    valid_ids = set(customers["customer_id"].dropna().astype(str))

    customer_id: pd.Series = tickets["customer_id"]
    null_mask = customer_id.isna()
    unknown_mask = (~null_mask) & (~customer_id.astype(str).isin(valid_ids))

    if not (null_mask | unknown_mask).any():
        return empty_exceptions()

    null_rows = tickets[null_mask]
    unknown_rows = tickets[unknown_mask]

    null_exc = make_exception_rows(
        "DQ012",
        record_keys=null_rows["ticket_id"].tolist(),
        issue_template="ticket_id={record_key}: customer_id is missing.",
    )

    unknown_exc = make_exception_rows(
        "DQ012",
        record_keys=unknown_rows["ticket_id"].tolist(),
        issue_template=(
            "ticket_id={record_key}: customer_id '{cid}' not found in customers."
        ),
        fields={"cid": unknown_rows["customer_id"].astype(str).tolist()},
    )

    return concat_exceptions(null_exc, unknown_exc)