export interface LoginRequest {
  identifier: string;
  password: string;
}

export interface LoginResponse {
  message: string;
  email?: string;
}

export interface OtpVerifyRequest {
  email: string;
  otp: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  name?: string;
  role?: string;
}

export interface FleetOverview {
  total_motors: number;
  active_motors: number;
  healthy_motors: number;
  warning_motors: number;
  critical_motors: number;
  total_alerts: number;
  unacknowledged_alerts: number;
}

export interface StatusDistribution {
  status: string;
  count: number;
}

export interface AlertTrend {
  date: string;
  count: number;
  critical?: number;
  warning?: number;
}

export interface Alert {
  id: string;
  motor_id: string;
  motor_name?: string;
  severity: "critical" | "warning" | "info";
  message: string;
  acknowledged: boolean;
  created_at: string;
}

export interface Motor {
  id: string;
  name: string;
  status: "healthy" | "warning" | "critical" | "inactive";
  location?: string;
  model?: string;
  created_at?: string;
  last_reading_at?: string;
}

export interface MotorReading {
  id?: string;
  motor_id: string;
  timestamp: string;
  [key: string]: unknown;
}

export interface SensorTrendPoint {
  timestamp: string;
  value: number;
}

export interface PredictionResult {
  motor_id: string;
  prediction: string;
  confidence: number;
  risk_level: "low" | "medium" | "high";
  details?: Record<string, unknown>;
}

export interface LivePayload {
  fleet_overview?: FleetOverview;
  status_distribution?: StatusDistribution[];
  recent_alerts?: Alert[];
  timestamp?: string;
}
