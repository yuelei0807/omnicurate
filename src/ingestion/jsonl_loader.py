"""Raw-layer JSONL ingestion (support_tickets only).

Reads support_tickets.jsonl line-by-line, parses each line as JSON,
and returns a pandas DataFrame shaped exactly like raw_support_tickets
so it can be inserted via the same insert_dataframe helper used for
the CSVs.

Three design rules:

* Bad values are preserved verbatim. Ticket T010 has
  ``created_ts == "bad_timestamp"`` -- the loader carries that string
  through unchanged so DQ011 can flag it downstream.
* Missing keys become ``pd.NA``, never KeyError. If a future ticket
  omits ``sentiment``, the row still loads.
* The DataFrame is forced into the column order and StringDtype that
  raw_support_tickets expects, so insert_dataframe needs no special
  case for this source.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

# Column order MUST match raw_support_tickets in sql/ddl/001_raw_tables.sql.
_JSONL_COLUMNS: tuple[str, ...] = (
    "ticket_id",
    "customer_id",
    "created_ts",
    "channel",
    "category",
    "sentiment",
    "description",
)


def load_jsonl(path: Path) -> pd.DataFrame:
    """Read a JSONL file into a DataFrame matching raw_support_tickets."""
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            record = json.loads(line)
            rows.append({col: record.get(col, pd.NA) for col in _JSONL_COLUMNS})

    # Column order is implicit: every dict in `rows` is built from
    # _JSONL_COLUMNS in the comprehension above, so pandas infers the
    # columns in that exact order from the dict keys (Python 3.7+).
    df = pd.DataFrame(rows)
    return df.astype({col: "string" for col in _JSONL_COLUMNS})