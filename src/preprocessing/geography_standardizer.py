"""Country/state standardization for DQ003 + dim_customer + fact_order.

Pure-function module. Lookup data comes from src.config.mappings
(COUNTRY_MAP, STATE_NAME_TO_CODE, VALID_STATE_CODES). Behaviour:

* standardize_country  -- case-insensitive map; unknown values pass
                          through unchanged so DQ003 can flag them.
* standardize_state    -- already-valid 2-letter codes (any case) are
                          uppercased; full names map to codes; unknown
                          values pass through.
* standardize_geo_columns -- DataFrame helper that applies both scalar
                             functions and preserves the original raw
                             values as ``<col>_raw`` for DQ exception
                             messages.

All three treat None / pd.NA / pd.NaT / NaN / "" as missing and return
None. We avoid pd.isna() because its return type is bool | NDArray |
NDFrame, which pyright cannot use in an ``if`` clause without false
alarms (Series.__bool__ raises). Explicit scalar sentinels are both
safer and clearer.
"""

from __future__ import annotations

import pandas as pd

from src.config.mappings import (
    COUNTRY_MAP,
    STATE_NAME_TO_CODE,
    VALID_STATE_CODES,
)


def _is_missing(value: object) -> bool:
    """Scalar missing-value check that never touches Series machinery."""
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, float) and value != value:  # NaN
        return True
    return False


def standardize_country(value: object) -> str | None:
    """Map a country variant to its canonical form (typically 'USA').

    Returns None for missing/empty. Unknown values are returned
    unchanged so DQ003 can flag them.
    """
    if _is_missing(value):
        return None
    s = str(value).strip()
    if not s:
        return None
    return COUNTRY_MAP.get(s.lower(), s)


def standardize_state(value: object) -> str | None:
    """Normalise a US state value to its 2-letter USPS code.

    Returns None for missing/empty. Unknown values are returned
    unchanged so DQ003 can flag them.
    """
    if _is_missing(value):
        return None
    s = str(value).strip()
    if not s:
        return None
    upper = s.upper()
    if upper in VALID_STATE_CODES:
        return upper
    code = STATE_NAME_TO_CODE.get(s.lower())
    if code is not None:
        return code
    return s


def standardize_geo_columns(
    df: pd.DataFrame,
    country_col: str | None = None,
    state_col: str | None = None,
) -> pd.DataFrame:
    """Return a copy of ``df`` with country/state columns standardized.

    Original raw values are preserved as ``<col>_raw`` so DQ003 can
    show the before/after pair in its exception messages. Pass
    ``None`` for either column to skip standardizing that side.
    """
    out = df.copy()
    if country_col is not None:
        out[f"{country_col}_raw"] = out[country_col]
        out[country_col] = out[country_col].apply(standardize_country)
    if state_col is not None:
        out[f"{state_col}_raw"] = out[state_col]
        out[state_col] = out[state_col].apply(standardize_state)
    return out