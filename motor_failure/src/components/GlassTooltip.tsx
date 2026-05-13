import React from "react";

interface GlassTooltipProps {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number; color?: string; dataKey?: string }>;
  label?: string;
}

const GlassTooltip: React.FC<GlassTooltipProps> = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-xl px-3.5 py-2.5 text-xs shadow-2xl bg-white/10 backdrop-blur-2xl border border-white/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_8px_32px_rgba(0,0,0,0.3)]">
      {label && (
        <p className="text-muted-foreground font-medium mb-1.5 text-[11px] uppercase tracking-wider">{label}</p>
      )}
      <div className="space-y-1">
        {payload.map((entry, i) => (
          <div key={i} className="flex items-center gap-2">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{
                backgroundColor: entry.color,
                boxShadow: `0 0 6px ${entry.color}`,
              }}
            />
            <span className="text-muted-foreground">{entry.name || entry.dataKey}</span>
            <span className="font-semibold text-foreground ml-auto tabular-nums">
              {typeof entry.value === "number" ? entry.value.toLocaleString() : entry.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default GlassTooltip;
