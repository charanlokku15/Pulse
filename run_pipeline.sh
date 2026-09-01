#!/bin/bash
# Full Pulse pipeline. Paths resolve relative to this script, so it runs anywhere.
cd "$(dirname "$0")"
source venv/bin/activate
mkdir -p logs

echo "=== Pipeline started: $(date) ===" >> logs/pipeline.log
python ingestion/fetch_tracks.py     >> logs/pipeline.log 2>&1   # pull latest scrobbles
python ingestion/load_to_duckdb.py   >> logs/pipeline.log 2>&1   # load raw events (idempotent)
(cd pulse_dbt && dbt run)            >> logs/pipeline.log 2>&1   # canonical model + behavioral marts
python ingestion/generate_report.py  >> logs/pipeline.log 2>&1   # build listening report (md + json)
echo "=== Pipeline complete: $(date) ===" >> logs/pipeline.log
