-- Equivalent SQL for documentation; runtime uses Python in src/transformation/*
-- View name: v_fact_payment
--
-- Mirrors src/transformation/fact_payment.py:
-- payment_id -> payment_key
-- keep orphan payments (PMT029 -> O9999)
-- parse payment_ts -> payment_date (DATE)
-- amount cast to DECIMAL(12,2)

CREATE OR REPLACE VIEW v_fact_payment AS
SELECT
    payment_id AS payment_key,
    order_id   AS order_key,
    CAST(
        coalesce(
            try_strptime(trim(payment_ts), '%Y-%m-%dT%H:%M:%SZ'),
            try_strptime(trim(payment_ts), '%Y-%m-%dT%H:%M:%S'),
            try_strptime(trim(payment_ts), '%Y-%m-%d %H:%M:%S'),
            try_strptime(trim(payment_ts), '%Y-%m-%d %H:%M'),
            try_strptime(trim(payment_ts), '%Y/%m/%d %H:%M:%S'),
            try_strptime(trim(payment_ts), '%Y/%m/%d %H:%M'),
            try_strptime(trim(payment_ts), '%m/%d/%Y %H:%M'),
            try_strptime(trim(payment_ts), '%m-%d-%Y %H:%M')
        ) AS DATE
    ) AS payment_date,
    payment_method,
    payment_status,
    try_cast(trim(amount) AS DECIMAL(12,2)) AS payment_amount
FROM raw_payments
ORDER BY payment_key;