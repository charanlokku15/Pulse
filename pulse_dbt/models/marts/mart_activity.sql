-- Listening activity and diversity over time (DuckDB)
-- Per month: total plays, active days, unique tracks/artists, and a concentration
-- ratio (share of plays taken by the top artist) as a simple diversity signal.
-- youtube_takeout only, for consistent longitudinal history.

WITH base AS (
    SELECT
        CAST(date_trunc('month', event_timestamp) AS DATE) AS month,
        played_date, track, artist
    FROM {{ ref('stg_events') }}
    WHERE is_valid_music_event
      AND source = 'youtube_takeout'
),

per_artist AS (
    SELECT month, artist, COUNT(*) AS plays
    FROM base GROUP BY month, artist
),

top_artist AS (
    SELECT month, MAX(plays) AS top_artist_plays
    FROM per_artist GROUP BY month
),

agg AS (
    SELECT
        month,
        COUNT(*)                        AS total_plays,
        COUNT(DISTINCT played_date)     AS active_days,
        COUNT(DISTINCT track)           AS unique_tracks,
        COUNT(DISTINCT artist)          AS unique_artists
    FROM base
    GROUP BY month
)

SELECT
    a.month,
    a.total_plays,
    a.active_days,
    ROUND(a.total_plays * 1.0 / a.active_days, 1) AS plays_per_active_day,
    a.unique_tracks,
    a.unique_artists,
    ROUND(100.0 * t.top_artist_plays / a.total_plays, 1) AS top_artist_concentration_pct
FROM agg a
JOIN top_artist t USING (month)
ORDER BY a.month DESC
