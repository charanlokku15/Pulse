import duckdb
import json
import os
from datetime import datetime
from google.cloud import bigquery

# Connect to DuckDB
con = duckdb.connect("/Users/charanlokku/pulse/pulse.db")

# BigQuery client
bq_client = bigquery.Client(project="pulse-de-project")

PROJECT = "pulse-de-project"
DATASET = "pulse_data"


def load_listening_events():
    """
    Load raw listening events from DuckDB to BigQuery.
    Only loads records not already in BigQuery.
    """
    print("Loading listening events to BigQuery...")

    # Get all records from DuckDB
    rows = con.execute("""
        SELECT
            track_name,
            artist,
            album,
            timestamp,
            unix_timestamp,
            loaded_at
        FROM raw_listening_events
        WHERE unix_timestamp IS NOT NULL
        ORDER BY unix_timestamp ASC
    """).fetchall()

    if not rows:
        print("No records to load.")
        return

    # Get existing unix_timestamps from BigQuery to avoid duplicates
    existing = set()
    try:
        query = f"""
            SELECT unix_timestamp
            FROM `{PROJECT}.{DATASET}.raw_listening_events`
        """
        result = bq_client.query(query).result()
        existing = {row.unix_timestamp for row in result}
        print(f"  Existing in BigQuery: {len(existing)} records")
    except Exception:
        print("  No existing records in BigQuery yet.")

    # Filter out duplicates
    new_rows = [r for r in rows if r[4] not in existing]
    print(f"  New records to insert: {len(new_rows)}")

    if not new_rows:
        print("  All records already in BigQuery.")
        return

    # Write to newline-delimited JSON file for batch load
    tmp_file = "/tmp/pulse_events.json"
    with open(tmp_file, "w") as f:
        for row in new_rows:
            f.write(json.dumps({
                "track_name":     row[0],
                "artist":         row[1],
                "album":          row[2],
                "timestamp":      row[3],
                "unix_timestamp": row[4],
                "loaded_at":      datetime.utcnow().isoformat()
            }) + "\n")

    table_ref = bq_client.dataset(DATASET).table("raw_listening_events")
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )

    with open(tmp_file, "rb") as f:
        job = bq_client.load_table_from_file(f, table_ref, job_config=job_config)

    job.result()  # Wait for job to complete
    print(f"✓ Done. {len(new_rows)} records loaded to BigQuery.")


def load_user_embeddings():
    """
    Load user embeddings from DuckDB to BigQuery.
    """
    print("\nLoading user embeddings to BigQuery...")

    rows = con.execute("""
        SELECT username, embedding, embedding_dim, top_mood,
               avg_energy, avg_valence, total_plays, days_active
        FROM user_embeddings
    """).fetchall()

    if not rows:
        print("No embeddings to load.")
        return

    rows_to_insert = [
        {
            "username":      row[0],
            "embedding":     row[1],
            "embedding_dim": row[2],
            "top_mood":      row[3],
            "avg_energy":    float(row[4]),
            "avg_valence":   float(row[5]),
            "total_plays":   row[6],
            "days_active":   row[7],
            "created_at":    datetime.utcnow().isoformat(),
            "updated_at":    datetime.utcnow().isoformat(),
        }
        for row in rows
    ]

    # Write to newline-delimited JSON file for batch load
    tmp_file = "/tmp/pulse_embeddings.json"
    with open(tmp_file, "w") as f:
        for row in rows_to_insert:
            f.write(json.dumps(row) + "\n")

    table_ref = bq_client.dataset(DATASET).table("user_embeddings")
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    with open(tmp_file, "rb") as f:
        job = bq_client.load_table_from_file(f, table_ref, job_config=job_config)

    job.result()
    print(f"✓ Done. {len(rows_to_insert)} embeddings loaded to BigQuery.")


if __name__ == "__main__":
    print("Starting BigQuery load...\n")
    load_listening_events()
    load_user_embeddings()
    print("\n✓ BigQuery migration complete.")
    print(f"  Dataset: {PROJECT}.{DATASET}")
    print("  Tables: raw_listening_events, user_embeddings")