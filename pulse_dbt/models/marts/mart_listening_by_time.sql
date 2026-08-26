-- Listening rhythm across the day and week (DuckDB)
-- Base: valid music events only. Source-aware: `source` is a dimension, so the
-- combined picture and the per-source picture are both available without blending.

WITH events AS (
    SELECT
        source,
        time_of_day,
        played_hour,
        day_of_week,
        is_weekend,
        event_id
    FROM {{ ref('stg_events') }}
    WHERE is_valid_music_event
),

-- one row per (source, time_of_day) plus an 'all_sources' rollup
by_time_of_day AS (
    SELECT source, 'time_of_day' AS dimension, time_of_day AS bucket, COUNT(*) AS plays
    FROM events GROUP BY source, time_of_day
    UNION ALL
    SELECT 'all_sources', 'time_of_day', time_of_day, COUNT(*)
    FROM events GROUP BY time_of_day
),

by_hour AS (
    SELECT source, 'hour' AS dimension, CAST(played_hour AS VARCHAR) AS bucket, COUNT(*) AS plays
    FROM events GROUP BY source, played_hour
    UNION ALL
    SELECT 'all_sources', 'hour', CAST(played_hour AS VARCHAR), COUNT(*)
    FROM events GROUP BY played_hour
),

by_dow AS (
    SELECT source, 'day_of_week' AS dimension, CAST(day_of_week AS VARCHAR) AS bucket, COUNT(*) AS plays
    FROM events GROUP BY source, day_of_week
    UNION ALL
    SELECT 'all_sources', 'day_of_week', CAST(day_of_week AS VARCHAR), COUNT(*)
    FROM events GROUP BY day_of_week
),

by_weekend AS (
    SELECT source, 'weekend' AS dimension,
           CASE WHEN is_weekend THEN 'weekend' ELSE 'weekday' END AS bucket, COUNT(*) AS plays
    FROM events GROUP BY source, is_weekend
    UNION ALL
    SELECT 'all_sources', 'weekend',
           CASE WHEN is_weekend THEN 'weekend' ELSE 'weekday' END, COUNT(*)
    FROM events GROUP BY is_weekend
),

unioned AS (
    SELECT * FROM by_time_of_day
    UNION ALL SELECT * FROM by_hour
    UNION ALL SELECT * FROM by_dow
    UNION ALL SELECT * FROM by_weekend
)

SELECT
    source,
    dimension,
    bucket,
    plays,
    ROUND(100.0 * plays / SUM(plays) OVER (PARTITION BY source, dimension), 1) AS pct_within_source
FROM unioned
ORDER BY source, dimension, plays DESC
