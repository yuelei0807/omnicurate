# OmniRetail Agentic Data Management — Detailed Implementation Plan & Prompts

This document is the **atomic step-by-step build guide** for the OmniRetail take-home. Every step is small enough to execute as a single agent turn, and ships with a copy-paste **Prompt to Agent**. Steps are numbered `<Phase>.<Step>`. Module boundaries are strict: each module owns its inputs/outputs and is independently testable.

---

## 0. Stack, Conventions, Non-Negotiables

- **Language**: Python 3.11
- **DB**: DuckDB (file at `outputs/curated.duckdb`)
- **Data libs**: pandas (primary), pyarrow (parquet/CSV speed), python-dateutil (mixed timestamp parsing), email-validator (DQ002)
- **UI**: Streamlit (4 pages: Home, Data Quality, Analytics (5 tabs), Curated Model Explorer)
- **Tests**: pytest (per-module + an end-to-end reconciliation test)
- **Style**: ruff + black (line length 100)
- **Single entrypoint**: `python -m src.pipeline` rebuilds everything; `streamlit run app/Home.py` serves the UI
- **Determinism**: pipeline is idempotent. Re-running drops/recreates curated tables from the raw layer.
- **No hard-coded answers**: every number rendered in the UI must come from a SQL query against `curated.duckdb`.

### Modular contract (enforced)

```
input_data/*  →  ingestion  →  raw_*  (DuckDB)
raw_*         →  preprocessing  →  stg_*  (pure functions, no DB writes)
stg_*         →  validation  →  dq_exception_report  (+ pass/fail flags)
stg_* + flags →  transformation  →  dim_* / fact_*
curated       →  analytics  →  vw_q1..vw_q5
curated + vw  →  reporting  →  markdown / csv
curated       →  app (Streamlit)  →  UI
```

Rules:
1. A module **never reaches across layers** (e.g., transformation never reads CSV).
2. A module **never writes outside its layer** (e.g., preprocessing never touches `dim_*`).
3. Every module exposes a single `run(...)` function with explicit DataFrame in / DataFrame out (except DB-bound ones, which take a `duckdb.DuckDBPyConnection`).
4. Every module ships with a sibling unit test before the next module is built.

---

## Repository Layout (target)

```
omni-retail-agentic-data-management/
├── input_data/                       # provided, untouched
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── settings.py               # paths, db uri, constants
│   │   ├── schemas.py                # raw + curated column dtypes
│   │   └── mappings.py               # country/state lookups
│   ├── database/
│   │   ├── connection.py             # duckdb context manager
│   │   └── ddl.py                    # executes SQL DDL files
│   ├── ingestion/
│   │   ├── csv_loader.py
│   │   ├── jsonl_loader.py
│   │   └── loaders.py                # load_all()
│   ├── preprocessing/
│   │   ├── timestamp_parser.py
│   │   ├── geography_standardizer.py
│   │   ├── deduplication.py
│   │   ├── type_coercion.py
│   │   └── email_normalizer.py
│   ├── validation/
│   │   ├── rule_registry.py          # DQRule dataclass + REGISTRY
│   │   ├── checks/                   # one file per DQ001..DQ012
│   │   ├── runner.py                 # apply_all() → exceptions df
│   │   └── exception_writer.py
│   ├── transformation/
│   │   ├── dim_customer.py
│   │   ├── dim_product.py
│   │   ├── fact_order.py
│   │   ├── fact_payment.py
│   │   └── fact_customer_issue.py
│   ├── analytics/
│   │   ├── q1_revenue_by_month.py
│   │   ├── q2_top_customers.py
│   │   ├── q3_order_exceptions.py
│   │   ├── q4_revenue_by_state.py
│   │   └── q5_sentiment_link.py
│   ├── reporting/
│   │   ├── dq_report.py
│   │   └── business_answers.py
│   └── pipeline.py                   # orchestrator
├── sql/
│   ├── ddl/
│   │   ├── 001_raw_tables.sql
│   │   └── 002_curated_tables.sql
│   ├── transformations/
│   │   ├── 010_dim_customer.sql
│   │   ├── 020_dim_product.sql
│   │   ├── 030_fact_order.sql
│   │   ├── 040_fact_payment.sql
│   │   └── 050_fact_customer_issue.sql
│   └── analytics/
│       ├── q1_revenue_by_month.sql
│       ├── q2_top_customers.sql
│       ├── q3_order_exceptions.sql
│       ├── q4_revenue_by_state.sql
│       └── q5_sentiment_link.sql
├── app/
│   ├── Home.py
│   ├── pages/
│   │   ├── 1_Data_Quality.py
│   │   ├── 2_Analytics.py            # uses st.tabs for Q1..Q5
│   │   └── 3_Curated_Model_Explorer.py
│   ├── components/
│   │   ├── header.py
│   │   ├── kpi_card.py
│   │   └── data_table.py
│   ├── services/
│   │   └── data_loader.py            # cached duckdb reads
│   └── styles/
│       └── theme.css
├── tests/
│   ├── conftest.py
│   ├── test_ingestion.py
│   ├── test_preprocessing.py
│   ├── test_validation.py
│   ├── test_transformation.py
│   ├── test_analytics.py
│   └── test_end_to_end_reconciliation.py
├── outputs/                          # generated; gitignored
│   ├── curated.duckdb
│   ├── exceptions.csv
│   ├── data_quality_report.md
│   └── business_answers.md
├── README.md
├── AI_USAGE.md
├── APPROACH.md
├── requirements.txt
├── pyproject.toml                    # ruff/black/pytest config
├── Makefile
└── .gitignore
```

---

## Phase 0 — Project Scaffolding

### 0.1 Create the folder skeleton
**File(s)**: directories only.
**Prompt to Agent**:
> Create the following empty directories under the workspace root: `src/{config,database,ingestion,preprocessing,validation,validation/checks,transformation,analytics,reporting}`, `sql/{ddl,transformations,analytics}`, `app/{pages,components,services,styles}`, `tests/`, `outputs/`. Add an empty `__init__.py` to every Python package directory under `src/`, `src/validation/checks/`, `app/components/`, `app/services/`, and `tests/`. Do not create any other files yet.

