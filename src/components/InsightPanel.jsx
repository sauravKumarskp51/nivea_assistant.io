import { useEffect, useRef, useState } from "react";

export default function NiveaHeartVideoPanel({ isDead }) {
  return (
    <div className={`heart-video-panel ${isDead ? "dead" : ""}`}>
      <video
        src="/heart.mp4"
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        className="heart-video"
      />
      {/* This layer applies the color match */}
      <div className="heart-overlay" />
    </div>
  );
}
