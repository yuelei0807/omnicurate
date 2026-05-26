"""Build fact_order from staged raw orders.

1. drop_exact_duplicates (O1018 byte-id dup -> 30 rows)
2. Parse order_ts -> order_date; coerce quantity and order_total
3. Standardize shipping_state to USPS code
4. Left-join products for unit_price; calculated = qty * price when both exist
5. variance = gross - calculated when both are finite Decimals (NULL if not computable)

Invalid customer_id / product_id rows are kept (O1019, O1020) per spec.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.preprocessing.deduplication import drop_exact_duplicates
from src.preprocessing.geography_standardizer import standardize_state
from src.preprocessing.timestamp_parser import parse_series
from src.preprocessing.type_coercion import coerce_decimal_series, coerce_int_series, to_decimal


def build(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return a DataFrame ready for fact_order insert."""
    orders = stg["orders"]
    products = stg["products"]

    kept, _dropped = drop_exact_duplicates(orders)
    df = kept.reset_index(drop=True)

    parsed_ts, valid_ts = parse_series(df["order_ts"])
    order_dates = parsed_ts.dt.date
    order_dates = order_dates.where(valid_ts, other=pd.NaT)

    qty_typed, qty_valid = coerce_int_series(df["quantity"])
    gross_typed, gross_valid = coerce_decimal_series(df["order_total"])

    price_lookup = products.set_index("product_id")["unit_price"]
    raw_price = df["product_id"].map(price_lookup)

    price_typed, price_valid = coerce_decimal_series(raw_price)

    calc_list: list[Decimal | None] = []
    var_list: list[Decimal | None] = []

    for i in df.index:
        q_ok = bool(qty_valid.iloc[i])
        p_ok = bool(price_valid.iloc[i])
        g_ok = bool(gross_valid.iloc[i])
        qv = qty_typed.iloc[i]
        pv = price_typed.iloc[i]
        gv = gross_typed.iloc[i]

        if q_ok and p_ok and qv is not None and pv is not None:
            calculated = Decimal(int(qv)) * pv
        else:
            calculated = None

        if calculated is not None and g_ok and gv is not None:
            variance = gv - calculated
        else:
            variance = None

        calc_list.append(calculated)
        var_list.append(variance)

    out = pd.DataFrame(
        {
            "order_key": df["order_id"].astype(str),
            "customer_key": df["customer_id"].astype(str),
            "product_key": df["product_id"].astype(str),
            "order_date": order_dates,
            "quantity": qty_typed.astype("Int64"),
            "order_status": df["order_status"],
            "shipping_state": df["shipping_state"].apply(standardize_state),
            "gross_order_amount": gross_typed,
            "calculated_order_amount": calc_list,
            "order_amount_variance": var_list,
        }
    )

    return out.sort_values("order_key").reset_index(drop=True)