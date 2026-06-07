import duckdb
import json
import os
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime

con = duckdb.connect("pulse.db")


def create_embeddings_table():
    """
    Store user emotional fingerprint vectors.
    Each user gets one row — their behavioral signature.
    """
    con.execute("""
        CREATE TABLE IF NOT EXISTS user_embeddings (
            username        VARCHAR PRIMARY KEY,
            embedding       VARCHAR,  -- JSON array of floats
            embedding_dim   INTEGER,
            top_mood        VARCHAR,
            avg_energy      FLOAT,
            avg_valence     FLOAT,
            total_plays     INTEGER,
            days_active     INTEGER,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Table created: user_embeddings")


def get_mood_profile():
    """
    Pull the full mood timeline from the warehouse.
    This is the raw material for the embedding.
    """
    rows = con.execute("""
        SELECT
            played_date,
            total_plays,
            avg_energy,
            avg_valence,
            avg_tempo,
            avg_danceability,
            pct_energetic,
            pct_melancholic,
            pct_peaceful,
            pct_neutral,
            dominant_mood,
            dominant_time_of_day
        FROM stg_daily_mood
        ORDER BY played_date ASC
    """).fetchall()
    return rows


def get_time_of_day_distribution():
    """
    What percentage of listening happens at each time of day.
    This is a behavioral signal — night listeners vs morning listeners.
    """
    rows = con.execute("""
        SELECT
            time_of_day,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS pct
        FROM stg_listening_events
        GROUP BY time_of_day
    """).fetchall()
    dist = {row[0]: round(row[1], 2) for row in rows}
    return {
        "morning":   dist.get("morning",   0.0),
        "afternoon": dist.get("afternoon", 0.0),
        "evening":   dist.get("evening",   0.0),
        "night":     dist.get("night",     0.0),
    }


def get_top_artists_signal():
    """
    What percentage of plays are from the top 10 artists.
    High concentration = narrow taste. Low = eclectic.
    """
    result = con.execute("""
        WITH artist_plays AS (
            SELECT artist_clean, COUNT(*) as plays
            FROM stg_listening_events
            WHERE artist_clean != 'Unknown Artist'
            GROUP BY artist_clean
            ORDER BY plays DESC
        ),
        total AS (SELECT SUM(plays) as total FROM artist_plays),
        top10 AS (SELECT SUM(plays) as top10_plays FROM (
            SELECT plays FROM artist_plays LIMIT 10
        ))
        SELECT
            ROUND(top10.top10_plays * 100.0 / total.total, 2)
        FROM total, top10
    """).fetchone()
    return result[0] if result else 50.0


def build_user_vector(mood_profile, time_dist, top_artist_concentration):
    """
    Build a 20-dimensional embedding vector from behavioral signals.

    Dimensions:
    0-3:   Average mood percentages (energetic, melancholic, peaceful, neutral)
    4-5:   Average energy and valence
    6-7:   Energy and valence standard deviation (consistency signal)
    8-11:  Time of day distribution (morning, afternoon, evening, night)
    12:    Top artist concentration (taste breadth)
    13:    Average plays per day (listening intensity)
    14:    Days active (consistency)
    15:    Weekend vs weekday listening ratio
    16-19: Mood trajectory (is mood improving or declining over time?)
    """
    if not mood_profile:
        return [0.5] * 20

    # Basic mood averages
    energetic_pcts  = [r[6] or 0 for r in mood_profile]
    melancholic_pcts = [r[7] or 0 for r in mood_profile]
    peaceful_pcts   = [r[8] or 0 for r in mood_profile]
    neutral_pcts    = [r[9] or 0 for r in mood_profile]
    energies        = [r[2] or 0.5 for r in mood_profile]
    valences        = [r[3] or 0.5 for r in mood_profile]
    plays_per_day   = [r[1] or 0 for r in mood_profile]

    avg_energetic   = np.mean(energetic_pcts)
    avg_melancholic = np.mean(melancholic_pcts)
    avg_peaceful    = np.mean(peaceful_pcts)
    avg_neutral     = np.mean(neutral_pcts)
    avg_energy      = np.mean(energies)
    avg_valence     = np.mean(valences)
    std_energy      = np.std(energies)
    std_valence     = np.std(valences)
    avg_plays       = np.mean(plays_per_day)
    days_active     = len(mood_profile)

    # Mood trajectory — compare first half vs second half valence
    mid = len(valences) // 2
    if mid > 0:
        early_valence = np.mean(valences[:mid])
        late_valence  = np.mean(valences[mid:])
        valence_trend = late_valence - early_valence  # positive = improving
    else:
        valence_trend = 0.0

    early_energy  = np.mean(energies[:mid]) if mid > 0 else avg_energy
    late_energy   = np.mean(energies[mid:]) if mid > 0 else avg_energy
    energy_trend  = late_energy - early_energy

    # Normalize concentration to 0-1
    concentration_norm = top_artist_concentration / 100.0

    # Build the vector
    vector = [
        avg_energetic / 100.0,       # 0: energetic %
        avg_melancholic / 100.0,     # 1: melancholic %
        avg_peaceful / 100.0,        # 2: peaceful %
        avg_neutral / 100.0,         # 3: neutral %
        avg_energy,                  # 4: avg energy
        avg_valence,                 # 5: avg valence
        min(std_energy, 1.0),        # 6: energy consistency
        min(std_valence, 1.0),       # 7: valence consistency
        time_dist["morning"] / 100.0,    # 8: morning listener
        time_dist["afternoon"] / 100.0,  # 9: afternoon listener
        time_dist["evening"] / 100.0,    # 10: evening listener
        time_dist["night"] / 100.0,      # 11: night listener
        concentration_norm,          # 12: taste concentration
        min(avg_plays / 50.0, 1.0),  # 13: listening intensity
        min(days_active / 30.0, 1.0), # 14: days active ratio
        0.5,                         # 15: weekend ratio (placeholder)
        (valence_trend + 1) / 2,     # 16: valence trend normalized
        (energy_trend + 1) / 2,      # 17: energy trend normalized
        avg_energy * avg_valence,    # 18: happiness index
        1 - (avg_melancholic / 100.0), # 19: positivity score
    ]

    return [round(float(v), 4) for v in vector]


def cosine_similarity(v1, v2):
    """
    Calculate similarity between two vectors.
    1.0 = identical, 0.0 = completely different.
    """
    v1 = np.array(v1)
    v2 = np.array(v2)
    dot    = np.dot(v1, v2)
    norms  = np.linalg.norm(v1) * np.linalg.norm(v2)
    return round(float(dot / norms) if norms > 0 else 0.0, 4)


def save_embedding(username, vector, mood_profile, time_dist):
    """
    Save or update the user's embedding in the warehouse.
    """
    if not mood_profile:
        return

    top_mood   = max(
        ["energetic", "melancholic", "peaceful", "neutral"],
        key=lambda m: sum(
            1 for r in mood_profile if r[10] == m
        )
    )
    avg_energy  = round(float(np.mean([r[2] or 0.5 for r in mood_profile])), 4)
    avg_valence = round(float(np.mean([r[3] or 0.5 for r in mood_profile])), 4)
    total_plays = sum(r[1] for r in mood_profile)
    days_active = len(mood_profile)

    # Delete existing and re-insert
    con.execute("DELETE FROM user_embeddings WHERE username = ?", [username])
    con.execute("""
        INSERT INTO user_embeddings
        (username, embedding, embedding_dim, top_mood,
         avg_energy, avg_valence, total_plays, days_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        username,
        json.dumps(vector),
        len(vector),
        top_mood,
        avg_energy,
        avg_valence,
        total_plays,
        days_active
    ])

    print(f"✓ Embedding saved for {username}")
    print(f"  Dimensions:  {len(vector)}")
    print(f"  Top mood:    {top_mood}")
    print(f"  Avg energy:  {avg_energy}")
    print(f"  Avg valence: {avg_valence}")
    print(f"  Days active: {days_active}")
    print(f"  Vector:      {vector[:5]}... (first 5 of {len(vector)} dims)")


if __name__ == "__main__":
    print("Building your emotional fingerprint...\n")

    create_embeddings_table()

    username     = "charanlokku"
    mood_profile = get_mood_profile()
    time_dist    = get_time_of_day_distribution()
    concentration = get_top_artists_signal() 

    if not mood_profile:
        print("No mood data found. Run the pipeline first.")
        exit()

    vector = build_user_vector(mood_profile, time_dist, concentration)
    save_embedding(username, vector, mood_profile, time_dist)

    print("\n✓ Emotional fingerprint complete.")
    print("\nWhat this vector represents:")
    labels = [
        "energetic %", "melancholic %", "peaceful %", "neutral %",
        "avg energy", "avg valence", "energy consistency",
        "valence consistency", "morning listener", "afternoon listener",
        "evening listener", "night listener", "taste concentration",
        "listening intensity", "days active ratio", "weekend ratio",
        "valence trend", "energy trend", "happiness index", "positivity score"
    ]
    for i, (label, val) in enumerate(zip(labels, vector)):
        print(f"  [{i:2d}] {label:<25} {val}")