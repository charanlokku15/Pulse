-- Discovery vs repeat behavior over time (DuckDB)
-- For each month: how many plays were of tracks heard for the FIRST time (discovery)
-- vs tracks heard before (repeat). "First seen" is the earliest event for a track.
-- youtube_takeout only -- it's the source with real longitudinal history.

WITH base AS (
    SELECT
        event_timestamp,
        CAST(date_trunc('month', event_timestamp) AS DATE) AS month,
        track, artist
    FROM {{ ref('stg_events') }}
    WHERE is_valid_music_event
      AND source = 'youtube_takeout'
),

first_seen AS (
    SELECT track, artist, MIN(event_timestamp) AS first_ts
    FROM base
    GROUP BY track, artist
),

flagged AS (
    SELECT
        b.month,
        CASE WHEN b.event_timestamp = f.first_ts THEN 1 ELSE 0 END AS is_discovery
    FROM base b
    JOIN first_seen f ON b.track = f.track AND b.artist = f.artist
)

SELECT
    month,
    COUNT(*)                                             AS total_plays,
    SUM(is_discovery)                                    AS discovery_plays,
    COUNT(*) - SUM(is_discovery)                         AS repeat_plays,
    ROUND(100.0 * SUM(is_discovery) / COUNT(*), 1)       AS pct_discovery,
    ROUND(100.0 * (COUNT(*) - SUM(is_discovery)) / COUNT(*), 1) AS pct_repeat
FROM flagged
GROUP BY month
ORDER BY month DESC
