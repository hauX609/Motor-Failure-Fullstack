import React, { useEffect, useState } from "react";
import { useTheme } from "@/context/ThemeContext";

const InteractiveBackground: React.FC = () => {
  const { resolved } = useTheme();
  const [mousePos, setMousePos] = useState({ x: 50, y: 50 });

  useEffect(() => {
    let lastUpdateTime = 0;
    const THROTTLE_MS = 16; // ~60 FPS throttle (16ms = one frame at 60fps)

    const handleMouseMove = (e: MouseEvent) => {
      const now = performance.now();
      if (now - lastUpdateTime < THROTTLE_MS) return;

      lastUpdateTime = now;
      const x = (e.clientX / window.innerWidth) * 100;
      const y = (e.clientY / window.innerHeight) * 100;
      setMousePos({ x, y });
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  const isDark = resolved === "dark";

  return (
    <div
      className={`fixed inset-0 z-[-1] pointer-events-none overflow-hidden ${
        isDark ? "bg-[#0f1115]" : "bg-slate-50"
      }`}
      style={{
        "--mouse-x": `${mousePos.x}%`,
        "--mouse-y": `${mousePos.y}%`,
      } as React.CSSProperties}
    >
      {/* Primary orb — follows cursor */}
      <div
        className={`absolute w-[40vw] h-[40vw] rounded-full blur-[120px] ${
          isDark ? "bg-blue-800/20" : "bg-blue-500/50"
        }`}
        style={{
          transform: "translate(calc(var(--mouse-x) - 50%), calc(var(--mouse-y) - 50%))",
          transition: "transform 0.8s cubic-bezier(0.25, 1, 0.5, 1)",
        }}
      />

      {/* Secondary orb — inverse/offset follow */}
      <div
        className={`absolute w-[40vw] h-[40vw] rounded-full blur-[120px] ${
          isDark ? "bg-purple-900/20" : "bg-purple-500/50"
        }`}
        style={{
          right: 0,
          bottom: 0,
          transform: `translate(calc(${100 - mousePos.x}% - 50%), calc(${100 - mousePos.y}% - 50%))`,
          transition: "transform 0.8s cubic-bezier(0.25, 1, 0.5, 1)",
        }}
      />

      {/* SVG noise overlay */}
      <svg className="fixed inset-0 w-0 h-0" aria-hidden="true">
        <filter id="noiseFilter">
          <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
      </svg>
      <div
        className="absolute inset-0 opacity-[0.035] dark:opacity-[0.05]"
        style={{ filter: "url(#noiseFilter)", width: "100%", height: "100%" }}
      />
    </div>
  );
};

export default InteractiveBackground;
