import duckdb
import json
import glob
import os
from datetime import timezone
from dateutil import parser as dateparser

DB_PATH  = os.getenv("PULSE_DB", "pulse.db")
RAW_GLOB = "data/raw/*.json"

TZINFOS = {
    "CDT": -5 * 3600, "CST": -6 * 3600,
    "EDT": -4 * 3600, "EST": -5 * 3600,
    "MDT": -6 * 3600, "MST": -7 * 3600,
    "PDT": -7 * 3600, "PST": -8 * 3600,
}


def create_tables(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_listening_events (
            track_name     VARCHAR,
            artist         VARCHAR,
            album          VARCHAR,
            timestamp      VARCHAR,
            unix_timestamp BIGINT,
            source         VARCHAR,
            url            VARCHAR,
            loaded_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("OK  table ready: raw_listening_events")


def _coerce_unix(track):
    uts = track.get("unix_timestamp")
    if uts:
        return int(uts)
    ts = track.get("timestamp")
    if not ts:
        return None
    try:
        dt = dateparser.parse(ts, tzinfos=TZINFOS)
    except (ValueError, OverflowError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _source_of(track):
    """Prefer the explicit source field; else infer from the url/timestamp."""
    s = (track.get("source") or "").strip().lower()
    if s:
        return "youtube_takeout" if "takeout" in s or "youtube" in s else s
    url = (track.get("url") or "").lower()
    if "youtube" in url:
        return "youtube_takeout"
    return "lastfm_scrobble"


def load_raw_files(con):
    files = sorted(glob.glob(RAW_GLOB))
    if not files:
        print("!!  no raw files found in data/raw/")
        return 0

    rows, seen, skipped = [], set(), 0
    for fp in files:
        with open(fp) as f:
            tracks = json.load(f)
        for t in tracks:
            u = _coerce_unix(t)
            if u is None:
                skipped += 1
                continue
            # de-dupe on (source_string, unix) so identical events collapse
            key = (t.get("timestamp"), u)
            if key in seen:
                continue
            seen.add(key)
            rows.append((
                (t.get("track_name") or "").strip(),
                (t.get("artist") or "").strip(),
                (t.get("album") or "").strip(),
                t.get("timestamp"),
                u,
                _source_of(t),
                t.get("url"),
            ))

    if not rows:
        print("!!  no valid rows to load")
        return 0

    con.execute("""
        CREATE TEMP TABLE _incoming (
            track_name VARCHAR, artist VARCHAR, album VARCHAR,
            timestamp VARCHAR, unix_timestamp BIGINT, source VARCHAR, url VARCHAR
        )
    """)
    con.executemany("INSERT INTO _incoming VALUES (?, ?, ?, ?, ?, ?, ?)", rows)

    before = con.execute("SELECT COUNT(*) FROM raw_listening_events").fetchone()[0]
    con.execute("""
        INSERT INTO raw_listening_events
            (track_name, artist, album, timestamp, unix_timestamp, source, url)
        SELECT i.track_name, i.artist, i.album, i.timestamp,
               i.unix_timestamp, i.source, i.url
        FROM _incoming i
        WHERE NOT EXISTS (
            SELECT 1 FROM raw_listening_events r
            WHERE r.unix_timestamp = i.unix_timestamp
              AND r.timestamp IS NOT DISTINCT FROM i.timestamp
        )
    """)
    after = con.execute("SELECT COUNT(*) FROM raw_listening_events").fetchone()[0]
    con.execute("DROP TABLE _incoming")

    inserted = after - before
    print(f"OK  inserted:        {inserted} new events")
    print(f"..  already present: {len(rows) - inserted} (idempotent skip)")
    print(f"..  skipped:         {skipped} rows with missing/unparseable timestamps")
    return inserted


def preview(con):
    total = con.execute("SELECT COUNT(*) FROM raw_listening_events").fetchone()[0]
    print(f"\n{'='*50}\nTotal events: {total}\n{'='*50}")
    print("By source:")
    for s, n in con.execute("""SELECT source, COUNT(*) FROM raw_listening_events
                               GROUP BY source ORDER BY COUNT(*) DESC""").fetchall():
        print(f"  {s}: {n}")


if __name__ == "__main__":
    print(f"Loading into {DB_PATH} ...\n")
    con = duckdb.connect(DB_PATH)
    create_tables(con)
    load_raw_files(con)
    preview(con)
    con.close()
    print("\nDone.")
