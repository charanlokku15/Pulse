import duckdb
import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
con = duckdb.connect("pulse.db")


def get_weekly_mood_data():
    """
    Pull the last 7 days of mood data from the warehouse.
    """
    rows = con.execute("""
        SELECT
            played_date,
            total_plays,
            dominant_mood,
            avg_energy,
            avg_valence,
            pct_energetic,
            pct_melancholic,
            pct_peaceful,
            pct_neutral,
            dominant_time_of_day
        FROM stg_daily_mood
        ORDER BY played_date DESC
        LIMIT 7
    """).fetchall()
    return rows


def get_top_artists_this_week():
    """
    Top 5 artists from the last 7 days.
    """
    rows = con.execute("""
        SELECT
            artist_clean,
            COUNT(*) as plays
        FROM stg_listening_events
        WHERE artist_clean != 'Unknown Artist'
        AND played_date >= (
            SELECT MAX(played_date) - INTERVAL 7 DAYS
            FROM stg_listening_events
        )
        GROUP BY artist_clean
        ORDER BY plays DESC
        LIMIT 5
    """).fetchall()
    return rows


def build_prompt(mood_data, top_artists):
    """
    Build the LLM prompt from structured warehouse data.
    """
    days_summary = []
    for row in mood_data:
        date    = str(row[0])[:10]
        plays   = row[1]
        mood    = row[2]
        energy  = row[3]
        valence = row[4]
        tod     = row[9]
        days_summary.append(
            f"- {date}: {plays} songs, dominant mood: {mood}, "
            f"energy: {energy}, valence: {valence}, "
            f"listened mostly: {tod}"
        )

    artists_summary = ", ".join([f"{r[0]} ({r[1]} plays)" for r in top_artists])

    prompt = f"""You are Pulse — a music emotional intelligence engine.
Based on someone's real listening data from the past week, write their
weekly Pulse Report. Make it personal, insightful, and slightly poetic.
2-3 short paragraphs. No bullet points. Sound like a friend who 
understands music and emotions deeply.

THEIR LISTENING DATA THIS WEEK:

Daily mood breakdown:
{chr(10).join(days_summary)}

Top artists this week:
{artists_summary}

Write their Pulse Report. Reference specific days, patterns, and artists.
End with one forward-looking insight about what their listening suggests
about where they're headed emotionally."""

    return prompt


def generate_report(prompt):
    """
    Call Gemini API to generate the weekly report.
    """
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    response = requests.post(
        url,
        headers={"content-type": "application/json"},
        json={
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
    )

    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def save_report(report):
    """
    Save the report to a file with timestamp.
    """
    os.makedirs("data/reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"data/reports/pulse_report_{timestamp}.txt"

    with open(filename, "w") as f:
        f.write(report)

    return filename


if __name__ == "__main__":
    print("Generating your Pulse Report...\n")

    mood_data   = get_weekly_mood_data()
    top_artists = get_top_artists_this_week()

    if not mood_data:
        print("No mood data found. Run the pipeline first.")
        exit()

    prompt  = build_prompt(mood_data, top_artists)
    report  = generate_report(prompt)
    filepath = save_report(report)

    print("=" * 50)
    print("YOUR WEEKLY PULSE REPORT")
    print("=" * 50)
    print(report)
    print("=" * 50)
    print(f"\nSaved to {filepath}")