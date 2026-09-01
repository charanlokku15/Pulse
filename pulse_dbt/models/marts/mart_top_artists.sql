-- Most-played artists by day / week / month / all-time (DuckDB)
-- Grain: (period_type, period_start, source, artist, artist_type) -> plays, rank.
-- artist_type is preserved so reporting can show "top musicians" (artist)
-- or "all artist/channel entities" without losing data here.

WITH base AS (
    SELECT event_id, artist, artist_type, source, event_timestamp
    FROM {{ ref('stg_events') }}
    WHERE is_valid_music_event
),

expanded AS (
    SELECT event_id, artist, artist_type, source,        event_timestamp FROM base
    UNION ALL
    SELECT event_id, artist, artist_type, 'all_sources', event_timestamp FROM base
),

periodized AS (
    SELECT *, 'all_time' AS period_type, CAST(NULL AS DATE)                      AS period_start FROM expanded
    UNION ALL SELECT *, 'month',         CAST(date_trunc('month', event_timestamp) AS DATE) FROM expanded
    UNION ALL SELECT *, 'week',          CAST(date_trunc('week',  event_timestamp) AS DATE) FROM expanded
    UNION ALL SELECT *, 'day',           CAST(date_trunc('day',   event_timestamp) AS DATE) FROM expanded
),

counted AS (
    SELECT
        period_type,
        period_start,
        source,
        artist,
        artist_type,
        COUNT(*) AS plays
    FROM periodized
    GROUP BY period_type, period_start, source, artist, artist_type
)

SELECT
    period_type,
    period_start,
    CASE period_type
        WHEN 'all_time' THEN 'all_time'
        ELSE CAST(period_start AS VARCHAR)
    END AS period,
    source,
    artist,
    artist_type,
    plays,
    ROW_NUMBER() OVER (
        PARTITION BY period_type, period_start, source
        ORDER BY plays DESC, artist
    ) AS rank_within_period
FROM counted
