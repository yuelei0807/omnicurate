-- Q1: Completed revenue by month
-- Uses gross_order_amount as source-of-truth revenue for completed orders.
-- Order amount variance is tracked separately (DQ008 / fact_order.order_amount_variance).

SELECT
    date_trunc('month', order_date) AS month,
    ROUND(SUM(gross_order_amount), 2) AS completed_revenue,
    COUNT(*) AS completed_orders
FROM fact_order
WHERE order_status = 'completed'
  AND order_date IS NOT NULL
GROUP BY 1
ORDER BY 1;