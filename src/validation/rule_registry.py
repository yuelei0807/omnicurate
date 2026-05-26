"""Authoritative DQ rule registry, sourced from input_data/data_quality_rules.csv.

Every DQ check reads its identity (rule_id, dataset, severity, description,
suggested_action) from REGISTRY rather than hard-coding strings. This
guarantees every exception row has consistent shape and that any rule
edits in the source CSV propagate without touching check code.

`suggested_action` is NOT in the source CSV (the spec only adds it to the
exception report). It is hard-coded here, one short business-actionable
sentence per rule. Keys must align 1:1 with rule_ids in the source CSV;
a missing mapping raises at import time so drift is caught immediately.

This module is intentionally pandas-free so importing the registry from
every check is cheap and the dict itself is trivially unit-testable.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass

from src.config import settings


@dataclass(frozen=True)
class DQRule:
    """Immutable identity for a single data-quality rule."""

    rule_id: str
    dataset: str
    description: str
    severity: str  # 'High' | 'Medium' | 'Low'
    suggested_action: str


# Business-actionable directive per rule. Keys MUST match rule_ids in
# data_quality_rules.csv; import-time validation guards against drift.
_SUGGESTED_ACTIONS: dict[str, str] = {
    "DQ001": "Merge or quarantine duplicate customer profiles before downstream join.",
    "DQ002": "Backfill missing email or flag the customer for outbound contact.",
    "DQ003": "Standardize country to USA and state to USPS code; review with the data steward.",
    "DQ004": "Drop the byte-identical duplicate order row; keep the first occurrence.",
    "DQ005": "Quarantine the order until the customer master is updated with the missing id.",
    "DQ006": "Quarantine the order until the product master is updated with the missing id.",
    "DQ007": "Investigate the source system; correct quantity sign or reverse the order.",
    "DQ008": "Reconcile order_total vs quantity * unit_price with the merchandising team.",
    "DQ009": "Hold the payment for AR review; do not post to GL until the order id is resolved.",
    "DQ010": "Reconcile payment shortfall/overage with the billing team before settlement close.",
    "DQ011": "Backfill created_ts from the source system audit log; flag for ingestion review.",
    "DQ012": "Flag the ticket for CRM review; create a stub customer record if confirmed.",
}


def _load_registry() -> dict[str, DQRule]:
    """Read the source CSV and build REGISTRY. Called once at import time."""
    path = settings.INPUT_DIR / "data_quality_rules.csv"
    registry: dict[str, DQRule] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = row["rule_id"].strip()
            action = _SUGGESTED_ACTIONS.get(rid)
            if action is None:
                raise KeyError(
                    f"rule_registry: no suggested_action defined for {rid!r}. "
                    f"Add an entry to _SUGGESTED_ACTIONS."
                )
            registry[rid] = DQRule(
                rule_id=rid,
                dataset=row["dataset"].strip(),
                description=row["rule_description"].strip(),
                severity=row["severity"].strip(),
                suggested_action=action,
            )
    # Symmetric check: every hard-coded action key must exist in the CSV.
    extras = set(_SUGGESTED_ACTIONS) - set(registry)
    if extras:
        raise KeyError(
            f"rule_registry: _SUGGESTED_ACTIONS has unknown rule_ids {sorted(extras)} "
            f"not present in data_quality_rules.csv."
        )
    return registry


REGISTRY: dict[str, DQRule] = _load_registry()


def get(rule_id: str) -> DQRule:
    """Return the DQRule for rule_id; raise KeyError with a helpful message."""
    try:
        return REGISTRY[rule_id]
    except KeyError as e:
        raise KeyError(
            f"Unknown DQ rule_id: {rule_id!r}. "
            f"Known rule_ids: {sorted(REGISTRY)}"
        ) from e


def all_rules() -> list[DQRule]:
    """Return all rules in source-file order. Stable across runs."""
    return list(REGISTRY.values())