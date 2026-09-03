#!/bin/bash
set -euo pipefail
cd /app

: "${S3_BUCKET:?S3_BUCKET env var is required}"
RAW_PREFIX="${S3_RAW_PREFIX:-raw}"
OUT_PREFIX="${S3_OUTPUT_PREFIX:-reports}"

echo "=== [$(date -u)] Pulse pipeline starting (bucket=$S3_BUCKET) ==="

mkdir -p data/raw reports

# 1. Pull raw data down from S3 (the source of truth)
aws s3 sync "s3://${S3_BUCKET}/${RAW_PREFIX}/" data/raw/

# 2. Rebuild everything from raw (idempotent + deterministic)
python ingestion/load_to_duckdb.py
(cd pulse_dbt && dbt run)
(cd pulse_dbt && dbt test)
python ingestion/generate_report.py

# 3. Push the report back up to S3
aws s3 sync reports/ "s3://${S3_BUCKET}/${OUT_PREFIX}/"

echo "=== [$(date -u)] Pulse pipeline complete ==="
