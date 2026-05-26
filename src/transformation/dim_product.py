"""Build dim_product from staged raw products.

Maps product_id -> product_key, coerces unit_price to Decimal,
and converts active_flag Y/N to boolean. No dedup needed (12 unique
products in source).
"""

from __future__ import annotations

import pandas as pd

from src.preprocessing.type_coercion import coerce_decimal_series


def _to_active_flag(value: object) -> bool:
    if value is None or (isinstance(value, float) and value != value):
        return False
    s = str(value).strip().upper()
    return s in ("Y", "YES", "TRUE", "1")


def build(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Return a DataFrame ready for dim_product insert."""
    products = stg["products"]

    typed_price, valid_price = coerce_decimal_series(products["unit_price"])
    # Source data has no bad unit_price values; keep Decimal objects.
    unit_price = typed_price

    out = pd.DataFrame(
        {
            "product_key": products["product_id"].astype(str),
            "product_name": products["product_name"],
            "category": products["category"],
            "unit_price": unit_price,
            "active_flag": products["active_flag"].map(_to_active_flag).astype(bool),
        }
    )

    return out.sort_values("product_key").reset_index(drop=True)