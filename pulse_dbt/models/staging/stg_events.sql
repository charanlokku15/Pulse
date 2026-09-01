-- Canonical event model (DuckDB)
-- One row per listening/watch event, normalized across sources.
-- Principle: canonical schema, source-aware semantics -- we normalize shape
-- but preserve `source` so downstream marts can filter or segment, never blend blindly.

WITH raw AS (
    SELECT track_name, artist, album, timestamp, unix_timestamp, source, url
    FROM {{ source('pulse_data', 'raw_listening_events') }}
),

cleaned AS (
    SELECT
        md5(COALESCE(timestamp, '') || '|' || CAST(unix_timestamp AS VARCHAR) || '|' || source) AS event_id,

        TRIM(replace(replace(replace(replace(track_name,
            '&quot;', '"'), '&amp;', '&'), '&#39;', ''''), '&#38;', '&')) AS track,
        TRIM(artist) AS artist,
        TRIM(album)  AS album,

        source,
        url,

        to_timestamp(unix_timestamp)::TIMESTAMP                    AS event_timestamp,
        date_trunc('day', to_timestamp(unix_timestamp))::TIMESTAMP AS played_date,
        EXTRACT(hour FROM to_timestamp(unix_timestamp))            AS played_hour,
        EXTRACT(dow  FROM to_timestamp(unix_timestamp))            AS day_of_week,
        (EXTRACT(dow FROM to_timestamp(unix_timestamp)) IN (0, 6)) AS is_weekend,
        CASE
            WHEN EXTRACT(hour FROM to_timestamp(unix_timestamp)) BETWEEN 5  AND 11 THEN 'morning'
            WHEN EXTRACT(hour FROM to_timestamp(unix_timestamp)) BETWEEN 12 AND 17 THEN 'afternoon'
            WHEN EXTRACT(hour FROM to_timestamp(unix_timestamp)) BETWEEN 18 AND 21 THEN 'evening'
            ELSE 'night'
        END                                                        AS time_of_day,

        unix_timestamp
    FROM raw
),

classified AS (
    SELECT
        *,
        -- Movie/album, extracted from the "(From "...")" tag in the title.
        -- Populated for ~9% of tracks that name their film; NULL otherwise.
        -- In Indian film music the movie IS the album. Best-effort, not guessed.
        NULLIF(TRIM(regexp_extract(track, '(?i)\(from\s*"([^"]+)"', 1)), '') AS movie,

        -- non-music signal can appear in EITHER the title or the "artist" field.
        -- BGM / background score deliberately stay music.
        CASE
            WHEN regexp_matches(lower(track) || ' | ' || lower(artist),
                'trailer|interview|review|reaction|roast|shorts|podcast|episode|season|vlog|unboxing|tutorial|explained|comedy|stand ?up|press meet|teaser|highlights|nutshell|in a nut|full movie|movie in|movie scene|scenes|first time watching')
            THEN 'non_music'
            ELSE 'music'
        END AS event_type,

        CASE
            WHEN regexp_matches(lower(artist),
                'music|records|entertainment|t-series|saregama|release|studios|official|media|tunes|audios|label|company|productions')
            THEN 'label_or_channel'
            ELSE 'artist'
        END AS artist_type
    FROM cleaned
)

SELECT
    event_id,
    event_timestamp,
    played_date,
    played_hour,
    day_of_week,
    is_weekend,
    time_of_day,
    track,
    movie,
    artist,
    artist_type,
    album,
    source,
    event_type,
    (event_type = 'music') AS is_valid_music_event,
    url,
    unix_timestamp
FROM classified
