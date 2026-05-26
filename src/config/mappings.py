"""Static lookup tables for country / state standardization (DQ003).

Pure-data module: only constants, no functions, no imports of third-party
libraries. All dictionary keys are lowercased; callers must lowercase
their input before lookup (this keeps standardization logic in one place,
in src/preprocessing/geography_standardizer.py).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Country canonicalization. Maps every observed (and a few common) variants
# to the canonical "USA". Keys are lowercased.
# ---------------------------------------------------------------------------

COUNTRY_MAP: dict[str, str] = {
    "usa": "USA",
    "us": "USA",
    "u.s.": "USA",
    "u.s.a.": "USA",
    "united states": "USA",
    "united states of america": "USA",
}

# ---------------------------------------------------------------------------
# Full state name -> 2-letter USPS code. Keys are lowercase.
# All 50 states + DC are listed even though the current dataset only uses
# 7 of them. Including the full set is cheap and prevents future whack-a-mole.
# ---------------------------------------------------------------------------

STATE_NAME_TO_CODE: dict[str, str] = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "district of columbia": "DC",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}

# ---------------------------------------------------------------------------
# Valid 2-letter USPS codes (50 states + DC). Built from STATE_NAME_TO_CODE
# so the two constants can never drift apart. frozenset prevents accidental
# mutation at runtime.
# ---------------------------------------------------------------------------

VALID_STATE_CODES: frozenset[str] = frozenset(STATE_NAME_TO_CODE.values())