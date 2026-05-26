"""Analytics dashboard — business questions Q1–Q5."""

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
from src.analytics.q5_sentiment_link import per_customer_detail
from src.config import settings

_SQL = settings.SQL_DIR / "analytics"


def _load_sql(filename: str) -> str:
    return (_SQL / filename).read_text(encoding="utf-8")


def _show_sql(filename: str) -> None:
    with st.expander("Show SQL"):
        st.code(_load_sql(filename), language="sql")


st.set_page_config(page_title="Analytics", layout="wide")
header.render("Analytics", "Stakeholder questions Q1–Q5")
data_loader.require_database()

tab_q1, tab_q2, tab_q3, tab_q4, tab_q5 = st.tabs(
    [
        "Q1 Monthly Revenue",
        "Q2 Top Customers",
        "Q3 Order Exceptions",
        "Q4 Revenue by State",
        "Q5 Sentiment vs Exceptions",
    ]
)

# --- Q1 ---
with tab_q1:
    q1 = data_loader.query(_load_sql("q1_revenue_by_month.sql"))
    total_rev = float(q1["completed_revenue"].sum()) if not q1.empty else 0.0
    kpi_card.grid([("Total Completed Revenue", f"${total_rev:,.2f}")])

    if not q1.empty:
        plot_df = q1.copy()
        plot_df["month_label"] = pd.to_datetime(plot_df["month"]).dt.strftime("%Y-%m")
        line = (
            alt.Chart(plot_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("month_label:N", title="Month", sort=None),
                y=alt.Y("completed_revenue:Q", title="Revenue (USD)"),
                tooltip=["month_label", "completed_revenue", "completed_orders"],
            )
        )
        st.altair_chart(line, use_container_width=True)

    data_table.render(q1, filename="q1_revenue_by_month.csv")
    _show_sql("q1_revenue_by_month.sql")

# --- Q2 ---
with tab_q2:
    q2 = data_loader.query(_load_sql("q2_top_customers.sql"))
    if not q2.empty:
        bar = (
            alt.Chart(q2)
            .mark_bar()
            .encode(
                y=alt.Y("customer_key:N", title="Customer", sort="-x"),
                x=alt.X("completed_value:Q", title="Completed value (USD)"),
                tooltip=["customer_key", "full_name", "completed_value", "completed_orders"],
            )
        )
        st.altair_chart(bar, use_container_width=True)

    data_table.render(q2, filename="q2_top_customers.csv")
    _show_sql("q2_top_customers.sql")

# --- Q3 ---
with tab_q3:
    q3 = data_loader.query(_load_sql("q3_order_exceptions.sql"))
    distinct_rules = 0
    if not q3.empty and "triggered_rules" in q3.columns:
        distinct_rules = len(
            {r for rules in q3["triggered_rules"] for r in str(rules).split(",")}
        )

    kpi_card.grid(
        [
            ("Orders with exceptions", f"{len(q3):,}"),
            ("Distinct rules (approx.)", f"{distinct_rules:,}"),
        ]
    )

    rule_filter = st.multiselect(
        "Filter by rule (substring match on triggered_rules)",
        options=["DQ004", "DQ005", "DQ006", "DQ007", "DQ008", "DQ010"],
        default=[],
    )
    filtered_q3: pd.DataFrame = q3.copy()
    if rule_filter:
        mask = pd.Series(filtered_q3["triggered_rules"]).astype(str).apply(
            lambda s: any(r in s for r in rule_filter)
        )
        filtered_q3 = filtered_q3.loc[mask]

    data_table.render(filtered_q3, filename="q3_order_exceptions.csv")
    _show_sql("q3_order_exceptions.sql")

# --- Q4 ---
with tab_q4:
    q4 = data_loader.query(_load_sql("q4_revenue_by_state.sql"))
    if not q4.empty:
        bar = (
            alt.Chart(q4)
            .mark_bar()
            .encode(
                y=alt.Y("state:N", title="State", sort="-x"),
                x=alt.X("completed_revenue:Q", title="Revenue (USD)"),
                tooltip=["state", "completed_revenue", "completed_orders"],
            )
        )
        st.altair_chart(bar, use_container_width=True)

    data_table.render(q4, filename="q4_revenue_by_state.csv")
    _show_sql("q4_revenue_by_state.sql")

# --- Q5 ---
with tab_q5:
    q5 = data_loader.query(_load_sql("q5_sentiment_link.sql"))
    detail = per_customer_detail(data_loader.get_con())

    st.markdown('<p class="section-title">Cohort summary</p>', unsafe_allow_html=True)
    data_table.render(q5, height=220, downloadable=False)

    if not q5.empty:
        pct_chart = (
            alt.Chart(q5)
            .mark_bar()
            .encode(
                x=alt.X("cohort:N", title="Cohort"),
                y=alt.Y("pct_orders_with_exception:Q", title="% orders with exception"),
                color="cohort:N",
                tooltip=[
                    "cohort",
                    "customer_count",
                    "total_orders",
                    "orders_with_exception",
                    "pct_orders_with_exception",
                ],
            )
        )
        st.altair_chart(pct_chart, use_container_width=True)

    st.markdown('<p class="section-title">Per-customer drill-down</p>', unsafe_allow_html=True)
    data_table.render(detail, filename="q5_customer_detail.csv", height=480)
    _show_sql("q5_sentiment_link.sql")