"""Build fact_payment from staged raw payments.

Expected behavior (aligned with DQ009 and curated DDL):
* One row per raw payment (no dedup required; payments.csv is clean enough
  for this exercise).
* Keep orphan payments whose order_id is not present in the orders master
  (PMT029 -> O9999) so Q3 can surface them via exceptions.
* payment_ts is parsed to DATE via timestamp_parser; invalid timestamps
  become NULL.
* amount is coerced to Decimal; invalid amounts become NULL.
"""

from __future__ import annotations

import pandas as pd

from src.preprocessing.timestamp_parser import parse_series
from src.preprocessing.type_coercion import coerce_decimal_series


def _optional_str(value: object) -> str | None:
    """Convert a scalar to str unless it is missing (keeps NULLs as None)."""
    if value is None or value is pd.NA:
        return None
    # NaN float check (rare in our string dtypes, but safe)
    if isinstance(value, float) and value != value:
        return None
    return str(value)


def build(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return a DataFrame ready for fact_payment insert."""
    payments = stg["payments"]

    parsed_ts, valid_mask = parse_series(payments["payment_ts"])
    payment_dates = parsed_ts.dt.date
    payment_dates = payment_dates.where(valid_mask, other=pd.NaT)

    typed_amount, _valid_amount = coerce_decimal_series(payments["amount"])

    out = pd.DataFrame(
        {
            "payment_key": payments["payment_id"].astype(str),
            "order_key": payments["order_id"].apply(_optional_str),
            "payment_date": payment_dates,
            "payment_method": payments["payment_method"].astype(str),
            "payment_status": payments["payment_status"].astype(str),
            "payment_amount": typed_amount,
        }
    )

    return out.sort_values("payment_key").reset_index(drop=True)