### 0.2 Create `requirements.txt`
**File**: `requirements.txt`
**Prompt to Agent**:
> Create `requirements.txt` with pinned compatible versions: `duckdb>=1.1,<2`, `pandas>=2.2,<3`, `pyarrow>=16`, `python-dateutil>=2.9`, `email-validator>=2.2`, `streamlit>=1.36`, `altair>=5.3`, `pytest>=8`, `ruff>=0.6`, `black>=24.8`. Add a one-line top comment explaining this is a local-only pipeline with no cloud deps.

### 0.3 Create `pyproject.toml` with ruff/black/pytest config
**File**: `pyproject.toml`
**Prompt to Agent**:
> Create a minimal `pyproject.toml` containing only tool configuration (no build system). Configure `[tool.black]` with `line-length = 100`, `[tool.ruff]` with `line-length = 100` and rule selection `E, F, I, B, UP`, and `[tool.pytest.ini_options]` with `testpaths = ["tests"]`, `addopts = "-q"`.

### 0.4 Create `.gitignore`
**File**: `.gitignore`
**Prompt to Agent**:
> Create `.gitignore` covering: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `.DS_Store`, `outputs/curated.duckdb`, `outputs/*.csv` (except `outputs/.gitkeep`), `.venv/`, `*.egg-info/`. Also add `outputs/.gitkeep` (empty file).

### 0.5 Create `Makefile`
**File**: `Makefile`
**Prompt to Agent**:
> Create a `Makefile` with these targets, each a single shell line: `setup` (`pip install -r requirements.txt`), `pipeline` (`python -m src.pipeline`), `app` (`streamlit run app/Home.py`), `test` (`pytest`), `lint` (`ruff check src tests app && black --check src tests app`), `format` (`black src tests app && ruff check --fix src tests app`), `clean` (`rm -f outputs/curated.duckdb outputs/*.csv outputs/*.md`). Add a `.PHONY` line listing all targets.

---

## Phase 1 — Configuration & Schemas

### 1.1 `src/config/settings.py`
**Prompt to Agent**:
> Create `src/config/settings.py`. Define module-level constants computed from `pathlib.Path(__file__).resolve().parents[2]` so paths work regardless of cwd: `PROJECT_ROOT`, `INPUT_DIR = PROJECT_ROOT / "input_data"`, `OUTPUT_DIR = PROJECT_ROOT / "outputs"`, `SQL_DIR = PROJECT_ROOT / "sql"`, `DUCKDB_PATH = OUTPUT_DIR / "curated.duckdb"`, `EXCEPTIONS_CSV = OUTPUT_DIR / "exceptions.csv"`, `DQ_REPORT_MD = OUTPUT_DIR / "data_quality_report.md"`, `ANSWERS_MD = OUTPUT_DIR / "business_answers.md"`. Add a helper `ensure_output_dir()` that creates `OUTPUT_DIR` if missing. Do not import pandas or duckdb in this file.

### 1.2 `src/config/schemas.py`
**Prompt to Agent**:
> Create `src/config/schemas.py`. Export three dicts mapping each raw filename to its expected pandas dtypes-on-read: `RAW_CUSTOMERS_DTYPES`, `RAW_PRODUCTS_DTYPES`, `RAW_ORDERS_DTYPES`, `RAW_PAYMENTS_DTYPES`. All ID/text fields use `"string"`. Numeric fields stay as `"string"` on read (we cast in preprocessing to surface bad values explicitly). Also export `RAW_TABLE_NAMES = ["raw_customers", "raw_products", "raw_orders", "raw_payments", "raw_support_tickets"]` and `CURATED_TABLE_NAMES = ["dim_customer", "dim_product", "fact_order", "fact_payment", "fact_customer_issue", "dq_exception_report"]`.

### 1.3 `src/config/mappings.py`
**Prompt to Agent**:
> Create `src/config/mappings.py`. Export `COUNTRY_MAP: dict[str, str]` mapping every casing/variant in the data (`"USA"`, `"US"`, `"United States"`, `"usa"`, `"us"`, `"united states"`) to canonical `"USA"`. Export `STATE_NAME_TO_CODE: dict[str, str]` mapping full state names (lowercase keys: `"illinois"`, `"california"`, `"new york"`, `"texas"`, `"massachusetts"`, `"washington"`, `"florida"`) to two-letter codes. Add `VALID_STATE_CODES: set[str]` with all 50 US state abbreviations + DC. No functions, only constants. Add a one-line module docstring describing intent.

---

## Phase 2 — Database Layer & DDL

### 2.1 `src/database/connection.py`
**Prompt to Agent**:
> Create `src/database/connection.py`. Implement `@contextmanager def duckdb_connection(read_only: bool = False) -> Iterator[duckdb.DuckDBPyConnection]:` that calls `settings.ensure_output_dir()`, opens `duckdb.connect(str(DUCKDB_PATH), read_only=read_only)`, yields the connection, and always closes in `finally`. Also implement `def reset_database() -> None:` that deletes `DUCKDB_PATH` if it exists. Import only `duckdb`, `contextlib`, `pathlib`, and `src.config.settings`.

### 2.2 `sql/ddl/001_raw_tables.sql`
**Prompt to Agent**:
> Create `sql/ddl/001_raw_tables.sql`. Write `CREATE OR REPLACE TABLE` statements for `raw_customers`, `raw_products`, `raw_orders`, `raw_payments`, `raw_support_tickets`. Every column is `VARCHAR`. Column names exactly match the source columns (look at `input_data/*.csv` and `support_tickets.jsonl`). Separate each table with a blank line and a `-- ===== <table> =====` header comment. Do not create indexes.

### 2.3 `sql/ddl/002_curated_tables.sql`
**Prompt to Agent**:
> Create `sql/ddl/002_curated_tables.sql`. Define `CREATE OR REPLACE TABLE` statements for the six curated tables per the spec in `Take-home-exercise_v1.md` section 6: `dim_customer`, `dim_product`, `fact_order`, `fact_payment`, `fact_customer_issue`, `dq_exception_report`. Use `VARCHAR` for keys, `DATE` for date columns, `TIMESTAMP` for ts columns, `DECIMAL(12,2)` for money, `INTEGER` for quantities, `BOOLEAN` for `active_flag` and `duplicate_resolution_flag`. `dq_exception_report` columns: `rule_id VARCHAR, dataset VARCHAR, record_key VARCHAR, severity VARCHAR, issue_description VARCHAR, suggested_action VARCHAR, detected_at TIMESTAMP`. No FKs (DuckDB enforces only via our pipeline). Do not insert data.

