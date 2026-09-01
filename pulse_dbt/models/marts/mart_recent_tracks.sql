-- Most-recent listening events, newest first, SOURCE-AWARE (DuckDB)
-- Recency is ranked within each source plus an all_sources rollup, because
-- freshness and quality differ by source: youtube_takeout is the clean music
-- history; lastfm_scrobble is near-live but sparse and carries non-music that
-- slips past title filtering. Reporting should headline the clean source and
-- show scrobbles separately -- never blend them into one "recent" list.

WITH valid AS (
    SELECT event_timestamp, played_date, time_of_day, source,
           track, artist, artist_type, event_id
    FROM {{ ref('stg_events') }}
    WHERE is_valid_music_event
),

per_source AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY source ORDER BY event_timestamp DESC) AS recency_rank
    FROM valid
),

all_sources AS (
    SELECT event_timestamp, played_date, time_of_day,
           'all_sources' AS source, track, artist, artist_type, event_id,
           ROW_NUMBER() OVER (ORDER BY event_timestamp DESC) AS recency_rank
    FROM valid
)

SELECT * FROM per_source
UNION ALL
SELECT * FROM all_sources
