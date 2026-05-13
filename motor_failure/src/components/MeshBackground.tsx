import React from "react";

const MeshBackground: React.FC = () => (
  <>
    {/* SVG noise filter */}
    <svg className="fixed inset-0 w-0 h-0" aria-hidden="true">
      <filter id="noiseFilter">
        <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
    </svg>

    {/* Noise overlay */}
    <div
      className="fixed inset-0 z-0 pointer-events-none opacity-[0.035] dark:opacity-[0.05]"
      style={{ filter: "url(#noiseFilter)", width: "100%", height: "100%" }}
    />

    {/* Animated mesh gradient orbs */}
    <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none" aria-hidden="true">
      <div className="mesh-orb mesh-orb-1" />
      <div className="mesh-orb mesh-orb-2" />
      <div className="mesh-orb mesh-orb-3" />
      <div className="mesh-orb mesh-orb-4" />
    </div>
  </>
);

export default MeshBackground;
