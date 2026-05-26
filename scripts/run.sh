#!/usr/bin/env bash
# One-command entry: install deps, run pipeline, start Streamlit.
set -euo pipefail
cd "$(dirname "$0")/.."
pip install -r requirements.txt
python -m src.pipeline
exec streamlit run app/Home.py
