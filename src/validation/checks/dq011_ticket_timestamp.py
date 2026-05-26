"""DQ011: support_tickets.created_ts must parse to a valid timestamp.

Uses parse_series from timestamp_parser so DQ011 and the
transformation layer (fact_customer_issue.created_date) share the
same parse contract.

Two flavours of violation, both under rule_id DQ011:

* Missing: created_ts is NULL or empty/whitespace.
* Unparseable: value is present but parse_timestamp returns valid=False
  (e.g. T010's literal 'bad_timestamp').

This dataset triggers DQ011 exactly once: ticket_id=T010 has
created_ts='bad_timestamp'. All other nine tickets parse cleanly.
"""

from __future__ import annotations

import pandas as pd

from src.preprocessing.timestamp_parser import parse_series
from src.validation._helpers import (
    concat_exceptions,
    empty_exceptions,
    make_exception_rows,
)


def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Emit one exception per ticket whose created_ts is missing or unparseable.

    Args:
        stg: Mapping of staged raw DataFrames; uses stg["support_tickets"].

    Returns:
        DataFrame in dq_exception_report shape. Missing rows are listed
        before unparseable rows. Zero rows when every created_ts parses.
    """
    tickets = stg["support_tickets"]

    created_ts: pd.Series = tickets["created_ts"]
    raw_str = created_ts.fillna("").astype(str).str.strip()
    null_mask = created_ts.isna() | (raw_str == "")

    _parsed, valid_mask = parse_series(created_ts)
    valid_bool = valid_mask.astype(bool)
    unparseable_mask = (~null_mask) & (~valid_bool)

    if not (null_mask | unparseable_mask).any():
        return empty_exceptions()

    null_rows = tickets[null_mask]
    bad_rows = tickets[unparseable_mask]

    null_exc = make_exception_rows(
        "DQ011",
        record_keys=null_rows["ticket_id"].tolist(),
        issue_template="ticket_id={record_key}: created_ts is missing.",
    )

    unparseable_exc = make_exception_rows(
        "DQ011",
        record_keys=bad_rows["ticket_id"].tolist(),
        issue_template=(
            "ticket_id={record_key}: created_ts failed to parse: '{raw}'."
        ),
        fields={"raw": bad_rows["created_ts"].astype(str).tolist()},
    )

    return concat_exceptions(null_exc, unparseable_exc)