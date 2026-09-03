FROM python:3.11-slim

# git for dbt/duckdb; awscli for S3 sync; unzip/curl to install awscli v2
RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates curl unzip \
    && curl -sSL "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o /tmp/awscliv2.zip \
    && unzip -q /tmp/awscliv2.zip -d /tmp \
    && /tmp/aws/install \
    && rm -rf /tmp/aws /tmp/awscliv2.zip \
    && apt-get purge -y unzip curl && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.docker.txt .
RUN pip install --no-cache-dir -r requirements.docker.txt

COPY profiles.docker.yml /root/.dbt/profiles.yml
COPY ingestion/    ingestion/
COPY pulse_dbt/    pulse_dbt/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENV DBT_PROFILES_DIR=/root/.dbt
ENTRYPOINT ["./entrypoint.sh"]
