import axios from "axios";
import { mockRequest } from "./mock-api";
import { RUNTIME } from "@/lib/runtime";
import { logger } from "@/lib/logger";

const API_BASE = RUNTIME.apiBase;

function isMockActive(): boolean {
  const stored = localStorage.getItem("mock_mode");
  if (!RUNTIME.enableMock) {
    if (stored !== "false") {
      localStorage.setItem("mock_mode", "false");
    }
    return false;
  }
  if (stored !== null) return stored === "true";
  return RUNTIME.enableMock;
}

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  const requestId = crypto.randomUUID();

  config.headers = config.headers ?? {};
  config.headers["X-Request-ID"] = requestId;

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  logger.debug("API request", {
    method: config.method,
    url: config.url,
    requestId,
    mock: isMockActive(),
  });

  return config;
});

// Mock interceptor — short-circuits all requests when mock mode is on
apiClient.interceptors.request.use(async (config) => {
  if (!isMockActive()) return config;

  const method = config.method || "get";
  const url = (config.baseURL || "") + (config.url || "");
  const body = config.data ? (typeof config.data === "string" ? JSON.parse(config.data) : config.data) : undefined;
  const result = await mockRequest(method, url, body);

  logger.debug("Mock API response", {
    method,
    url,
    status: result.status,
  });

  // Throw a cancel-like object that the response interceptor will treat as a successful response
  return Promise.reject({
    __mock: true,
    response: { data: result.data, status: result.status, headers: {}, config },
  });
}, undefined);

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    // Handle mock responses
    if (error?.__mock) {
      return Promise.resolve(error.response);
    }
    if (error.response?.status === 401) {
      const reqUrl = String(error?.config?.url || "");
      const hasAuthHeader = Boolean(error?.config?.headers?.Authorization);

      // Only force logout for protected calls that were sent with a bearer token.
      // Auth bootstrap endpoints (login/verify/reset/etc.) should surface their own errors in-page.
      if (hasAuthHeader && !reqUrl.startsWith("/auth/login") && !reqUrl.startsWith("/auth/verify-otp")) {
        localStorage.removeItem("auth_token");
        if (window.location.pathname !== "/login") {
          window.location.href = "/login";
        }
      }
    }

    logger.error("API request failed", {
      url: error?.config?.url,
      method: error?.config?.method,
      status: error?.response?.status,
      message: error?.response?.data?.error || error?.message,
      requestId: error?.config?.headers?.["X-Request-ID"],
    });

    return Promise.reject(error);
  }
);

export default apiClient;
export { API_BASE, isMockActive };
