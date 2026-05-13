import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import GlassCard from "@/components/GlassCard";
import GlassTooltip from "@/components/GlassTooltip";
import StatusBadge from "@/components/StatusBadge";
import DataState from "@/components/DataState";
import type { Motor, MotorReading, SensorTrendPoint, PredictionResult } from "@/types/dto";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { useTheme } from "@/context/ThemeContext";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const SENSORS = ["s11", "s12", "s13", "s14", "s15"];
const RUL_SECONDS_PER_CYCLE = Number(import.meta.env.VITE_RUL_SECONDS_PER_CYCLE || 5);

const normalizeReadingsPayload = (payload: any): MotorReading[] => {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.readings)) return payload.readings;
  return [];
};

const normalizeSensorTrendPayload = (payload: any): SensorTrendPoint[] => {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.points)) return payload.points;
  return [];
};

const mapStatusToRisk = (status: unknown): PredictionResult["risk_level"] => {
  const s = String(status || "").toLowerCase();
  if (s === "critical") return "high";
  if (s === "degrading" || s === "warning") return "medium";
  return "low";
};

const normalizePredictionPayload = (payload: any): PredictionResult => {
  const probs = Array.isArray(payload?.probabilities) ? payload.probabilities : [];
  const numericProbs = probs.map((p: unknown) => Number(p)).filter((p: number) => Number.isFinite(p));
  const maxProb = numericProbs.length ? Math.max(...numericProbs) : 0;

  const prediction = String(payload?.prediction ?? payload?.predicted_status ?? "Unknown");
  const riskLevel = payload?.risk_level ?? mapStatusToRisk(prediction);

  return {
    motor_id: String(payload?.motor_id || ""),
    prediction,
    confidence: Number.isFinite(Number(payload?.confidence)) ? Number(payload.confidence) : maxProb,
    risk_level: riskLevel,
    details: {
      predicted_rul: payload?.predicted_rul,
      probabilities: numericProbs,
      timestamp: payload?.timestamp,
    },
  } as PredictionResult;
};

const riskGlow: Record<string, string> = {
  low: "radial-gradient(ellipse at 30% 50%, hsl(142 71% 45% / 0.12) 0%, transparent 70%)",
  medium: "radial-gradient(ellipse at 30% 50%, hsl(38 92% 50% / 0.12) 0%, transparent 70%)",
  high: "radial-gradient(ellipse at 30% 50%, hsl(0 84% 60% / 0.15) 0%, transparent 70%)",
  critical: "radial-gradient(ellipse at 30% 50%, hsl(0 84% 60% / 0.2) 0%, transparent 70%)",
};

