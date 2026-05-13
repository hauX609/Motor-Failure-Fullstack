import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import apiClient from "@/lib/api-client";
import GlassCard from "@/components/GlassCard";
import GlassTooltip from "@/components/GlassTooltip";
import GlassSkeleton from "@/components/GlassSkeleton";
import AnimatedCounter from "@/components/AnimatedCounter";
import StatusBadge from "@/components/StatusBadge";
import DataState from "@/components/DataState";
import { useLiveStream } from "@/hooks/useLiveStream";
import type { FleetOverview, StatusDistribution, AlertTrend, Alert } from "@/types/dto";
import { Activity, Cpu, AlertTriangle, Shield, Bell } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, CartesianGrid } from "recharts";
import { useTheme } from "@/context/ThemeContext";
import { toast } from "sonner";

const PIE_GRADIENT_FILLS = [
  "url(#gradHealthy)",
  "url(#gradWarning)",
  "url(#gradCritical)",
  "url(#gradInactive)",
];

const containerVariants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.05 }, // Reduced from 0.08 for faster cascade
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring" as const, stiffness: 200, damping: 20 }, // Less jank
  },
};

function normalizeStatusDistribution(value: unknown): StatusDistribution[] {
  if (Array.isArray(value)) {
    return value.map((entry: any) => ({
      status: String(entry?.status ?? "Unknown"),
      count: Number(entry?.count ?? 0),
    }));
  }

  const distribution = value && typeof value === "object" ? (value as Record<string, unknown>).distribution : undefined;
  if (Array.isArray(distribution)) {
    return distribution.map((entry: any) => ({
      status: String(entry?.status ?? "Unknown"),
      count: Number(entry?.count ?? 0),
    }));
  }

  const source = value && typeof value === "object" ? (distribution && typeof distribution === "object" ? distribution : value) : null;
  if (source && typeof source === "object") {
    return Object.entries(source as Record<string, unknown>).map(([status, count]) => {
      const key = String(status).toLowerCase();
      const normalizedStatus =
        key === "optimal" ? "healthy" :
        key === "degrading" ? "warning" :
        key;

      return {
        status: normalizedStatus,
        count: Number(count ?? 0),
      };
    });
  }

  return [];
}

function normalizeAlertsTrend(value: unknown): AlertTrend[] {
  const raw = Array.isArray(value)
    ? value
    : value && typeof value === "object" && Array.isArray((value as Record<string, unknown>).trend)
      ? ((value as Record<string, unknown>).trend as unknown[])
      : [];

  if (!raw.length) {
    const today = new Date();
    return Array.from({ length: 7 }).map((_, idx) => {
      const d = new Date(today);
      d.setDate(today.getDate() - (6 - idx));
      const date = d.toISOString().slice(0, 10);
      return { date, count: 0 };
    });
  }

  // Backend returns rows like { day, severity, count }.
  const grouped = new Map<string, number>();
  for (const row of raw as any[]) {
    const date = String(row?.date ?? row?.day ?? "");
    if (!date) continue;
    const prev = grouped.get(date) ?? 0;
    grouped.set(date, prev + Number(row?.count ?? 0));
  }

  return Array.from(grouped.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, count]) => ({ date, count }));
}

function fillAlertsTrend(points: AlertTrend[]): AlertTrend[] {
  if (points.length >= 7) return points;

  const byDate = new Map(points.map((item) => [item.date, item.count]));
  const today = new Date();
  return Array.from({ length: 7 }).map((_, idx) => {
    const d = new Date(today);
    d.setDate(today.getDate() - (6 - idx));
    const date = d.toISOString().slice(0, 10);
    return { date, count: Number(byDate.get(date) ?? 0) };
  });
}

function normalizeAlerts(value: unknown): Alert[] {
  const raw = Array.isArray(value)
    ? value
    : value && typeof value === "object" && Array.isArray((value as Record<string, unknown>).alerts)
      ? ((value as Record<string, unknown>).alerts as unknown[])
      : [];

  const normalizeSeverity = (severity: unknown): Alert["severity"] => {
    const s = String(severity ?? "").toLowerCase();
    if (s === "critical") return "critical";
    if (s === "warning" || s === "degrading") return "warning";
    return "info";
  };

  return raw.map((a: any) => ({
    id: String(a?.id ?? a?.alert_id ?? ""),
    motor_id: String(a?.motor_id ?? ""),
    motor_name: a?.motor_name,
    severity: normalizeSeverity(a?.severity),
    message: String(a?.message ?? ""),
    acknowledged: Boolean(a?.acknowledged),
    created_at: String(a?.created_at ?? a?.timestamp ?? new Date().toISOString()),
  }));
}

