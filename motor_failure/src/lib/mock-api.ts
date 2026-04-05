/**
 * Mock API layer – returns mock data with simulated latency.
 * Intercepts apiClient when mock mode is active.
 */
import {
  mockUser,
  mockFleetOverview,
  mockStatusDistribution,
  mockAlertsTrend,
  mockAlerts,
  mockMotors,
  mockPrediction,
  generateSensorTrend,
  generateReadings,
} from "./mock-data";

const delay = () => new Promise((r) => setTimeout(r, 500 + Math.random() * 300));

type MockRoute = {
  match: (method: string, url: string) => boolean;
  handle: (url: string, body?: any) => any;
};

const routes: MockRoute[] = [
  // Auth
  { match: (m, u) => m === "post" && u.includes("/auth/login"), handle: () => ({ message: "OTP sent", email: "demo@motorpredict.io" }) },
  { match: (m, u) => m === "post" && u.includes("/auth/verify-otp"), handle: () => ({ access_token: "mock-jwt-token", token_type: "bearer" }) },
  { match: (m, u) => m === "post" && u.includes("/auth/resend-otp"), handle: () => ({ message: "OTP resent" }) },
  { match: (m, u) => m === "get" && u.includes("/auth/me"), handle: () => mockUser },
  { match: (m, u) => m === "post" && u.includes("/auth/logout"), handle: () => ({ message: "Logged out" }) },

  // Insights
  { match: (m, u) => m === "get" && u.includes("/insights/fleet-overview"), handle: () => mockFleetOverview },
  { match: (m, u) => m === "get" && u.includes("/insights/status-distribution"), handle: () => mockStatusDistribution },
  { match: (m, u) => m === "get" && u.includes("/insights/alerts-trend"), handle: () => mockAlertsTrend },
  { match: (m, u) => m === "get" && u.includes("/insights/sensor-trend"), handle: () => generateSensorTrend(200) },

  // Motors
  { match: (m, u) => m === "get" && /\/motors\/[^/]+\/readings/.test(u), handle: (u) => { const id = u.match(/\/motors\/([^/]+)/)?.[1] || "mot-001"; return generateReadings(id); } },
  { match: (m, u) => m === "get" && /\/motors\/[^/]+/.test(u) && !u.includes("/readings"), handle: (u) => { const id = u.match(/\/motors\/([^/]+)/)?.[1]; return mockMotors.find((m) => m.id === id) || mockMotors[0]; } },
  { match: (m, u) => m === "get" && u.endsWith("/motors"), handle: () => mockMotors },
  { match: (m, u) => m === "post" && u.endsWith("/motors"), handle: (_u, body) => ({ id: `mot-new-${Date.now()}`, name: body?.name || "New Motor", status: "healthy", ...body }) },
  { match: (m, u) => m === "delete" && u.includes("/motors/"), handle: () => ({ message: "Motor deactivated" }) },
  { match: (m, u) => m === "post" && u.includes("/reactivate"), handle: () => ({ message: "Motor reactivated" }) },

  // Alerts
  { match: (m, u) => m === "get" && u.includes("/alerts"), handle: () => mockAlerts },
  { match: (m, u) => m === "post" && u.includes("/alerts/batch/ack"), handle: () => ({ message: "Batch acknowledged" }) },
  { match: (m, u) => m === "post" && u.includes("/alerts/") && u.includes("/ack"), handle: () => ({ message: "Acknowledged" }) },

  // Predict
  { match: (m, u) => m === "get" && u.includes("/predict/"), handle: (u) => ({ ...mockPrediction, motor_id: u.match(/\/predict\/([^?]+)/)?.[1] || mockPrediction.motor_id }) },
];

export async function mockRequest(method: string, url: string, body?: any): Promise<any> {
  await delay();
  const m = method.toLowerCase();
  for (const route of routes) {
    if (route.match(m, url)) {
      return { data: route.handle(url, body), status: 200 };
    }
  }
  return { data: { detail: "Mock: not found" }, status: 404 };
}
