"""Streamlit home page — OmniRetail Data Platform."""

from __future__ import annotations

import importlib.util
from pathlib import Path

# Streamlit puts app/ on sys.path, not the repo root — bootstrap before app.* imports.
_bootstrap_path = Path(__file__).resolve().parent / "_bootstrap.py"
_spec = importlib.util.spec_from_file_location("app_bootstrap", _bootstrap_path)
if _spec and _spec.loader:
    _bootstrap = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_bootstrap)
    _bootstrap.setup()

import streamlit as st

from app.components import header, kpi_card
from app.services import data_loader
from src.config import settings

_BUSINESS_CONTEXT = settings.INPUT_DIR / "business_context.md"


def _load_business_context() -> str:
    if _BUSINESS_CONTEXT.exists():
        return _BUSINESS_CONTEXT.read_text(encoding="utf-8")
    return "_business_context.md not found in input_data._"


st.set_page_config(
    page_title="OmniRetail Data Platform",
    layout="wide",
    initial_sidebar_state="expanded",
)

header.render("Home", "Customer-360 & Order Reconciliation Overview")
data_loader.require_database()
metrics = data_loader.kpi_metrics()

kpi_card.grid(
    [
        ("Total Customers", metrics["total_customers"]),
        ("Completed Revenue", metrics["completed_revenue"]),
        ("DQ Exceptions", metrics["total_exceptions"]),
        ("Last Pipeline Run", metrics["last_pipeline_run"]),
    ]
)

st.markdown("---")

left, right = st.columns([3, 2], gap="large")

with left:
    st.markdown('<p class="section-title">About this platform</p>', unsafe_allow_html=True)
    st.markdown(_load_business_context())

with right:
    st.markdown('<p class="section-title">Navigate</p>', unsafe_allow_html=True)
    st.markdown(
        "Use the **sidebar** to open:\n\n"
        "- **1 Data Quality** — exceptions and rule reference\n"
        "- **2 Analytics** — business questions Q1–Q5\n"
        "- **3 Curated Model Explorer** — table browser and SQL"
    )

    st.markdown("---")
    st.markdown('<p class="section-title">Run instructions</p>', unsafe_allow_html=True)
    st.code(
        "cd Agentic_Data_Management_Take_Home_Candidate_Pack\n"
        "python -m src.pipeline\n"
        "streamlit run app/Home.py",
        language="bash",
    )

st.caption(
    "Data sourced from local CSV/JSONL inputs; curated tables and reports live under outputs/."
)