function normalizeFleetOverview(value: unknown, statusDist: StatusDistribution[]): FleetOverview | undefined {
  if (!value || typeof value !== "object") return undefined;

  const data = value as Record<string, unknown>;
  const statusMap = new Map(statusDist.map((s) => [String(s.status).toLowerCase(), Number(s.count || 0)]));
  const statusTotal = Array.from(statusMap.values()).reduce((sum, n) => sum + Number(n || 0), 0);

  const activeMotors = Number(data.active_motors ?? 0);
  const warningMotors = Number(data.warning_motors ?? statusMap.get("warning") ?? statusMap.get("degrading") ?? 0);
  const criticalMotors = Number(data.critical_motors ?? statusMap.get("critical") ?? 0);
  const healthyFromData = data.healthy_motors;
  const healthyFromStatus = statusMap.get("healthy") ?? statusMap.get("optimal");
  const healthyMotors =
    healthyFromData !== undefined && healthyFromData !== null
      ? Number(healthyFromData)
      : (healthyFromStatus !== undefined && (statusTotal > 0 || activeMotors === 0))
        ? Number(healthyFromStatus)
        : Math.max(0, activeMotors - warningMotors - criticalMotors);
  const inactiveMotors = Number(statusMap.get("inactive") ?? 0);

  return {
    total_motors: Number(data.total_motors ?? activeMotors + inactiveMotors),
    active_motors: activeMotors,
    healthy_motors: healthyMotors,
    warning_motors: warningMotors,
    critical_motors: criticalMotors,
    total_alerts: Number(data.total_alerts ?? data.open_alerts ?? 0),
    unacknowledged_alerts: Number(data.unacknowledged_alerts ?? data.open_alerts ?? 0),
  };
}

