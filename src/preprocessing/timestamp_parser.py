"""Mixed-format timestamp parser for the raw layer.

The raw data contains seven distinct timestamp formats across
orders.order_ts, payments.payment_ts, customers.signup_date, and
support_tickets.created_ts.

Strategy: try each known format in a deterministic order with
``datetime.strptime``; if none match, fall back to ``dateutil.parse``
(which handles unusual but valid representations and still raises
on garbage like "bad_timestamp"). On total failure we return
``(pd.NaT, False)`` so DQ011 can flag the row explicitly.

We deliberately avoid ``pd.to_datetime(..., infer_datetime_format=True)``
because it:
  1. Silently converts parse failures to NaT (we cannot distinguish
     "missing" from "unparseable"), and
  2. Can guess wrong on ambiguous dates like 03/04/2025 (is that
     March 4 or April 3?). Our explicit ordered list pins US
     month-first convention, matching the source data.

Two public functions:

* ``parse_timestamp(value)``  -> (Timestamp | NaT, valid: bool)
* ``parse_series(series)``    -> (parsed_series, valid_mask)
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from dateutil import parser as du_parser

# Order matters: most specific formats first so that a string with
# seconds doesn't accidentally match a less-specific format that
# would silently drop them.
_KNOWN_FORMATS: tuple[str, ...] = (
    "%Y-%m-%dT%H:%M:%SZ",   # 2025-03-05T16:45:00Z   (orders, ISO with Z)
    "%Y-%m-%dT%H:%M:%S",    # 2025-03-02T11:00:00    (tickets, ISO no Z)
    "%Y-%m-%d %H:%M:%S",    # 2025-03-01 10:15:00    (orders/payments)
    "%Y-%m-%d %H:%M",       # 2025-03-07 11:30       (orders/payments)
    "%Y/%m/%d %H:%M:%S",    # defensive variant
    "%Y/%m/%d %H:%M",       # 2025/03/03 09:00       (orders)
    "%m/%d/%Y %H:%M",       # 03/02/2025 14:20       (orders, US slash)
    "%m-%d-%Y %H:%M",       # 05-06-2025 16:30       (orders, US dash)
    "%Y-%m-%d",             # 2025-01-04             (customers ISO date)
    "%Y/%m/%d",             # 2025/01/14             (customers slash)
    "%m/%d/%Y",             # 01/12/2025             (customers US)
    "%m-%d-%Y",             # 03-06-2025             (customers US dash)
)


def parse_timestamp(value: object) -> tuple[pd.Timestamp, bool]:
    """Parse one value into a Timestamp.

    Returns (Timestamp, True) on success and (pd.NaT, False) on
    any failure including None, pd.NA, empty string, or unparseable
    garbage like "bad_timestamp".
    """
    # Scalar missing-value handling. We deliberately avoid pd.isna()
    # here because its return type is bool | NDArray | NDFrame, and a
    # pandas Series raises in a boolean context. parse_timestamp is
    # only ever called with scalars (directly or via Series.apply),
    # so checking each sentinel explicitly is both safer and clearer.
    if value is None or value is pd.NA or value is pd.NaT:
        return pd.NaT, False
    if isinstance(value, float) and value != value:  # NaN-check
        return pd.NaT, False

    s = str(value).strip()
    if not s:
        return pd.NaT, False

    for fmt in _KNOWN_FORMATS:
        try:
            return pd.Timestamp(datetime.strptime(s, fmt)), True
        except ValueError:
            continue

    # Last-resort fallback: dateutil handles unusual but valid forms
    # and still raises on garbage.
    try:
        return pd.Timestamp(du_parser.parse(s)), True
    except (ValueError, TypeError, OverflowError):
        return pd.NaT, False


def parse_series(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Apply ``parse_timestamp`` to every value in a Series.

    Returns ``(parsed_series, valid_mask)``. ``parsed_series`` is a
    proper ``datetime64[ns]`` Series with ``NaT`` where parsing
    failed; ``valid_mask`` is a boolean Series aligned to the input
    index, ``True`` where parsing succeeded.
    """
    pairs = series.apply(parse_timestamp)
    parsed = pairs.apply(lambda t: t[0])
    valid = pairs.apply(lambda t: t[1]).astype(bool)
    return pd.to_datetime(parsed), valid