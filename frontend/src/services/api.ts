const BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const KEY = import.meta.env.VITE_API_KEY || "ratescope-demo-key";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-API-Key", KEY);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const message = body?.error?.message || body?.detail || res.statusText;
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  overview: () => request<import("../types").Overview>("/overview"),
  hotels: (city?: string) => request<import("../types").Hotel[]>(`/hotels${city ? `?city=${encodeURIComponent(city)}` : ""}`),
  hotelRates: (id: number, stayDate?: string) =>
    request<{ hotel: import("../types").Hotel; rooms: import("../types").Room[]; latest_rates: Record<string, unknown>[] }>(
      `/hotels/${id}/rates${stayDate ? `?stay_date=${stayDate}` : ""}`
    ),
  priceHistory: (roomId: number, stayDate?: string) =>
    request<{ items: import("../types").PricePoint[] }>(
      `/rooms/${roomId}/price-history${stayDate ? `?stay_date=${stayDate}` : ""}`
    ),
  alerts: (params: Record<string, string | undefined>) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) q.set(k, v);
    });
    const s = q.toString();
    return request<{ items: import("../types").AlertItem[]; next_cursor: number | null; has_more: boolean }>(
      `/alerts${s ? `?${s}` : ""}`
    );
  },
  patchAlert: (id: number, status: string) => request(`/alerts/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  parity: (city?: string) => request<Record<string, unknown>>(`/parity/report${city ? `?city=${encodeURIComponent(city)}` : ""}`),
  stats: () => request<{ items: Record<string, unknown>[] }>("/stats/daily"),
  health: () => request<import("../types").SystemHealth>("/health/system"),
  ask: (question: string) => request<Record<string, unknown>>("/ask", { method: "POST", body: JSON.stringify({ question }) }),
  live: () => request<{ status: string }>("/health/live"),
};

export function alertsStreamUrl(): string {
  return `${BASE}/stream/alerts`;
}

export function apiKey(): string {
  return KEY;
}
