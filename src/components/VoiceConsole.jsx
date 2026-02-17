import { useEffect, useState } from "react";

export default function VoiceConsole() {
  const [state, setState] = useState("idle");

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch("http://127.0.0.1:5000/api/voice/state");
        const data = await res.json();

        if (data.state) {
          setState(data.state);
        }
      } catch (err) {
        console.error("Voice state fetch failed", err);
      }
    }, 300); // 🔥 fast enough to feel alive

    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`voice-console ${state}`}>
      <div className="presence-orb">
        <div className="orb-core" />
        <div className="orb-ring" />
        <div className="orb-field" />
      </div>
    </div>
  );
}
