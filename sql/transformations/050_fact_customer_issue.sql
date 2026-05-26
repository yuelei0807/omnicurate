-- Equivalent SQL for documentation; runtime uses Python in src/transformation/*
-- View name: v_fact_customer_issue
--
-- Mirrors src/transformation/fact_customer_issue.py:
-- keep all tickets (even bad timestamps and unknown customers)
-- parse created_ts -> created_date (DATE); invalid -> NULL

CREATE OR REPLACE VIEW v_fact_customer_issue AS
SELECT
    ticket_id,
    customer_id AS customer_key,
    CAST(
        coalesce(
            try_strptime(trim(created_ts), '%Y-%m-%dT%H:%M:%SZ'),
            try_strptime(trim(created_ts), '%Y-%m-%dT%H:%M:%S'),
            try_strptime(trim(created_ts), '%Y-%m-%d %H:%M:%S'),
            try_strptime(trim(created_ts), '%Y-%m-%d %H:%M'),
            try_strptime(trim(created_ts), '%Y/%m/%d %H:%M:%S'),
            try_strptime(trim(created_ts), '%Y/%m/%d %H:%M'),
            try_strptime(trim(created_ts), '%m/%d/%Y %H:%M'),
            try_strptime(trim(created_ts), '%m-%d-%Y %H:%M')
        ) AS DATE
    ) AS created_date,
    channel,
    category AS issue_category,
    sentiment,
    description
FROM raw_support_tickets
ORDER BY ticket_id;