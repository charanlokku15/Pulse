-- Most-recent listening events, newest first (DuckDB)
-- Freshness is bounded by the upstream source: lastfm_scrobble is near-live but
-- sparse; youtube_takeout is only as fresh as the last export. `source` is kept
-- visible so recency quality is never mistaken for uniform.

SELECT
    event_timestamp,
    played_date,
    time_of_day,
    source,
    track,
    artist,
    artist_type,
    event_id,
    ROW_NUMBER() OVER (ORDER BY event_timestamp DESC) AS recency_rank
FROM {{ ref('stg_events') }}
WHERE is_valid_music_event
ORDER BY event_timestamp DESC
