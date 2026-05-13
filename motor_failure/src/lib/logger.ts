import { RUNTIME, getRuntimeLabel } from "@/lib/runtime";

type LogLevel = "debug" | "info" | "warn" | "error";

const levelOrder: Record<LogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

const configuredLevel = (import.meta.env.VITE_LOG_LEVEL || (import.meta.env.PROD ? "warn" : "debug")).toLowerCase() as LogLevel;
const currentLevel = levelOrder[configuredLevel] ?? levelOrder.info;

function shouldLog(level: LogLevel): boolean {
  return levelOrder[level] >= currentLevel;
}

function write(level: LogLevel, message: string, meta?: unknown) {
  if (!shouldLog(level)) return;

  const prefix = `[${getRuntimeLabel()}]`;
  const writer = console[level] ?? console.log;

  if (meta === undefined) {
    writer(`${prefix} ${message}`);
    return;
  }

  writer(`${prefix} ${message}`, meta);
}

async function reportRemote(level: LogLevel, message: string, meta?: unknown) {
  if (!RUNTIME.enableTelemetry || !RUNTIME.telemetryEndpoint) return;

  const payload = {
    level,
    message,
    meta,
    app: RUNTIME.appName,
    version: RUNTIME.appVersion,
    href: window.location.href,
    userAgent: navigator.userAgent,
    timestamp: new Date().toISOString(),
  };

  try {
    const body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: "application/json" });
      navigator.sendBeacon(RUNTIME.telemetryEndpoint, blob);
      return;
    }

    await fetch(RUNTIME.telemetryEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    });
  } catch {
    // telemetry must never break the app
  }
}

export const logger = {
  debug: (message: string, meta?: unknown) => {
    write("debug", message, meta);
  },
  info: (message: string, meta?: unknown) => {
    write("info", message, meta);
  },
  warn: (message: string, meta?: unknown) => {
    write("warn", message, meta);
    void reportRemote("warn", message, meta);
  },
  error: (message: string, meta?: unknown) => {
    write("error", message, meta);
    void reportRemote("error", message, meta);
  },
};

export function setupClientErrorHandlers(): void {
  window.addEventListener("error", (event) => {
    logger.error("Unhandled window error", {
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      error: event.error?.message,
    });
  });

  window.addEventListener("unhandledrejection", (event) => {
    logger.error("Unhandled promise rejection", {
      reason: event.reason instanceof Error ? event.reason.message : event.reason,
    });
  });
}
