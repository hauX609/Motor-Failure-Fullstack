import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import apiClient, { isMockActive } from "@/lib/api-client";
import type { User } from "@/types/dto";

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<{ email: string }>;
  verifyOtp: (email: string, otp: string) => Promise<void>;
  resendOtp: (email: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem("auth_token"));
  const [loading, setLoading] = useState(true);

  const normalizeUser = (payload: any): User | null => {
    const raw = payload?.user ?? payload;
    if (!raw) return null;

    const email = raw.email ?? "";
    if (!email) return null;

    return {
      id: String(raw.id ?? raw.user_id ?? email),
      email: String(email),
      name: raw.name ?? raw.username,
      role: raw.role,
    } as User;
  };

  const checkSession = useCallback(async () => {
    // In mock mode, auto-authenticate so login is skipped
    if (isMockActive()) {
      const mockToken = "mock-jwt-token";
      localStorage.setItem("auth_token", mockToken);
      setToken(mockToken);
      try {
        const { data } = await apiClient.get("/auth/me");
        setUser(normalizeUser(data) || ({ id: "mock-user", email: "demo@motorpredict.io", name: "Demo User" } as User));
      } catch {
        setUser({ id: "mock-user", email: "demo@motorpredict.io", name: "Demo User" } as User);
      }
      setLoading(false);
      return;
    }

    const t = localStorage.getItem("auth_token");
    if (!t) { setLoading(false); return; }
    try {
      const { data } = await apiClient.get("/auth/me");
      setUser(normalizeUser(data));
      setToken(t);
    } catch {
      localStorage.removeItem("auth_token");
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { checkSession(); }, [checkSession]);

  const login = async (identifier: string, password: string) => {
    const { data } = await apiClient.post("/auth/login", { identifier, password });
    return { email: data.email || identifier };
  };

  const verifyOtp = async (email: string, otp: string) => {
    const { data } = await apiClient.post("/auth/verify-otp", { email, otp });
    const accessToken = data.access_token;
    localStorage.setItem("auth_token", accessToken);
    setToken(accessToken);
    await checkSession();
  };

  const resendOtp = async (email: string) => {
    await apiClient.post("/auth/resend-otp", { email });
  };

  const logout = async () => {
    try { await apiClient.post("/auth/logout"); } catch {}
    localStorage.removeItem("auth_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, verifyOtp, resendOtp, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
