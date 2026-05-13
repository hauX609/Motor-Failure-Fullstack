import React from "react";

interface Props {
  status: string;
  pulse?: boolean;
}

const colorMap: Record<string, string> = {
  healthy: "bg-status-healthy/15 text-status-healthy",
  warning: "bg-status-warning/15 text-status-warning",
  critical: "bg-status-critical/15 text-status-critical",
  inactive: "bg-muted text-muted-foreground",
  info: "bg-primary/15 text-primary",
  low: "bg-status-healthy/15 text-status-healthy",
  medium: "bg-status-warning/15 text-status-warning",
  high: "bg-status-critical/15 text-status-critical",
};

const StatusBadge: React.FC<Props> = ({ status, pulse }) => (
  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${colorMap[status] || "bg-muted text-muted-foreground"}`}>
    {pulse && <span className={`w-1.5 h-1.5 rounded-full pulse-live ${status === "critical" ? "bg-status-critical" : status === "warning" ? "bg-status-warning" : "bg-status-healthy"}`} />}
    {status}
  </span>
);

export default StatusBadge;
