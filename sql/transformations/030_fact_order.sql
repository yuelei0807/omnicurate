-- Equivalent SQL for documentation; runtime uses Python in src/transformation/*
-- View name: v_fact_order
--
-- Mirrors src/transformation/fact_order.py:
-- 1) drop byte-identical duplicate order rows (O1018)
-- 2) parse order_ts -> order_date (DATE)
-- 3) standardize shipping_state to USPS code
-- 4) gross_order_amount from order_total
-- 5) calculated_order_amount = quantity * unit_price when product exists
-- 6) order_amount_variance = gross - calculated when computable
--
-- Invalid FK rows are kept (O1019 -> C999, O1020 -> P999). For invalid
-- product_id, calculated/variance become NULL.

CREATE OR REPLACE VIEW v_fact_order AS
WITH dedup AS (
    SELECT DISTINCT * FROM raw_orders
),
typed AS (
    SELECT
        order_id AS order_key,
        customer_id AS customer_key,
        product_id AS product_key,

        CAST(
            coalesce(
                try_strptime(trim(order_ts), '%Y-%m-%dT%H:%M:%SZ'),
                try_strptime(trim(order_ts), '%Y-%m-%dT%H:%M:%S'),
                try_strptime(trim(order_ts), '%Y-%m-%d %H:%M:%S'),
                try_strptime(trim(order_ts), '%Y-%m-%d %H:%M'),
                try_strptime(trim(order_ts), '%Y/%m/%d %H:%M:%S'),
                try_strptime(trim(order_ts), '%Y/%m/%d %H:%M'),
                try_strptime(trim(order_ts), '%m/%d/%Y %H:%M'),
                try_strptime(trim(order_ts), '%m-%d-%Y %H:%M')
            ) AS DATE
        ) AS order_date,

        -- quantity as INTEGER (NULL if unparseable)
        try_cast(trim(quantity) AS INTEGER) AS quantity,

        order_status,

        -- shipping_state standardization (subset needed for this dataset)
        CASE
            WHEN shipping_state IS NULL OR trim(cast(shipping_state AS VARCHAR)) = '' THEN NULL
            WHEN upper(trim(shipping_state)) IN (
                'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
                'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
                'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'
            ) THEN upper(trim(shipping_state))
            WHEN lower(trim(shipping_state)) = 'illinois' THEN 'IL'
            WHEN lower(trim(shipping_state)) = 'california' THEN 'CA'
            WHEN lower(trim(shipping_state)) = 'new york' THEN 'NY'
            WHEN lower(trim(shipping_state)) = 'texas' THEN 'TX'
            WHEN lower(trim(shipping_state)) = 'massachusetts' THEN 'MA'
            WHEN lower(trim(shipping_state)) = 'washington' THEN 'WA'
            WHEN lower(trim(shipping_state)) = 'florida' THEN 'FL'
            ELSE trim(shipping_state)
        END AS shipping_state,

        -- gross from source string
        try_cast(trim(order_total) AS DECIMAL(12,2)) AS gross_order_amount
    FROM dedup
),
joined AS (
    SELECT
        t.*,
        try_cast(trim(p.unit_price) AS DECIMAL(12,2)) AS unit_price_dec
    FROM typed t
    LEFT JOIN raw_products p
        ON p.product_id = t.product_key
),
final AS (
    SELECT
        order_key,
        customer_key,
        product_key,
        order_date,
        quantity,
        order_status,
        shipping_state,
        gross_order_amount,
        CASE
            WHEN quantity IS NULL OR unit_price_dec IS NULL THEN NULL
            ELSE cast(quantity AS DECIMAL(12,2)) * unit_price_dec
        END AS calculated_order_amount,
        CASE
            WHEN gross_order_amount IS NULL THEN NULL
            WHEN quantity IS NULL OR unit_price_dec IS NULL THEN NULL
            ELSE gross_order_amount - (cast(quantity AS DECIMAL(12,2)) * unit_price_dec)
        END AS order_amount_variance
    FROM joined
)
SELECT *
FROM final
ORDER BY order_key;