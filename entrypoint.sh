#!/bin/bash
set -euo pipefail
cd /app

echo "=== [$(date -u)] Pulse pipeline starting ==="

# (AWS steps get added in Phase 3: aws s3 sync s3://.../raw -> data/raw here)

python ingestion/load_to_duckdb.py          # load raw events (idempotent)
(cd pulse_dbt && dbt run)                    # canonical model + behavioral marts
(cd pulse_dbt && dbt test)                   # data-quality gate
python ingestion/generate_report.py          # report md + json

# (AWS steps: aws s3 sync outputs -> s3://... here)

echo "=== [$(date -u)] Pulse pipeline complete ==="
