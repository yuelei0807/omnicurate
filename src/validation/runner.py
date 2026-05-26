"""DQ runner: discover and apply all checks.

This module auto-discovers DQ checks in src.validation.checks and
combines their outputs into one canonically-shaped DataFrame matching
dq_exception_report.

Sorting: severity (High > Medium > Low), then rule_id, then record_key.
"""

from __future__ import annotations

import importlib
import pkgutil

import pandas as pd

from src.validation._helpers import EXCEPTION_COLUMNS, concat_exceptions, empty_exceptions


_SEVERITY_ORDER: dict[str, int] = {"High": 0, "Medium": 1, "Low": 2}


def _discover_check_modules() -> list[str]:
    """Return fully-qualified module names under src.validation.checks.*."""
    import src.validation.checks as checks_pkg  # local import for pkg path

    names: list[str] = []
    for m in pkgutil.iter_modules(checks_pkg.__path__):
        if m.ispkg:
            continue
        if m.name.startswith("_"):
            continue
        names.append(f"{checks_pkg.__name__}.{m.name}")
    return sorted(names)


def apply_all(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Run every discovered DQ check and return combined exceptions DataFrame."""
    modules = _discover_check_modules()
    if not modules:
        return empty_exceptions()

    per_rule: list[pd.DataFrame] = []
    for mod_name in modules:
        mod = importlib.import_module(mod_name)
        if not hasattr(mod, "check"):
            raise AttributeError(f"{mod_name} is missing required function check(stg)")
        df = mod.check(stg)  # type: ignore[attr-defined]
        # Hard guard: every check must return canonical columns in order
        if list(df.columns) != list(EXCEPTION_COLUMNS):
            raise ValueError(
                f"{mod_name}.check returned wrong columns.\n"
                f"got: {list(df.columns)}\n"
                f"expected: {list(EXCEPTION_COLUMNS)}"
            )
        per_rule.append(df)

    combined = concat_exceptions(*per_rule)

    if len(combined) == 0:
        return combined

    # Print per-rule counts (debug-friendly)
    counts = combined["rule_id"].value_counts().sort_index()
    for rid, n in counts.items():
        print(f"{rid}: {n}")

    # Sort by severity then rule_id then record_key
    sev_rank = combined["severity"].map(lambda s: _SEVERITY_ORDER.get(str(s), 99))
    combined = combined.assign(_sev_rank=sev_rank)
    combined = combined.sort_values(
        by=["_sev_rank", "rule_id", "dataset", "record_key"],
        kind="mergesort",  # stable
    ).drop(columns=["_sev_rank"])

    combined = combined.reset_index(drop=True)
    return combined