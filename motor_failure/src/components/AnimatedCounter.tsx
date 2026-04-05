import { useEffect, useRef, useState, memo } from "react";
import { animate } from "framer-motion";

interface Props {
  value: number;
  duration?: number;
  className?: string;
}

const AnimatedCounter: React.FC<Props> = memo(({ value, duration = 0.5, className }) => {
  const ref = useRef<HTMLSpanElement>(null);
  const prev = useRef(0);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const controls = animate(prev.current, value, {
      duration,
      ease: "easeOut",
      onUpdate: (v) => {
        node.textContent = Math.round(v).toLocaleString();
      },
    });

    prev.current = value;
    return () => controls.stop();
  }, [value, duration]);

  return <span ref={ref} className={className}>{value}</span>;
}, (prev, next) => prev.value === next.value && prev.duration === next.duration);

export default AnimatedCounter;