### 2.4 `src/database/ddl.py`
**Prompt to Agent**:
> Create `src/database/ddl.py`. Implement `def execute_sql_file(con, path: Path) -> None:` that reads the file text and calls `con.execute(text)` (DuckDB supports multi-statement). Implement `def create_raw_tables(con) -> None:` and `def create_curated_tables(con) -> None:` that call `execute_sql_file` with the right paths from `settings.SQL_DIR`. Add one-line docstrings only.

### 2.5 Tests for database layer
**File**: `tests/test_database.py`
**Prompt to Agent**:
> Create `tests/test_database.py`. Write `test_connection_creates_file_and_closes` using a `tmp_path` monkeypatch over `settings.DUCKDB_PATH` to ensure the file is created and the context manager closes. Write `test_create_raw_and_curated_tables` that runs both DDL functions then asserts `con.execute("SHOW TABLES").fetchall()` returns the expected 11 table names (5 raw + 6 curated).

---

## Phase 3 — Ingestion (raw layer)

### 3.1 `src/ingestion/csv_loader.py`
**Prompt to Agent**:
> Create `src/ingestion/csv_loader.py`. Implement `def load_csv(path: Path, dtypes: dict[str, str]) -> pd.DataFrame:` that reads the CSV with `pandas.read_csv(path, dtype=dtypes, keep_default_na=False, na_values=[""])`. Implement `def insert_dataframe(con, table_name: str, df: pd.DataFrame) -> int:` that registers the dataframe as a temp view and runs `INSERT INTO {table_name} SELECT * FROM df_view`, then returns the number of rows inserted (`con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]`). Use a parameterized table name only via an allow-list check against `RAW_TABLE_NAMES` to avoid injection.

### 3.2 `src/ingestion/jsonl_loader.py`
**Prompt to Agent**:
> Create `src/ingestion/jsonl_loader.py`. Implement `def load_jsonl(path: Path) -> pd.DataFrame:` that reads `support_tickets.jsonl` line by line, json-parses each, and returns a DataFrame with columns `["ticket_id","customer_id","created_ts","channel","category","sentiment","description"]` all as `string` dtype. Missing keys produce `pd.NA`. Do not attempt to parse `created_ts` here.

### 3.3 `src/ingestion/loaders.py` orchestrator
**Prompt to Agent**:
> Create `src/ingestion/loaders.py`. Implement `def load_all(con) -> dict[str, int]:` that calls the DDL to create raw tables, loads each of the five raw files into the matching `raw_*` table using the loaders above, and returns a dict like `{"raw_customers": 21, "raw_products": 12, ...}`. Truncate each raw table before insert (`DELETE FROM raw_*`) so the function is idempotent. Print a single-line summary per table.

### 3.4 Tests for ingestion
**File**: `tests/test_ingestion.py`
**Prompt to Agent**:
> In `tests/test_ingestion.py` add `test_load_all_row_counts` that runs `load_all` against a temp DuckDB and asserts exact raw row counts: customers=20, products=12, orders=31, payments=30, support_tickets=10 (total 103). Add `test_load_all_is_idempotent` that runs `load_all` twice and asserts counts do not double. Add `test_jsonl_preserves_bad_timestamp` asserting ticket `T010` has `created_ts == "bad_timestamp"` in raw.

---

## Phase 4 — Preprocessing (pure functions, raw → stg)

Each module here is a **pure function over a DataFrame**. No DB writes, no side effects.

### 4.1 `src/preprocessing/timestamp_parser.py`
**Prompt to Agent**:
> Create `src/preprocessing/timestamp_parser.py`. Implement `def parse_timestamp(value: str | None) -> tuple[pd.Timestamp | pd.NaT, bool]:` that tries (in order) ISO 8601, `"%Y-%m-%d %H:%M:%S"`, `"%Y-%m-%d %H:%M"`, `"%Y-%m-%dT%H:%M:%SZ"`, `"%m/%d/%Y %H:%M"`, `"%Y/%m/%d %H:%M"`, `"%m-%d-%Y %H:%M"`, `"%Y-%m-%d"`, `"%m/%d/%Y"`, `"%Y/%m/%d"`, `"%m-%d-%Y"`; returns `(Timestamp, True)` on success, `(pd.NaT, False)` on failure. Use `dateutil.parser.parse` as final fallback. Implement `def parse_series(series: pd.Series) -> tuple[pd.Series, pd.Series]:` returning parsed Timestamp series and a boolean `valid` mask. No regex try/except chains that hide errors — return `False` explicitly.

### 4.2 Tests for timestamp parser
**Prompt to Agent**:
> Add to `tests/test_preprocessing.py`: `test_parse_timestamp_handles_each_known_format` parameterized over every example in `orders.csv` and `support_tickets.jsonl`: `"2025-03-01 10:15:00"`, `"03/02/2025 14:20"`, `"2025/03/03 09:00"`, `"2025-03-05T16:45:00Z"`, `"05-06-2025 16:30"`, `"2025-03-02T11:00:00"` — each must return `valid=True`. `test_parse_timestamp_returns_false_for_bad_timestamp` asserts `"bad_timestamp"` returns `(NaT, False)`.

### 4.3 `src/preprocessing/geography_standardizer.py`
**Prompt to Agent**:
> Create `src/preprocessing/geography_standardizer.py`. Implement `def standardize_country(value: str | None) -> str | None:` using `COUNTRY_MAP` (case-insensitive lookup); returns `None` if input is None/empty, else the canonical value or the raw input if no mapping. Implement `def standardize_state(value: str | None) -> str | None:` that uppercases two-letter inputs already in `VALID_STATE_CODES`, otherwise maps full names via `STATE_NAME_TO_CODE`, otherwise returns the original. Implement `def standardize_geo_columns(df: pd.DataFrame, country_col: str, state_col: str) -> pd.DataFrame:` returning a new dataframe with the two columns replaced.

### 4.4 Tests for geography
**Prompt to Agent**:
> In `tests/test_preprocessing.py` add `test_country_variants_all_map_to_USA` parameterized over `["USA","US","United States","united states","us"]`. Add `test_state_full_name_maps_to_code` parameterized over `[("Illinois","IL"),("New York","NY"),("Texas","TX"),("Florida","FL"),("California","CA"),("Massachusetts","MA"),("Washington","WA")]`. Add `test_state_already_code_is_uppercased` for `"il"` → `"IL"`.

