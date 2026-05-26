"""Build dim_customer from staged raw customers.

Pipeline:
1. resolve_pk_duplicates on customer_id (C006 loser dropped -> 19 rows)
2. mark_soft_duplicates on (first_name, last_name, phone) for
   duplicate_resolution_flag (C019 flagged True)
3. standardize country/state; normalize email; parse signup_date

Output sorted by customer_key. Matches test_transformation expectations:
19 rows; C019 duplicate_resolution_flag=True; C001 flag=False.
"""

from __future__ import annotations

import pandas as pd

from src.preprocessing.deduplication import (
    mark_soft_duplicates,
    resolve_pk_duplicates,
)
from src.preprocessing.email_normalizer import normalize_email
from src.preprocessing.geography_standardizer import standardize_geo_columns
from src.preprocessing.timestamp_parser import parse_series


def build(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return a DataFrame ready for dim_customer insert."""
    customers = stg["customers"]

    winners, _losers = resolve_pk_duplicates(customers, ["customer_id"])
    winners = winners.reset_index(drop=True)

    flagged = mark_soft_duplicates(
        winners,
        ["first_name", "last_name", "phone"],
        flag_col="duplicate_resolution_flag",
    )

    geo = standardize_geo_columns(flagged, country_col="country", state_col="state")

    parsed_signup, valid_signup = parse_series(geo["signup_date"])
    signup_dates = parsed_signup.dt.date
    signup_dates = signup_dates.where(valid_signup, other=pd.NaT)

    out = pd.DataFrame(
        {
            "customer_key": geo["customer_id"].astype(str),
            "full_name": (
                geo["first_name"].astype(str).str.strip()
                + " "
                + geo["last_name"].astype(str).str.strip()
            ),
            "email": geo["email"].apply(normalize_email),
            "phone": geo["phone"],
            "standard_country": geo["country"],
            "standard_state": geo["state"],
            "signup_date": signup_dates,
            "loyalty_tier": geo["loyalty_tier"],
            "duplicate_resolution_flag": geo["duplicate_resolution_flag"].astype(bool),
        }
    )

    return out.sort_values("customer_key").reset_index(drop=True)