import { useEffect, useState } from "react";

export default function GitaPanel({ visible }) {
  const [shlok, setShlok] = useState(null);

  useEffect(() => {
    if (!visible) return;

    fetchShlok();
    const interval = setInterval(fetchShlok, 1 * 60 * 1000); // every 5 min
    return () => clearInterval(interval);
  }, [visible]);

  async function fetchShlok() {
    const res = await fetch("http://127.0.0.1:5000/api/gita/random");
    const data = await res.json();
    setShlok(data);
  }

  if (!visible) return null;

  if (!shlok) {
    return (
      <div className="glass gita-panel">
        <p>श्लोक लोड हो रहा है...</p>
      </div>
    );
  }

  return (
    <div className="glass gita-panel">
      <img src="/kris2.png" className="krishna" />
      <p className="shlok">{shlok.hindi}</p>
      <span className="ref">
        अध्याय {shlok.chapter}, श्लोक {shlok.verse}
      </span>
    </div>
  );
}
