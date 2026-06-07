from airflow import DAG
from airflow.operators.bash import BashOperator # pyright: ignore[reportMissingImports]
from airflow.operators.python import PythonOperator # pyright: ignore[reportMissingImports]
from datetime import datetime, timedelta
import os

PULSE_DIR = "/Users/charanlokku/pulse"

default_args = {
    "owner":            "charanlokku",
    "retries":          1,
    "retry_delay":      timedelta(minutes=5),
    "start_date":       datetime(2026, 1, 1),
}

with DAG(
    dag_id="pulse_daily_pipeline",
    default_args=default_args,
    description="Daily Pulse data pipeline",
    schedule="0 9 * * *",  # runs every day at 9am
    catchup=False,
    tags=["pulse", "music", "data-engineering"],
) as dag:

    # Task 1: Fetch new scrobbles from Last.fm
    fetch_tracks = BashOperator(
        task_id="fetch_tracks",
        bash_command=f"cd {PULSE_DIR} && source venv/bin/activate && python ingestion/fetch_tracks.py",
    )

    # Task 2: Load raw data into DuckDB
    load_to_warehouse = BashOperator(
        task_id="load_to_warehouse",
        bash_command=f"cd {PULSE_DIR} && source venv/bin/activate && python ingestion/load_to_duckdb.py",
    )

    # Task 3: Run dbt transformations
    run_dbt = BashOperator(
        task_id="run_dbt_models",
        bash_command=f"cd {PULSE_DIR}/pulse_dbt && source ../venv/bin/activate && dbt run",
    )

    # Task 4: Fetch audio features for new tracks
    fetch_features = BashOperator(
        task_id="fetch_audio_features",
        bash_command=f"cd {PULSE_DIR} && source venv/bin/activate && python ingestion/fetch_audio_features.py",
    )

    # Task 5: Generate weekly report (Sundays only)
    generate_report = BashOperator(
        task_id="generate_weekly_report",
        bash_command=f"cd {PULSE_DIR} && source venv/bin/activate && python ingestion/generate_pulse_report.py",
    )

    # Define the order — each task waits for the previous one
    fetch_tracks >> load_to_warehouse >> run_dbt >> fetch_features >> generate_report