-- Daily mood summary per user
-- Joins listening events with track features
-- Calculates dominant mood, avg energy, avg valence per day

WITH listening_with_features AS (
    SELECT
        e.play_id,
        e.track_name,
        e.artist_clean,
        e.played_date,
        e.played_hour,
        e.time_of_day,
        e.played_day_of_week,
        f.energy,
        f.valence,
        f.tempo,
        f.danceability,
        f.mood_label
    FROM {{ ref('stg_listening_events') }} e
    LEFT JOIN {{ source('pulse_data', 'track_features') }} f
        ON e.track_name = f.track_name
    WHERE f.mood_label IS NOT NULL
),

daily_stats AS (
    SELECT
        played_date,
        COUNT(*)                        AS total_plays,
        ROUND(AVG(energy), 3)           AS avg_energy,
        ROUND(AVG(valence), 3)          AS avg_valence,
        ROUND(AVG(tempo), 1)            AS avg_tempo,
        ROUND(AVG(danceability), 3)     AS avg_danceability,

        -- Count each mood
        COUNT(CASE WHEN mood_label = 'energetic'   THEN 1 END) AS energetic_count,
        COUNT(CASE WHEN mood_label = 'melancholic' THEN 1 END) AS melancholic_count,
        COUNT(CASE WHEN mood_label = 'peaceful'    THEN 1 END) AS peaceful_count,
        COUNT(CASE WHEN mood_label = 'intense'     THEN 1 END) AS intense_count,
        COUNT(CASE WHEN mood_label = 'neutral'     THEN 1 END) AS neutral_count,

        -- Most listened time of day
        (SELECT time_of_day FROM (
            SELECT time_of_day, COUNT(*) as cnt
            FROM {{ ref('stg_listening_events') }} lf2
            WHERE lf2.played_date = listening_with_features.played_date
            GROUP BY time_of_day
            ORDER BY cnt DESC
            LIMIT 1
        )) AS dominant_time_of_day
    FROM listening_with_features
    GROUP BY played_date
),

daily_with_dominant_mood AS (
    SELECT
        *,
        -- Dominant mood using CASE on counts
        CASE
            WHEN energetic_count >= melancholic_count
             AND energetic_count >= peaceful_count
             AND energetic_count >= intense_count
             AND energetic_count >= neutral_count   THEN 'energetic'
            WHEN melancholic_count >= peaceful_count
             AND melancholic_count >= intense_count
             AND melancholic_count >= neutral_count THEN 'melancholic'
            WHEN peaceful_count >= intense_count
             AND peaceful_count >= neutral_count    THEN 'peaceful'
            WHEN intense_count >= neutral_count     THEN 'intense'
            ELSE 'neutral'
        END AS dominant_mood,

        -- Mood percentages
        ROUND(100.0 * energetic_count   / total_plays, 1) AS pct_energetic,
        ROUND(100.0 * melancholic_count / total_plays, 1) AS pct_melancholic,
        ROUND(100.0 * peaceful_count    / total_plays, 1) AS pct_peaceful,
        ROUND(100.0 * neutral_count     / total_plays, 1) AS pct_neutral
    FROM daily_stats
)

SELECT * FROM daily_with_dominant_mood
ORDER BY played_date DESC