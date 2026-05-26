"""Reusable KPI card components for Streamlit pages."""

from __future__ import annotations

import html

import streamlit as st


def render(label: str, value: str, help_text: str | None = None) -> None:
    """Render a single KPI card with label and value."""
    safe_label = html.escape(label)
    safe_value = html.escape(value)
    help_attr = ""
    if help_text:
        help_attr = f' title="{html.escape(help_text)}"'

    st.markdown(
        f"""
        <div class="kpi-card"{help_attr}>
          <div class="kpi-label">{safe_label}</div>
          <div class="kpi-value">{safe_value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def grid(items: list[tuple[str, str]]) -> None:
    """Lay out KPI cards in a single row using Streamlit columns."""
    if not items:
        return
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        with col:
            render(label, value)