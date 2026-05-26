"""Email normalization and syntactic validation (drives DQ002).

Two scalar functions, both safe to apply via Series.apply:

* normalize_email -- lowercase + strip; returns None for missing/empty.
                     This is what dim_customer.email stores.
* is_valid_email  -- RFC-compliant syntactic check via email_validator
                     (no DNS lookup, so offline + deterministic).
                     Returns False for missing/empty/exception.

Why email_validator instead of a regex? A correct email regex is
famously hard (~6000 chars and still wrong on edge cases). The
email_validator package is the reference implementation; using it
pins DQ002's contract to a real standard rather than a fragile
pattern we maintain ourselves.

Both functions use the same scalar missing-value pattern as the
other preprocessing modules (avoid pd.isna to keep pyright clean).
"""

from __future__ import annotations

import pandas as pd
from email_validator import EmailNotValidError, validate_email


def _is_missing(value: object) -> bool:
    """Scalar missing-value check; same pattern as other preprocessing modules."""
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, float) and value != value:  # NaN
        return True
    return False


def normalize_email(value: object) -> str | None:
    """Lowercase + strip; return None for missing/empty input."""
    if _is_missing(value):
        return None
    s = str(value).strip().lower()
    return s if s else None


def is_valid_email(value: object) -> bool:
    """Return True iff value is a syntactically valid email address.

    ``check_deliverability=False`` skips DNS resolution so the
    validator is offline and deterministic. Missing, empty, or
    unparseable input all return False.
    """
    if _is_missing(value):
        return False
    s = str(value).strip()
    if not s:
        return False
    try:
        validate_email(s, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False