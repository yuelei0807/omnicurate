"""DQ004: order_id must be unique.

Two flavours of violation, both emitted under rule_id DQ004 but with
different descriptions so the steward can tell at a glance whether
the dropped row was redundant or a conflicting variant:

* Byte-identical duplicate -- drop_exact_duplicates catches these.
  The dropped row carries no new information; the surviving row is
  byte-for-byte the same.
* PK collision with different attributes -- resolve_pk_duplicates on
  the post-byte-id-dedup remainder catches these. Here the data
  actually differs across rows; we keep the lowest-index row by the
  deterministic tie-breaker.

Processing order matters: we drop byte-id duplicates FIRST so they
don't get conflated with PK collisions in the second step. Both
categories emit cleanly separable exception rows.

This dataset triggers DQ004 once: order_id=O1018 appears at source
rows 19 and 20 as identical rows; the line-20 occurrence is dropped.
"""

from __future__ import annotations

import pandas as pd

from src.preprocessing.deduplication import (
    drop_exact_duplicates,
    resolve_pk_duplicates,
)
from src.validation._helpers import (
    concat_exceptions,
    empty_exceptions,
    make_exception_rows,
)


def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Emit one exception row per duplicate order_id occurrence.

    Args:
        stg: Mapping of staged raw DataFrames; uses stg["orders"].

    Returns:
        DataFrame in dq_exception_report shape. Byte-id rows are
        listed before PK-collision rows so the report groups by
        root cause. Zero rows when every order_id is unique.
    """
    orders = stg["orders"]

    kept, byte_id_dropped = drop_exact_duplicates(orders)
    _winners, pk_losers = resolve_pk_duplicates(kept, ["order_id"])

    if byte_id_dropped.empty and pk_losers.empty:
        return empty_exceptions()

    byte_id_exc = make_exception_rows(
        "DQ004",
        record_keys=byte_id_dropped["order_id"].tolist(),
        issue_template=(
            "Duplicate order_id={record_key}; identical row was dropped "
            "(no information lost)."
        ),
    )

    pk_collision_exc = make_exception_rows(
        "DQ004",
        record_keys=pk_losers["order_id"].tolist(),
        issue_template=(
            "Duplicate order_id={record_key}; later occurrence with different "
            "attributes was dropped in favour of the canonical first row."
        ),
    )

    return concat_exceptions(byte_id_exc, pk_collision_exc)