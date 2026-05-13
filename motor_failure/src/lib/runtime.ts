const isProd = import.meta.env.PROD;
const appEnv = String(import.meta.env.VITE_APP_ENV || (isProd ? "production" : "development")).trim().toLowerCase();
const isProductionLike = isProd || appEnv === "production";
const apiBase = (import.meta.env.VITE_API_BASE_URL || "http://localhost:5001").trim();
const rawUseMock = import.meta.env.VITE_USE_MOCK_DATA === "true";
const allowMockInProd = import.meta.env.VITE_ALLOW_MOCK_IN_PROD === "true";
const enableMock = rawUseMock && (!isProductionLike || allowMockInProd);
const appName = import.meta.env.VITE_APP_NAME || "MotorPredict";
const appVersion = import.meta.env.VITE_APP_VERSION || "dev";
const telemetryEndpoint = (import.meta.env.VITE_CLIENT_LOG_ENDPOINT || "").trim();
const enableTelemetry = import.meta.env.VITE_ENABLE_CLIENT_TELEMETRY === "true";
const enablePerfMonitoring = import.meta.env.VITE_ENABLE_PERF_MONITORING === "true";

export const RUNTIME = {
  appName,
  appVersion,
  isProd,
  appEnv,
  isProductionLike,
  apiBase,
  enableMock,
  allowMockInProd,
  telemetryEndpoint,
  enableTelemetry,
  enablePerfMonitoring,
} as const;

export function validateFrontendConfig(): void {
  if (!isProductionLike) return;

  if (!apiBase) {
    throw new Error("VITE_API_BASE_URL is required in production.");
  }

  if (/localhost|127\.0\.0\.1/.test(apiBase)) {
    // This is a safe fallback warning for production builds that still point to local APIs.
    console.warn(`[${appName}] API base points to localhost in production-like mode: ${apiBase}`);
  }

  if (rawUseMock && !allowMockInProd) {
    console.warn(`[${appName}] VITE_USE_MOCK_DATA is enabled but ignored in production.`);
  }

  if (enableTelemetry && !telemetryEndpoint) {
    console.warn(`[${appName}] Client telemetry is enabled but VITE_CLIENT_LOG_ENDPOINT is not set.`);
  }
}

export function getRuntimeLabel(): string {
  return `${appName}/${appVersion}`;
}
