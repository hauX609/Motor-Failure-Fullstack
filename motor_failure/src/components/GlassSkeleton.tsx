import React from "react";
import { motion } from "framer-motion";

interface Props {
  className?: string;
  count?: number;
}

const GlassSkeleton: React.FC<Props> = ({ className = "h-24", count = 1 }) => (
  <>
    {Array.from({ length: count }).map((_, i) => (
      <div
        key={i}
        className={`relative overflow-hidden rounded-2xl backdrop-blur-2xl border border-white/10 dark:border-white/10 bg-white/5 dark:bg-white/5 ${className}`}
      >
        <motion.div
          className="absolute inset-0"
          style={{
            background:
              "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.08) 40%, rgba(255,255,255,0.12) 50%, rgba(255,255,255,0.08) 60%, transparent 100%)",
          }}
          animate={{ x: ["-100%", "100%"] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
    ))}
  </>
);

export default GlassSkeleton;
