"""DQ010: settled payment amount should equal completed order total.

Cross-table reconciliation. Joins settled payments to completed
orders (post byte-id dedup) on order_id, then flags rows where
abs(amount - order_total) > 0.01.

Out of scope (no DQ010 row):
* voided / refunded payments
* payments whose order_id has no matching completed order (DQ009)
* unparseable amount or order_total
* rows where amounts match even if other DQ rules fire (e.g. PMT030:
  settled -21.00 matches O1030 order_total -21.00)

Uses Decimal for cent-exact comparison (same tolerance as DQ008).

This dataset triggers DQ010 exactly once: PMT021 settled amount=44.00
vs O1021 order_total=50.00 (diff=6.00) -- the same $6 variance as
DQ008 on that order.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.preprocessing.deduplication import drop_exact_duplicates
from src.preprocessing.type_coercion import coerce_decimal_series
from src.validation._helpers import empty_exceptions, make_exception_rows

_TOLERANCE = Decimal("0.01")


def _is_settled(value: object) -> bool:
    if value is None or (isinstance(value, float) and value != value):
        return False
    return str(value).strip().lower() == "settled"


def _is_completed(value: object) -> bool:
    if value is None or (isinstance(value, float) and value != value):
        return False
    return str(value).strip().lower() == "completed"


def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Emit one exception per settled payment that mismatches its order total.

    Args:
        stg: Mapping of staged raw DataFrames; uses stg["payments"]
            AND stg["orders"].

    Returns:
        DataFrame in dq_exception_report shape. Zero rows when every
        in-scope payment matches its completed order total within
        tolerance.
    """
    payments = stg["payments"]
    orders = stg["orders"]

    settled = payments[payments["payment_status"].map(_is_settled)]
    kept_orders, _dropped = drop_exact_duplicates(orders)
    completed = kept_orders[kept_orders["order_status"].map(_is_completed)]

    if settled.empty or completed.empty:
        return empty_exceptions()

    merged = settled.merge(
        completed[["order_id", "order_total"]],
        on="order_id",
        how="inner",
    )

    amount: pd.Series = merged["amount"]
    order_total: pd.Series = merged["order_total"]

    typed_amount, valid_amount = coerce_decimal_series(amount)
    typed_total, valid_total = coerce_decimal_series(order_total)
    computable = valid_amount.astype(bool) & valid_total.astype(bool)

    if not computable.any():
        return empty_exceptions()

    violations: list[str] = []
    amounts: list[str] = []
    totals: list[str] = []
    diffs: list[str] = []

    for idx in merged.index[computable]:
        amt_val = typed_amount.loc[idx]
        total_val = typed_total.loc[idx]
        if amt_val is None or total_val is None:
            continue
        # order_total - amount: positive when order exceeds payment (same
        # sign convention as DQ008's order_total - calculated).
        diff = total_val - amt_val
        if abs(diff) > _TOLERANCE:
            violations.append(str(merged.loc[idx, "payment_id"]))
            amounts.append(str(amt_val))
            totals.append(str(total_val))
            diffs.append(str(diff))

    if not violations:
        return empty_exceptions()

    return make_exception_rows(
        "DQ010",
        record_keys=violations,
        issue_template=(
            "payment_id={record_key}: settled payment {amount} != "
            "completed order total {order_total} (diff={diff})."
        ),
        fields={
            "amount": amounts,
            "order_total": totals,
            "diff": diffs,
        },
    )