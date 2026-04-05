import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { logger } from "@/lib/logger";
import { RUNTIME } from "@/lib/runtime";

const routeStartLabel = "frontend-route-start";

const FrontendTelemetry: React.FC = () => {
  const location = useLocation();
  const previousPathRef = useRef<string | null>(null);
  const routeStartedAtRef = useRef<number>(performance.now());

  useEffect(() => {
    if (!RUNTIME.enablePerfMonitoring) return;

    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === "longtask" && entry.duration >= 200) {
          logger.warn("Long task detected", {
            duration_ms: Math.round(entry.duration),
            name: entry.name,
          });
        }
      }
    });

    try {
      observer.observe({ entryTypes: ["longtask"] });
    } catch {
      // Not supported in all browsers; ignore.
    }

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const previousPath = previousPathRef.current;
    const elapsedMs = Math.round(performance.now() - routeStartedAtRef.current);

    if (previousPath) {
      logger.info("Route transition complete", {
        from: previousPath,
        to: `${location.pathname}${location.search}`,
        duration_ms: elapsedMs,
      });
    } else {
      logger.info("Route initialised", {
        to: `${location.pathname}${location.search}`,
      });
    }

    previousPathRef.current = `${location.pathname}${location.search}`;
    routeStartedAtRef.current = performance.now();

    if (RUNTIME.enablePerfMonitoring) {
      try {
        performance.mark(routeStartLabel);
      } catch {
        // Ignore if marks are unsupported or duplicated.
      }
    }
  }, [location.pathname, location.search]);

  return null;
};

export default FrontendTelemetry;
