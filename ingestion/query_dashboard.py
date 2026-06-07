import duckdb
import json
import os

con = duckdb.connect("/Users/charanlokku/pulse/pulse.db")

def get_dashboard_data():
    # Weekly mood timeline
    mood_timeline = con.execute("""
        SELECT
            CAST(played_date AS VARCHAR) as date,
            total_plays,
            dominant_mood,
            ROUND(avg_energy, 3) as avg_energy,
            ROUND(avg_valence, 3) as avg_valence,
            ROUND(pct_energetic, 1) as pct_energetic,
            ROUND(pct_melancholic, 1) as pct_melancholic,
            dominant_time_of_day
        FROM stg_daily_mood
        ORDER BY played_date DESC
        LIMIT 14
    """).fetchall()

    # Top artists
    top_artists = con.execute("""
        SELECT artist_clean, COUNT(*) as plays
        FROM stg_listening_events
        WHERE artist_clean != 'Unknown Artist'
        GROUP BY artist_clean
        ORDER BY plays DESC
        LIMIT 10
    """).fetchall()

    # Time of day distribution
    time_dist = con.execute("""
        SELECT time_of_day, COUNT(*) as plays
        FROM stg_listening_events
        GROUP BY time_of_day
        ORDER BY plays DESC
    """).fetchall()

    # User embedding
    embedding = con.execute("""
        SELECT top_mood, avg_energy, avg_valence,
               total_plays, days_active, embedding
        FROM user_embeddings
        WHERE username = 'charanlokku'
    """).fetchone()

    # Latest pulse report
    report_dir = "/Users/charanlokku/pulse/data/reports"
    latest_report = ""
    if os.path.exists(report_dir):
        reports = sorted(os.listdir(report_dir))
        if reports:
            with open(os.path.join(report_dir, reports[-1])) as f:
                latest_report = f.read()

    # Taste Tribe matches
    tribe = con.execute("""
        SELECT username, top_mood, avg_energy, avg_valence, days_active
        FROM user_embeddings
        WHERE username != 'charanlokku'
        ORDER BY username
    """).fetchall()

    # Calculate similarity for each
    my_embedding = con.execute("""
        SELECT embedding FROM user_embeddings
        WHERE username = 'charanlokku'
    """).fetchone()

    import numpy as np

    taste_tribe = []
    if my_embedding and tribe:
        my_vec = np.array(json.loads(my_embedding[0]))
        for row in tribe:
            other_vec = np.array(json.loads(
                con.execute("SELECT embedding FROM user_embeddings WHERE username = ?",
                [row[0]]).fetchone()[0]
            ))
            dot   = np.dot(my_vec, other_vec)
            norms = np.linalg.norm(my_vec) * np.linalg.norm(other_vec)
            sim   = round(float(dot / norms) * 100, 1) if norms > 0 else 0
            taste_tribe.append({
                "username":   row[0],
                "similarity": sim,
                "top_mood":   row[1],
                "avg_energy": round(row[2], 2),
                "days_active": row[4]
            })
        taste_tribe.sort(key=lambda x: x["similarity"], reverse=True)

    return {
        "mood_timeline": [
            {
                "date":            row[0][:10],
                "total_plays":     row[1],
                "dominant_mood":   row[2],
                "avg_energy":      row[3],
                "avg_valence":     row[4],
                "pct_energetic":   row[5],
                "pct_melancholic": row[6],
                "time_of_day":     row[7]
            }
            for row in mood_timeline
        ],
        "top_artists": [
            {"artist": row[0], "plays": row[1]}
            for row in top_artists
        ],
        "time_distribution": [
            {"time": row[0], "plays": row[1]}
            for row in time_dist
        ],
        "fingerprint": {
            "top_mood":    embedding[0] if embedding else "neutral",
            "avg_energy":  embedding[1] if embedding else 0.5,
            "avg_valence": embedding[2] if embedding else 0.5,
            "total_plays": embedding[3] if embedding else 0,
            "days_active": embedding[4] if embedding else 0,
        } if embedding else {},
        "weekly_report": latest_report,
        "taste_tribe":   taste_tribe
    }
print(json.dumps(get_dashboard_data()))
