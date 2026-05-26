-- =====================================================================
-- 001_raw_tables.sql
--
-- Raw landing tables. Every column is VARCHAR on purpose: the raw layer
-- must preserve the source bytes verbatim, including malformed values
-- (bad timestamps, negative quantities, mismatched totals). Typed casts
-- happen in src/preprocessing/* and any failure is recorded in
-- dq_exception_report via src/validation/* — never silently dropped.
--
-- CREATE OR REPLACE TABLE keeps the script idempotent.
-- =====================================================================


-- ===== raw_customers =====
CREATE OR REPLACE TABLE raw_customers (
    customer_id   VARCHAR,
    first_name    VARCHAR,
    last_name     VARCHAR,
    email         VARCHAR,
    phone         VARCHAR,
    country       VARCHAR,
    state         VARCHAR,
    signup_date   VARCHAR,
    loyalty_tier  VARCHAR
);


-- ===== raw_products =====
CREATE OR REPLACE TABLE raw_products (
    product_id    VARCHAR,
    product_name  VARCHAR,
    category      VARCHAR,
    unit_price    VARCHAR,
    active_flag   VARCHAR
);


-- ===== raw_orders =====
CREATE OR REPLACE TABLE raw_orders (
    order_id        VARCHAR,
    customer_id     VARCHAR,
    order_ts        VARCHAR,
    product_id      VARCHAR,
    quantity        VARCHAR,
    order_status    VARCHAR,
    shipping_state  VARCHAR,
    order_total     VARCHAR
);


-- ===== raw_payments =====
CREATE OR REPLACE TABLE raw_payments (
    payment_id      VARCHAR,
    order_id        VARCHAR,
    payment_ts      VARCHAR,
    payment_method  VARCHAR,
    payment_status  VARCHAR,
    amount          VARCHAR
);


-- ===== raw_support_tickets =====
CREATE OR REPLACE TABLE raw_support_tickets (
    ticket_id     VARCHAR,
    customer_id   VARCHAR,
    created_ts    VARCHAR,
    channel       VARCHAR,
    category      VARCHAR,
    sentiment     VARCHAR,
    description   VARCHAR
);