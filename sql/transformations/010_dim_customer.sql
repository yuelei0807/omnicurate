-- Equivalent SQL for documentation; runtime uses Python in src/transformation/*
-- View name: v_dim_customer
--
-- Mirrors src/transformation/dim_customer.py:
-- 1) PK dedup on customer_id (keep first row per customer_id)
-- 2) soft-dup flag on (first_name,last_name,phone) => duplicate_resolution_flag
-- 3) standardize country/state; normalize email; parse signup_date to DATE

CREATE OR REPLACE VIEW v_dim_customer AS
WITH base AS (
    SELECT
        customer_id,
        first_name,
        last_name,
        email,
        phone,
        country,
        state,
        signup_date,
        loyalty_tier,
        -- PK dedup: keep first row per customer_id.
        -- Note: raw tables have no explicit ingestion row number; this ORDER BY is a
        -- deterministic proxy for "first occurrence" used in Python.
        row_number() OVER (
            PARTITION BY customer_id
            ORDER BY customer_id, coalesce(email, ''), coalesce(phone, ''), coalesce(signup_date, '')
        ) AS rn_customer_id
    FROM raw_customers
),
pk_winners AS (
    SELECT *
    FROM base
    WHERE rn_customer_id = 1
),
soft_dup_flagged AS (
    SELECT
        *,
        CASE
            WHEN phone IS NULL OR trim(cast(phone AS VARCHAR)) = '' THEN FALSE
            WHEN row_number() OVER (
                PARTITION BY lower(trim(first_name)), lower(trim(last_name)), trim(phone)
                ORDER BY customer_id
            ) = 1 THEN FALSE
            ELSE TRUE
        END AS duplicate_resolution_flag
    FROM pk_winners
),
standardized AS (
    SELECT
        customer_id AS customer_key,
        trim(first_name) || ' ' || trim(last_name) AS full_name,

        -- normalize email: lower + trim; empty -> NULL
        NULLIF(lower(trim(email)), '') AS email,

        phone,

        -- standard_country
        CASE
            WHEN country IS NULL OR trim(cast(country AS VARCHAR)) = '' THEN NULL
            WHEN lower(trim(country)) IN (
                'usa','us','u.s.','u.s.a.','united states','united states of america'
            ) THEN 'USA'
            ELSE trim(country)
        END AS standard_country,

        -- standard_state (codes pass-through uppercased; full names mapped)
        CASE
            WHEN state IS NULL OR trim(cast(state AS VARCHAR)) = '' THEN NULL
            WHEN upper(trim(state)) IN (
                'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
                'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
                'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'
            ) THEN upper(trim(state))
            WHEN lower(trim(state)) = 'illinois' THEN 'IL'
            WHEN lower(trim(state)) = 'california' THEN 'CA'
            WHEN lower(trim(state)) = 'new york' THEN 'NY'
            WHEN lower(trim(state)) = 'texas' THEN 'TX'
            WHEN lower(trim(state)) = 'massachusetts' THEN 'MA'
            WHEN lower(trim(state)) = 'washington' THEN 'WA'
            WHEN lower(trim(state)) = 'florida' THEN 'FL'
            ELSE trim(state)
        END AS standard_state,

        -- signup_date parse (DATE) with multiple source formats
        CAST(
            coalesce(
                try_strptime(trim(signup_date), '%Y-%m-%d'),
                try_strptime(trim(signup_date), '%Y/%m/%d'),
                try_strptime(trim(signup_date), '%m/%d/%Y'),
                try_strptime(trim(signup_date), '%m-%d-%Y')
            ) AS DATE
        ) AS signup_date,

        loyalty_tier,
        duplicate_resolution_flag
    FROM soft_dup_flagged
)
SELECT *
FROM standardized
ORDER BY customer_key;