"""Deterministic duplicate detection for raw entities.

This dataset has three distinct duplicate patterns that the
validation layer needs to surface and the transformation layer
needs to resolve:

1. Exact-row duplicates -- e.g. orders.csv emits O1018 twice as
   byte-identical rows. drop_exact_duplicates collapses these
   silently (no business decision needed).

2. Primary-key collisions -- e.g. customers.csv has TWO rows with
   customer_id=C006 that disagree on email, phone, and country
   string. resolve_pk_duplicates picks ONE row per id using a
   fixed tie-breaker (lowest source row index wins; the later
   row becomes a DQ005 exception).

3. Cross-id soft duplicates -- C001 and C019 are different
   customer_ids but the same human (same first/last name + phone).
   mark_soft_duplicates adds a `duplicate_resolution_flag` column
   = True for the second+ row that shares the dup-key tuple with
   an earlier row. The first occurrence is canonical.

Determinism: every tie-breaker uses a totally-ordered key (source
row index). Re-running the pipeline always picks the same survivor,
so curated tables are byte-stable across runs.

This module is pure-function. It does NOT write to DQ tables; the
validation layer calls these helpers and then emits exception rows.
"""

from __future__ import annotations

import pandas as pd


def drop_exact_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split df into (kept, dropped) by byte-identical duplicate rows.

    Duplicates are determined across ALL columns; the first occurrence
    wins. Used for orders.csv O1018, which is emitted twice with no
    differences between the rows.
    """
    mask_dup = df.duplicated(keep="first")
    kept = df[~mask_dup].copy()
    dropped = df[mask_dup].copy()
    return kept, dropped


def resolve_pk_duplicates(
    df: pd.DataFrame,
    key_cols: list[str] | tuple[str, ...],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pick exactly one row per primary-key tuple.

    Returns (winners, losers). The tie-breaker is fixed: the row with
    the lowest source index value wins. We sort by index first so that
    duplicated(keep='first') means 'earliest source position' rather
    than 'earliest in current order' -- this stays deterministic even
    if upstream code has filtered/joined rows. Losers feed DQ005.
    """
    keys = list(key_cols)
    df_sorted = df.sort_index()
    mask_dup = df_sorted.duplicated(subset=keys, keep="first")
    winners = df_sorted[~mask_dup].copy()
    losers = df_sorted[mask_dup].copy()
    return winners, losers


def mark_soft_duplicates(
    df: pd.DataFrame,
    dup_key_cols: list[str] | tuple[str, ...],
    flag_col: str = "duplicate_resolution_flag",
) -> pd.DataFrame:
    """Add a boolean flag column for cross-id soft duplicates.

    A row is flagged True if it shares the ``dup_key_cols`` tuple
    with an earlier row (lower source index) AND every dup-key value
    on that row is non-null. Missing-key rows never identify a
    duplicate (a missing value cannot prove identity).

    Requires a unique-label index; raises ValueError otherwise so
    callers reset_index() upstream if they have joined/filtered.
    """
    if not df.index.is_unique:
        raise ValueError(
            "mark_soft_duplicates requires a unique-label index; "
            "call .reset_index(drop=True) first"
        )
    keys = list(dup_key_cols)
    out = df.copy()
    df_sorted = out.sort_index()
    key_complete = df_sorted[keys].notna().all(axis=1)
    dup = df_sorted.duplicated(subset=keys, keep="first") & key_complete
    out[flag_col] = dup.reindex(out.index).fillna(False).astype(bool)
    return out