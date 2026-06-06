import json
import os
import re
from datetime import datetime


def parse_watch_history_fast(filepath):
    print(f"Reading {filepath}...")

    music_plays = []

    # Read entire file as one string
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split into individual entry blocks
    blocks = content.split('class="outer-cell')

    print(f"Total blocks found: {len(blocks)}")

    for block in blocks:
        # Only process YouTube Music blocks
        if '>YouTube Music<br>' not in block:
            continue

        # Extract track URL and name
        track_match = re.search(
    r'Watched\xa0<a href=["\']?(https://music\.youtube\.com/watch\?v=[^"\'>\s]+)["\']?>([^<]+)</a>',
    block
    )
        if not track_match:
            continue

        url        = track_match.group(1)
        track_name = track_match.group(2).strip()

        # Extract artist — second anchor tag
        artist_matches = re.findall(
            r'<a href="https://www\.youtube\.com/channel/[^"]+">([^<]+)</a>',
            block
        )
        artist = artist_matches[0].strip() if artist_matches else "Unknown Artist"

        # Clean up Topic artists
        if artist.endswith(" - Topic"):
            artist = artist.replace(" - Topic", "")

        # Extract timestamp
        date_match = re.search(
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
            r'\s+\d+,\s+\d{4},\s+\d+:\d+:\d+\s+[AP]M\s+\w+',
            block
        )
        timestamp = date_match.group(0).strip() if date_match else None

        music_plays.append({
            "track_name":     track_name,
            "artist":         artist,
            "album":          "",
            "timestamp":      timestamp,
            "unix_timestamp": None,
            "source":         "youtube_music_takeout",
            "url":            url
        })

    print(f"YouTube Music plays found: {len(music_plays)}")
    return music_plays


def save_music(tracks):
    os.makedirs("data/raw", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"data/raw/takeout_music_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(tracks, f, indent=2)

    print(f"\nSaved to {filename}")
    print("\nPreview — first 5 music plays:")
    for t in tracks[:5]:
        print(f"  {t.get('artist','?')} — {t['track_name']} ({t.get('timestamp','?')})")

    return filename


if __name__ == "__main__":
    filepath = "Takeout/YouTube and YouTube Music/history/watch-history.html"
    tracks   = parse_watch_history_fast(filepath)

    if tracks:
        save_music(tracks)
    else:
        print("\nNo YouTube Music plays found.")