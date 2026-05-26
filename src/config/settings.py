"""Project-wide path constants and tiny path helpers.

This module is intentionally dependency-free: it must not import
pandas, duckdb, streamlit, or any other third-party library. Every
other module in the project imports its paths from here so that
file locations are defined in exactly one place.
"""

from __future__ import annotations

from pathlib import Path

# Resolve the project root from this file's location so the constants
# work no matter what the current working directory is at runtime.
#   src/config/settings.py -> parents[0]=src/config, [1]=src, [2]=root
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

INPUT_DIR: Path = PROJECT_ROOT / "input_data"
OUTPUT_DIR: Path = PROJECT_ROOT / "outputs"
SQL_DIR: Path = PROJECT_ROOT / "sql"

DUCKDB_PATH: Path = OUTPUT_DIR / "curated.duckdb"
EXCEPTIONS_CSV: Path = OUTPUT_DIR / "exceptions.csv"
DQ_REPORT_MD: Path = OUTPUT_DIR / "data_quality_report.md"
ANSWERS_MD: Path = OUTPUT_DIR / "business_answers.md"


def ensure_output_dir() -> None:
    """Create OUTPUT_DIR if it does not exist. Safe to call repeatedly."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)