"""DQ008: order_total should equal quantity * product unit_price.

Cross-table arithmetic check. Joins orders to products on product_id,
coerces quantity (int) and money columns (Decimal), then flags rows
where abs(order_total - calculated) > 0.01.

Rows are skipped (no exception) when:
* product_id is unknown (no unit_price after left join) -- DQ006 covers that
* quantity, order_total, or unit_price is missing or unparseable

Uses Decimal throughout so cent-level reconciliation matches Q5 and
fact_order.order_amount_variance (0.1 + 0.2 float drift is unacceptable).

This dataset triggers DQ008 exactly once: O1021 has quantity=4,
P008 unit_price=11.00 -> calculated=44.00, order_total=50.00,
diff=6.00.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.preprocessing.type_coercion import (
    coerce_decimal_series,
    coerce_int_series,
)
from src.validation._helpers import empty_exceptions, make_exception_rows

_TOLERANCE = Decimal("0.01")


def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Emit one exception per order whose total does not match qty * unit_price.

    Args:
        stg: Mapping of staged raw DataFrames; uses stg["orders"]
            AND stg["products"].

    Returns:
        DataFrame in dq_exception_report shape. Zero rows when every
        computable order total matches within tolerance.
    """
    orders = stg["orders"]
    products = stg["products"]

    merged = orders.merge(
        products[["product_id", "unit_price"]],
        on="product_id",
        how="left",
    )

    quantity: pd.Series = merged["quantity"]
    order_total: pd.Series = merged["order_total"]
    unit_price: pd.Series = merged["unit_price"]

    typed_qty, valid_qty = coerce_int_series(quantity)
    typed_total, valid_total = coerce_decimal_series(order_total)
    typed_price, valid_price = coerce_decimal_series(unit_price)

    valid_qty_b = valid_qty.astype(bool)
    valid_total_b = valid_total.astype(bool)
    valid_price_b = valid_price.astype(bool)
    computable = valid_qty_b & valid_total_b & valid_price_b

    if not computable.any():
        return empty_exceptions()

    violations: list[str] = []
    order_totals: list[str] = []
    calculateds: list[str] = []
    diffs: list[str] = []

    for idx in merged.index[computable]:
        qty_val = typed_qty.loc[idx]
        total_val = typed_total.loc[idx]
        price_val = typed_price.loc[idx]
        if qty_val is None or total_val is None or price_val is None:
            continue
        calculated = Decimal(int(qty_val)) * price_val
        diff = total_val - calculated
        if abs(diff) > _TOLERANCE:
            violations.append(str(merged.loc[idx, "order_id"]))
            order_totals.append(str(total_val))
            calculateds.append(str(calculated))
            diffs.append(str(diff))

    if not violations:
        return empty_exceptions()

    return make_exception_rows(
        "DQ008",
        record_keys=violations,
        issue_template=(
            "order_id={record_key}: order_total={order_total} vs "
            "quantity*unit_price={calculated} (diff={diff})."
        ),
        fields={
            "order_total": order_totals,
            "calculated": calculateds,
            "diff": diffs,
        },
    )