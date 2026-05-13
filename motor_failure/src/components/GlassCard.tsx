import React from "react";
import { motion } from "framer-motion";

interface Props {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

const GlassCard: React.FC<Props> = ({ children, className = "", hover = false }) => (
  <motion.div
    whileHover={hover ? { y: -2, scale: 1.01 } : undefined}
    transition={{ type: "spring", stiffness: 400, damping: 25 }}
    className={`rounded-2xl p-6 bg-white/10 dark:bg-white/10 backdrop-blur-2xl border border-white/10 dark:border-white/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_8px_32px_rgba(0,0,0,0.3)] ${className}`}
  >
    {children}
  </motion.div>
);

export default GlassCard;
