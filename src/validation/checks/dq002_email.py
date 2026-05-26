"""DQ002: email should be present and syntactically valid when available.

Two sub-violations, both Medium severity but with different fixes:

* Missing: normalize_email returns None (raw value was None / pd.NA /
  NaN / empty / pure whitespace). Fix: backfill from source system.
* Invalid syntax: email is present but email_validator rejects it.
  Fix: correct the typo or escalate to data steward.

Both share rule_id DQ002 but emit different issue_description text so
the report makes the corrective action obvious without forcing the
reader to inspect the raw row.

This dataset triggers DQ002 exactly once: C004 has an empty email cell.
All other 19 customers (including the PK loser C006 and the soft-dup
C019) have syntactically valid emails.

The check operates on raw stg["customers"] without pre-deduplicating;
keeping every check independent of every other simplifies the runner
and surfaces email problems even on rows that will be dropped later.
"""

from __future__ import annotations

import pandas as pd

from src.preprocessing.email_normalizer import is_valid_email, normalize_email

from src.validation._helpers import (
    concat_exceptions,
    empty_exceptions,
    make_exception_rows,
)


def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Emit one exception row per missing or syntactically invalid email.

    Args:
        stg: Mapping of staged raw DataFrames; uses stg["customers"].

    Returns:
        DataFrame in dq_exception_report shape. Missing-email rows are
        emitted before invalid-syntax rows so the report groups by
        root cause. Zero rows when every email is present and valid.
    """
    customers = stg["customers"]

    normalized = customers["email"].apply(normalize_email)
    valid = customers["email"].apply(is_valid_email)

    missing_mask = normalized.isna()
    invalid_syntax_mask = (~missing_mask) & (~valid.astype(bool))

    if not (missing_mask | invalid_syntax_mask).any():
        return empty_exceptions()

    missing_rows = customers[missing_mask]
    invalid_rows = customers[invalid_syntax_mask]

    missing_exceptions = make_exception_rows(
        "DQ002",
        record_keys=missing_rows["customer_id"].tolist(),
        issue_template="customer_id={record_key}: email is missing.",
    )

    invalid_exceptions = make_exception_rows(
        "DQ002",
        record_keys=invalid_rows["customer_id"].tolist(),
        issue_template=(
            "customer_id={record_key}: email '{raw}' failed syntactic validation."
        ),
        fields={"raw": invalid_rows["email"].astype(str).tolist()},
    )

    return concat_exceptions(missing_exceptions, invalid_exceptions)