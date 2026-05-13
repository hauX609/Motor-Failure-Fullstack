import { useState, useEffect, useRef, useCallback } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { API_BASE, isMockActive } from "@/lib/api-client";
import { generateLivePayload } from "@/lib/mock-data";
import type { LivePayload } from "@/types/dto";

export function useLiveStream() {
  const [data, setData] = useState<LivePayload | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mockTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startPolling = useCallback(() => {
    if (pollTimerRef.current) return;
    pollTimerRef.current = setInterval(async () => {
      try {
        const token = localStorage.getItem("auth_token");
        const res = await fetch(`${API_BASE}/insights/fleet-overview`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.ok) {
          const overview = await res.json();
          setData((prev) => ({ ...prev, fleet_overview: overview }));
        }
      } catch {}
    }, 30000);
  }, []);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (!token) return;

    // Mock SSE — push synthetic data every 5s
    if (isMockActive()) {
      setData(generateLivePayload());
      mockTimerRef.current = setInterval(() => {
        setData(generateLivePayload());
      }, 5000);
      return () => {
        if (mockTimerRef.current) clearInterval(mockTimerRef.current);
      };
    }

    const ctrl = new AbortController();
    controllerRef.current = ctrl;

    fetchEventSource(`${API_BASE}/insights/live/stream?interval=5`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: ctrl.signal,
      onmessage(ev) {
        try {
          const payload: LivePayload = JSON.parse(ev.data);
          setData(payload);
          stopPolling();
        } catch {}
      },
      onerror() {
        startPolling();
      },
      onclose() {
        startPolling();
      },
    }).catch(() => {
      startPolling();
    });

    return () => {
      ctrl.abort();
      stopPolling();
    };
  }, [startPolling, stopPolling]);

  return data;
}
