#!/bin/bash
# Run the full Pulse pipeline. Paths resolve relative to this script,
# so it works on any machine — not just the author's laptop.
cd "$(dirname "$0")"
source venv/bin/activate
mkdir -p logs

echo "=== Pipeline started: $(date) ===" >> logs/pipeline.log
python ingestion/fetch_tracks.py          >> logs/pipeline.log 2>&1
python ingestion/load_to_duckdb.py        >> logs/pipeline.log 2>&1
(cd pulse_dbt && dbt run)                  >> logs/pipeline.log 2>&1
python ingestion/fetch_audio_features.py  >> logs/pipeline.log 2>&1
echo "=== Pipeline complete: $(date) ===" >> logs/pipeline.log
