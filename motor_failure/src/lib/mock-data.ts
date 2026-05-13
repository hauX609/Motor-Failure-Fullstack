import type {
  FleetOverview,
  StatusDistribution,
  AlertTrend,
  Alert,
  Motor,
  MotorReading,
  SensorTrendPoint,
  PredictionResult,
  User,
  LivePayload,
} from "@/types/dto";

export const mockUser: User = {
  id: "usr-mock-001",
  email: "demo@motorpredict.io",
  name: "Demo User",
  role: "admin",
};

export const mockFleetOverview: FleetOverview = {
  total_motors: 24,
  active_motors: 21,
  healthy_motors: 16,
  warning_motors: 3,
  critical_motors: 2,
  total_alerts: 47,
  unacknowledged_alerts: 12,
};

export const mockStatusDistribution: StatusDistribution[] = [
  { status: "healthy", count: 16 },
  { status: "warning", count: 3 },
  { status: "critical", count: 2 },
  { status: "inactive", count: 3 },
];

const d = (daysAgo: number) => {
  const dt = new Date();
  dt.setDate(dt.getDate() - daysAgo);
  return dt.toISOString().slice(0, 10);
};

export const mockAlertsTrend: AlertTrend[] = [
  { date: d(6), count: 5, critical: 1, warning: 4 },
  { date: d(5), count: 8, critical: 2, warning: 6 },
  { date: d(4), count: 3, critical: 0, warning: 3 },
  { date: d(3), count: 12, critical: 4, warning: 8 },
  { date: d(2), count: 7, critical: 2, warning: 5 },
  { date: d(1), count: 9, critical: 3, warning: 6 },
  { date: d(0), count: 3, critical: 1, warning: 2 },
];

const ts = (minsAgo: number) => {
  const dt = new Date();
  dt.setMinutes(dt.getMinutes() - minsAgo);
  return dt.toISOString();
};

export const mockAlerts: Alert[] = [
  { id: "alt-001", motor_id: "mot-001", motor_name: "Compressor A1", severity: "critical", message: "Bearing temperature exceeded 120°C threshold", acknowledged: false, created_at: ts(5) },
  { id: "alt-002", motor_id: "mot-003", motor_name: "Pump B2", severity: "warning", message: "Vibration levels rising above normal range", acknowledged: false, created_at: ts(15) },
  { id: "alt-003", motor_id: "mot-005", motor_name: "Fan C1", severity: "critical", message: "Current draw spike detected — potential winding fault", acknowledged: false, created_at: ts(30) },
  { id: "alt-004", motor_id: "mot-002", motor_name: "Conveyor A2", severity: "warning", message: "Lubrication interval overdue by 48 hours", acknowledged: true, created_at: ts(60) },
  { id: "alt-005", motor_id: "mot-004", motor_name: "Mixer D1", severity: "info", message: "Scheduled maintenance reminder", acknowledged: true, created_at: ts(120) },
  { id: "alt-006", motor_id: "mot-001", motor_name: "Compressor A1", severity: "warning", message: "Slight imbalance detected in phase current", acknowledged: false, created_at: ts(180) },
  { id: "alt-007", motor_id: "mot-006", motor_name: "Blower E1", severity: "info", message: "Firmware update available", acknowledged: false, created_at: ts(240) },
  { id: "alt-008", motor_id: "mot-003", motor_name: "Pump B2", severity: "critical", message: "Abnormal acoustic pattern — possible cavitation", acknowledged: false, created_at: ts(300) },
  { id: "alt-009", motor_id: "mot-007", motor_name: "Crusher F1", severity: "warning", message: "Load factor above 92% for extended period", acknowledged: true, created_at: ts(400) },
  { id: "alt-010", motor_id: "mot-002", motor_name: "Conveyor A2", severity: "info", message: "Operating hours milestone: 10,000 hrs", acknowledged: true, created_at: ts(500) },
];

export const mockMotors: Motor[] = [
  { id: "mot-001", name: "Compressor A1", status: "critical", location: "Plant Floor 1", model: "ABB M3BP 315", last_reading_at: ts(1) },
  { id: "mot-002", name: "Conveyor A2", status: "healthy", location: "Plant Floor 1", model: "Siemens 1LE1", last_reading_at: ts(2) },
  { id: "mot-003", name: "Pump B2", status: "warning", location: "Pump House", model: "WEG W22", last_reading_at: ts(3) },
  { id: "mot-004", name: "Mixer D1", status: "healthy", location: "Chemical Lab", model: "Nidec U-GMX", last_reading_at: ts(5) },
  { id: "mot-005", name: "Fan C1", status: "critical", location: "HVAC Zone A", model: "Baldor EM3714T", last_reading_at: ts(8) },
  { id: "mot-006", name: "Blower E1", status: "healthy", location: "HVAC Zone B", model: "Marathon 256T", last_reading_at: ts(10) },
  { id: "mot-007", name: "Crusher F1", status: "warning", location: "Processing Bay", model: "Toshiba EQP III", last_reading_at: ts(12) },
  { id: "mot-008", name: "Agitator G1", status: "inactive", location: "Tank Farm", model: "Regal Beloit", last_reading_at: ts(500) },
];

export function generateSensorTrend(count = 200): SensorTrendPoint[] {
  const points: SensorTrendPoint[] = [];
  let value = 50 + Math.random() * 20;
  for (let i = count; i > 0; i--) {
    const t = new Date();
    t.setMinutes(t.getMinutes() - i);
    value += (Math.random() - 0.48) * 3;
    value = Math.max(20, Math.min(100, value));
    points.push({ timestamp: t.toISOString(), value: parseFloat(value.toFixed(2)) });
  }
  return points;
}

export function generateReadings(motorId: string, count = 50): MotorReading[] {
  return Array.from({ length: count }, (_, i) => {
    const t = new Date();
    t.setMinutes(t.getMinutes() - (count - i));
    return {
      id: `rdg-${i}`,
      motor_id: motorId,
      timestamp: t.toISOString(),
      s11: parseFloat((50 + Math.random() * 30).toFixed(3)),
      s12: parseFloat((40 + Math.random() * 25).toFixed(3)),
      s13: parseFloat((60 + Math.random() * 20).toFixed(3)),
      s14: parseFloat((45 + Math.random() * 35).toFixed(3)),
      s15: parseFloat((55 + Math.random() * 15).toFixed(3)),
    };
  });
}

export const mockPrediction: PredictionResult = {
  motor_id: "mot-001",
  prediction: "Bearing Degradation",
  confidence: 0.87,
  risk_level: "high",
  details: { estimated_rul_hours: 340, failure_mode: "inner_race_fault" },
};

export function generateLivePayload(): LivePayload {
  const jitter = () => Math.floor(Math.random() * 3) - 1;
  return {
    fleet_overview: {
      ...mockFleetOverview,
      warning_motors: mockFleetOverview.warning_motors + jitter(),
      unacknowledged_alerts: Math.max(0, mockFleetOverview.unacknowledged_alerts + jitter()),
    },
    status_distribution: mockStatusDistribution.map((s) => ({
      ...s,
      count: Math.max(0, s.count + jitter()),
    })),
    recent_alerts: mockAlerts.slice(0, 5),
    timestamp: new Date().toISOString(),
  };
}
