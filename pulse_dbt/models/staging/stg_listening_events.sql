-- Staging model: clean raw listening events (DuckDB)
-- Fixes playlist-as-artist issue and standardizes all fields

WITH raw AS (
    SELECT track_name, artist, album, timestamp, unix_timestamp, loaded_at
    FROM {{ source('pulse_data', 'raw_listening_events') }}
),

cleaned AS (
    SELECT
        unix_timestamp                                    AS play_id,
        TRIM(track_name)                                  AS track_name,

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

        TRIM(artist)                                      AS artist_raw,
        TRIM(album)                                       AS album,

        timestamp                                         AS played_at_str,
        to_timestamp(unix_timestamp)::TIMESTAMP           AS played_at,
        date_trunc('day', to_timestamp(unix_timestamp))::TIMESTAMP AS played_date,
        EXTRACT(hour FROM to_timestamp(unix_timestamp))   AS played_hour,
        EXTRACT(dow  FROM to_timestamp(unix_timestamp))   AS played_day_of_week,

        CASE
            WHEN EXTRACT(hour FROM to_timestamp(unix_timestamp)) BETWEEN 5  AND 11 THEN 'morning'
            WHEN EXTRACT(hour FROM to_timestamp(unix_timestamp)) BETWEEN 12 AND 17 THEN 'afternoon'
            WHEN EXTRACT(hour FROM to_timestamp(unix_timestamp)) BETWEEN 18 AND 21 THEN 'evening'
            ELSE 'night'
        END                                               AS time_of_day,

        loaded_at
    FROM raw
)

SELECT * FROM cleaned
