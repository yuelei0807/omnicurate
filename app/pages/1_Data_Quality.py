"""Data Quality dashboard page."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_bootstrap_path = Path(__file__).resolve().parents[1] / "_bootstrap.py"
_spec = importlib.util.spec_from_file_location("app_bootstrap", _bootstrap_path)
if _spec and _spec.loader:
    _bootstrap = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_bootstrap)
    _bootstrap.setup()

import altair as alt
import pandas as pd
import streamlit as st

from app.components import data_table, header, kpi_card
from app.services import data_loader
from src.validation.rule_registry import all_rules

st.set_page_config(page_title="Data Quality", layout="wide")

header.render("Data Quality", "Exception monitoring and rule reference")
data_loader.require_database()

exceptions = data_loader.query(
    """
    SELECT
        rule_id,
        dataset,
        record_key,
        severity,
        issue_description,
        suggested_action,
        detected_at
    FROM dq_exception_report
    ORDER BY rule_id, record_key
    """
)

high_count = int((exceptions["severity"] == "High").sum())
medium_count = int((exceptions["severity"] == "Medium").sum())
unique_rules = int(exceptions["rule_id"].nunique())

kpi_card.grid(
    [
        ("Total Exceptions", f"{len(exceptions):,}"),
        ("High Severity", f"{high_count:,}"),
        ("Medium Severity", f"{medium_count:,}"),
        ("Unique Rules Triggered", f"{unique_rules:,}"),
    ]
)

st.markdown('<p class="section-title">Violations by rule</p>', unsafe_allow_html=True)
if exceptions.empty:
    st.info("No exceptions recorded.")
else:
    chart_df = (
        exceptions.groupby(["rule_id", "severity"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            y=alt.Y("rule_id:N", title="Rule", sort=alt.EncodingSortField(field="count", order="descending")),
            x=alt.X("count:Q", title="Violations"),
            color=alt.Color("severity:N", title="Severity"),
            tooltip=["rule_id", "severity", "count"],
        )
    )
    st.altair_chart(chart, use_container_width=True)

st.markdown('<p class="section-title">Exception detail</p>', unsafe_allow_html=True)

rule_options = sorted(exceptions["rule_id"].unique().tolist()) if not exceptions.empty else []
severity_options = sorted(exceptions["severity"].unique().tolist()) if not exceptions.empty else []

col1, col2 = st.columns(2)
with col1:
    selected_rules = st.multiselect("Rule", rule_options, default=rule_options)
with col2:
    selected_severities = st.multiselect("Severity", severity_options, default=severity_options)

filtered: pd.DataFrame = exceptions.copy()
if selected_rules:
    rule_mask = pd.Series(filtered["rule_id"]).isin(selected_rules)
    filtered = filtered.loc[rule_mask]
if selected_severities:
    severity_mask = pd.Series(filtered["severity"]).isin(selected_severities)
    filtered = filtered.loc[severity_mask]

data_table.render(filtered, filename="dq_exceptions.csv")

with st.expander("Rule reference"):
    rules_df = pd.DataFrame(
        [
            {
                "rule_id": rule.rule_id,
                "dataset": rule.dataset,
                "description": rule.description,
                "severity": rule.severity,
                "suggested_action": rule.suggested_action,
            }
            for rule in all_rules()
        ]
    )
    st.dataframe(rules_df, use_container_width=True, hide_index=True)