### 4.5 `src/preprocessing/email_normalizer.py`
**Prompt to Agent**:
> Create `src/preprocessing/email_normalizer.py`. Implement `def normalize_email(value: str | None) -> str | None:` that lowercases and strips whitespace, returns `None` for empty. Implement `def is_valid_email(value: str | None) -> bool:` using `email_validator.validate_email(value, check_deliverability=False)`; return `False` on any exception or empty input.

### 4.6 `src/preprocessing/type_coercion.py`
**Prompt to Agent**:
> Create `src/preprocessing/type_coercion.py`. Implement `def to_decimal(value, default=None) -> Decimal | None:` and `def to_int(value, default=None) -> int | None:` that safely coerce and return `default` on failure (no exception). Implement `def coerce_orders(df: pd.DataFrame) -> pd.DataFrame:` casting `quantity` to nullable Int64 and `order_total` to float (we'll use Decimal only at validation/reporting boundary to keep pandas math fast). Same idea for `def coerce_payments(df)` (`amount` to float) and `def coerce_products(df)` (`unit_price` to float, `active_flag` to boolean from `Y`/`N`).

### 4.7 `src/preprocessing/deduplication.py`
**Prompt to Agent**:
> Create `src/preprocessing/deduplication.py`. Implement `def resolve_customer_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:` returning `(resolved_df, duplicates_df)`. Strategy: group by `customer_id`; if multiple rows, keep the row with the most non-null fields, tie-break by latest `signup_date`. Additionally, detect **soft duplicates** across distinct `customer_id` rows where the combination `(lower(first_name), lower(last_name), phone)` matches another row — mark the later `signup_date` row as a soft duplicate via `duplicate_resolution_flag = True` (but keep it in `resolved_df`). The `duplicates_df` contains hard duplicates that were dropped, with columns `[customer_id, reason]`. Implement `def deduplicate_orders(df) -> tuple[pd.DataFrame, pd.DataFrame]:` dropping exact duplicate `order_id` rows; the dropped rows go to the second return value.

### 4.8 Tests for deduplication
**Prompt to Agent**:
> In `tests/test_preprocessing.py` add fixtures using the real `customers.csv` data. Test `test_customer_dedup_drops_exact_duplicate_C006` (two C006 rows in input, expect 1 in resolved + 1 in duplicates_df). Test `test_customer_dedup_flags_C019_as_soft_duplicate_of_C001` (same phone `312-555-0101`, same name `Ava Patel`; both remain, C019 has `duplicate_resolution_flag=True`). Test `test_order_dedup_drops_O1018_duplicate` (orders.csv has O1018 twice, expect 1 row in resolved, 1 in duplicates_df).

---

## Phase 5 — Validation (Data Quality)

Each DQ rule is a **single file** exposing `def check(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:` returning rows shaped like `dq_exception_report`. The runner concatenates all results.

### 5.1 `src/validation/rule_registry.py`
**Prompt to Agent**:
> Create `src/validation/rule_registry.py`. Define `@dataclass(frozen=True) class DQRule: rule_id: str; dataset: str; description: str; severity: str; suggested_action: str`. Read `input_data/data_quality_rules.csv` at import time, build `REGISTRY: dict[str, DQRule]` keyed by `rule_id`. Define a `suggested_action` per rule (hard-coded, business-sensible: e.g. for DQ001 `"Merge duplicate customer profiles"`, for DQ010 `"Reconcile payment vs order total with billing team"`). Expose `def get(rule_id: str) -> DQRule`.

### 5.2 Helper: `src/validation/_helpers.py`
**Prompt to Agent**:
> Create `src/validation/_helpers.py`. Implement `def make_exception_rows(rule_id: str, dataset: str, record_keys: Iterable[str], issue_template: str, *, fields: dict[str, Iterable] | None = None) -> pd.DataFrame:` that builds a DataFrame matching the `dq_exception_report` schema, pulling severity/suggested_action from the registry, with `detected_at = pd.Timestamp.utcnow()`. `issue_template` is a Python format string that can reference `record_key` and any `fields`.

### 5.3 `src/validation/checks/dq001_customer_unique.py`
**Prompt to Agent**:
> Create the file. Implement `def check(stg) -> pd.DataFrame:`. After preprocessing, `stg["customers_duplicates"]` already holds hard duplicates; emit one exception row per dropped duplicate `customer_id` with `issue_description = "Duplicate customer_id detected and resolved"`.

### 5.4 `src/validation/checks/dq002_email_present_valid.py`
**Prompt to Agent**:
> Implement `check(stg)` against `stg["customers"]`. Two sub-cases: missing email (issue `"Email is missing"`), invalid email syntax (issue `"Email failed syntactic validation"`). Use `is_valid_email`. Severity from registry. Record key = `customer_id`.

### 5.5 `src/validation/checks/dq003_geo_standardized.py`
**Prompt to Agent**:
> Implement `check(stg)`. Compare each row's original country/state (preserved as `country_raw`, `state_raw` columns added in preprocessing) to the standardized values. Emit an exception when the standardized state is not in `VALID_STATE_CODES` or the country is not `"USA"`. Issue text `"Country/state could not be standardized: country={country_raw}, state={state_raw}"`.

### 5.6 `src/validation/checks/dq004_order_unique.py`
**Prompt to Agent**:
> Implement `check(stg)`. Uses `stg["orders_duplicates"]` from preprocessing. Emit one exception per dropped duplicate `order_id`. Issue `"Duplicate order_id detected"`.

### 5.7 `src/validation/checks/dq005_order_customer_fk.py`
**Prompt to Agent**:
> Implement `check(stg)`. Left-anti join `stg["orders"]` against `stg["customers"]` on `customer_id`. Emit exception per offending order with issue `"customer_id={customer_id} not found in dim_customer"`.

### 5.8 `src/validation/checks/dq006_order_product_fk.py`
**Prompt to Agent**:
> Same pattern as DQ005 against `stg["products"]` on `product_id`. Issue `"product_id={product_id} not found in dim_product"`.

### 5.9 `src/validation/checks/dq007_completed_positive_qty.py`
**Prompt to Agent**:
> Implement `check(stg)`. Filter `stg["orders"]` where `order_status == "completed"` and `quantity <= 0`. Issue `"Completed order has non-positive quantity: {quantity}"`.

### 5.10 `src/validation/checks/dq008_order_total_matches.py`
**Prompt to Agent**:
> Implement `check(stg)`. Join `stg["orders"]` to `stg["products"]` on `product_id`. Compute `calculated = quantity * unit_price`. Emit exception when `abs(order_total - calculated) > 0.01` AND product is valid. Issue `"order_total={order_total} vs quantity*unit_price={calculated} (diff={diff})"`. Include `calculated` and `diff` in fields.

### 5.11 `src/validation/checks/dq009_payment_order_fk.py`
**Prompt to Agent**:
> Implement `check(stg)`. Left-anti join `stg["payments"]` against `stg["orders"]` (post-dedup) on `order_id`. Issue `"Orphan payment for order_id={order_id}"`.

### 5.12 `src/validation/checks/dq010_payment_matches_completed.py`
**Prompt to Agent**:
> Implement `check(stg)`. Join settled payments (`payment_status == "settled"`) to completed orders (`order_status == "completed"`) on `order_id`. Emit exception when `abs(amount - order_total) > 0.01`. Issue `"Settled payment {amount} != completed order total {order_total} (diff={diff})"`.

### 5.13 `src/validation/checks/dq011_ticket_timestamp_parses.py`
**Prompt to Agent**:
> Implement `check(stg)`. From `stg["support_tickets"]`, find rows where `created_ts_valid == False`. Issue `"created_ts failed to parse: {created_ts_raw}"`.

### 5.14 `src/validation/checks/dq012_ticket_customer_fk.py`
**Prompt to Agent**:
> Implement `check(stg)`. Left-anti join tickets to `stg["customers"]` on `customer_id`. Issue `"customer_id={customer_id} not found in dim_customer"`.

### 5.15 `src/validation/runner.py`
**Prompt to Agent**:
> Create `src/validation/runner.py`. Discover all modules in `src.validation.checks` via `pkgutil.iter_modules`, import each, call `check(stg)`, concat results. Implement `def apply_all(stg: dict[str, pd.DataFrame]) -> pd.DataFrame:` returning a single dataframe shaped like `dq_exception_report`. Sort by `severity` (`High`>`Medium`>`Low`) then `rule_id`. Print a one-line per-rule violation count.

### 5.16 `src/validation/exception_writer.py`
**Prompt to Agent**:
> Create `src/validation/exception_writer.py`. Implement `def persist_exceptions(con, exceptions_df: pd.DataFrame) -> None:` that truncates `dq_exception_report` then inserts the dataframe, and `def write_exceptions_csv(exceptions_df) -> Path:` writing to `settings.EXCEPTIONS_CSV` (returns the path). Both must be idempotent.

### 5.17 Tests for validation
**Prompt to Agent**:
> In `tests/test_validation.py`: for each DQ rule, build a tiny fixture `stg` dict containing only the minimum rows needed to trigger / not trigger the rule, and assert the resulting exception count and `record_key` set. Required cases (every must be present):
> - DQ001: C006 duplicate
> - DQ002: C004 missing email
> - DQ004: O1018 duplicate
> - DQ005: O1019 references C999
> - DQ006: O1020 references P999
> - DQ007: O1030 has quantity -1
> - DQ008: O1021 total 50 vs 4×11=44 (diff 6)
> - DQ009: PMT029 → O9999 orphan
> - DQ010: PMT021 amount 44 vs order total 50 (diff 6)
> - DQ011: T010 bad_timestamp
> - DQ012: T005 → C999
>
> Then `test_apply_all_total_violations_count` running on the full real dataset and asserting an exact number (compute it once locally and lock the assertion).

---

## Phase 6 — Transformation (stg → dim/fact)

Each transformation is a **Python function that returns a DataFrame**, plus a parallel **SQL file** for documentation/portability. Python is the source of truth for runtime; SQL files are persisted to `sql/transformations/` for reviewers.

### 6.1 `src/transformation/dim_customer.py`
**Prompt to Agent**:
> Create `src/transformation/dim_customer.py`. Implement `def build(stg) -> pd.DataFrame:` producing columns: `customer_key` (= resolved `customer_id`), `full_name` (concat), `email` (normalized), `phone`, `standard_country`, `standard_state`, `signup_date` (parsed via timestamp parser then `.dt.date`), `loyalty_tier`, `duplicate_resolution_flag` (bool). Drop hard duplicates already handled in preprocessing. Sort by `customer_key`.

### 6.2 `src/transformation/dim_product.py`
**Prompt to Agent**:
> Implement `build(stg)` returning `product_key, product_name, category, unit_price (DECIMAL via float→round 2), active_flag (bool)`. Sort by `product_key`.

### 6.3 `src/transformation/fact_order.py`
**Prompt to Agent**:
> Implement `build(stg, dim_product) -> pd.DataFrame:`. Columns: `order_key (=order_id)`, `customer_key`, `product_key`, `order_date` (parsed `order_ts` to date), `quantity`, `order_status`, `shipping_state` (standardized via geography_standardizer), `gross_order_amount` (= source `order_total`), `calculated_order_amount` (= `quantity * dim_product.unit_price`, NULL when product invalid), `order_amount_variance` (= `gross - calculated`, NULL when invalid). Drop rows present in `stg["orders_duplicates"]`. Keep rows with invalid FKs (so they appear in exceptions report joined view) — set the FK to original value, do NOT null it; downstream queries filter via DQ exceptions table.

### 6.4 `src/transformation/fact_payment.py`
**Prompt to Agent**:
> Implement `build(stg) -> pd.DataFrame:`. Columns: `payment_key, order_key, payment_date (parsed payment_ts to date), payment_method, payment_status, payment_amount`. Keep orphan payments; they show up in exceptions and Q3.

### 6.5 `src/transformation/fact_customer_issue.py`
**Prompt to Agent**:
> Implement `build(stg) -> pd.DataFrame:`. Columns: `ticket_id, customer_key, created_date (parsed; NULL when invalid), channel, issue_category, sentiment, description`. Keep rows even when created_ts is bad or customer_id is unknown (they appear in DQ011/DQ012 exceptions).

### 6.6 `src/transformation/persist.py`
**Prompt to Agent**:
> Create `src/transformation/persist.py`. Implement `def persist_curated(con, frames: dict[str, pd.DataFrame]) -> None:` that for each curated table in `CURATED_TABLE_NAMES` (excluding `dq_exception_report`), truncates and inserts the matching dataframe from `frames`. Use the same parameterized allow-list pattern as `csv_loader`.

### 6.7 SQL companions (documentation)
**Prompt to Agent**:
> Create `sql/transformations/{010_dim_customer,020_dim_product,030_fact_order,040_fact_payment,050_fact_customer_issue}.sql`. Each file contains a `-- Equivalent SQL for documentation; runtime uses Python in src/transformation/*` header comment, followed by a `CREATE OR REPLACE VIEW v_<name> AS SELECT ...` statement reading from `raw_*` tables that re-implements the Python transformation as closely as possible. These views are not used by the pipeline; they prove the logic is expressible in SQL.

### 6.8 Tests for transformation
**Prompt to Agent**:
> In `tests/test_transformation.py`: `test_dim_customer_row_count` after dedup = 19 (20 raw − 1 hard duplicate C006; the soft duplicate C019 is kept with `duplicate_resolution_flag=True`). `test_fact_order_row_count` = 30 (31 raw − 1 hard duplicate O1018). `test_fact_order_order_amount_variance_for_O1021` equals 6.00. `test_fact_order_keeps_invalid_fk_rows` (O1019, O1020 present in fact_order). `test_fact_payment_keeps_orphan_PMT029`. `test_fact_customer_issue_T010_created_date_is_null`. `test_dim_product_active_flag_for_P011_is_false`.

---

## Phase 7 — Analytics (Business Questions)

Each analytic is a SQL file + a thin Python wrapper that runs the SQL and returns a DataFrame.

### 7.1 `sql/analytics/q1_revenue_by_month.sql`
**Prompt to Agent**:
> Create the SQL: `SELECT date_trunc('month', order_date) AS month, ROUND(SUM(gross_order_amount), 2) AS completed_revenue, COUNT(*) AS completed_orders FROM fact_order WHERE order_status = 'completed' GROUP BY 1 ORDER BY 1;`. Add a header comment stating it answers Q1 and notes that `gross_order_amount` is the source-of-truth revenue per business rule (we surface variance separately).

### 7.2 `src/analytics/q1_revenue_by_month.py`
**Prompt to Agent**:
> Implement `def run(con) -> pd.DataFrame:` that reads the SQL file content and runs `con.execute(sql).df()`. Add `def describe() -> str:` returning a 1-2 sentence business summary string used in reports/UI.

### 7.3 `sql/analytics/q2_top_customers.sql`
**Prompt to Agent**:
> `SELECT c.customer_key, c.full_name, c.standard_state, ROUND(SUM(o.gross_order_amount), 2) AS completed_value, COUNT(*) AS completed_orders FROM fact_order o JOIN dim_customer c USING (customer_key) WHERE o.order_status = 'completed' GROUP BY 1,2,3 ORDER BY completed_value DESC LIMIT 10;`. Header comment notes invalid-FK orders are excluded by the inner join.

### 7.4 `src/analytics/q2_top_customers.py`
**Prompt to Agent**: mirror 7.2.

### 7.5 `sql/analytics/q3_order_exceptions.sql`
**Prompt to Agent**:
> Build a unified view: `WITH all_ex AS (SELECT order_key, rule_id, severity, issue_description FROM (SELECT record_key AS order_key, rule_id, severity, issue_description FROM dq_exception_report WHERE dataset IN ('orders','payments'))) SELECT o.order_key, o.customer_key, o.product_key, o.order_status, o.quantity, o.gross_order_amount, o.calculated_order_amount, o.order_amount_variance, LIST(DISTINCT rule_id) AS triggered_rules, LIST(DISTINCT issue_description) AS issues FROM fact_order o LEFT JOIN all_ex e ON e.order_key = o.order_key GROUP BY 1,2,3,4,5,6,7,8 HAVING triggered_rules IS NOT NULL AND len(triggered_rules) > 0 ORDER BY o.order_key;` Header comment ties to Q3.

### 7.6 `src/analytics/q3_order_exceptions.py`
**Prompt to Agent**: mirror 7.2 plus add a `def summary(con) -> dict:` returning counts per rule.

### 7.7 `sql/analytics/q4_revenue_by_state.sql`
**Prompt to Agent**:
> `SELECT shipping_state AS state, ROUND(SUM(gross_order_amount), 2) AS completed_revenue, COUNT(*) AS completed_orders FROM fact_order WHERE order_status = 'completed' AND shipping_state IS NOT NULL GROUP BY 1 ORDER BY completed_revenue DESC;`. Header comment notes states are standardized 2-letter codes.

### 7.8 `src/analytics/q4_revenue_by_state.py`
**Prompt to Agent**: mirror 7.2.

### 7.9 `sql/analytics/q5_sentiment_link.sql`
**Prompt to Agent**:
> Compute the cross-tab: customers who had at least one **negative** ticket vs customers who did not, against the number of order/payment exceptions per customer. Output two rows: `cohort = 'has_negative_ticket'` and `cohort = 'no_negative_ticket'` with `customer_count`, `total_orders`, `orders_with_exception`, `pct_orders_with_exception`. Use `fact_order`, `fact_customer_issue`, and `dq_exception_report` filtered to `dataset IN ('orders','payments')`. Round percentages to 2 decimals.

### 7.10 `src/analytics/q5_sentiment_link.py`
**Prompt to Agent**: mirror 7.2 plus add `def per_customer_detail(con) -> pd.DataFrame:` returning the underlying per-customer breakdown (used for the UI drill-down table).

### 7.11 Tests for analytics
**Prompt to Agent**:
> In `tests/test_analytics.py` run each Q against a fully-populated test DuckDB and assert:
> - Q1: number of months ≥ 3 and total completed revenue equals SUM of completed orders' gross_order_amount (recompute in pandas for parity).
> - Q2: returns exactly 10 rows (or fewer if dataset is small — for our data assert `<= 10` and the first row's customer is the one with highest completed sum, computed independently in pandas).
> - Q3: includes order_keys O1018 (dup), O1019 (bad customer fk), O1020 (bad product fk), O1021 (total mismatch), O1030 (neg qty + neg total).
> - Q4: top state matches a pandas groupby check.
> - Q5: percentage for negative-ticket cohort > percentage for no-negative cohort (or assert the exact computed values).

---

## Phase 8 — Reporting (markdown artifacts)

### 8.1 `src/reporting/dq_report.py`
**Prompt to Agent**:
> Create `src/reporting/dq_report.py`. Implement `def render(con) -> str:` that builds a markdown report with: H1 title, H2 "Summary" with total exceptions / unique rules triggered / severity breakdown, H2 "By Rule" with a table of rule_id, description, severity, violations, then H2 "Sample records" showing up to 5 rows per rule. Implement `def write(con) -> Path:` writing the result to `settings.DQ_REPORT_MD`.

### 8.2 `src/reporting/business_answers.py`
**Prompt to Agent**:
> Implement `def render(con) -> str:` producing a markdown doc with one section per business question (Q1..Q5), each containing the SQL used (read from `sql/analytics/*.sql`), the result as a markdown table (pandas `to_markdown(index=False)`), and a one-paragraph plain-English finding generated from the result data (computed deterministically, not LLM-written — e.g., "Top revenue state is TX with $X"). Implement `def write(con) -> Path:` writing to `settings.ANSWERS_MD`.

---

## Phase 9 — Pipeline Orchestrator

### 9.1 `src/pipeline.py`
**Prompt to Agent**:
> Create `src/pipeline.py`. Implement `def run() -> None:` performing the following ordered phases, each wrapped in `print("[phase X] ...")` markers:
> 1. `reset_database()` then open connection in write mode
> 2. `create_raw_tables` / `create_curated_tables`
> 3. `ingestion.load_all(con)`
> 4. Read raw tables into pandas; run preprocessing → assemble `stg` dict containing `customers`, `customers_duplicates`, `products`, `orders`, `orders_duplicates`, `payments`, `support_tickets` with all parsed fields and raw fields preserved.
> 5. `validation.runner.apply_all(stg)` → exceptions df → persist to DB + CSV
> 6. `transformation.*.build(...)` → assemble `frames` dict → `persist_curated`
> 7. `reporting.dq_report.write(con)` and `reporting.business_answers.write(con)`
> 8. Print final summary table (rows per curated table).
> Add `if __name__ == "__main__": run()`. Total runtime target < 5 seconds on this dataset.

### 9.2 End-to-end reconciliation test
**File**: `tests/test_end_to_end_reconciliation.py`
**Prompt to Agent**:
> Write a single test `test_full_pipeline_reconciles` that calls `pipeline.run()` against a tmp DuckDB (monkeypatch `settings.DUCKDB_PATH`) and then asserts: total raw rows ingested = 103; `dim_customer` row count matches expected; SUM(fact_order.gross_order_amount WHERE status='completed') equals an independently computed pandas sum from `orders.csv`; SUM(fact_payment.payment_amount WHERE status='settled') equals an independently computed pandas sum from `payments.csv`; `dq_exception_report` is non-empty; `outputs/exceptions.csv`, `outputs/data_quality_report.md`, `outputs/business_answers.md` all exist and are non-empty.

---

## Phase 10 — Streamlit Application

### 10.1 `app/styles/theme.css`
**Prompt to Agent**:
> Create `app/styles/theme.css` with a minimalist business-admin look: neutral palette (background `#FAFAFA`, surface `#FFFFFF`, text `#111827`, muted `#6B7280`, accent `#2563EB`), system font stack, 16px base, 24px section padding, subtle `1px solid #E5E7EB` card borders, no shadows on top-level surfaces. Override Streamlit defaults: hide hamburger and "Made with Streamlit", widen content to 1200px max, increase header weight to 600, set sidebar background to `#F3F4F6`. Provide `.kpi-card`, `.kpi-label`, `.kpi-value`, `.section-title` utility classes.

### 10.2 `app/components/header.py`
**Prompt to Agent**:
> Create `app/components/header.py`. Implement `def render(title: str, subtitle: str | None = None) -> None:` that injects the CSS file once (using `st.markdown(..., unsafe_allow_html=True)` with `<style>` block), renders the page title (H1 with brand mark "OmniRetail · Data Platform") and a subtitle line. Use `st.session_state` to ensure the CSS is injected only once per session.

### 10.3 `app/components/kpi_card.py`
**Prompt to Agent**:
> Implement `def render(label: str, value: str, help_text: str | None = None) -> None:` outputting a small div with `kpi-label` and `kpi-value` classes (via `st.markdown` with `unsafe_allow_html=True`). Also implement `def grid(items: list[tuple[str,str]]) -> None:` that lays out KPI cards in a row using `st.columns(len(items))`.

### 10.4 `app/components/data_table.py`
**Prompt to Agent**:
> Implement `def render(df: pd.DataFrame, *, height: int = 420, downloadable: bool = True, filename: str = "data.csv") -> None:` using `st.dataframe(df, use_container_width=True, height=height, hide_index=True)`, optionally followed by `st.download_button` exporting to CSV.

### 10.5 `app/services/data_loader.py`
**Prompt to Agent**:
> Create `app/services/data_loader.py`. Implement `@st.cache_resource def get_con()` returning a read-only DuckDB connection. Implement `@st.cache_data(ttl=60) def query(sql: str) -> pd.DataFrame:` running `get_con().execute(sql).df()`. Implement convenience wrappers `def list_tables()`, `def table_preview(name: str, limit: int = 100)`, `def kpi_metrics() -> dict[str, str]` returning total customers / total completed revenue / total exceptions / pipeline last-run timestamp (from the file mtime of `DUCKDB_PATH`). Always guard with `if not DUCKDB_PATH.exists(): st.warning("Pipeline has not been run yet — run `make pipeline`."); st.stop()`.

### 10.6 `app/Home.py`
**Prompt to Agent**:
> Create `app/Home.py`. Set page config (`st.set_page_config(page_title="OmniRetail Data Platform", layout="wide", initial_sidebar_state="expanded")`). Render header via `components.header.render("Home", "Customer-360 & Order Reconciliation Overview")`. Show a KPI row (use `kpi_card.grid`): Total Customers, Completed Revenue (USD), Total DQ Exceptions, Last Pipeline Run. Below, render a two-column layout: left = a short narrative of the project and the data sources (read from `business_context.md`), right = quick-link buttons to the three sub-pages using `st.page_link("pages/1_Data_Quality.py", label="Open Data Quality", icon="📊")` (no emoji unless user-permitted — use plain labels). Footer line with build/run instructions.

### 10.7 `app/pages/1_Data_Quality.py`
**Prompt to Agent**:
> Create the page. Render header `"Data Quality"`. KPI row: Total Exceptions, High severity count, Medium count, Unique rules triggered. Show a "Violations by Rule" bar chart using Altair (encode rule_id on Y, count on X, color by severity). Below, a multi-select filter for rule_id and severity, then `data_table.render` over the filtered `dq_exception_report` with a download button. Add an expandable "Rule reference" section listing all rules from `data_quality_rules.csv` with the suggested_action column. All data via `data_loader.query`.

### 10.8 `app/pages/2_Analytics.py`
**Prompt to Agent**:
> Create the page. Render header `"Analytics"`. Use `st.tabs(["Q1 Monthly Revenue","Q2 Top Customers","Q3 Order Exceptions","Q4 Revenue by State","Q5 Sentiment vs Exceptions"])`. Inside each tab:
> - Q1: line chart (month, revenue) + KPI total + data table + expandable SQL.
> - Q2: bar chart top-10 customers + table + SQL.
> - Q3: KPIs (orders with exceptions, distinct rules) + filterable table (by rule_id) + SQL.
> - Q4: bar chart by state + map-free table + SQL.
> - Q5: 2-row summary table + bar chart comparing percentages + drill-down per-customer table + SQL.
> Each tab reads from `data_loader.query` using the SQL files in `sql/analytics/`. Wrap SQL display in `st.expander("Show SQL")` with `st.code(sql, language="sql")`.

### 10.9 `app/pages/3_Curated_Model_Explorer.py`
**Prompt to Agent**:
> Create the page. Render header `"Curated Model Explorer"`. Sidebar select-box listing curated tables (`CURATED_TABLE_NAMES`). Main area: show table row count, column dtypes (`con.execute("DESCRIBE ...").df()`), then a filterable `st.data_editor` (read-only) of the first 1000 rows. Add a "Run custom SQL" expander with a `st.text_area` for ad-hoc SELECT-only queries; reject any input that doesn't start with `select` (case-insensitive) after stripping comments.

### 10.10 Streamlit smoke test
**Prompt to Agent**:
> Add `tests/test_app_imports.py` that imports `app.Home`, `app.pages.1_Data_Quality`, `app.pages.2_Analytics`, `app.pages.3_Curated_Model_Explorer` using `importlib.import_module` with a context that monkeypatches `streamlit` to a no-op stub (so we just assert files parse and top-level code does not error). This catches syntax/import regressions without spinning Streamlit.

---

## Phase 11 — Documentation

### 11.1 `README.md`
**Prompt to Agent**:
> Create `README.md`. Sections (in order): One-paragraph project description, "Quickstart" (Python version, `pip install -r requirements.txt`, `make pipeline`, `make app`, expected runtime), "Repository layout" (mirroring the layout section of this doc), "Architecture" (a mermaid flowchart of `raw → preprocessing → validation → transformation → analytics → reporting → UI`), "Business Questions Answered" (list of Q1-Q5 with one-line answers computed from the latest run — say "See outputs/business_answers.md for live values"), "Data Quality Rules" (table from `data_quality_rules.csv`), "How modules are isolated" (3-bullet contract from section 0 of this doc), "Testing" (`make test`), "Assumptions & Tradeoffs" (link to APPROACH.md). No marketing language.

### 11.2 `APPROACH.md`
**Prompt to Agent**:
> Create `APPROACH.md` covering: (a) why DuckDB, (b) why pandas + SQL hybrid (Python for transformation, SQL for analytics), (c) dedup strategy (hard vs soft duplicates) with specific call-out of C001/C019 soft duplicate, (d) timestamp parser strategy and fallback order, (e) FK handling (we keep invalid-FK rows in facts and rely on DQ tables to surface them), (f) variance handling (we keep `gross_order_amount` from source as revenue per business rule, surface variance separately), (g) "What I'd add next" (incremental ingestion, Great Expectations, dbt-style lineage, Streamlit auth).

### 11.3 `AI_USAGE.md`
**Prompt to Agent**:
> Create `AI_USAGE.md`. Sections: "Tool used" (Cursor + Claude), "How I steered the agent" (link to `PLAN_IMPLEMENTATION_PROMPTS.md` as the master prompt list), "Sample prompts" (paste 3-5 representative prompts from this doc and the iterations that followed), "Agent output I rejected and why" (template — fill during build, e.g. "Agent first suggested storing money as floats; rejected and switched to DECIMAL(12,2) in DDL with float math in pandas only"), "Verification I performed manually" (row counts, reconciliation totals, spot checks of O1021/O1030/PMT029), "What I would improve next time".

---

## Phase 12 — Final QA Pass

### 12.1 Lint + format
**Prompt to Agent**:
> Run `make format` then `make lint`. Fix any remaining ruff errors by hand. Do not silence rules.

### 12.2 Full test suite
**Prompt to Agent**:
> Run `make test`. All tests must pass. If any DQ-related assertion fails because the dataset shifted, investigate before relaxing the assertion — the input file is fixed for this exercise.

### 12.3 Manual reconciliation
**Prompt to Agent**:
> Open `outputs/business_answers.md` and `outputs/exceptions.csv`. Verify by hand: (1) Q1 total completed revenue equals SUM of `order_total` for `order_status='completed'` in `orders.csv` minus the duplicate O1018 row; (2) O1021 appears in DQ008 with diff=6.00 and DQ010 with diff=6.00; (3) O1030 appears in DQ007 (qty -1); (4) PMT029 appears in DQ009; (5) T010 appears in DQ011; (6) Q4 state codes all have length 2 and are in `VALID_STATE_CODES`. Document each spot check in `AI_USAGE.md` under "Verification".

### 12.4 Streamlit walk-through
**Prompt to Agent**:
> Start `make app`. On each page, screenshot one KPI/chart that matches the corresponding value in `outputs/business_answers.md` to confirm UI is reading from the same DuckDB. Save screenshots under `outputs/screenshots/` and reference them from `README.md`.

---

## Execution order summary (the only order that matters)

```
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12
```

Within a phase, steps may be parallelized if their files don't depend on each other (e.g., all DQ rule files in Phase 5 can be authored in parallel after 5.1 and 5.2 exist).
