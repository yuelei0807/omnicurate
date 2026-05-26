-- Q4: Completed revenue by shipping state (standardized 2-letter codes)
-- Uses gross_order_amount for completed orders.

SELECT
    shipping_state AS state,
    ROUND(SUM(gross_order_amount), 2) AS completed_revenue,
    COUNT(*) AS completed_orders
FROM fact_order
WHERE order_status = 'completed'
  AND shipping_state IS NOT NULL
GROUP BY 1
ORDER BY completed_revenue DESC;