#!/bin/bash
# Full Pulse pipeline. Paths resolve relative to this script, so it runs anywhere.
cd "$(dirname "$0")"
source venv/bin/activate
mkdir -p logs

echo "=== Pipeline started: $(date) ===" >> logs/pipeline.log

# 1. Pull latest scrobbles -> data/raw/*.json
python ingestion/fetch_tracks.py                          >> logs/pipeline.log 2>&1
# 2. Load raw events (idempotent)
python ingestion/load_to_duckdb.py                        >> logs/pipeline.log 2>&1
# 3. Build staging so the features step can read it
(cd pulse_dbt && dbt run --select stg_listening_events)   >> logs/pipeline.log 2>&1
# 4. Derive audio features + mood (needs stg_listening_events)
python ingestion/fetch_audio_features.py                  >> logs/pipeline.log 2>&1
# 5. Build the rest (stg_daily_mood needs track_features)
(cd pulse_dbt && dbt run)                                 >> logs/pipeline.log 2>&1

echo "=== Pipeline complete: $(date) ===" >> logs/pipeline.log
