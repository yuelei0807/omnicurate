-- Equivalent SQL for documentation; runtime uses Python in src/transformation/*
-- View name: v_dim_product
--
-- Mirrors src/transformation/dim_product.py:
-- product_id -> product_key
-- unit_price cast to DECIMAL(12,2)
-- active_flag Y/N -> boolean

CREATE OR REPLACE VIEW v_dim_product AS
SELECT
    product_id   AS product_key,
    product_name,
    category,
    CAST(unit_price AS DECIMAL(12,2)) AS unit_price,
    CASE
        WHEN active_flag IS NULL THEN FALSE
        WHEN upper(trim(active_flag)) IN ('Y','YES','TRUE','1') THEN TRUE
        ELSE FALSE
    END AS active_flag
FROM raw_products
ORDER BY product_key;