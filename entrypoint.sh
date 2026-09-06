#!/bin/bash
set -euo pipefail
cd /app

: "${S3_BUCKET:?S3_BUCKET env var is required}"
RAW_PREFIX="${S3_RAW_PREFIX:-raw}"
OUT_PREFIX="${S3_OUTPUT_PREFIX:-reports}"

echo "=== [$(date -u)] Pulse pipeline starting (bucket=$S3_BUCKET) ==="

mkdir -p data/raw reports

# 1. Pull existing raw history down from S3 (source of truth)
aws s3 sync "s3://${S3_BUCKET}/${RAW_PREFIX}/" data/raw/

# 2. Fetch fresh scrobbles from Last.fm into a new raw file (LIVE ingestion)
if [ -n "${LASTFM_API_KEY:-}" ] && [ -n "${LASTFM_USERNAME:-}" ]; then
    python ingestion/fetch_tracks.py || echo "!! live fetch failed - continuing with existing raw data"
else
    echo "!! LASTFM creds not set - skipping live fetch, using existing raw only"
fi

# 3. Push any new raw files back to S3 so history accumulates
aws s3 sync data/raw/ "s3://${S3_BUCKET}/${RAW_PREFIX}/"

# 4. Rebuild everything from the updated raw set
python ingestion/load_to_duckdb.py
(cd pulse_dbt && dbt run)
(cd pulse_dbt && dbt test)
python ingestion/generate_report.py

# 5. Push the fresh report up
aws s3 sync reports/ "s3://${S3_BUCKET}/${OUT_PREFIX}/"

echo "=== [$(date -u)] Pulse pipeline complete ==="