const MotorDetailPage: React.FC = () => {
  const { motorId } = useParams<{ motorId: string }>();
  const { resolved } = useTheme();
  const [sensor, setSensor] = useState("s11");

  const motorQ = useQuery({
    queryKey: ["motor", motorId],
    queryFn: () => apiClient.get<Motor>(`/motors/${motorId}`).then((r) => r.data),
    enabled: !!motorId,
  });

  const readingsQ = useQuery({
    queryKey: ["readings", motorId],
    queryFn: () => apiClient.get(`/motors/${motorId}/readings?limit=200`).then((r) => normalizeReadingsPayload(r.data)),
    enabled: !!motorId,
  });

  const sensorQ = useQuery({
    queryKey: ["sensor-trend", motorId, sensor],
    queryFn: () => apiClient.get(`/insights/sensor-trend/${motorId}?sensor=${sensor}&limit=200`).then((r) => normalizeSensorTrendPayload(r.data)),
    enabled: !!motorId,
  });

  const predictMut = useMutation({
    mutationFn: () => apiClient.get(`/predict/${motorId}`).then((r) => normalizePredictionPayload(r.data)),
    onError: () => toast.error("Prediction failed"),
  });

  const textColor = resolved === "dark" ? "rgba(255,255,255,0.35)" : "rgba(0,0,0,0.3)";
  const gridStroke = resolved === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";

  return (
    <div className="space-y-6">
      <DataState isLoading={motorQ.isLoading} isError={motorQ.isError} error={motorQ.error} onRetry={() => motorQ.refetch()}>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold">{motorQ.data?.name}</h2>
            <div className="flex items-center gap-3 mt-1">
              <StatusBadge status={motorQ.data?.status || "inactive"} pulse={motorQ.data?.status === "critical"} />
              {motorQ.data?.location && <span className="text-sm text-muted-foreground">📍 {motorQ.data.location}</span>}
            </div>
          </div>
          <motion.button
            whileTap={{ scale: 0.98 }}
            onClick={() => predictMut.mutate()}
            disabled={predictMut.isPending}
            className="flex items-center gap-2 px-5 py-2.5 min-h-[2.75rem] rounded-xl text-sm font-semibold text-primary-foreground disabled:opacity-50 transition-all active:scale-[0.98]"
            style={{
              background: "linear-gradient(180deg, #3b82f6 0%, #2563eb 100%)",
              borderTop: "1px solid rgba(255,255,255,0.3)",
              boxShadow: "0 4px 14px -2px rgba(37, 99, 235, 0.5), inset 0 1px 0 rgba(255,255,255,0.2)",
            }}
          >
            {predictMut.isPending ? <RefreshCw size={16} className="animate-spin" /> : <Brain size={16} />}
            Run Prediction
          </motion.button>
        </div>
      </DataState>

      {/* Prediction Result */}
      {predictMut.data && (
        <GlassCard className="relative overflow-hidden">
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ background: riskGlow[predictMut.data.risk_level] || riskGlow.medium }}
          />
          <div className="relative">
            <h3 className="text-sm font-semibold mb-3">Prediction Result</h3>
            <div className="flex flex-wrap gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Prediction</p>
                <p className="font-semibold">{predictMut.data.prediction}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Confidence</p>
                <p className="font-semibold">{(Math.max(0, Math.min(1, Number(predictMut.data.confidence) || 0)) * 100).toFixed(1)}%</p>
              </div>
              {Number.isFinite(Number((predictMut.data.details as any)?.predicted_rul)) && (
                <div>
                  <p className="text-xs text-muted-foreground">Predicted RUL</p>
                  <p className="font-semibold">{Number((predictMut.data.details as any)?.predicted_rul).toFixed(0)} cycles</p>
                  <p className="text-xs text-muted-foreground">
                    ~{(Number((predictMut.data.details as any)?.predicted_rul) * RUL_SECONDS_PER_CYCLE / 60).toFixed(1)} min
                  </p>
                </div>
              )}
              <div>
                <p className="text-xs text-muted-foreground">Risk Level</p>
                <StatusBadge status={predictMut.data.risk_level} />
              </div>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Sensor Trend */}
      <GlassCard>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 gap-2">
          <h3 className="text-sm font-semibold">Sensor Trend</h3>
          <div className="relative flex rounded-xl p-1" style={{ background: "hsl(var(--muted))", boxShadow: "inset 0 2px 6px rgba(0,0,0,0.12)" }}>
            {SENSORS.map((s) => (
              <button
                key={s}
                onClick={() => setSensor(s)}
                className="relative z-10 px-3 py-2 min-h-[2.75rem] rounded-lg text-xs font-medium transition-all"
                style={sensor === s ? {} : { color: "hsl(var(--muted-foreground))" }}
              >
                {sensor === s && (
                  <motion.div
                    layoutId="sensorIndicator"
                    className="absolute inset-0 rounded-lg bg-background"
                    style={{ boxShadow: "0 2px 4px rgba(0,0,0,0.1)" }}
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                )}
                <span className="relative z-10">{s.toUpperCase()}</span>
              </button>
            ))}
          </div>
        </div>
        <DataState isLoading={sensorQ.isLoading} isError={sensorQ.isError} error={sensorQ.error} onRetry={() => sensorQ.refetch()} isEmpty={!sensorQ.data?.length}>
          <div className="h-64 recharts-neon-glow">
              <ResponsiveContainer>
                <AreaChart data={sensorQ.data || []}>
                  <defs>
                    <linearGradient id="sensorGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(215, 90%, 52%)" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="hsl(215, 90%, 52%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={gridStroke} strokeDasharray="4 6" vertical={false} />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 10, fill: textColor }} axisLine={false} tickLine={false} tickFormatter={(v) => new Date(v).toLocaleTimeString()} />
                  <YAxis tick={{ fontSize: 10, fill: textColor }} axisLine={false} tickLine={false} />
                  <Tooltip content={<GlassTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="hsl(215, 90%, 52%)"
                    fill="url(#sensorGrad)"
                    strokeWidth={2.5}
                    style={{ filter: "drop-shadow(0 0 6px hsl(215 90% 52% / 0.4))" }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
        </DataState>
      </GlassCard>

      {/* Readings Table */}
      <GlassCard>
        <h3 className="text-sm font-semibold mb-4">Historical Readings</h3>
        <DataState isLoading={readingsQ.isLoading} isError={readingsQ.isError} error={readingsQ.error} onRetry={() => readingsQ.refetch()} isEmpty={!readingsQ.data?.length} emptyText="No readings">
           <div className="overflow-x-auto max-h-96">
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-20" style={{ backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)", background: "hsl(var(--background) / 0.88)" }}>
                <tr style={{ borderBottom: "1px solid rgba(0,0,0,0.04)" }} className="text-muted-foreground">
                  <th className="text-left py-2 px-3 font-medium">Timestamp</th>
                  {readingsQ.data?.[0] && Object.keys(readingsQ.data[0]).filter((k) => !["id", "motor_id", "timestamp"].includes(k)).slice(0, 8).map((key) => (
                    <th key={key} className="text-left py-2 px-3 font-medium">{key}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(readingsQ.data || []).slice(0, 50).map((r, i) => (
                  <tr key={i} className="hover:bg-accent/30 transition-colors" style={{ borderBottom: "1px solid rgba(0,0,0,0.04)" }}>
                    <td className="py-2 px-3 text-xs text-muted-foreground">{new Date(r.timestamp).toLocaleString()}</td>
                    {Object.entries(r).filter(([k]) => !["id", "motor_id", "timestamp"].includes(k)).slice(0, 8).map(([k, v]) => (
                      <td key={k} className="py-2 px-3 text-xs">{typeof v === "number" ? (v as number).toFixed(3) : String(v)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DataState>
      </GlassCard>
    </div>
  );
};

export default MotorDetailPage;
