#!/bin/bash
cd /Users/charanlokku/pulse
source venv/bin/activate
echo "=== Pipeline started: $(date) ===" >> logs/pipeline.log
python ingestion/fetch_tracks.py >> logs/pipeline.log 2>&1
python ingestion/load_to_duckdb.py >> logs/pipeline.log 2>&1
cd pulse_dbt && dbt run >> ../logs/pipeline.log 2>&1 && cd ..
python ingestion/fetch_audio_features.py >> logs/pipeline.log 2>&1
echo "=== Pipeline complete: $(date) ===" >> logs/pipeline.log
