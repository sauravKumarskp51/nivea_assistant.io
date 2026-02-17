import { useEffect, useState } from "react";

/* ⏱ Convert milliseconds → mm:ss */
function msToTime(ms) {
  if (!ms) return "0:00";
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  return `${min}:${sec.toString().padStart(2, "0")}`;
}

export default function SpotifyCard() {
  const [data, setData] = useState(null);

  // 🔁 Poll Spotify status
  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  async function fetchStatus() {
    try {
      const res = await fetch("http://127.0.0.1:5000/api/spotify/status");
      const json = await res.json();
      setData(json);
    } catch (e) {
      console.error("Spotify status error", e);
    }
  }

  // 🎮 Play / Pause / Next / Prev
  async function control(action) {
    await fetch("http://127.0.0.1:5000/api/spotify/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action })
    });
    fetchStatus();
  }

  // 🎚 Seek when progress bar dragged
  async function seek(e) {
    if (!data?.duration_ms) return;

    const percent = e.target.value;
    const positionMs = Math.floor(
      (percent / 100) * data.duration_ms
    );

    await fetch("http://127.0.0.1:5000/api/spotify/seek", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ position_ms: positionMs })
    });
  }

  if (!data) {
    return <div className="glass spotify-card">Loading Spotify...</div>;
  }

  if (!data.connected) {
    return <div className="glass spotify-card">Spotify not connected</div>;
  }

  return (
    <div className="glass spotify-card">

      {/* HEADER */}
      <div className="spotify-header">
        <span>🎵 Spotify</span>
        <span className="device">📱 {data.device}</span>
      </div>

      {/* TRACK INFO */}
      <div className="track-center">
        <img className="cover" src={data.album_art}/>
        <h4 className="song">{data.song}</h4>
        <p className="artist">{data.artist}</p>
      </div>

      {/* CONTROLS */}
      <div className="controls">
        <button onClick={() => control("prev")}>⏮</button>
        <button className="play" onClick={() => control("playpause")}>
          {data.playing ? "⏸" : "▶"}
        </button>
        <button onClick={() => control("next")}>⏭</button>
      </div>

      {/* PROGRESS */}
      <div className="progress">
        <span>{msToTime(data.progress_ms)}</span>

        <input
          type="range"
          min="0"
          max="100"
          value={
            data.duration_ms
              ? (data.progress_ms / data.duration_ms) * 100
              : 0
          }
          onChange={seek}
        />

        <span>{msToTime(data.duration_ms)}</span>
      </div>

    </div>
  );
}
