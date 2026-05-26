"""Curated model explorer — browse tables and run ad-hoc SELECT queries."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

_bootstrap_path = Path(__file__).resolve().parents[1] / "_bootstrap.py"
_spec = importlib.util.spec_from_file_location("app_bootstrap", _bootstrap_path)
if _spec and _spec.loader:
    _bootstrap = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_bootstrap)
    _bootstrap.setup()

import streamlit as st

from app.components import header
from app.services import data_loader

_SELECT_ONLY = re.compile(r"^\s*select\b", re.IGNORECASE | re.DOTALL)


def _strip_sql_comments(sql: str) -> str:
    """Remove line and block comments before validating SELECT-only input."""
    no_block = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    lines: list[str] = []
    for line in no_block.splitlines():
        if "--" in line:
            line = line.split("--", 1)[0]
        lines.append(line)
    return "\n".join(lines)


def _is_select_only(sql: str) -> bool:
    """Return True when the statement is a single SELECT (comments stripped)."""
    cleaned = _strip_sql_comments(sql).strip()
    if not cleaned:
        return False
    return _SELECT_ONLY.match(cleaned) is not None


st.set_page_config(page_title="Curated Model Explorer", layout="wide")
header.render("Curated Model Explorer", "Inspect curated tables and run read-only SQL")

data_loader.require_database()
tables = data_loader.list_tables()

selected = st.sidebar.selectbox("Curated table", tables)

row_count = int(
    data_loader.query(f"SELECT COUNT(*) AS n FROM {selected}").iloc[0]["n"]
)
st.markdown(f"**{selected}** — `{row_count:,}` rows")

schema_df = data_loader.query(f"DESCRIBE {selected}")
st.markdown("**Schema**")
st.dataframe(schema_df, use_container_width=True, hide_index=True)

preview = data_loader.table_preview(selected, limit=1000)
st.markdown("**Preview (up to 1,000 rows)**")
st.data_editor(preview, use_container_width=True, height=480, disabled=True)

with st.expander("Run custom SQL (SELECT only)"):
    default_sql = f"SELECT * FROM {selected} LIMIT 100"
    user_sql = st.text_area("SQL", value=default_sql, height=160)
    if st.button("Run query"):
        if not _is_select_only(user_sql):
            st.error("Only SELECT statements are allowed.")
        else:
            result = data_loader.query(user_sql)
            st.dataframe(result, use_container_width=True, hide_index=True)
            st.caption(f"{len(result):,} rows returned")
