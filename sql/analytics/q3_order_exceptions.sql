-- Q3: Orders with data-quality / reconciliation exceptions
-- Combines order-level DQ rows (dataset=orders) with payment DQ rows
-- joined through fact_payment (payment_id -> order_key).

WITH order_ex AS (
    SELECT
        record_key AS order_key,
        rule_id,
        severity,
        issue_description
    FROM dq_exception_report
    WHERE dataset = 'orders'
),
payment_ex AS (
    SELECT
        fp.order_key AS order_key,
        pe.rule_id,
        pe.severity,
        pe.issue_description
    FROM dq_exception_report pe
    INNER JOIN fact_payment fp
        ON pe.record_key = fp.payment_key
    WHERE pe.dataset = 'payments'
      AND fp.order_key IS NOT NULL
),
all_ex AS (
    SELECT * FROM order_ex
    UNION ALL
    SELECT * FROM payment_ex
)
SELECT
    o.order_key,
    o.customer_key,
    o.product_key,
    o.order_status,
    o.quantity,
    o.gross_order_amount,
    o.calculated_order_amount,
    o.order_amount_variance,
    list(DISTINCT e.rule_id ORDER BY e.rule_id) AS triggered_rules,
    list(DISTINCT e.issue_description ORDER BY e.issue_description) AS issues
FROM fact_order o
INNER JOIN all_ex e
    ON o.order_key = e.order_key
GROUP BY
    o.order_key,
    o.customer_key,
    o.product_key,
    o.order_status,
    o.quantity,
    o.gross_order_amount,
    o.calculated_order_amount,
    o.order_amount_variance
ORDER BY o.order_key;