-- Staging model: clean raw listening events
-- Fixes playlist-as-artist issue and standardizes all fields

WITH raw AS (
    SELECT
        track_name,
        artist,
        album,
        timestamp,
        unix_timestamp,
        loaded_at
    FROM raw_listening_events
),

cleaned AS (
    SELECT
        -- Generate a unique ID for each play
        unix_timestamp                                    AS play_id,

        -- Clean track name
        TRIM(track_name)                                  AS track_name,

        -- Fix playlist-as-artist problem
        -- Playlists often contain these patterns
        CASE
            WHEN artist ILIKE '%top%songs%'    THEN 'Unknown Artist'
            WHEN artist ILIKE '%hit songs%'    THEN 'Unknown Artist'
            WHEN artist ILIKE '%best songs%'   THEN 'Unknown Artist'
            WHEN artist ILIKE '%collection%'   THEN 'Unknown Artist'
            WHEN artist ILIKE '%non stop%'     THEN 'Unknown Artist'
            WHEN artist ILIKE '%tamil hits%'   THEN 'Unknown Artist'
            WHEN artist ILIKE '%telugu songs%' THEN 'Unknown Artist'
            WHEN artist ILIKE '%jukebox%'      THEN 'Unknown Artist'
            ELSE TRIM(artist)
        END                                               AS artist_clean,

        -- Keep original for reference
        TRIM(artist)                                      AS artist_raw,

        -- Clean album
        TRIM(album)                                       AS album,

        -- Parse timestamp into proper date parts
        timestamp                                         AS played_at_str,
        TO_TIMESTAMP(unix_timestamp)                      AS played_at,
        DATE_TRUNC('day', TO_TIMESTAMP(unix_timestamp))   AS played_date,
        HOUR(TO_TIMESTAMP(unix_timestamp))                AS played_hour,
        DAYOFWEEK(TO_TIMESTAMP(unix_timestamp))           AS played_day_of_week,

        -- Time of day bucket
        CASE
            WHEN HOUR(TO_TIMESTAMP(unix_timestamp)) BETWEEN 5  AND 11 THEN 'morning'
            WHEN HOUR(TO_TIMESTAMP(unix_timestamp)) BETWEEN 12 AND 17 THEN 'afternoon'
            WHEN HOUR(TO_TIMESTAMP(unix_timestamp)) BETWEEN 18 AND 21 THEN 'evening'
            ELSE 'night'
        END                                               AS time_of_day,

        loaded_at
    FROM raw
)

SELECT * FROM cleaned