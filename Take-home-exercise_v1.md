# Take-Home Exercise

## Agentic Data Management Engineering Challenge

*Candidate-ready assignment for evaluating practical use of Claude Code, Cursor, Windsurf, GitHub Copilot, or similar agentic coding tools*

---

> **Core objective:** Assess how effectively a candidate uses agentic development tools to generate, validate, and explain a data-management outcome. The goal is not just to see code; it is to see tool-driven problem decomposition, prompt quality, verification discipline, debugging, and human judgment.

---

| **Item** | **Expectation** |
|---|---|
| Role target | Fresher / early-career Data Management, Data Engineering, or Forward Deployed Engineering candidate |
| Estimated effort | 6–8 hours maximum |
| Turnaround | 2 calendar days from receipt |
| Required tool usage | Candidate must use at least one agentic coding assistant: Claude Code, Cursor, Windsurf, GitHub Copilot, or equivalent |
| Execution mode | Local-only execution; no cloud deployment or paid APIs required |
| Recommended stack | Python + SQL + DuckDB or SQLite; pandas/polars optional; pytest optional |
| Final submission | GitHub repo or ZIP with runnable code, generated outputs, README, and AI_USAGE.md |

---

## 1. Objective

This exercise evaluates the candidate's ability to use agentic development tools productively while still demonstrating ownership of the data-management solution. The candidate should use AI tools to accelerate planning, code generation, test creation, documentation, data-quality checks, and debugging, but must verify the results manually and explain the decisions made.

**Primary evaluation:** How effectively the candidate uses Claude Code, Cursor, Windsurf, GitHub Copilot, or a similar tool to deliver a working, explainable outcome.

**Secondary evaluation:** Data-management fundamentals: ingestion, schema design, transformation, data quality, reconciliation, SQL, and communication.

**Important principle:** AI-assisted output is acceptable and encouraged; unverified black-box output is not acceptable.

---

## 2. Business Scenario

OmniRetail is preparing a customer-360 and order-reconciliation initiative. The business has raw customer, product, order, payment, and support-ticket data from disconnected systems. The data contains realistic issues such as duplicate customers, inconsistent geography values, invalid references, payment mismatches, malformed timestamps, inactive products, and suspicious quantities.

The candidate must use an agentic coding assistant to build a small local data-management solution that ingests the raw files, creates curated tables, runs data-quality checks, and generates a concise report for business and technical stakeholders.

---

## 3. Candidate Assignment

Build a reproducible local pipeline that transforms raw OmniRetail data into curated, queryable tables and produces data-quality and analytics outputs.

| **Required component** | **What candidate must produce** |
|---|---|
| Ingestion | Load all provided raw files from `input_data` into a local database or in-memory model. DuckDB or SQLite is recommended. |
| Curated model | Create clean tables such as `dim_customer`, `dim_product`, `fact_order`, `fact_payment`, and `fact_customer_issue`. Similar names are acceptable if documented. |
| Data quality checks | Implement checks for duplicates, invalid customer/product/order references, timestamp parsing failures, negative quantities, inactive products, and payment mismatches. |
| Exception reporting | Create an exceptions output that explains bad records, rule violated, severity, and recommended handling. |
| Analytics answers | Answer the five business questions listed in the input file `expected_business_questions.md`. |
| AI usage evidence | Create `AI_USAGE.md` explaining the agentic tool used, prompts/tasks given, iterations, generated code accepted/rejected, manual fixes, and verification steps. |
| Runnable repository | Provide a README with setup instructions and a single command to run the pipeline where possible. |

---

## 4. Required Agentic Tool Usage

The candidate must actively use at least one agentic development tool. The exercise is intentionally designed to reveal whether the candidate can steer the tool, not merely paste code.

| **Expected agentic behavior** | **Evidence expected in submission** |
|---|---|
| Problem decomposition | Candidate asks the tool to inspect the input files, propose architecture, identify tasks, and generate an implementation plan. |
| Code generation with constraints | Candidate prompts the tool to write ingestion, transformation, SQL, DQ checks, tests, and reports with local-only constraints. |
| Iterative debugging | Candidate uses the tool to diagnose failing tests, bad joins, parsing errors, or mismatched totals, then records what changed. |
| Verification mindset | Candidate independently validates row counts, reconciliation totals, and DQ findings instead of trusting tool output blindly. |
| Documentation generation | Candidate uses the tool to draft README and approach notes, then edits for accuracy and clarity. |

**Required file: `AI_USAGE.md`.** This file is mandatory. It should include the tool used, important prompts or task descriptions, agent-generated artifacts, manual corrections, failed attempts, verification steps, and what the candidate would improve next.

---

## 5. Provided Input Files

The `input_data` folder included with this exercise contains all required data and guidance. Candidates should not need any additional input, cloud account, or paid service.

| **File** | **Purpose** | **Key characteristics** |
|---|---|---|
| `business_context.md` | Business framing | Explains OmniRetail use case and local-only constraint. |
| `customers.csv` | Customer master | Duplicate IDs, missing email, inconsistent country/state, duplicate phone clues. |
| `products.csv` | Product master | Product categories, unit prices, active/inactive flag. |
| `orders.csv` | Order transactions | Mixed timestamps, duplicate order, invalid customer/product IDs, suspicious quantity, total mismatch. |
| `payments.csv` | Payment transactions | Settled, voided, refunded, missing, mismatched, and orphan payments. |
| `support_tickets.jsonl` | Semi-structured issues | Customer issues, categories, sentiment, malformed timestamp, invalid customer reference. |
| `sttm_target_mapping.csv` | Source-to-target mapping | Guidance for building curated dimensions/facts. |
| `data_quality_rules.csv` | Suggested validations | Rules and severity levels candidates should implement or extend. |
| `expected_business_questions.md` | Analytics requirements | Five SQL/business questions to answer from the curated model. |

