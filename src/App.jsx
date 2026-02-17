import { useEffect, useState } from "react";
import AvatarPanel from "./components/AvatarPanel";
import WeatherCard from "./components/WeatherCard";
import SpotifyCard from "./components/SpotifyCard";
import GitaPanel from "./components/GitaPanel";
import SkillPanel from "./components/SkillPanel";
import VoiceConsole from "./components/VoiceConsole";
import InsightPanel from "./components/InsightPanel";

export default function App() {
  const [avatarState, setAvatarState] = useState("idle");
  const [showGita, setShowGita] = useState(true);
  const [activeSkill, setActiveSkill] = useState(null);

  // 🔥 CONNECT AVATAR TO VOICE STATE
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch("http://127.0.0.1:5000/api/voice/state");
        const data = await res.json();
        if (data.state) setAvatarState(data.state);
      } catch {}
    }, 300);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dashboard">

      {/* COLUMN 1 — Avatar + Spotify */}
      <div className="column">
        <AvatarPanel state={avatarState} />
        <SpotifyCard />
      </div>

      {/* COLUMN 2 — Weather + Gita */}
      <div className="column">
        <WeatherCard />
        <GitaPanel visible={showGita} />
      </div>

      {/* COLUMN 3 — Skills + Insight */}
      <div className="column">
        <SkillPanel
          activeSkill={activeSkill}
          onSkillSelect={setActiveSkill}
        />
        <InsightPanel />
      </div>

      {/* COLUMN 4 — Voice */}
      <div className="column voice-column">
        <VoiceConsole />
      </div>

    </div>
  );
}
