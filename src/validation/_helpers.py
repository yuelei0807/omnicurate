"""Exception-row factory used by every DQ check.

Every DQ check returns a DataFrame with the SAME seven-column shape so
the runner can concat them all without column re-alignment. This
helper encapsulates that contract in one place:

* pull rule metadata (dataset, severity, suggested_action) from REGISTRY
* stamp a single tz-naive UTC timestamp for the whole batch
* expand issue_description from a Python format-string template
* return a canonically-shaped DataFrame, even when zero violations

The 'one detected_at per call' design (rather than per-row) makes the
report easier to read: all violations from a single check share the
same timestamp, so you can group/sort by detected_at to see which
rules ran together.

Tz-naive UTC is used because DuckDB TIMESTAMP is tz-naive; passing a
tz-aware value would silently convert to local time on insert and
break cross-machine reproducibility.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone

import pandas as pd

from src.validation.rule_registry import get


# Single source of truth for the exception-report column order.
# Must match sql/ddl/002_curated_tables.sql dq_exception_report DDL.
EXCEPTION_COLUMNS: tuple[str, ...] = (
    "rule_id",
    "dataset",
    "record_key",
    "severity",
    "issue_description",
    "suggested_action",
    "detected_at",
)


def _utcnow_naive() -> pd.Timestamp:
    """Tz-naive UTC timestamp (DuckDB TIMESTAMP is tz-naive)."""
    return pd.Timestamp(datetime.now(timezone.utc).replace(tzinfo=None))


def empty_exceptions() -> pd.DataFrame:
    """Return a zero-row DataFrame with the canonical exception schema."""
    return pd.DataFrame({col: pd.Series(dtype="object") for col in EXCEPTION_COLUMNS})

def concat_exceptions(*dfs: pd.DataFrame) -> pd.DataFrame:
    """Safely concatenate exception DataFrames produced by multiple sub-checks.

    Filters out empty pieces before pd.concat so pandas does not raise the
    'empty or all-NA' FutureWarning. Returns empty_exceptions() if every
    piece is empty, so callers always receive a canonically-shaped result.

    Use this whenever a DQ check splits violations by sub-reason (e.g.
    DQ002 missing-vs-invalid email, DQ003 country-vs-state standardization).
    """
    non_empty = [df for df in dfs if len(df) > 0]
    if not non_empty:
        return empty_exceptions()
    return pd.concat(non_empty, ignore_index=True)

def make_exception_rows(
    rule_id: str,
    record_keys: Iterable[object],
    issue_template: str,
    *,
    fields: dict[str, Iterable[object]] | None = None,
    dataset_override: str | None = None,
    detected_at: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Build a DataFrame of exception rows for one rule.

    Args:
        rule_id: DQ rule identifier; must exist in REGISTRY.
        record_keys: Primary-key values (customer_id, order_id,
            payment_id, ticket_id). One row produced per key. Each key
            is stringified for storage in record_key VARCHAR.
        issue_template: Python format string. May reference {record_key}
            and any keys present in ``fields``. The same template is
            used for every row.
        fields: Optional per-row substitution values. Each iterable must
            be the same length as record_keys.
        dataset_override: Override the rule's registered dataset; use
            sparingly (DQ010 is the canonical case where a rule
            legitimately spans datasets).
        detected_at: Override the default tz-naive UTC timestamp
            (primarily for tests that need deterministic timestamps).

    Returns:
        DataFrame with EXCEPTION_COLUMNS in canonical order. Empty
        ``record_keys`` yields a zero-row, correctly-shaped DataFrame
        so callers can pd.concat without column re-alignment.

    Raises:
        KeyError: rule_id not in REGISTRY, or template references a
            field name not present in ``fields``.
        ValueError: a ``fields`` entry length does not match
            len(record_keys).
    """
    rule = get(rule_id)
    keys = [str(k) for k in record_keys]
    n = len(keys)

    if n == 0:
        return empty_exceptions()

    field_lists: dict[str, list[object]] = {}
    if fields:
        for name, values in fields.items():
            values_list = list(values)
            if len(values_list) != n:
                raise ValueError(
                    f"make_exception_rows: field {name!r} has "
                    f"{len(values_list)} values but record_keys has {n}"
                )
            field_lists[name] = values_list

    descriptions: list[str] = []
    for i in range(n):
        subs: dict[str, object] = {"record_key": keys[i]}
        for name, vals in field_lists.items():
            subs[name] = vals[i]
        try:
            descriptions.append(issue_template.format(**subs))
        except KeyError as e:
            raise KeyError(
                f"make_exception_rows: template {issue_template!r} references "
                f"missing field {e}; provided fields: {list(field_lists)}"
            ) from e

    ts = detected_at if detected_at is not None else _utcnow_naive()

    return pd.DataFrame(
        {
            "rule_id": [rule.rule_id] * n,
            "dataset": [dataset_override or rule.dataset] * n,
            "record_key": keys,
            "severity": [rule.severity] * n,
            "issue_description": descriptions,
            "suggested_action": [rule.suggested_action] * n,
            "detected_at": [ts] * n,
        }
    )[list(EXCEPTION_COLUMNS)]