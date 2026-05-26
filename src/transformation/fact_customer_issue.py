"""Build fact_customer_issue from staged raw support tickets.

Expected behavior (aligned with DQ011/DQ012 and curated DDL):
* One row per raw ticket (support_tickets.jsonl has 10 rows).
* Keep rows even when created_ts is bad or customer_id is unknown.
* created_ts is parsed to DATE; if unparseable/missing -> NULL.
* customer_key is derived directly from ticket.customer_id (string).
  If the customer_id is not present in dim_customer, this remains the
  orphan key value so the record can surface alongside exceptions.
"""

from __future__ import annotations

import pandas as pd

from src.preprocessing.timestamp_parser import parse_series


def _optional_str(value: object) -> str | None:
    """Convert scalar to str unless missing (keeps NULLs as None)."""
    if value is None or value is pd.NA:
        return None
    if isinstance(value, float) and value != value:
        return None
    return str(value)


def build(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return a DataFrame ready for fact_customer_issue insert."""
    tickets = stg["support_tickets"]

    parsed_ts, valid_mask = parse_series(tickets["created_ts"])
    created_dates = parsed_ts.dt.date
    created_dates = created_dates.where(valid_mask, other=pd.NaT)

    out = pd.DataFrame(
        {
            "ticket_id": tickets["ticket_id"].astype(str),
            "customer_key": tickets["customer_id"].apply(_optional_str),
            "created_date": created_dates,
            "channel": tickets["channel"].astype(str),
            "issue_category": tickets["category"].astype(str),
            "sentiment": tickets["sentiment"].astype(str),
            "description": tickets["description"].astype(str),
        }
    )

    return out.sort_values("ticket_id").reset_index(drop=True)

