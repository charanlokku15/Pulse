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
    FROM {{ source('pulse_data', 'raw_listening_events') }}
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
            WHEN LOWER(artist) LIKE '%top%songs%'    THEN 'Unknown Artist'
            WHEN LOWER(artist) LIKE '%hit songs%'    THEN 'Unknown Artist'
            WHEN LOWER(artist) LIKE '%best songs%'   THEN 'Unknown Artist'
            WHEN LOWER(artist) LIKE '%collection%'   THEN 'Unknown Artist'
            WHEN LOWER(artist) LIKE '%non stop%'     THEN 'Unknown Artist'
            WHEN LOWER(artist) LIKE '%tamil hits%'   THEN 'Unknown Artist'
            WHEN LOWER(artist) LIKE '%telugu songs%' THEN 'Unknown Artist'
            WHEN LOWER(artist) LIKE '%jukebox%'      THEN 'Unknown Artist'
            ELSE TRIM(artist)
        END                                               AS artist_clean,

        -- Keep original for reference
        TRIM(artist)                                      AS artist_raw,

        -- Clean album
        TRIM(album)                                       AS album,

        -- Parse timestamp into proper date parts
        timestamp                                         AS played_at_str,
        TIMESTAMP_SECONDS(unix_timestamp)                      AS played_at,
        DATE_TRUNC(TIMESTAMP_SECONDS(unix_timestamp), DAY)   AS played_date,
        EXTRACT(HOUR FROM TIMESTAMP_SECONDS(unix_timestamp))                AS played_hour,
        EXTRACT(DAYOFWEEK FROM TIMESTAMP_SECONDS(unix_timestamp))           AS played_day_of_week,

        -- Time of day bucket
        CASE
            WHEN EXTRACT(HOUR FROM TIMESTAMP_SECONDS(unix_timestamp)) BETWEEN 5  AND 11 THEN 'morning'
            WHEN EXTRACT(HOUR FROM TIMESTAMP_SECONDS(unix_timestamp)) BETWEEN 12 AND 17 THEN 'afternoon'
            WHEN EXTRACT(HOUR FROM TIMESTAMP_SECONDS(unix_timestamp)) BETWEEN 18 AND 21 THEN 'evening'
            ELSE 'night'
        END                                               AS time_of_day,

        loaded_at
    FROM raw
)

SELECT * FROM cleaned