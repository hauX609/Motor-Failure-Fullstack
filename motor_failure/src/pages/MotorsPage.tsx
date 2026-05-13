import React, { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import apiClient from "@/lib/api-client";
import GlassCard from "@/components/GlassCard";
import StatusBadge from "@/components/StatusBadge";
import DataState from "@/components/DataState";
import type { Motor } from "@/types/dto";
import { Plus, X, Search, RotateCcw, Trash2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";

const STATUS_FILTERS = ["all", "healthy", "warning", "critical", "inactive"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

const normalizeMotorStatus = (status: unknown): Motor["status"] => {
  const s = String(status || "").toLowerCase();
  if (s === "optimal" || s === "healthy") return "healthy";
  if (s === "degrading" || s === "warning") return "warning";
  if (s === "critical") return "critical";
  if (s === "inactive") return "inactive";
  return "healthy";
};

const normalizeMotorsPayload = (payload: any): Motor[] => {
  const raw = Array.isArray(payload) ? payload : Array.isArray(payload?.motors) ? payload.motors : [];

  return raw
    .map((m: any) => {
      const id = String(m?.id ?? m?.motor_id ?? "").trim();
      if (!id) return null;
      const isInactive = Number(m?.active) === 0 || String(m?.status || "").toLowerCase() === "inactive";
      return {
        id,
        name: String(m?.name ?? m?.motor_name ?? id),
        status: isInactive ? "inactive" : normalizeMotorStatus(m?.status ?? m?.latest_status),
        location: m?.location,
        model: m?.model ?? m?.motor_type,
      } as Motor;
    })
    .filter(Boolean) as Motor[];
};

const MotorsPage: React.FC = () => {
  const qc = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [model, setModel] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const motorsQ = useQuery({
    queryKey: ["motors"],
    queryFn: () => apiClient.get("/motors?include_inactive=true").then((r) => normalizeMotorsPayload(r.data)),
  });

  const addMotor = useMutation({
    mutationFn: (data: { name: string; location?: string; model?: string }) =>
      apiClient.post("/motors", {
        motor_id: data.name.trim(),
        motor_type: (data.model || "General").trim(),
        installation_date: null,
      }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["motors"] }); setShowAdd(false); setName(""); setLocation(""); setModel(""); toast.success("Motor added"); },
    onError: () => toast.error("Failed to add motor"),
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/motors/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["motors"] }); toast.success("Motor deactivated"); },
    onError: () => toast.error("Failed to deactivate motor"),
  });

  const reactivate = useMutation({
    mutationFn: (id: string) => apiClient.post(`/motors/${id}/reactivate`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["motors"] }); toast.success("Motor reactivated"); },
    onError: () => toast.error("Failed to reactivate motor"),
  });

  const filtered = useMemo(() => {
    let list = motorsQ.data || [];
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((m) => m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q));
    }
    if (statusFilter !== "all") {
      list = list.filter((m) => m.status === statusFilter);
    }
    return list;
  }, [motorsQ.data, search, statusFilter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Motors</h2>
          <p className="text-sm text-muted-foreground">Manage your motor fleet</p>
        </div>
        <motion.button whileTap={{ scale: 0.95 }} onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-4 py-2.5 min-h-[2.75rem] rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 transition-opacity">
          <Plus size={16} /> Add Motor
        </motion.button>
      </div>

      {/* Glassmorphic Filter Bar */}
      <div className="rounded-2xl p-4 bg-white/10 backdrop-blur-2xl border border-white/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_8px_32px_rgba(0,0,0,0.3)] space-y-4">
        {/* Search Input */}
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="glass-input w-full pl-10"
            placeholder="Search by motor name or ID..."
          />
        </div>

        {/* iOS-style Segmented Control */}
        <div className="flex rounded-xl bg-white/5 backdrop-blur-xl border border-white/10 p-1 gap-0.5 overflow-x-auto">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`relative flex-1 min-w-[5rem] min-h-[2.75rem] px-3 py-2 rounded-lg text-xs font-semibold capitalize transition-all duration-200 ${
                statusFilter === s
                  ? "text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {statusFilter === s && (
                <motion.div
                  layoutId="status-segment"
                  className="absolute inset-0 rounded-lg bg-primary shadow-lg"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <span className="relative z-10">{s}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Add Modal */}
      <AnimatePresence>
        {showAdd && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[70] flex items-center justify-center bg-black/45 backdrop-blur-[1px] p-4">
            <motion.div initial={{ scale: 0.94, y: 8 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.94, y: 8 }} className="p-6 w-full max-w-md rounded-2xl bg-background/90 border border-white/15 shadow-[0_20px_60px_rgba(0,0,0,0.45)]">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold">Add Motor</h3>
                <button onClick={() => setShowAdd(false)} className="p-1 rounded-lg hover:bg-accent"><X size={18} /></button>
              </div>
              <form onSubmit={(e) => { e.preventDefault(); addMotor.mutate({ name, location: location || undefined, model: model || undefined }); }} className="space-y-3">
                <input value={name} onChange={(e) => setName(e.target.value)} className="glass-input w-full" placeholder="Motor name *" required />
                <input value={location} onChange={(e) => setLocation(e.target.value)} className="glass-input w-full" placeholder="Location (optional)" />
                <input value={model} onChange={(e) => setModel(e.target.value)} className="glass-input w-full" placeholder="Model (optional)" />
                <motion.button whileTap={{ scale: 0.97 }} type="submit" disabled={addMotor.isPending} className="w-full py-3 min-h-[2.75rem] rounded-xl bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 disabled:opacity-50">
                  {addMotor.isPending ? "Adding..." : "Add Motor"}
                </motion.button>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Motor List */}
      <DataState isLoading={motorsQ.isLoading} isError={motorsQ.isError} error={motorsQ.error} onRetry={() => motorsQ.refetch()} isEmpty={!filtered.length} emptyText="No motors found">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((motor) => (
            <GlassCard key={motor.id} hover>
              <div className="flex items-start justify-between mb-3">
                <Link to={`/motors/${motor.id}`} className="text-base font-semibold hover:text-primary transition-colors">{motor.name}</Link>
                <StatusBadge status={motor.status} pulse={motor.status === "critical"} />
              </div>
              {motor.location && <p className="text-xs text-muted-foreground mb-1">📍 {motor.location}</p>}
              {motor.model && <p className="text-xs text-muted-foreground mb-3">🔧 {motor.model}</p>}
              <div className="flex gap-2 mt-3">
                {motor.status === "inactive" ? (
                  <button onClick={() => reactivate.mutate(motor.id)} className="flex items-center gap-1 min-h-[2.75rem] text-xs text-primary hover:underline"><RotateCcw size={12} /> Reactivate</button>
                ) : (
                  <button onClick={() => deactivate.mutate(motor.id)} className="flex items-center gap-1 min-h-[2.75rem] text-xs text-destructive hover:underline"><Trash2 size={12} /> Deactivate</button>
                )}
                <Link to={`/motors/${motor.id}`} className="text-xs text-primary hover:underline ml-auto">View Details →</Link>
              </div>
            </GlassCard>
          ))}
        </div>
      </DataState>

      {!motorsQ.isLoading && !filtered.length && statusFilter !== "all" && (
        <div className="flex items-center justify-center">
          <button
            onClick={() => setStatusFilter("all")}
            className="rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90"
          >
            Show All Motors
          </button>
        </div>
      )}
    </div>
  );
};

export default MotorsPage;
