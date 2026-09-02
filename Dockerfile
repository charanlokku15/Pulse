FROM python:3.11-slim

# dbt/duckdb need git + build basics; keep the layer small
RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# deps first for layer caching
COPY requirements.docker.txt .
RUN pip install --no-cache-dir -r requirements.docker.txt

# dbt profile inside the image
COPY profiles.docker.yml /root/.dbt/profiles.yml

# app code
COPY ingestion/    ingestion/
COPY pulse_dbt/    pulse_dbt/
COPY entrypoint.sh .

ENV DBT_PROFILES_DIR=/root/.dbt
ENTRYPOINT ["./entrypoint.sh"]
