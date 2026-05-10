import requests
import json
import os
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_KEY = os.getenv("LASTFM_API_KEY")
USERNAME = os.getenv("LASTFM_USERNAME")
BASE_URL = "https://ws.audioscrobbler.com/2.0/"


def fetch_recent_tracks(limit=200):
    """
    Fetch recent tracks from Last.fm API.
    Returns a list of track dictionaries.
    """
    all_tracks = []
    page = 1
    total_pages = 1

    print(f"Fetching listening history for {USERNAME}...")

    while page <= total_pages:
        params = {
            "method": "user.getrecenttracks",
            "user": USERNAME,
            "api_key": API_KEY,
            "format": "json",
            "limit": 200,
            "page": page
        }

        response = requests.get(BASE_URL, params=params)
        data = response.json()
        print(f"API Response: {data}")

        # Get total pages on first call
        if page == 1:
            total_pages = int(
                data["recenttracks"]["@attr"]["totalPages"]
            )
            total_tracks = data["recenttracks"]["@attr"]["total"]
            print(f"Found {total_tracks} total scrobbles across "
                  f"{total_pages} pages")

        tracks = data["recenttracks"]["track"]

        # Skip the "now playing" track if present
        for track in tracks:
            if "@attr" in track and track["@attr"].get("nowplaying"):
                continue
            all_tracks.append({
                "track_name": track["name"],
                "artist": track["artist"]["#text"],
                "album": track["album"]["#text"],
                "timestamp": track["date"]["#text"] if "date"
                             in track else None,
                "unix_timestamp": int(track["date"]["uts"]) if "date"
                                  in track else None
            })

        print(f"  Page {page}/{total_pages} fetched "
              f"— {len(all_tracks)} tracks so far")

        page += 1
        time.sleep(0.25)  # Respect API rate limits

    return all_tracks


def save_raw(tracks):
    """
    Save raw track data as JSON with a timestamp in the filename.
    """
    os.makedirs("data/raw", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data/raw/tracks_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(tracks, f, indent=2)

    print(f"\nSaved {len(tracks)} tracks to {filename}")
    return filename


if __name__ == "__main__":
    tracks = fetch_recent_tracks()
    saved_path = save_raw(tracks)

    # Preview first 3 tracks
    print("\nPreview of your data:")
    for track in tracks[:3]:
        print(f"  {track['artist']} — {track['track_name']} "
              f"({track['timestamp']})")              