#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
mkdir -p logs
echo "=== Pipeline started: $(date) ===" >> logs/pipeline.log
python ingestion/fetch_tracks.py    >> logs/pipeline.log 2>&1
python ingestion/load_to_duckdb.py  >> logs/pipeline.log 2>&1
(cd pulse_dbt && dbt run)           >> logs/pipeline.log 2>&1
echo "=== Pipeline complete: $(date) ===" >> logs/pipeline.log
