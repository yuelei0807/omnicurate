"""Reusable data table with optional CSV download."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render(
    df: pd.DataFrame,
    *,
    height: int = 420,
    downloadable: bool = True,
    filename: str = "data.csv",
) -> None:
    """Show a dataframe and optionally offer CSV download."""
    st.dataframe(df, use_container_width=True, height=height, hide_index=True)

    if downloadable and not df.empty:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download CSV",
            data=csv_bytes,
            file_name=filename,
            mime="text/csv",
        )