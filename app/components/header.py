"""Shared page header with one-time theme injection."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_THEME_PATH = Path(__file__).resolve().parents[1] / "styles" / "theme.css"
_CSS_SESSION_KEY = "_theme_css_injected"


def _inject_theme_once() -> None:
    """Load theme.css into the page once per Streamlit session."""
    if st.session_state.get(_CSS_SESSION_KEY):
        return
    css = _THEME_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    st.session_state[_CSS_SESSION_KEY] = True


def render(title: str, subtitle: str | None = None) -> None:
    """Render brand header, page title, and optional subtitle."""
    _inject_theme_once()

    st.markdown(
        '<p style="margin:0 0 4px 0;font-size:0.8rem;font-weight:600;'
        'letter-spacing:0.06em;text-transform:uppercase;color:#6B7280;">'
        "OmniRetail · Data Platform</p>",
        unsafe_allow_html=True,
    )
    st.title(title)
    if subtitle:
        st.caption(subtitle)