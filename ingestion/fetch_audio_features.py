import requests
import json
import os
import time
import duckdb
from dotenv import load_dotenv

load_dotenv()

AUDD_API_KEY = os.getenv("AUDD_API_KEY")
con = duckdb.connect("pulse.db")


def create_features_table():
    """
    Create track_features table if it doesn't exist.
    Stores audio features per unique track — fetched once, never re-fetched.
    """
    con.execute("""
        CREATE TABLE IF NOT EXISTS track_features (
            track_name      VARCHAR,
            artist          VARCHAR,
            energy          FLOAT,
            valence         FLOAT,
            tempo           FLOAT,
            danceability    FLOAT,
            acousticness    FLOAT,
            mood_label      VARCHAR,
            source          VARCHAR,
            fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Table created: track_features")


def classify_mood(energy, valence):
    """
    Valence-Arousal model — map energy + valence to mood category.
    Energy:  0.0 (calm) → 1.0 (intense)
    Valence: 0.0 (negative) → 1.0 (positive)
    """
    if energy is None or valence is None:
        return "neutral"
    if energy >= 0.6 and valence >= 0.6:
        return "energetic"
    elif energy >= 0.6 and valence < 0.4:
        return "intense"
    elif energy < 0.4 and valence < 0.4:
        return "melancholic"
    elif energy < 0.4 and valence >= 0.6:
        return "peaceful"
    else:
        return "neutral"


def fetch_features_from_audd(track_name, artist):
    """
    Fetch audio features for a track from AudD API.
    Returns dict with energy, valence, tempo etc or None if not found.
    """
    try:
        # Clean HTML entities from track names
        track_name = track_name.replace("&quot;", '"').replace("&amp;", "&")

        url    = "https://api.audd.io/findLyrics/"
        params = {
            "api_token": AUDD_API_KEY,
            "q":         f"{artist} {track_name}",
        }

        response = requests.get(url, params=params, timeout=10)
        data     = response.json()

        if data.get("status") == "success" and data.get("result"):
            result = data["result"][0]
            # AudD returns basic metadata — we use it to confirm match
            # and assign estimated features based on genre tags
            return {
                "found":  True,
                "title":  result.get("title", track_name),
                "artist": result.get("artist", artist),
            }
        return None

    except Exception as e:
        return None


def get_unique_tracks():
    """
    Get all unique track+artist combinations not yet in track_features.
    """
    rows = con.execute("""
        SELECT DISTINCT
            track_name,
            artist_clean as artist
        FROM stg_listening_events
        WHERE artist_clean != 'Unknown Artist'
        AND track_name NOT IN (
            SELECT track_name FROM track_features
        )
        LIMIT 5000
    """).fetchall()
    return rows


def assign_estimated_features(track_name, artist):
    """
    Estimate audio features based on track name and artist patterns.
    This is a heuristic approach since AudD's free tier doesn't return
    full audio features. We use keyword signals from track names.
    In production this would be replaced by a paid audio features API.
    """
    track_lower  = track_name.lower()
    artist_lower = artist.lower()

    # High energy signals
    if any(w in track_lower for w in [
        "dance", "beat", "party", "fire", "power", "rock",
        "fast", "run", "fight", "war", "pump", "hype", "intro",
        "bgm", "background score", "action", "theme"
    ]):
        energy   = 0.75
        valence  = 0.6
        tempo    = 128.0
        danceability = 0.7

    # Melancholic signals
    elif any(w in track_lower for w in [
        "sad", "cry", "tears", "miss", "alone", "pain",
        "hurt", "broken", "lost", "empty", "goodbye", "farewell",
        "nuvvani", "kaadhal", "love failure", "heart"
    ]):
        energy   = 0.3
        valence  = 0.25
        tempo    = 72.0
        danceability = 0.3

    # Peaceful/calm signals
    elif any(w in track_lower for w in [
        "sleep", "calm", "peace", "soft", "gentle", "lullaby",
        "rain", "night", "dream", "slow", "acoustic", "unplugged"
    ]):
        energy   = 0.25
        valence  = 0.65
        tempo    = 68.0
        danceability = 0.25

    # Happy/energetic signals
    elif any(w in track_lower for w in [
        "happy", "joy", "celebrate", "love", "wedding",
        "birthday", "fun", "good", "shine", "bright",
        "smile", "laugh", "wow", "yay"
    ]):
        energy   = 0.7
        valence  = 0.8
        tempo    = 118.0
        danceability = 0.75

    # Artist-based defaults for known artists
    elif "weeknd" in artist_lower:
        energy, valence, tempo, danceability = 0.65, 0.45, 110.0, 0.65
    elif "anirudh" in artist_lower:
        energy, valence, tempo, danceability = 0.72, 0.65, 120.0, 0.72
    elif "aditya" in artist_lower:
        energy, valence, tempo, danceability = 0.60, 0.60, 108.0, 0.62
    else:
        # Default neutral
        energy, valence, tempo, danceability = 0.5, 0.5, 100.0, 0.5

    acousticness = 1.0 - energy

    return {
        "energy":       energy,
        "valence":      valence,
        "tempo":        tempo,
        "danceability": danceability,
        "acousticness": acousticness
    }


def process_tracks():
    """
    Main pipeline — get unique tracks, estimate features, store in warehouse.
    """
    create_features_table()

    tracks = get_unique_tracks()
    print(f"\nTracks to process: {len(tracks)}")

    if not tracks:
        print("All tracks already have features.")
        return

    processed = 0
    for track_name, artist in tracks:
        features = assign_estimated_features(track_name, artist)
        mood     = classify_mood(features["energy"], features["valence"])

        con.execute("""
            INSERT INTO track_features
            (track_name, artist, energy, valence, tempo,
             danceability, acousticness, mood_label, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            track_name, artist,
            features["energy"], features["valence"], features["tempo"],
            features["danceability"], features["acousticness"],
            mood, "estimated"
        ])

        processed += 1
        if processed % 20 == 0:
            print(f"  Processed {processed}/{len(tracks)} tracks...")

    print(f"\n✓ Done. {processed} tracks processed.")

    # Preview mood distribution
    print("\nMood distribution:")
    rows = con.execute("""
        SELECT mood_label, COUNT(*) as count
        FROM track_features
        GROUP BY mood_label
        ORDER BY count DESC
    """).fetchall()
    for row in rows:
        print(f"  {row[0]}: {row[1]} tracks")


if __name__ == "__main__":
    process_tracks()