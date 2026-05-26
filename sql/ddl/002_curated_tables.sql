-- =====================================================================
-- 002_curated_tables.sql
--
-- Curated tables with semantically correct types.
--
-- Money is DECIMAL(12,2) (never DOUBLE/FLOAT) so reconciliation totals
-- and DQ008/DQ010 variance comparisons are exact — no binary rounding
-- drift. Dates are DATE, not TIMESTAMP, because Q1/Q4 roll up by day
-- or coarser; only dq_exception_report.detected_at keeps TIMESTAMP
-- because that field is event-time meaningful.
--
-- No FOREIGN KEY constraints: invalid-FK rows (O1019->C999, O1020->P999,
-- PMT029->O9999) are kept in fact tables on purpose so they surface in
-- Q3 (order exceptions). Referential integrity is enforced by the
-- validation layer (DQ005/DQ006/DQ009), not by the database engine.
--
-- CREATE OR REPLACE TABLE keeps the script idempotent.
-- =====================================================================


-- ===== dim_customer =====
CREATE OR REPLACE TABLE dim_customer (
    customer_key              VARCHAR,
    full_name                 VARCHAR,
    email                     VARCHAR,
    phone                     VARCHAR,
    standard_country          VARCHAR,
    standard_state            VARCHAR,
    signup_date               DATE,
    loyalty_tier              VARCHAR,
    duplicate_resolution_flag BOOLEAN
);


-- ===== dim_product =====
CREATE OR REPLACE TABLE dim_product (
    product_key   VARCHAR,
    product_name  VARCHAR,
    category      VARCHAR,
    unit_price    DECIMAL(12,2),
    active_flag   BOOLEAN
);


-- ===== fact_order =====
CREATE OR REPLACE TABLE fact_order (
    order_key                VARCHAR,
    customer_key             VARCHAR,
    product_key              VARCHAR,
    order_date               DATE,
    quantity                 INTEGER,
    order_status             VARCHAR,
    shipping_state           VARCHAR,
    gross_order_amount       DECIMAL(12,2),
    calculated_order_amount  DECIMAL(12,2),
    order_amount_variance    DECIMAL(12,2)
);


-- ===== fact_payment =====
CREATE OR REPLACE TABLE fact_payment (
    payment_key     VARCHAR,
    order_key       VARCHAR,
    payment_date    DATE,
    payment_method  VARCHAR,
    payment_status  VARCHAR,
    payment_amount  DECIMAL(12,2)
);


-- ===== fact_customer_issue =====
CREATE OR REPLACE TABLE fact_customer_issue (
    ticket_id       VARCHAR,
    customer_key    VARCHAR,
    created_date    DATE,
    channel         VARCHAR,
    issue_category  VARCHAR,
    sentiment       VARCHAR,
    description     VARCHAR
);


-- ===== dq_exception_report =====
CREATE OR REPLACE TABLE dq_exception_report (
    rule_id            VARCHAR,
    dataset            VARCHAR,
    record_key         VARCHAR,
    severity           VARCHAR,
    issue_description  VARCHAR,
    suggested_action   VARCHAR,
    detected_at        TIMESTAMP
);