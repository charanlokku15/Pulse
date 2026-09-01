-- Artist listening trends over time (DuckDB)
-- Monthly play counts, share-of-month, and two ranks: rank_in_month (all entities)
-- and rank_among_musicians (artist_type='artist' only; null for labels/channels).
-- The musicians-only rank is the meaningful "who I actually listened to" view;
-- the all-entity rank preserves reality (labels/channels are real upload sources).
-- Data supports real trends: ~728 active days over 3+ years, no export clustering.
-- youtube_takeout only -- scrobbles are too sparse for month-over-month trends.

WITH base AS (
    SELECT
        CAST(date_trunc('month', event_timestamp) AS DATE) AS month,
        artist, artist_type
    FROM {{ ref('stg_events') }}
    WHERE is_valid_music_event
      AND source = 'youtube_takeout'
),

monthly AS (
    SELECT month, artist, artist_type, COUNT(*) AS plays
    FROM base
    GROUP BY month, artist, artist_type
),

ranked AS (
    SELECT *,
        ROUND(100.0 * plays / SUM(plays) OVER (PARTITION BY month), 1) AS pct_of_month,
        ROW_NUMBER() OVER (PARTITION BY month ORDER BY plays DESC, artist) AS rank_in_month,
        CASE WHEN artist_type = 'artist' THEN
            ROW_NUMBER() OVER (PARTITION BY month, (artist_type = 'artist') ORDER BY plays DESC, artist)
        END AS rank_among_musicians
    FROM monthly
)

SELECT
    month,
    artist,
    artist_type,
    plays,
    pct_of_month,
    rank_in_month,
    rank_among_musicians,
    plays - LAG(plays) OVER (PARTITION BY artist ORDER BY month) AS plays_vs_prev_month
FROM ranked
ORDER BY month DESC, rank_in_month
