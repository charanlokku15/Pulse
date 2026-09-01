-- Most-played tracks by day / week / month / all-time (DuckDB)
-- Grain: (period_type, period_start, source, track, artist) -> plays, rank.
-- Track identity is exact (track, artist) -- no cross-source fuzzy matching.
-- Source-aware: `all_sources` rollup plus each real source.

WITH base AS (
    SELECT event_id, track, artist, source, event_timestamp
    FROM {{ ref('stg_events') }}
    WHERE is_valid_music_event
),

expanded AS (
    SELECT event_id, track, artist, source,        event_timestamp FROM base
    UNION ALL
    SELECT event_id, track, artist, 'all_sources', event_timestamp FROM base
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
        track,
        artist,
        COUNT(*) AS plays
    FROM periodized
    GROUP BY period_type, period_start, source, track, artist
)

SELECT
    period_type,
    period_start,
    CASE period_type
        WHEN 'all_time' THEN 'all_time'
        ELSE CAST(period_start AS VARCHAR)
    END AS period,
    source,
    track,
    artist,
    plays,
    ROW_NUMBER() OVER (
        PARTITION BY period_type, period_start, source
        ORDER BY plays DESC, track
    ) AS rank_within_period
FROM counted
