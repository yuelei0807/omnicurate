"""DQ001: customer_id must be unique after duplicate resolution.

Logic: run primary-key dedup on raw customers (lowest source index
wins, per deduplication.resolve_pk_duplicates). Each losing row
becomes one exception. The winner is the canonical dim_customer
record for that customer_id.

This dataset triggers DQ001 once: customer_id=C006 appears at source
rows 7 and 20 with different email/phone/country values. The first
occurrence wins (mason.davis@example.com); the second is dropped and
becomes an exception (mason.d@example.com).

NOT in scope here: cross-id soft duplicates (e.g. C019 vs C001 -- same
human, different customer_id). Those are resolved later via
dim_customer.duplicate_resolution_flag, which the transformation
layer sets using deduplication.mark_soft_duplicates. The take-home
spec explicitly lists that flag as a dim_customer column, so it is
intentionally NOT raised as a DQ001 exception.
"""

from __future__ import annotations

import pandas as pd

from src.preprocessing.deduplication import resolve_pk_duplicates
from src.validation._helpers import empty_exceptions, make_exception_rows


def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Emit one exception row per duplicate customer_id occurrence.

    Args:
        stg: Mapping of staged raw DataFrames; uses stg["customers"].

    Returns:
        DataFrame in dq_exception_report shape. Zero rows when every
        customer_id is unique.
    """
    customers = stg["customers"]
    _winners, losers = resolve_pk_duplicates(customers, ["customer_id"])
    if losers.empty:
        return empty_exceptions()

    # Use the loser's email as a discriminator so the report explains
    # *which* row was dropped, not just the duplicated id. Missing
    # emails render as '<missing>' so the description is still readable.
    loser_emails = losers["email"].fillna("<missing>").astype(str)

    return make_exception_rows(
        "DQ001",
        record_keys=losers["customer_id"].tolist(),
        issue_template=(
            "Duplicate customer_id={record_key}; this row (email={email}) "
            "was dropped in favour of the canonical first occurrence."
        ),
        fields={"email": loser_emails.tolist()},
    )