const DashboardPage: React.FC = () => {
  const { resolved } = useTheme();
  const qc = useQueryClient();
  const liveData = useLiveStream();

  const seedDemo = useMutation({
    mutationFn: () => apiClient.post("/dev/seed-demo-data"),
    onSuccess: () => {
      toast.success("Demo data seeded");
      qc.invalidateQueries({ queryKey: ["fleet-overview"] });
      qc.invalidateQueries({ queryKey: ["status-distribution"] });
      qc.invalidateQueries({ queryKey: ["alerts-trend"] });
      qc.invalidateQueries({ queryKey: ["latest-alerts"] });
      qc.invalidateQueries({ queryKey: ["all-alerts"] });
      qc.invalidateQueries({ queryKey: ["motors"] });
    },
    onError: () => toast.error("Failed to seed demo data"),
  });

  const fleetQ = useQuery({
    queryKey: ["fleet-overview"],
    queryFn: () => apiClient.get<FleetOverview>("/insights/fleet-overview").then((r) => r.data),
    refetchInterval: 30000,
  });

  const statusQ = useQuery({
    queryKey: ["status-distribution"],
    queryFn: () => apiClient.get("/insights/status-distribution").then((r) => normalizeStatusDistribution(r.data)),
    refetchInterval: 30000,
  });

  const trendQ = useQuery({
    queryKey: ["alerts-trend"],
    queryFn: () => apiClient.get("/insights/alerts-trend?days=7").then((r) => fillAlertsTrend(normalizeAlertsTrend(r.data))),
  });

  const alertsQ = useQuery({
    queryKey: ["latest-alerts"],
    queryFn: () => apiClient.get("/alerts?limit=20").then((r) => normalizeAlerts(r.data)),
    refetchInterval: 30000,
  });

  const statusDistRaw = normalizeStatusDistribution(liveData?.status_distribution ?? statusQ.data);
  const fleet = normalizeFleetOverview(liveData?.fleet_overview || fleetQ.data, statusDistRaw);
  const statusTotal = statusDistRaw.reduce((sum, item) => sum + Number(item.count || 0), 0);
  const statusDist =
    statusTotal > 0
      ? statusDistRaw
      : fleet
        ? [
            { status: "healthy", count: Number(fleet.healthy_motors || 0) },
            { status: "warning", count: Number(fleet.warning_motors || 0) },
            { status: "critical", count: Number(fleet.critical_motors || 0) },
          ].filter((x) => x.count > 0)
        : statusDistRaw;
  const latestAlerts = normalizeAlerts(liveData?.recent_alerts ?? alertsQ.data);

  const textColor = resolved === "dark" ? "rgba(255,255,255,0.35)" : "rgba(0,0,0,0.3)";
  const gridStroke = resolved === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)";

  const kpiItems = fleet
    ? [
        { label: "Total Motors", value: fleet.total_motors, icon: Cpu, color: "text-primary" },
        { label: "Active", value: fleet.active_motors, icon: Activity, color: "text-status-healthy" },
        { label: "Warnings", value: fleet.warning_motors, icon: AlertTriangle, color: "text-status-warning" },
        { label: "Critical", value: fleet.critical_motors, icon: Shield, color: "text-status-critical" },
        { label: "Unack Alerts", value: fleet.unacknowledged_alerts, icon: Bell, color: "text-destructive" },
      ]
    : [];

  const isFleetLoading = fleetQ.isLoading && !fleet;

  return (
    <motion.div
      className="space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="show"
      style={{ willChange: "transform, opacity" }}
    >
      <motion.div variants={itemVariants} className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Fleet Dashboard</h2>
          <p className="text-sm text-muted-foreground">Real-time motor health overview</p>
        </div>
        {liveData && (
          <span className="flex items-center gap-1.5 text-xs text-status-healthy font-medium">
            <span className="w-2 h-2 rounded-full bg-status-healthy pulse-live" />
            Live
          </span>
        )}
      </motion.div>

      {/* KPI Cards */}
      {isFleetLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <GlassSkeleton count={5} className="h-[4.5rem]" />
        </div>
      ) : (
        <DataState isLoading={false} isError={fleetQ.isError && !fleet} error={fleetQ.error} onRetry={() => fleetQ.refetch()} isEmpty={false}>
          <motion.div
            className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4"
            variants={containerVariants}
          >
            {kpiItems.map((kpi) => (
              <motion.div key={kpi.label} variants={itemVariants} style={{ willChange: "transform, opacity" }}>
                <GlassCard hover>
                  <div className="flex items-center gap-3">
                    <div className={`min-w-[2.75rem] min-h-[2.75rem] w-[2.75rem] h-[2.75rem] rounded-xl bg-accent/50 flex items-center justify-center ${kpi.color}`}>
                      <kpi.icon size={18} />
                    </div>
                    <div>
                      <AnimatedCounter value={kpi.value} className="text-2xl font-bold" />
                      <p className="text-xs text-muted-foreground">{kpi.label}</p>
                    </div>
                  </div>
                </GlassCard>
              </motion.div>
            ))}
          </motion.div>
        </DataState>
      )}

      {/* Charts row */}
      <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-3 gap-6" style={{ willChange: "transform, opacity" }}>
        {/* Status Pie */}
        <GlassCard className="lg:col-span-1">
          <h3 className="text-sm font-semibold mb-4">Status Distribution</h3>
          {statusQ.isLoading && !statusDist ? (
            <GlassSkeleton className="h-52" />
          ) : (
            <DataState isLoading={false} isError={statusQ.isError && !statusDist} error={statusQ.error} onRetry={() => statusQ.refetch()} isEmpty={!statusDist?.length}>
              <div className="h-52">
                <ResponsiveContainer>
                  <PieChart>
                    <defs>
                      <linearGradient id="gradHealthy" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#22c55e" stopOpacity={1}/>
                        <stop offset="100%" stopColor="#166534" stopOpacity={1}/>
                      </linearGradient>
                      <linearGradient id="gradWarning" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#f59e0b" stopOpacity={1}/>
                        <stop offset="100%" stopColor="#b45309" stopOpacity={1}/>
                      </linearGradient>
                      <linearGradient id="gradCritical" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ef4444" stopOpacity={1}/>
                        <stop offset="100%" stopColor="#991b1b" stopOpacity={1}/>
                      </linearGradient>
                      <linearGradient id="gradInactive" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="hsl(220, 14%, 75%)" stopOpacity={1}/>
                        <stop offset="100%" stopColor="hsl(220, 14%, 55%)" stopOpacity={1}/>
                      </linearGradient>
                    </defs>
                    <Pie data={statusDist || []} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={80} innerRadius={45} strokeWidth={0}>
                      {(statusDist || []).map((_entry, i) => (
                        <Cell key={i} fill={PIE_GRADIENT_FILLS[i % PIE_GRADIENT_FILLS.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<GlassTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </DataState>
          )}
        </GlassCard>

        {/* Alerts Trend */}
        <GlassCard className="lg:col-span-2">
          <h3 className="text-sm font-semibold mb-4">Alerts Trend (7 days)</h3>
          {trendQ.isLoading ? (
            <GlassSkeleton className="h-52" />
          ) : (
            <DataState
              isLoading={false}
              isError={trendQ.isError}
              error={trendQ.error}
              onRetry={() => trendQ.refetch()}
              isEmpty={!trendQ.data?.length}
              emptyText="No alerts yet. Run predictions on motors to generate trend data."
            >
              <div className="h-52 recharts-neon-glow">
                <ResponsiveContainer>
                  <AreaChart data={trendQ.data || []}>
                    <defs>
                      <linearGradient id="alertGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="hsl(215, 90%, 52%)" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="hsl(215, 90%, 52%)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke={gridStroke} strokeDasharray="4 6" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: textColor }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: textColor }} axisLine={false} tickLine={false} />
                    <Tooltip content={<GlassTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="count"
                      stroke="hsl(215, 90%, 52%)"
                      fill="url(#alertGrad)"
                      strokeWidth={2.5}
                      style={{ filter: "drop-shadow(0 0 6px hsl(215 90% 52% / 0.4))" }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </DataState>
          )}
        </GlassCard>
      </motion.div>

      {/* Latest Alerts Table */}
      <motion.div variants={itemVariants} style={{ willChange: "transform, opacity" }}>
        <GlassCard>
          <h3 className="text-sm font-semibold mb-4">Latest Alerts</h3>
          {alertsQ.isLoading && !latestAlerts ? (
            <GlassSkeleton count={4} className="h-10 mb-2" />
          ) : (
            <DataState
              isLoading={false}
              isError={alertsQ.isError && !latestAlerts}
              error={alertsQ.error}
              onRetry={() => alertsQ.refetch()}
              isEmpty={!latestAlerts?.length}
              emptyText="No alerts generated yet. Run a prediction to create your first alert."
            >
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border/50 text-muted-foreground">
                      <th className="text-left py-2 px-3 font-medium">Motor</th>
                      <th className="text-left py-2 px-3 font-medium">Severity</th>
                      <th className="text-left py-2 px-3 font-medium">Message</th>
                      <th className="text-left py-2 px-3 font-medium">Status</th>
                      <th className="text-left py-2 px-3 font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(latestAlerts || []).map((alert) => (
                      <tr key={alert.id} className="border-b border-border/30 hover:bg-accent/30 transition-colors min-h-[2.75rem]">
                        <td className="py-3 px-3 font-medium">{alert.motor_name || alert.motor_id}</td>
                        <td className="py-3 px-3"><StatusBadge status={alert.severity} pulse={alert.severity === "critical"} /></td>
                        <td className="py-3 px-3 text-muted-foreground max-w-xs truncate">{alert.message}</td>
                        <td className="py-3 px-3">{alert.acknowledged ? <span className="text-muted-foreground text-xs">Ack</span> : <span className="text-status-warning text-xs font-medium">Pending</span>}</td>
                        <td className="py-3 px-3 text-muted-foreground text-xs">{new Date(alert.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </DataState>
          )}
          {!alertsQ.isLoading && !latestAlerts?.length && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <Link
                to="/motors"
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90"
              >
                Go To Motors
              </Link>
              <button
                onClick={() => seedDemo.mutate()}
                disabled={seedDemo.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-foreground hover:opacity-90 disabled:opacity-60"
              >
                {seedDemo.isPending ? "Seeding..." : "Seed Demo Data"}
              </button>
            </div>
          )}
        </GlassCard>
      </motion.div>
    </motion.div>
  );
};

export default DashboardPage;
