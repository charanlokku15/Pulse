import duckdb, json, os
from datetime import datetime

DB_PATH = os.getenv("PULSE_DB", "pulse.db")
OUT_DIR = "reports"

def q(con, sql):
    return con.execute(sql).fetchall()

def build(con):
    latest_month = con.execute("SELECT MAX(month) FROM mart_artist_trends").fetchone()[0]
    data = {"generated_at": datetime.utcnow().isoformat() + "Z", "latest_month": str(latest_month)}

    data["top_musicians_all_time"] = [
        {"rank": i+1, "artist": a, "plays": p}
        for i,(a,p) in enumerate(q(con, """
            SELECT artist, COUNT(*) plays FROM stg_events
            WHERE is_valid_music_event AND artist_type='artist'
            GROUP BY artist ORDER BY plays DESC LIMIT 10"""))]

    data["top_tracks_all_time"] = [
        {"rank": i+1, "track": t, "artist": a, "movie": m, "plays": p}
        for i,(t,a,m,p) in enumerate(q(con, """
            SELECT TRIM(regexp_replace(track, '(?i)\s*\(from\s*"[^"]+"\)', '')) AS track, artist, movie, COUNT(*) plays FROM stg_events
            WHERE is_valid_music_event
            GROUP BY track, artist, movie ORDER BY plays DESC LIMIT 10"""))]

    data["top_movies"] = [
        {"rank": i+1, "movie": m, "plays": p}
        for i,(m,p) in enumerate(q(con, """
            SELECT movie, COUNT(*) plays FROM stg_events
            WHERE is_valid_music_event AND movie IS NOT NULL
            GROUP BY movie ORDER BY plays DESC LIMIT 8"""))]

    data["top_musicians_this_month"] = [
        {"rank": r, "artist": a, "plays": p, "pct_of_month": pct}
        for (a,r,p,pct) in q(con, f"""
            SELECT artist, rank_among_musicians, plays, pct_of_month
            FROM mart_artist_trends
            WHERE month = '{latest_month}' AND rank_among_musicians <= 10
            ORDER BY rank_among_musicians""")]

    disc = q(con, f"SELECT total_plays, pct_discovery, pct_repeat FROM mart_discovery WHERE month='{latest_month}'")
    act  = q(con, f"""SELECT active_days, plays_per_active_day, unique_tracks, unique_artists,
        top_artist_concentration_pct FROM mart_activity WHERE month='{latest_month}'""")
    data["month_summary"] = ({
        "total_plays": disc[0][0], "pct_discovery": disc[0][1], "pct_repeat": disc[0][2],
        "active_days": act[0][0], "plays_per_active_day": act[0][1],
        "unique_tracks": act[0][2], "unique_artists": act[0][3],
        "top_artist_concentration_pct": act[0][4]} if disc and act else {})

    data["listening_rhythm"] = {
        "by_time_of_day": [{"bucket": b, "pct": pct} for (b,pct) in q(con, """
            SELECT bucket, pct_within_source FROM mart_listening_by_time
            WHERE source='all_sources' AND dimension='time_of_day' ORDER BY plays DESC""")],
        "weekday_vs_weekend": [{"bucket": b, "pct": pct} for (b,pct) in q(con, """
            SELECT bucket, pct_within_source FROM mart_listening_by_time
            WHERE source='all_sources' AND dimension='weekend' ORDER BY plays DESC""")]}
    return data

def to_markdown(d):
    L = ["# Pulse — Your Listening Report",
         f"_Generated {d['generated_at']} · latest month {d['latest_month']}_\n"]
    m = d.get("month_summary", {})
    if m:
        L += [f"## This month ({d['latest_month']})",
              f"- **{m['total_plays']} plays** across {m['active_days']} active days ({m['plays_per_active_day']}/day)",
              f"- **{m['pct_discovery']}% new discoveries**, {m['pct_repeat']}% repeats",
              f"- {m['unique_artists']} artists, {m['unique_tracks']} tracks · top-artist concentration {m['top_artist_concentration_pct']}%\n"]
    L.append("## Top musicians (all time)")
    L += [f"{a['rank']}. {a['artist']} — {a['plays']} plays" for a in d["top_musicians_all_time"]]
    L.append("\n## Top tracks (all time)")
    for t in d["top_tracks_all_time"]:
        mv = f" — *{t['movie']}*" if t.get("movie") else ""
        L.append(f"{t['rank']}. {t['track']}{mv} — {t['artist']} ({t['plays']})")
    L.append("\n## Top movies / albums")
    L += [f"{mv['rank']}. {mv['movie']} — {mv['plays']} plays" for mv in d["top_movies"]]
    L.append("\n## Listening rhythm")
    L.append("- Time of day: " + ", ".join(f"{x['bucket']} {x['pct']}%" for x in d["listening_rhythm"]["by_time_of_day"]))
    L.append("- Week split: "  + ", ".join(f"{x['bucket']} {x['pct']}%" for x in d["listening_rhythm"]["weekday_vs_weekend"]))
    return "\n".join(L)

if __name__ == "__main__":
    con = duckdb.connect(DB_PATH)
    d = build(con)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(f"{OUT_DIR}/listening_report.json","w") as f: json.dump(d, f, indent=2, ensure_ascii=False)
    with open(f"{OUT_DIR}/listening_report.md","w") as f: f.write(to_markdown(d))
    print(f"Wrote {OUT_DIR}/listening_report.json and reports/listening_report.md\n")
    print(to_markdown(d))
