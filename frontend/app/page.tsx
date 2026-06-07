"use client";

import { useEffect, useState } from "react";

interface MoodDay {
  date: string;
  total_plays: number;
  dominant_mood: string;
  avg_energy: number;
  avg_valence: number;
  pct_energetic: number;
  pct_melancholic: number;
  time_of_day: string;
}

interface Artist {
  artist: string;
  plays: number;
}

interface Fingerprint {
  top_mood: string;
  avg_energy: number;
  avg_valence: number;
  total_plays: number;
  days_active: number;
}

interface TribeMember {
  username: string;
  similarity: number;
  top_mood: string;
  avg_energy: number;
  days_active: number;
}

interface DashboardData {
  mood_timeline: MoodDay[];
  top_artists: Artist[];
  fingerprint: Fingerprint;
  weekly_report: string;
  taste_tribe: TribeMember[];
}

const MOOD_COLORS: Record<string, string> = {
  energetic:   "bg-amber-400",
  melancholic: "bg-blue-400",
  peaceful:    "bg-green-400",
  intense:     "bg-red-400",
  neutral:     "bg-gray-400",
};

const MOOD_EMOJI: Record<string, string> = {
  energetic:   "⚡",
  melancholic: "🌧",
  peaceful:    "🌿",
  intense:     "🔥",
  neutral:     "⚪",
};

export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/pulse")
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="text-white text-xl animate-pulse">Loading your Pulse...</div>
    </div>
  );

  if (!data) return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="text-red-400 text-xl">Failed to load data</div>
    </div>
  );

  return (
    <main className="min-h-screen bg-black text-white p-6 max-w-4xl mx-auto">

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
          Pulse
        </h1>
        <p className="text-gray-400 mt-1">Your emotional music fingerprint</p>
      </div>

      {/* Fingerprint Summary */}
      {data.fingerprint && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-900 rounded-xl p-4">
            <p className="text-gray-400 text-sm">Top mood</p>
            <p className="text-2xl mt-1">
              {MOOD_EMOJI[data.fingerprint.top_mood]} {data.fingerprint.top_mood}
            </p>
          </div>
          <div className="bg-gray-900 rounded-xl p-4">
            <p className="text-gray-400 text-sm">Avg energy</p>
            <p className="text-2xl mt-1 text-amber-400">
              {Math.round(data.fingerprint.avg_energy * 100)}%
            </p>
          </div>
          <div className="bg-gray-900 rounded-xl p-4">
            <p className="text-gray-400 text-sm">Total plays</p>
            <p className="text-2xl mt-1 text-purple-400">
              {data.fingerprint.total_plays.toLocaleString()}
            </p>
          </div>
          <div className="bg-gray-900 rounded-xl p-4">
            <p className="text-gray-400 text-sm">Days active</p>
            <p className="text-2xl mt-1 text-green-400">
              {data.fingerprint.days_active}
            </p>
          </div>
        </div>
      )}

      {/* Mood Timeline */}
      <div className="bg-gray-900 rounded-xl p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Mood Timeline</h2>
        <div className="space-y-3">
          {data.mood_timeline.map((day) => (
            <div key={day.date} className="flex items-center gap-4">
              <span className="text-gray-400 text-sm w-24 shrink-0">{day.date}</span>
              <span className="text-lg w-6">{MOOD_EMOJI[day.dominant_mood]}</span>
              <div className="flex-1 bg-gray-800 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${MOOD_COLORS[day.dominant_mood]}`}
                  style={{ width: `${Math.min(day.avg_energy * 100, 100)}%` }}
                />
              </div>
              <span className="text-gray-400 text-sm w-16 text-right">
                {day.total_plays} plays
              </span>
              <span className="text-gray-500 text-xs w-20 text-right">
                {day.time_of_day}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Top Artists */}
      <div className="bg-gray-900 ratio rounded-xl p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Top Artists</h2>
        <div className="space-y-2">
          {data.top_artists.slice(0, 8).map((a, i) => (
            <div key={a.artist} className="flex items-center gap-3">
              <span className="text-gray-500 text-sm w-5">{i + 1}</span>
              <div className="flex-1">
                <div className="flex justify-between mb-1">
                  <span className="text-sm">{a.artist}</span>
                  <span className="text-gray-400 text-sm">{a.plays}</span>
                </div>
                <div className="bg-gray-800 rounded-full h-1">
                  <div
                    className="h-1 rounded-full bg-purple-400"
                    style={{
                      width: `${(a.plays / data.top_artists[0].plays) * 100}%`
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Taste Tribe */}
      {data.taste_tribe && data.taste_tribe.length > 0 && (
        <div className="bg-gray-900 rounded-xl p-6 mb-6">
          <h2 className="text-xl font-semibold mb-1">Taste Tribe</h2>
          <p className="text-gray-400 text-sm mb-4">
            People who listen the way you do
          </p>
          <div className="space-y-3">
            {data.taste_tribe.map((user) => (
              <div key={user.username}
                className="flex items-center gap-4 bg-gray-800 rounded-lg p-3">
                <div className="w-10 h-10 rounded-full bg-purple-600 flex items-center justify-center text-white font-semibold text-sm">
                  {user.username[0].toUpperCase()}
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-center">
                    <span className="font-medium text-sm">{user.username}</span>
                    <span className="text-purple-400 font-semibold">
                      {user.similarity}% match
                    </span>
                  </div>
                  <div className="flex gap-3 mt-1">
                    <span className="text-gray-400 text-xs">
                      {MOOD_EMOJI[user.top_mood] || "⚪"} {user.top_mood}
                    </span>
                    <span className="text-gray-400 text-xs">
                      ⚡ {Math.round(user.avg_energy * 100)}% energy
                    </span>
                    <span className="text-gray-400 text-xs">
                      📅 {user.days_active} days
                    </span>
                  </div>
                  <div className="bg-gray-700 rounded-full h-1 mt-2">
                    <div
                      className="h-1 rounded-full bg-purple-400"
                      style={{ width: `${user.similarity}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Weekly Report */}
      {data.weekly_report && (
        <div className="bg-gray-900 rounded-xl p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Weekly Pulse Report</h2>
          <p className="text-gray-300 leading-relaxed whitespace-pre-line">
            {data.weekly_report}
          </p>
        </div>
      )}

    </main>
  );
}
