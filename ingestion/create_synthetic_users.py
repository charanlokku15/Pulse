import duckdb
import json
import numpy as np

con = duckdb.connect("pulse.db")


def create_user(username, personality):
    """
    Create a synthetic user embedding based on personality type.
    Each personality maps to different values across the 20 dimensions.
    """
    personalities = {
        "late_night_melancholic": [
            0.08,  # energetic % — low
            0.45,  # melancholic % — high
            0.12,  # peaceful %
            0.35,  # neutral %
            0.32,  # avg energy — low
            0.28,  # avg valence — low
            0.08,  # energy consistency
            0.12,  # valence consistency
            0.02,  # morning — almost never
            0.08,  # afternoon — rarely
            0.25,  # evening
            0.65,  # night — almost always
            0.45,  # taste concentration
            0.35,  # listening intensity
            0.60,  # days active
            0.25,  # weekend ratio
            0.35,  # valence trend — declining
            0.40,  # energy trend
            0.09,  # happiness index — low
            0.55,  # positivity score
        ],
        "high_energy_morning": [
            0.55,  # energetic % — very high
            0.05,  # melancholic % — very low
            0.08,  # peaceful %
            0.32,  # neutral %
            0.78,  # avg energy — very high
            0.72,  # avg valence — high
            0.06,  # energy consistency
            0.08,  # valence consistency
            0.55,  # morning — peak time
            0.30,  # afternoon
            0.12,  # evening
            0.03,  # night — rarely
            0.65,  # taste concentration
            0.70,  # listening intensity — high
            0.80,  # days active
            0.40,  # weekend ratio
            0.65,  # valence trend — improving
            0.70,  # energy trend
            0.56,  # happiness index — high
            0.95,  # positivity score
        ],
        "eclectic_explorer": [
            0.22,  # energetic %
            0.18,  # melancholic %
            0.15,  # peaceful %
            0.45,  # neutral %
            0.52,  # avg energy — middle
            0.55,  # avg valence — middle
            0.18,  # energy consistency — high variance
            0.20,  # valence consistency — high variance
            0.20,  # morning
            0.30,  # afternoon
            0.28,  # evening
            0.22,  # night — balanced
            0.15,  # taste concentration — very low, eclectic
            0.55,  # listening intensity
            0.75,  # days active
            0.50,  # weekend ratio
            0.52,  # valence trend — stable
            0.50,  # energy trend
            0.29,  # happiness index
            0.82,  # positivity score
        ],
        "focused_neutral": [
            0.12,  # energetic %
            0.08,  # melancholic %
            0.05,  # peaceful %
            0.75,  # neutral % — very high
            0.50,  # avg energy — exactly middle
            0.50,  # avg valence — exactly middle
            0.03,  # energy consistency — very stable
            0.03,  # valence consistency — very stable
            0.10,  # morning
            0.50,  # afternoon — peak focus time
            0.30,  # evening
            0.10,  # night
            0.55,  # taste concentration
            0.40,  # listening intensity
            0.70,  # days active
            0.35,  # weekend ratio
            0.50,  # valence trend — flat
            0.50,  # energy trend — flat
            0.25,  # happiness index
            0.92,  # positivity score
        ],
        "weekend_warrior": [
            0.35,  # energetic %
            0.10,  # melancholic %
            0.08,  # peaceful %
            0.47,  # neutral %
            0.65,  # avg energy
            0.60,  # avg valence
            0.12,  # energy consistency
            0.10,  # valence consistency
            0.05,  # morning — rarely
            0.20,  # afternoon
            0.35,  # evening
            0.40,  # night
            0.50,  # taste concentration
            0.25,  # listening intensity — low weekdays
            0.45,  # days active — weekends only
            0.80,  # weekend ratio — very high
            0.58,  # valence trend
            0.62,  # energy trend
            0.39,  # happiness index
            0.90,  # positivity score
        ],
    }

    vector = personalities[personality]

    # Add small random noise to make each user unique
    noise = np.random.uniform(-0.03, 0.03, len(vector))
    vector = [round(float(max(0, min(1, v + n))), 4)
              for v, n in zip(vector, noise)]

    con.execute("DELETE FROM user_embeddings WHERE username = ?", [username])
    con.execute("""
        INSERT INTO user_embeddings
        (username, embedding, embedding_dim, top_mood,
         avg_energy, avg_valence, total_plays, days_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        username,
        json.dumps(vector),
        len(vector),
        personality.split("_")[0],
        vector[4],
        vector[5],
        int(np.random.uniform(2000, 8000)),
        int(np.random.uniform(180, 600)),
    ])

    print(f"✓ Created user: {username} ({personality})")


def cosine_similarity(v1, v2):
    v1 = np.array(v1)
    v2 = np.array(v2)
    dot   = np.dot(v1, v2)
    norms = np.linalg.norm(v1) * np.linalg.norm(v2)
    return round(float(dot / norms) if norms > 0 else 0.0, 4)


def find_similar_users(username, top_n=5):
    """
    Find the most similar users to the given username
    using cosine similarity on their embeddings.
    """
    # Get target user embedding
    target = con.execute("""
        SELECT embedding FROM user_embeddings
        WHERE username = ?
    """, [username]).fetchone()

    if not target:
        print(f"User {username} not found")
        return []

    target_vector = json.loads(target[0])

    # Get all other users
    others = con.execute("""
        SELECT username, embedding, top_mood,
               avg_energy, avg_valence, days_active
        FROM user_embeddings
        WHERE username != ?
    """, [username]).fetchall()

    similarities = []
    for row in others:
        other_username = row[0]
        other_vector   = json.loads(row[1])
        similarity     = cosine_similarity(target_vector, other_vector)

        similarities.append({
            "username":   other_username,
            "similarity": round(similarity * 100, 1),
            "top_mood":   row[2],
            "avg_energy": row[3],
            "avg_valence": row[4],
            "days_active": row[5],
        })

    # Sort by similarity descending
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    return similarities[:top_n]


if __name__ == "__main__":
    print("Creating synthetic users...\n")

    create_user("maya_nightowl",    "late_night_melancholic")
    create_user("alex_morningrun",  "high_energy_morning")
    create_user("jordan_explorer",  "eclectic_explorer")
    create_user("riley_focused",    "focused_neutral")
    create_user("sam_weekend",      "weekend_warrior")

    print("\nFinding your Taste Tribe...\n")

    matches = find_similar_users("charanlokku")

    print(f"{'Username':<20} {'Similarity':>10} {'Mood':<15} "
          f"{'Energy':>8} {'Valence':>8}")
    print("-" * 65)
    for m in matches:
        print(f"{m['username']:<20} {m['similarity']:>9}% "
              f"{m['top_mood']:<15} {m['avg_energy']:>8} "
              f"{m['avg_valence']:>8}")