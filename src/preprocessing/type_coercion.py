"""Type coercion utilities for raw VARCHAR inputs.

Two scalar functions plus thin Series-level helpers. Used by the
transformation layer to turn raw CSV strings into the typed values
that DQ checks (DQ007 negative amounts, DQ010 quantity sign, etc.)
and Q1-Q5 analytics reason about.

Semantics follow the same (typed_value, valid) pattern used by
timestamp_parser:

* Missing input (None / pd.NA / NaN / empty string / pure-whitespace
  string) returns (None, False).
* Unparseable input ('abc', '1.2.3', 'nan', 'inf', '$36') returns
  (None, False).
* Valid input returns (Decimal(...), True) or (int(...), True).

This deliberately conflates 'missing' and 'unparseable' at the
type-coercion layer; the validation layer distinguishes them by
inspecting the original raw value alongside the valid flag (same
contract as timestamp_parser.parse_series).

Negative numbers pass through cleanly. The decision to reject
negatives (DQ010 quantity, DQ007 payment amount) lives in the
validation layer, NOT here -- the type-coercion layer's job is
purely 'can this string become a number?'.

Decimal (not float) is used for money so cent-exact arithmetic is
preserved for Q5 reconciliation (0.1 + 0.2 != 0.3 in float).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import pandas as pd


def _is_missing(value: object) -> bool:
    """Scalar missing-value check used by every preprocessing module."""
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, float) and value != value:  # NaN
        return True
    return False


def to_decimal(value: object) -> tuple[Decimal | None, bool]:
    """Parse value into a Decimal.

    Returns (Decimal, True) on success, (None, False) for missing or
    unparseable input. Whitespace is stripped. Non-finite Decimals
    ('nan', 'inf') are rejected since they have no business meaning
    in money fields.
    """
    if _is_missing(value):
        return None, False
    s = str(value).strip()
    if not s:
        return None, False
    try:
        d = Decimal(s)
    except (InvalidOperation, ValueError):
        return None, False
    if not d.is_finite():
        return None, False
    return d, True


def to_int(value: object) -> tuple[int | None, bool]:
    """Parse value into an int.

    Accepts integer strings ('2', '-1') and integral-valued decimals
    ('2.0', '-3.0'), rejects non-integral ('2.5'). Returns
    (None, False) for missing or unparseable. Negatives pass through;
    DQ010 owns sign enforcement.
    """
    if _is_missing(value):
        return None, False
    s = str(value).strip()
    if not s:
        return None, False
    try:
        d = Decimal(s)
    except (InvalidOperation, ValueError):
        return None, False
    if not d.is_finite():
        return None, False
    if d != d.to_integral_value():
        return None, False
    return int(d), True


def coerce_decimal_series(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Apply to_decimal across a Series.

    Returns (typed_series, valid_series) sharing series.index.
    typed_series has dtype 'object' so it can hold Decimal | None
    without lossy float conversion.
    """
    pairs = series.apply(to_decimal)
    typed = pairs.apply(lambda t: t[0])
    valid = pairs.apply(lambda t: t[1]).astype(bool)
    return typed, valid


def coerce_int_series(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Apply to_int across a Series.

    Returns (typed_series, valid_series). typed_series uses pandas'
    nullable 'Int64' dtype so unparseable rows remain <NA> instead
    of being silently promoted to float NaN.
    """
    pairs = series.apply(to_int)
    typed = pairs.apply(lambda t: t[0])
    valid = pairs.apply(lambda t: t[1]).astype(bool)
    return typed.astype("Int64"), valid