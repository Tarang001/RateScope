import { useEffect, useMemo, useState } from "react";
import { Empty, ErrorBox, Loading, SeverityBadge } from "../components/States";
import { api, alertsStreamUrl, apiKey } from "../services/api";
import type { AlertItem } from "../types";

export default function Alerts() {
  const [items, setItems] = useState<AlertItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [city, setCity] = useState("");
  const [supplier, setSupplier] = useState("");
  const [type, setType] = useState("");
  const [severity, setSeverity] = useState("");
  const [live, setLive] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.alerts({ city, supplier, type, severity });
      setItems(res.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [city, supplier, type, severity]);

  useEffect(() => {
    if (!live) return;
    const params = new URLSearchParams({ api_key: apiKey() });
    if (city) params.set("city", city);
    const es = new EventSource(`${alertsStreamUrl()}?${params.toString()}`);
    es.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data) as { items: AlertItem[] };
        if (payload.items) setItems(payload.items);
      } catch {
        /* ignore malformed SSE frames */
      }
    };
    const t = setInterval(() => void load(), 8000);
    return () => {
      es.close();
      clearInterval(t);
    };
  }, [live, city, supplier, type, severity]);

  async function act(id: number, status: string) {
    await api.patchAlert(id, status);
    await load();
  }

  const filtered = useMemo(() => items, [items]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Live Alerts</h2>
          <p className="text-sm text-slate-500">Parity breaks and price anomalies. SSE-backed polling every 4s.</p>
        </div>
        <button className="btn btn-ghost" onClick={() => setLive((v) => !v)}>
          {live ? "Pause live" : "Resume live"}
        </button>
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <input className="card py-2" placeholder="City" value={city} onChange={(e) => setCity(e.target.value)} />
        <select className="card py-2" value={supplier} onChange={(e) => setSupplier(e.target.value)}>
          <option value="">All suppliers</option>
          <option>AGODA</option>
          <option>BOOKING</option>
          <option>EXPEDIA</option>
        </select>
        <select className="card py-2" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">All types</option>
          <option value="PARITY">PARITY</option>
          <option value="ANOMALY">ANOMALY</option>
        </select>
        <select className="card py-2" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          <option value="">All severities</option>
          <option>LOW</option>
          <option>MEDIUM</option>
          <option>HIGH</option>
        </select>
      </div>
      {loading && <Loading label="Loading alerts" />}
      {error && <ErrorBox message={error} onRetry={load} />}
      {!loading && !error && filtered.length === 0 && (
        <Empty title="No alerts match" hint="Wait for the simulator or widen filters." />
      )}
      {!loading && filtered.length > 0 && (
        <div className="card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-slate-500">
                <th className="py-2">When</th>
                <th>Hotel</th>
                <th>City</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Title</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((a) => (
                <tr key={a.id} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-2 whitespace-nowrap">{new Date(a.created_at).toLocaleString()}</td>
                  <td>{a.hotel_name}</td>
                  <td>{a.city}</td>
                  <td>{a.alert_type}</td>
                  <td>
                    <SeverityBadge value={a.severity} />
                  </td>
                  <td>{a.status}</td>
                  <td className="max-w-xs truncate">{a.title}</td>
                  <td className="space-x-2 whitespace-nowrap">
                    {a.status === "OPEN" && (
                      <button className="btn btn-ghost" onClick={() => void act(a.id, "ACKNOWLEDGED")}>
                        Ack
                      </button>
                    )}
                    {a.status !== "RESOLVED" && (
                      <button className="btn btn-primary" onClick={() => void act(a.id, "RESOLVED")}>
                        Resolve
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="hidden text-xs text-slate-400">stream {alertsStreamUrl()} key {apiKey()}</p>
    </div>
  );
}
