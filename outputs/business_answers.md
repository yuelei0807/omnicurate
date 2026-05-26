# Business Answers

## Q1 — Completed revenue by month

Completed revenue by calendar month, using gross_order_amount for orders with status 'completed'.

### SQL

```sql
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
```

### Results

| month | completed_revenue | completed_orders |
| --- | --- | --- |
| 2025-03-01 00:00:00 | 440.7 | 9 |
| 2025-04-01 00:00:00 | 394.95 | 9 |
| 2025-05-01 00:00:00 | 425.2 | 10 |

### Finding

Total completed revenue is $1,260.85 across 28 orders. Peak month is 2025-03 with $440.70 from 9 orders.

## Q2 — Top customers by completed order value

Top customers ranked by total completed order value (gross_order_amount), excluding orders with invalid customer_key.

### SQL

```sql
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
```

### Results

| customer_key | full_name | standard_state | completed_value | completed_orders |
| --- | --- | --- | --- | --- |
| C010 | Lucas Taylor | MA | 194.98 | 2 |
| C016 | Henry Martin | IL | 133.98 | 2 |
| C012 | James Thomas | WA | 133.98 | 2 |
| C007 | Sophia Miller | TX | 99.98 | 2 |
| C002 | Liam Nguyen | IL | 89.99 | 2 |
| C009 | Isabella Moore | MA | 83.25 | 2 |
| C004 | Emma Brown | CA | 74.97 | 1 |
| C003 | Noah Williams | CA | 73.75 | 2 |
| C013 | Charlotte Jackson | WA | 59.0 | 1 |
| C018 | Daniel Clark | NY | 54.0 | 2 |

### Finding

Top customer is C010 (Lucas Taylor, MA) with $194.98 across 2 completed orders.

## Q3 — Orders with data-quality exceptions

Orders that triggered at least one data-quality or reconciliation exception (order-level or payment-mapped-to-order).

### SQL

```sql
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
```

### Results

| order_key | customer_key | product_key | order_status | quantity | gross_order_amount | calculated_order_amount | order_amount_variance | triggered_rules | issues |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| O1018 | C018 | P012 | completed | 1 | 75.0 | 75.0 | 0.0 | ['DQ004'] | ['Duplicate order_id=O1018; identical row was dropped (no information lost).'] |
| O1019 | C999 | P002 | completed | 1 | 24.99 | 24.99 | 0.0 | ['DQ005'] | ["order_id=O1019: customer_id 'C999' not found in customers."] |
| O1020 | C001 | P999 | completed | 1 | 12.99 | nan | nan | ['DQ006'] | ["order_id=O1020: product_id 'P999' not found in products."] |
| O1021 | C002 | P008 | completed | 4 | 50.0 | 44.0 | 6.0 | ['DQ008' 'DQ010'] | ['order_id=O1021: order_total=50.00 vs quantity*unit_price=44.00 (diff=6.00).'
 'payment_id=PMT021: settled payment 44.00 != completed order total 50.00 (diff=6.00).'] |
| O1030 | C018 | P010 | completed | -1 | -21.0 | -21.0 | 0.0 | ['DQ007'] | ['order_id=O1030: completed-order quantity -1 is not positive.'] |

### Finding

5 distinct orders triggered at least one exception. Affected order keys: O1018, O1019, O1020, O1021, O1030.

## Q4 — Completed revenue by shipping state

Completed revenue aggregated by standardized shipping_state (USPS 2-letter codes).

### SQL

```sql
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
```

### Results

| state | completed_revenue | completed_orders |
| --- | --- | --- |
| IL | 315.95 | 8 |
| MA | 278.23 | 4 |
| WA | 192.98 | 3 |
| CA | 169.72 | 4 |
| TX | 141.98 | 3 |
| NY | 96.0 | 3 |
| FL | 65.99 | 3 |

### Finding

Top revenue state is IL with $315.95 from 8 completed orders.

## Q5 — Negative tickets vs order exceptions

Compares customers with negative support tickets vs those without, measuring the share of their orders that triggered exceptions.

### SQL

```sql
-- Q5: Relationship between negative support tickets and order/payment exceptions
-- Compares customers with >=1 negative ticket vs customers without,
-- measuring what share of their orders triggered DQ exceptions.

WITH negative_customers AS (
    SELECT DISTINCT customer_key
    FROM fact_customer_issue
    WHERE lower(sentiment) = 'negative'
),
order_ex AS (
    SELECT record_key AS order_key
    FROM dq_exception_report
    WHERE dataset = 'orders'
    UNION
    SELECT fp.order_key
    FROM dq_exception_report pe
    INNER JOIN fact_payment fp
        ON pe.record_key = fp.payment_key
    WHERE pe.dataset = 'payments'
      AND fp.order_key IS NOT NULL
),
orders_flagged AS (
    SELECT
        o.customer_key,
        o.order_key,
        CASE WHEN e.order_key IS NOT NULL THEN 1 ELSE 0 END AS has_exception
    FROM fact_order o
    LEFT JOIN order_ex e
        ON o.order_key = e.order_key
),
per_customer AS (
    SELECT
        customer_key,
        COUNT(*) AS total_orders,
        SUM(has_exception) AS orders_with_exception
    FROM orders_flagged
    GROUP BY customer_key
),
cohorted AS (
    SELECT
        c.customer_key,
        CASE
            WHEN nc.customer_key IS NOT NULL THEN 'has_negative_ticket'
            ELSE 'no_negative_ticket'
        END AS cohort,
        COALESCE(pc.total_orders, 0) AS total_orders,
        COALESCE(pc.orders_with_exception, 0) AS orders_with_exception
    FROM dim_customer c
    LEFT JOIN negative_customers nc
        ON c.customer_key = nc.customer_key
    LEFT JOIN per_customer pc
        ON c.customer_key = pc.customer_key
)
SELECT
    cohort,
    COUNT(DISTINCT customer_key) AS customer_count,
    SUM(total_orders) AS total_orders,
    SUM(orders_with_exception) AS orders_with_exception,
    ROUND(
        100.0 * SUM(orders_with_exception) / NULLIF(SUM(total_orders), 0),
        2
    ) AS pct_orders_with_exception
FROM cohorted
GROUP BY cohort
ORDER BY cohort;
```

### Results

| cohort | customer_count | total_orders | orders_with_exception | pct_orders_with_exception |
| --- | --- | --- | --- | --- |
| has_negative_ticket | 6 | 10.0 | 4.0 | 40.0 |
| no_negative_ticket | 13 | 19.0 | 0.0 | 0.0 |

### Finding

Among 6 customers with negative support tickets, 40.0% of their orders triggered exceptions, versus 0.0% for customers without negative tickets.
