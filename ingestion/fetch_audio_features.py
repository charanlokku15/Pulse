import requests
import os
import time
import duckdb
from dotenv import load_dotenv

load_dotenv()

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
DB_PATH        = os.getenv("PULSE_DB", "pulse.db")
MAX_TRACKS     = int(os.getenv("MAX_TRACKS", "5000"))
REBUILD        = os.getenv("REBUILD", "0") == "1"

LASTFM_URL = "http://ws.audioscrobbler.com/2.0/"

# Last.fm mood tags -> our mood buckets
TAG_MOOD_MAP = {
    "energetic":   ["energetic","upbeat","party","dance","danceable","happy",
                    "feel good","feelgood","fun","uplifting","summer"],
    "intense":     ["aggressive","intense","hard","heavy","angry","dark","hardcore"],
    "melancholic": ["sad","melancholic","melancholy","depressing","depressive",
                    "heartbreak","emotional","moody","tragic","longing"],
    "peaceful":    ["chill","chillout","chill out","mellow","relaxing","relax",
                    "calm","ambient","peaceful","acoustic","soft","dreamy","soothing"],
}
TAG_TO_MOOD = {tag: mood for mood, tags in TAG_MOOD_MAP.items() for tag in tags}

# Representative numeric features per mood, so energy/valence stay populated downstream
MOOD_FEATURES = {
    "energetic":   (0.75, 0.70, 128.0, 0.72),
    "intense":     (0.78, 0.30, 130.0, 0.55),
    "melancholic": (0.30, 0.25,  72.0, 0.30),
    "peaceful":    (0.25, 0.65,  68.0, 0.30),
    "neutral":     (0.50, 0.50, 100.0, 0.50),
}

con = duckdb.connect(DB_PATH)


def create_features_table():
    con.execute("""
        CREATE TABLE IF NOT EXISTS track_features (
            track_name   VARCHAR,
            artist       VARCHAR,
            energy       FLOAT,
            valence      FLOAT,
            tempo        FLOAT,
            danceability FLOAT,
            acousticness FLOAT,
            mood_label   VARCHAR,
            source       VARCHAR,
            fetched_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def fetch_lastfm_tags(track_name, artist):
    """Popularity-ordered lowercased Last.fm tags for a track, or [] on miss/error."""
    clean = track_name.replace("&quot;", '"').replace("&amp;", "&")
    try:
        resp = requests.get(LASTFM_URL, params={
            "method":      "track.gettoptags",
            "api_key":     LASTFM_API_KEY,
            "artist":      artist,
            "track":       clean,
            "autocorrect": 1,
            "format":      "json",
        }, timeout=10)
        data = resp.json()
    except Exception:
        return []
    tags = data.get("toptags", {}).get("tag", [])
    if isinstance(tags, dict):          # Last.fm returns a bare dict for a single tag
        tags = [tags]
    return [t.get("name", "").lower() for t in tags if t.get("name")]


def mood_from_tags(tags):
    for t in tags:
        if t in TAG_TO_MOOD:
            return TAG_TO_MOOD[t]
    return None


def classify_mood(energy, valence):
    if energy is None or valence is None:
        return "neutral"
    if energy >= 0.6 and valence >= 0.6:   return "energetic"
    if energy >= 0.6 and valence <  0.4:   return "intense"
    if energy <  0.4 and valence <  0.4:   return "melancholic"
    if energy <  0.4 and valence >= 0.6:   return "peaceful"
    return "neutral"


def assign_estimated_features(track_name, artist):
    """Keyword heuristic fallback for tracks with no usable Last.fm mood tags."""
    tl, al = track_name.lower(), artist.lower()
    if any(w in tl for w in ["dance","beat","party","fire","power","rock","fast",
        "run","fight","war","pump","hype","intro","bgm","background score","action","theme"]):
        e, v, t, d = 0.75, 0.60, 128.0, 0.70
    elif any(w in tl for w in ["sad","cry","tears","miss","alone","pain","hurt",
        "broken","lost","empty","goodbye","farewell","kaadhal","love failure","heart"]):
        e, v, t, d = 0.30, 0.25, 72.0, 0.30
    elif any(w in tl for w in ["sleep","calm","peace","soft","gentle","lullaby",
        "rain","night","dream","slow","acoustic","unplugged"]):
        e, v, t, d = 0.25, 0.65, 68.0, 0.25
    elif any(w in tl for w in ["happy","joy","celebrate","love","wedding","birthday",
        "fun","good","shine","bright","smile","laugh"]):
        e, v, t, d = 0.70, 0.80, 118.0, 0.75
    elif "weeknd" in al:   e, v, t, d = 0.65, 0.45, 110.0, 0.65
    elif "anirudh" in al:  e, v, t, d = 0.72, 0.65, 120.0, 0.72
    else:                  e, v, t, d = 0.50, 0.50, 100.0, 0.50
    return e, v, t, d


def get_unique_tracks():
    return con.execute(f"""
        SELECT DISTINCT track_name, artist_clean AS artist
        FROM stg_listening_events
        WHERE artist_clean != 'Unknown Artist'
          AND track_name NOT IN (SELECT track_name FROM track_features)
        LIMIT {MAX_TRACKS}
    """).fetchall()


def process_tracks():
    create_features_table()
    if REBUILD:
        con.execute("DELETE FROM track_features")
        print("REBUILD: cleared track_features")

    tracks = get_unique_tracks()
    print(f"Tracks to process: {len(tracks)}\n")
    if not tracks:
        print("All tracks already have features.")
        return

    lastfm_hits = 0
    for i, (track_name, artist) in enumerate(tracks, 1):
        tags = fetch_lastfm_tags(track_name, artist)
        mood = mood_from_tags(tags)
        if mood:
            energy, valence, tempo, dance = MOOD_FEATURES[mood]
            source = "lastfm_tags"
            lastfm_hits += 1
        else:
            energy, valence, tempo, dance = assign_estimated_features(track_name, artist)
            mood = classify_mood(energy, valence)
            source = "heuristic_fallback"

        con.execute("""
            INSERT INTO track_features
            (track_name, artist, energy, valence, tempo, danceability,
             acousticness, mood_label, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [track_name, artist, energy, valence, tempo, dance,
              1.0 - energy, mood, source])

        if i % 20 == 0:
            print(f"  {i}/{len(tracks)}  (Last.fm hits so far: {lastfm_hits})")
        time.sleep(0.25)   # respect Last.fm rate limits (~5 req/s)

    print(f"\nDone. {len(tracks)} processed, {lastfm_hits} via Last.fm tags.")

    print("\nMood distribution:")
    for m, c in con.execute("""SELECT mood_label, COUNT(*) FROM track_features
                               GROUP BY mood_label ORDER BY COUNT(*) DESC""").fetchall():
        print(f"  {m}: {c}")

    print("\nSource coverage:")
    for s, c in con.execute("""SELECT source, COUNT(*) FROM track_features
                               GROUP BY source ORDER BY COUNT(*) DESC""").fetchall():
        print(f"  {s}: {c}")


if __name__ == "__main__":
    process_tracks()
    con.close()