---

## 6. Suggested Target Model

The candidate may implement the following model or propose a better one with justification.

| **Target object** | **Suggested columns / description** |
|---|---|
| `dim_customer` | customer_key, full_name, email, phone, standard_country, standard_state, signup_date, loyalty_tier, duplicate_resolution_flag |
| `dim_product` | product_key, product_name, category, unit_price, active_flag |
| `fact_order` | order_key, customer_key, product_key, order_date, quantity, order_status, shipping_state, gross_order_amount, calculated_order_amount, order_amount_variance |
| `fact_payment` | payment_key, order_key, payment_date, payment_method, payment_status, payment_amount |
| `fact_customer_issue` | ticket_id, customer_key, created_date, channel, issue_category, sentiment, description |
| `dq_exception_report` | rule_id, dataset, record_key, severity, issue_description, suggested_action |

---

## 7. Required Submission Deliverables

| **Deliverable** | **Required content** |
|---|---|
| `README.md` | Setup instructions, command to run, dependencies, design summary, and assumptions. |
| `AI_USAGE.md` | Agentic tool used, prompts/tasks, iterations, generated code accepted/rejected, manual changes, verification performed. |
| `src/` or `notebooks/` | Pipeline code for ingestion, cleaning, transformation, DQ, and reporting. Code must be runnable. |
| `sql/` | SQL used for curated tables, checks, or business questions. If SQL is generated by Python, explain where. |
| `outputs/` | Generated curated database/table outputs, DQ report, exceptions report, and business-question answers. |
| `tests/` or validation script | At minimum, lightweight assertions for row counts, referential checks, amount checks, and parsing checks. |
| `APPROACH.md` or section in README | Design decisions, assumptions, tradeoffs, known limitations, and next-step recommendations. |

---

## 8. Recommended Repository Structure

```
omni-retail-agentic-data-management/
  input_data/
  src/
    pipeline.py
    ingest.py
    transform.py
    quality_checks.py
    reporting.py
  sql/
    curated_model.sql
    business_questions.sql
  tests/
    test_quality_checks.py
  outputs/
    curated.duckdb or curated.sqlite
    data_quality_report.md
    exceptions.csv
    business_answers.md
  README.md
  AI_USAGE.md
  APPROACH.md
  requirements.txt
```

---

## 9. Business Questions to Answer

1. What is completed revenue by month?
2. Who are the top 10 customers by completed order value?
3. Which orders have payment mismatches, missing payments, invalid customer references, invalid product references, or suspicious quantities?
4. Which states have the highest completed revenue?
5. Is there any visible relationship between negative support tickets and order/payment exceptions?

---

## 10. Rules and Guardrails

- Use agentic coding tools, but do not submit unverified generated code.
- Use local-only execution. Do not require cloud accounts, paid APIs, or proprietary services.
- Do not hard-code final answer values. Generate outputs from the input files.
- Document assumptions. When there are multiple reasonable ways to handle a data issue, explain the decision.
- Keep the solution simple and reproducible. Production-grade orchestration is not required.
- A polished README and clear `AI_USAGE.md` are as important as the code for this exercise.

---

## 11. Evaluation Rubric — 100 Points

| **Dimension** | **Points** | **What good looks like** |
|---|---|---|
| Agentic tool usage and steering | 35 | Strong problem decomposition; clear prompts/tasks; meaningful iterations; tool output reviewed critically; `AI_USAGE.md` is specific and credible. |
| Data-management outcome | 30 | Correct ingestion, curated model, joins, transformation logic, DQ checks, exception reporting, and business answers. |
| Verification and testing | 15 | Candidate validates row counts, references, amount reconciliation, timestamp parsing, and edge cases; includes tests or validation script. |
| Code quality and reproducibility | 10 | Readable structure, minimal dependencies, simple run command, clear error handling, no hard-coded output answers. |
| Communication and judgment | 10 | Clear README, assumptions, tradeoffs, limitations, and next-step recommendations. |

---

## Appendix A — Input File Schema Summary

| **Input file** | **Columns / record fields** |
|---|---|
| `customers.csv` | customer_id, first_name, last_name, email, phone, country, state, signup_date, loyalty_tier |
| `products.csv` | product_id, product_name, category, unit_price, active_flag |
| `orders.csv` | order_id, customer_id, order_ts, product_id, quantity, order_status, shipping_state, order_total |
| `payments.csv` | payment_id, order_id, payment_ts, payment_method, payment_status, amount |
| `support_tickets.jsonl` | ticket_id, customer_id, created_ts, channel, category, sentiment, description |
| `sttm_target_mapping.csv` | target_table, target_column, source_file, source_column, transformation_rule |
| `data_quality_rules.csv` | rule_id, dataset, rule_description, severity |

---

## Appendix B — Sample Records

The files in `input_data` contain the complete input. The sample below shows the type of records included; candidates should process the actual files, not copy from this appendix.

| **File** | **Sample record** |
|---|---|
| `customers.csv` | C002, Liam, Nguyen, liam.nguyen@example.com, 773-555-0188, US, Illinois, 01/12/2025, Silver |
| `orders.csv` | O1021, C002, 2025-05-02 14:00, P008, 4, completed, IL, 50.00 |
| `payments.csv` | PMT021, O1021, 2025-05-02 14:01, paypal, settled, 44.00 |
| `support_tickets.jsonl` | `{"ticket_id":"T007","customer_id":"C002","category":"billing","sentiment":"negative",...}` |

---

*Agentic Data Management Take-Home Exercise — Candidate Pack*
