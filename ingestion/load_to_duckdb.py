import duckdb
import json
import os
import glob
from datetime import datetime

# Connect to DuckDB — creates pulse.db file in your project folder
con = duckdb.connect("pulse.db")


def create_tables():
    """
    Create the raw listening events table if it doesn't exist.
    This is your first data warehouse table.
    """
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_listening_events (
            track_name      VARCHAR,
            artist          VARCHAR,
            album           VARCHAR,
            timestamp       VARCHAR,
            unix_timestamp  BIGINT,
            loaded_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Table created: raw_listening_events")


def load_raw_files():
    """
    Find all JSON files in data/raw/ and load them into DuckDB.
    Skips duplicates based on unix_timestamp.
    """
    raw_files = glob.glob("data/raw/*.json")

    if not raw_files:
        print("✗ No raw files found in data/raw/")
        return

    total_loaded = 0

    for filepath in raw_files:
        print(f"\nLoading: {filepath}")

        with open(filepath, "r") as f:
            tracks = json.load(f)

        inserted = 0
        skipped = 0

    for track in tracks:
    # Convert string timestamp to unix if missing
        if not track.get("unix_timestamp"):
            if track.get("timestamp"):
                try:
                    from dateutil import parser as dateparser
                    dt = dateparser.parse(track["timestamp"])
                    track["unix_timestamp"] = int(dt.timestamp())
                except Exception:
                    skipped += 1
                    continue
            else:
                skipped += 1
                continue

            # Check for duplicate before inserting
            existing = con.execute("""
                SELECT COUNT(*) FROM raw_listening_events
                WHERE unix_timestamp = ?
            """, [track["unix_timestamp"]]).fetchone()[0]

            if existing > 0:
                skipped += 1
                continue

            con.execute("""
                INSERT INTO raw_listening_events
                (track_name, artist, album, timestamp, unix_timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, [
                track["track_name"],
                track["artist"],
                track["album"],
                track["timestamp"],
                track["unix_timestamp"]
            ])
            inserted += 1

        print(f"  ✓ Inserted: {inserted} tracks")
        print(f"  ○ Skipped:  {skipped} duplicates or missing timestamps")
        total_loaded += inserted

    return total_loaded


def preview():
    """
    Show a preview of what's now in the warehouse.
    """
    count = con.execute(
        "SELECT COUNT(*) FROM raw_listening_events"
    ).fetchone()[0]

    print(f"\n{'='*50}")
    print(f"Total tracks in warehouse: {count}")
    print(f"{'='*50}")

    print("\nMost recent 5 tracks:")
    rows = con.execute("""
        SELECT artist, track_name, timestamp
        FROM raw_listening_events
        ORDER BY unix_timestamp DESC
        LIMIT 5
    """).fetchall()

    for row in rows:
        print(f"  {row[0]} — {row[1]} ({row[2]})")

    print("\nTop 5 most played artists:")
    rows = con.execute("""
        SELECT artist, COUNT(*) as play_count
        FROM raw_listening_events
        GROUP BY artist
        ORDER BY play_count DESC
        LIMIT 5
    """).fetchall()

    for row in rows:
        print(f"  {row[0]}: {row[1]} plays")


if __name__ == "__main__":
    print("Starting DuckDB load...\n")
    create_tables()
    total = load_raw_files()
    preview()
    print("\n✓ Done. Your data is in pulse.db")