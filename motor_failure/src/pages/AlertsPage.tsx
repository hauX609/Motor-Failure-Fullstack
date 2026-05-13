import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import GlassCard from "@/components/GlassCard";
import StatusBadge from "@/components/StatusBadge";
import DataState from "@/components/DataState";
import type { Alert } from "@/types/dto";
import { Check, CheckCheck, Filter } from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";

const normalizeSeverity = (severity: unknown): Alert["severity"] => {
  const s = String(severity || "").toLowerCase();
  if (s === "critical") return "critical";
  if (s === "warning" || s === "degrading") return "warning";
  return "info";
};

const normalizeAlertsPayload = (payload: any): Alert[] => {
  const raw = Array.isArray(payload) ? payload : Array.isArray(payload?.alerts) ? payload.alerts : [];

  return raw
    .map((a: any) => {
      const id = String(a?.id ?? a?.alert_id ?? "").trim();
      if (!id) return null;
      return {
        id,
        motor_id: String(a?.motor_id ?? ""),
        motor_name: a?.motor_name,
        severity: normalizeSeverity(a?.severity),
        message: String(a?.message ?? ""),
        acknowledged: Boolean(a?.acknowledged),
        created_at: String(a?.created_at ?? a?.timestamp ?? new Date().toISOString()),
      } as Alert;
    })
    .filter(Boolean) as Alert[];
};

const AlertsPage: React.FC = () => {
  const qc = useQueryClient();
  const [severity, setSeverity] = useState<string>("all");
  const [ackFilter, setAckFilter] = useState<string>("all");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const alertsQ = useQuery({
    queryKey: ["all-alerts"],
    queryFn: () => apiClient.get("/alerts").then((r) => normalizeAlertsPayload(r.data)),
    refetchInterval: 30000,
  });

  const ackOne = useMutation({
    mutationFn: (id: string) => apiClient.post(`/alerts/${id}/ack`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["all-alerts"] }); toast.success("Alert acknowledged"); },
    onError: () => toast.error("Failed to acknowledge"),
  });

  const ackBatch = useMutation({
    mutationFn: (ids: string[]) => {
      const numericIds = ids
        .map((id) => Number(id))
        .filter((id) => Number.isInteger(id) && id > 0);
      return apiClient.post("/alerts/batch/ack", { alert_ids: numericIds });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["all-alerts"] }); setSelected(new Set()); toast.success("Alerts acknowledged"); },
    onError: () => toast.error("Failed to batch acknowledge"),
  });

  const filtered = (alertsQ.data || []).filter((a) => {
    if (severity !== "all" && a.severity !== severity) return false;
    if (ackFilter === "unack" && a.acknowledged) return false;
    if (ackFilter === "ack" && !a.acknowledged) return false;
    return true;
  });

  const toggleSelect = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Alerts</h2>
          <p className="text-sm text-muted-foreground">{alertsQ.data?.length || 0} total alerts</p>
        </div>
        {selected.size > 0 && (
          <motion.button
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => ackBatch.mutate(Array.from(selected))}
            disabled={ackBatch.isPending}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 disabled:opacity-50"
          >
            <CheckCheck size={16} /> Acknowledge {selected.size} selected
          </motion.button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-center">
        <Filter size={14} className="text-muted-foreground" />
        {["all", "critical", "warning", "info"].map((s) => (
          <button key={s} onClick={() => setSeverity(s)} className={`px-3 py-2 min-h-[2.75rem] rounded-lg text-xs font-medium transition-all capitalize ${severity === s ? "bg-primary text-primary-foreground" : "bg-accent text-muted-foreground hover:text-foreground"}`}>
            {s}
          </button>
        ))}
        <span className="text-border">|</span>
        {["all", "unack", "ack"].map((s) => (
          <button key={s} onClick={() => setAckFilter(s)} className={`px-3 py-2 min-h-[2.75rem] rounded-lg text-xs font-medium transition-all ${ackFilter === s ? "bg-primary text-primary-foreground" : "bg-accent text-muted-foreground hover:text-foreground"}`}>
            {s === "all" ? "All" : s === "unack" ? "Pending" : "Acknowledged"}
          </button>
        ))}
      </div>

      <GlassCard>
        <DataState isLoading={alertsQ.isLoading} isError={alertsQ.isError} error={alertsQ.error} onRetry={() => alertsQ.refetch()} isEmpty={!filtered.length} emptyText="No alerts match filters">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/50 text-muted-foreground">
                  <th className="py-2 px-3 w-8"></th>
                  <th className="text-left py-2 px-3 font-medium">Motor</th>
                  <th className="text-left py-2 px-3 font-medium">Severity</th>
                  <th className="text-left py-2 px-3 font-medium">Message</th>
                  <th className="text-left py-2 px-3 font-medium">Time</th>
                  <th className="text-left py-2 px-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((alert) => (
                  <tr key={alert.id} className="border-b border-border/30 hover:bg-accent/30 transition-colors min-h-[2.75rem]">
                    <td className="py-2.5 px-3">
                      {!alert.acknowledged && (
                        <input type="checkbox" checked={selected.has(alert.id)} onChange={() => toggleSelect(alert.id)} className="rounded" />
                      )}
                    </td>
                    <td className="py-2.5 px-3 font-medium">{alert.motor_name || alert.motor_id}</td>
                    <td className="py-2.5 px-3"><StatusBadge status={alert.severity} pulse={alert.severity === "critical"} /></td>
                    <td className="py-2.5 px-3 text-muted-foreground max-w-xs truncate">{alert.message}</td>
                    <td className="py-2.5 px-3 text-muted-foreground text-xs whitespace-nowrap">{new Date(alert.created_at).toLocaleString()}</td>
                    <td className="py-2.5 px-3">
                      {!alert.acknowledged ? (
                        <button onClick={() => ackOne.mutate(alert.id)} className="flex items-center gap-1 text-xs text-primary hover:underline min-h-[2.75rem] px-2">
                          <Check size={12} /> Ack
                        </button>
                      ) : (
                        <span className="text-xs text-muted-foreground">Done</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DataState>

        {!alertsQ.isLoading && !filtered.length && (severity !== "all" || ackFilter !== "all") && (
          <div className="mt-4 flex items-center justify-center">
            <button
              onClick={() => {
                setSeverity("all");
                setAckFilter("all");
              }}
              className="rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90"
            >
              Clear Filters
            </button>
          </div>
        )}
      </GlassCard>
    </div>
  );
};

export default AlertsPage;
