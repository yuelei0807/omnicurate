# Approach and Design Decisions

This document explains the main architectural choices for the OmniRetail take-home data-management pipeline.

## Why DuckDB

DuckDB is a strong fit for a local, agent-built analytics stack on a small fixed dataset:

- **Single file, zero ops** — `outputs/curated.duckdb` is easy to reset, ship, and open from Streamlit without running a database server.
- **SQL-first analytics** — Business questions Q1–Q5 are expressed as readable SQL under `sql/analytics/`, which stakeholders can review independently of Python.
- **Pandas interoperability** — Ingestion and transformation stay in pandas; results land in DuckDB via `INSERT` for querying and the UI.
- **Fast enough** — Full pipeline runs in under one second on this data volume, so iteration during development stays frictionless.

Tradeoff: DuckDB is not a shared production warehouse. For this exercise, local reproducibility matters more than multi-user concurrency.

## Why pandas + SQL (hybrid)

The pipeline splits work by layer strength:

| Layer | Tool | Rationale |
|-------|------|-----------|
| Ingestion, preprocessing, validation, transformation | **pandas** | Row-level rules, dedup tie-breakers, email/geo normalization, and exception row assembly are clearer in Python with unit tests per function. |
| Analytics (Q1–Q5) | **SQL** | Aggregations, joins, and cohort logic are concise in SQL and mirror how analysts would query a curated warehouse. |
| Documentation | **SQL views** in `sql/transformations/` | Mirror Python transform logic for reviewers who prefer DDL over code. |

Validation produces a canonical `dq_exception_report`; transformation does not silently drop bad rows that analytics still need to reference (e.g. orphan orders for Q3).

## Deduplication strategy

Three patterns appear in the source data; each is handled explicitly in `src/preprocessing/deduplication.py`:

### 1. Byte-identical duplicates (hard drop)

Example: **O1018** appears twice in `orders.csv` with identical columns. `drop_exact_duplicates` keeps the first row and drops the rest. DQ004 records the dropped row as informational (no information lost).

### 2. Primary-key collisions (deterministic survivor)

Example: **C006** appears twice with the same `customer_id` but different email/phone/country. `resolve_pk_duplicates` keeps the **lowest source row index**; the loser becomes a DQ001 exception. `dim_customer` ends with 19 rows from 20 raw customer rows.

Orders follow the same pattern after byte-id dedup if conflicting PK rows existed.

### 3. Cross-ID soft duplicates (flag, do not merge)

Example: **C001** and **C019** share first name, last name, and phone but different `customer_id`. These are **not** merged (that would violate the customer master). Instead, `mark_soft_duplicates` sets `duplicate_resolution_flag = True` on the non-canonical row (C019). DQ001 does not fire for this pattern — the flag is a stewardship signal in `dim_customer`, not a hard delete.

## Timestamp parsing

Raw timestamps mix ISO with `Z`, ISO without timezone, space-separated datetimes, US dates, and plain dates. The parser in `src/preprocessing/timestamp_parser.py`:

1. Tries a **fixed ordered list** of `strptime` formats (most specific first).
2. Falls back to **`dateutil.parser`** for odd but valid strings.
3. Returns `(NaT, valid=False)` on total failure so **DQ011** can flag tickets like **T010** (`bad_timestamp`) instead of silently coercing to null without an exception.

We avoid blind `pd.to_datetime(..., infer_datetime_format=True)` because it can guess ambiguous US/EU dates wrong and conflate “missing” with “unparseable.”

Curated facts store **dates** (not timestamps) for reporting grain aligned with the business questions.

## Foreign-key handling

Invalid references are **kept in fact tables** with their original key values:

| Record | Issue | Behavior |
|--------|--------|----------|
| **O1019** | `customer_id = C999` (unknown) | Row stays in `fact_order`; DQ005 exception |
| **O1020** | `product_id = P999` (unknown) | Row stays; calculated amount NULL; DQ006 |
| **PMT029** | `order_id = O9999` (orphan payment) | Row stays in `fact_payment`; DQ009 |

Q2 inner-joins to `dim_customer` so invalid customer keys are excluded from “top customer” rankings, while Q3 and the exception report still surface problematic orders. This separates **reporting convenience** from **audit completeness**.

## Revenue and variance handling

For orders:

- **`gross_order_amount`** comes from source `order_total` (after type coercion) and is used as completed revenue in Q1/Q2/Q4.
- **`calculated_order_amount`** = `quantity × unit_price` when both are valid.
- **`order_amount_variance`** = `gross − calculated` when both sides are finite.

Example: **O1021** has gross $50.00 vs calculated $44.00 → variance **$6.00**; DQ008 flags the order; DQ010 flags payment **PMT021** with the same diff convention (`order_total − amount`).

Negative quantity on **O1030** is retained in `fact_order` (calculated −$21) but flagged by **DQ007** (completed order with non-positive quantity). We do not clamp or drop — stewards decide reversal vs data fix.

## What I would add next

With more time and a production target:

1. **Incremental ingestion** — watermark columns, `MERGE` into raw/curated, and idempotent partition keys.
2. **Great Expectations or Soda** — declarative suites generated from `data_quality_rules.csv` with profiling on each run.
3. **dbt-style lineage** — transform SQL as versioned models with dependency graph and column-level docs.
4. **Streamlit auth** — SSO or role-based views so exception detail is not open on a shared URL.
5. **`requirements.txt` + Makefile** — pinned deps and `make pipeline` / `make test` for one-command onboarding (planned in scaffold phase, not required for core logic).
