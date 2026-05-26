.PHONY: all run setup pipeline app test lint format clean help

# Default: install deps, run pipeline, run tests (CI / QA)
all: setup pipeline test

# One command: install deps, build curated data + reports, launch Streamlit
run: setup pipeline
	streamlit run app/Home.py

setup:
	pip install -r requirements.txt

pipeline:
	python -m src.pipeline

app:
	streamlit run app/Home.py

test:
	pytest tests/ -v

lint:
	ruff check src tests app
	black --check src tests app

format:
	black src tests app
	ruff check --fix src tests app

clean:
	rm -f outputs/curated.duckdb outputs/exceptions.csv
	rm -f outputs/data_quality_report.md outputs/business_answers.md

help:
	@echo "Targets:"
	@echo "  make run      - install, pipeline, open Streamlit (single command)"
	@echo "  make all      - install, pipeline, pytest (verify without UI)"
	@echo "  make pipeline - run ETL + reports only"
	@echo "  make app      - Streamlit UI (run pipeline first)"
	@echo "  make test     - pytest"
	@echo "  make lint     - ruff + black --check"
	@echo "  make format   - auto-format code"
	@echo "  make clean    - remove generated outputs"
