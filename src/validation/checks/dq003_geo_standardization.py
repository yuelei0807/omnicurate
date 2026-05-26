"""DQ003: country and state must be standardized.

Logic: apply standardize_country / standardize_state to every customer
row; a row violates when raw value (after whitespace strip) differs
from the canonical form.

A single customer may have both country AND state issues. We emit ONE
row per affected customer with both fragments combined in the
description, so the steward sees the full fix list per customer rather
than two separate work items.

Missing country or state is NOT a DQ003 violation -- the rule is about
standardization, not presence. Whitespace-only differences ('USA ' vs
'USA') are also ignored; that's canonicalization, not a quality issue.

This dataset triggers DQ003 six times: C002 (US + Illinois), C003
(United States), C006 winner row (US + New York), C008 (Texas), C011
(United States), C015 (Florida). The C006 PK loser row (USA, NY) is
already canonical and does not appear in DQ003 -- it appears only in
DQ001.
"""

from __future__ import annotations

import pandas as pd

from src.preprocessing.geography_standardizer import (
    standardize_country,
    standardize_state,
)
from src.validation._helpers import empty_exceptions, make_exception_rows


def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Emit one exception per customer whose country or state needed standardization."""
    customers = stg["customers"]

    std_country = customers["country"].apply(standardize_country)
    std_state = customers["state"].apply(standardize_state)

    # Whitespace-trimmed comparison: 'USA ' vs 'USA' is not a violation.
    raw_country_str = customers["country"].fillna("").astype(str).str.strip()
    raw_state_str = customers["state"].fillna("").astype(str).str.strip()
    std_country_str = std_country.fillna("").astype(str)
    std_state_str = std_state.fillna("").astype(str)

    # notna() guard: missing values do not violate this rule.
    country_violation = customers["country"].notna() & (raw_country_str != std_country_str)
    state_violation = customers["state"].notna() & (raw_state_str != std_state_str)

    any_violation = country_violation | state_violation
    if not any_violation.any():
        return empty_exceptions()

    record_keys: list[str] = []
    details: list[str] = []
    for i, row in customers[any_violation].iterrows():
        parts: list[str] = []
        if country_violation.loc[i]:
            parts.append(
                f"country '{row['country']}' standardized to '{std_country.loc[i]}'"
            )
        if state_violation.loc[i]:
            parts.append(
                f"state '{row['state']}' standardized to '{std_state.loc[i]}'"
            )
        record_keys.append(str(row["customer_id"]))
        details.append("; ".join(parts) + ".")

    return make_exception_rows(
        "DQ003",
        record_keys=record_keys,
        issue_template="customer_id={record_key}: {detail}",
        fields={"detail": details},
    )