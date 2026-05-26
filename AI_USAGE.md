# AI Usage Disclosure

This project was built with AI assistance (Cursor + Claude) following a step-by-step implementation plan. The candidate implemented each module locally, ran smoke tests, and adjusted the next step based on execution results.

## Tool used

- **IDE:** Cursor  
- **Model:** Claude (via Cursor Agent)  
- **Primary guide:** `PLAN_IMPLEMENTATION_PROMPTS.md` in this repository (atomic steps with copy-paste prompts per module)

## How I steered the agent

1. **One atomic step at a time** — Requested a single sub-step per message (e.g. “Step 5.7 dq007 only”) and pasted terminal output before continuing.  
2. **Modularity constraints** — Required strict layer boundaries (ingestion → preprocessing → validation → transformation → analytics → reporting → UI) and independent, testable modules.  
3. **Reproducibility** — Insisted on smoke tests after every step with locked row counts (e.g. 19 `dim_customer`, 30 `fact_order`, 17 exceptions).  
4. **Rejected over-engineering** — Preferred minimal diffs aligned with existing patterns rather than new abstractions.  
5. **Local-first** — Deferred GitHub/version-control work until functional requirements were complete.

## Sample prompts

Representative prompts used during the build (paraphrased from the plan and chat):

1. **Planning (Ask mode)**  
   > Read `Take-home-exercise_v1.md` and `input_data/` in detail. Plan a modular system with Streamlit pages, reproducible pipelines, and atomic implementation steps with agent prompts in `PLAN_IMPLEMENTATION_PROMPTS.md`.

2. **Config / database**  
   > Create `src/config/settings.py` with `PROJECT_ROOT`, `INPUT_DIR`, `OUTPUT_DIR`, `DUCKDB_PATH`, and `ensure_output_dir()` — no pandas or duckdb imports.

3. **Validation rule**  
   > Create `src/validation/checks/dq010_payment_amount_matches.py`. Flag settled payments where amount mismatches completed `order_total` within tolerance; use `diff = order_total - amount` (positive when order exceeds payment).

4. **Transformation**  
   > Create `fact_order` with `gross_order_amount`, `calculated_order_amount`, and `order_amount_variance`. Drop byte-identical duplicates (O1018); keep invalid FK rows O1019/O1020.

5. **Incremental fix after smoke test**  
   > Pyright error: `Object of type "None" is not subscriptable` on `fetchone()[0]` in `dq_report.py` — fix and verify without changing runtime behavior.

## Agent output I rejected and why

| Suggestion / output | Why rejected | What we did instead |
|---------------------|--------------|---------------------|
| Store money as float in curated tables | Rounding risk on revenue totals | `DECIMAL` in DDL; `Decimal` in pandas transforms |
| `pd.to_datetime` with inference for all timestamps | Ambiguous US dates; silent NaT | Ordered `strptime` list + dateutil fallback + DQ011 for failures |
| `REGISTRY.get(rid)` in reports | Pyright `None` on `.description` | `REGISTRY[rid]` for known rule IDs |
| `load_all_raw` in pipeline smoke tests | Function does not exist | `ingestion.load_all(con)` |
| `st.page_link` on Home for navigation | Breaks outside `streamlit run`; path issues | Sidebar multipage navigation only |
| Clamp negative quantity on O1030 | Hides real DQ007 violation | Keep −1 in fact; flag in DQ007 |
| Merge C001 and C019 into one customer | Different `customer_id`s | Soft-dup flag on C019 only |

## Verification I performed manually

Checks run during development (terminal smoke tests and spot reads):

| Check | Expected | Result |
|-------|----------|--------|
| Raw rows ingested | 103 | 103 |
| `dim_customer` rows | 19 (C006 PK loser dropped) | 19 |
| `fact_order` rows | 30 (O1018 byte-dup dropped) | 30 |
| Total DQ exceptions | 17 | 17 |
| O1021 variance | $6.00 (50 vs 44) | DQ008 + DQ010 diff 6.00 |
| O1030 quantity | −1, DQ007 fired | Confirmed |
| PMT029 orphan payment | order O9999, DQ009 | Confirmed |
| T010 bad timestamp | NULL date, DQ011 | Confirmed |
| Q1 completed revenue | $1,260.85 | Matches `business_answers.md` |
| Q5 negative-ticket cohort | 40% orders with exceptions | Confirmed in analytics |
| End-to-end pytest | `test_full_pipeline_reconciles` | PASSED |
| Streamlit UI | Home + 3 pages load from DuckDB | Working after `app/_bootstrap.py` |
| Phase 12 `pytest tests/ -v` | 12 passed | PASSED (2026-05-25) |
| Phase 12 `make run` / `make all` | One-command entry | Scaffold added (`Makefile`, `requirements.txt`) |

## What I would improve next time

1. **Scaffold Phase 0 earlier** — Add `requirements.txt`, `pyproject.toml`, and `Makefile` up front so `make pipeline` / `make test` match the README.  
2. **Single Streamlit entry at repo root** — Avoid `sys.path` bootstrap by using `streamlit run streamlit_app.py` with `pages/` at root.  
3. **Stricter CI from day one** — Run pyright + pytest on every module before moving to the next phase.  
4. **Capture screenshots in Phase 12** — Save `outputs/screenshots/` during first successful Streamlit run while numbers are fresh.  
5. **Shorter agent threads** — Start a new chat per phase to reduce context drift on row-count assumptions (e.g. 20 vs 21 customers).
