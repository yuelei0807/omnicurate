-- Q2: Top 10 customers by completed order value
-- Inner join to dim_customer excludes orders with invalid customer_key
-- (e.g. O1019 -> C999) from this ranking.

SELECT
    c.customer_key,
    c.full_name,
    c.standard_state,
    ROUND(SUM(o.gross_order_amount), 2) AS completed_value,
    COUNT(*) AS completed_orders
FROM fact_order o
INNER JOIN dim_customer c
    ON o.customer_key = c.customer_key
WHERE o.order_status = 'completed'
GROUP BY 1, 2, 3
ORDER BY completed_value DESC
LIMIT 10;