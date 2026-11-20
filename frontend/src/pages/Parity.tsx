import { useMemo, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Empty, ErrorBox, Loading } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";

type Pair = {
  supplier_a: string;
  supplier_b: string;
  spread_pct: number;
  cheaper: string;
  hotel_id: number;
  city: string;
  stay_date: string;
  price_a: number;
  price_b: number;
};

type Report = {
  threshold_pct: number;
  pairs: Pair[];
  city_heatmap: Array<{ city: string; avg_spread_pct: number; violations: number; max_spread_pct: number }>;
  open_alerts: number;
};

export default function Parity() {
  const [city, setCity] = useState("");
  const { data, error, loading, reload } = useAsync(() => api.parity(city || undefined) as Promise<Report>, [city]);

  const heat = useMemo(() => data?.city_heatmap ?? [], [data]);
  const max = Math.max(1, ...heat.map((h) => h.avg_spread_pct));

  if (loading) return <Loading label="Building parity report" />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Parity Analysis</h2>
          <p className="text-sm text-slate-500">Threshold {data.threshold_pct}% · {data.open_alerts} open parity alerts</p>
        </div>
        <input className="card py-2" placeholder="Filter city" value={city} onChange={(e) => setCity(e.target.value)} />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h3 className="mb-3 font-medium">City-wise spread heatmap</h3>
          {heat.length === 0 ? (
            <Empty title="No city spreads yet" hint="Parity needs multiple suppliers on the same stay." />
          ) : (
            <div className="grid gap-2">
              {heat.map((h) => (
                <div key={h.city} className="flex items-center gap-3">
                  <div className="w-28 text-sm">{h.city}</div>
                  <div className="h-8 flex-1 overflow-hidden rounded bg-slate-100 dark:bg-ink-800">
                    <div
                      className="h-full bg-brand-500"
                      style={{ width: `${(h.avg_spread_pct / max) * 100}%` }}
                      title={`${h.avg_spread_pct}%`}
                    />
                  </div>
                  <div className="w-24 text-right text-xs text-slate-500">
                    {h.avg_spread_pct}% · {h.violations}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="card h-80">
          <h3 className="mb-3 font-medium">Violations by city</h3>
          <ResponsiveContainer width="100%" height="90%">
            <BarChart data={heat}>
              <XAxis dataKey="city" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="violations" fill="#0f766e" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="card overflow-x-auto">
        <h3 className="mb-3 font-medium">Supplier pair comparisons</h3>
        {data.pairs.length === 0 ? (
          <Empty title="No pair violations" hint="Prices are currently within the configured threshold." />
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-slate-500">
                <th className="py-2">City</th>
                <th>Stay</th>
                <th>A</th>
                <th>B</th>
                <th>Spread</th>
                <th>Cheaper</th>
              </tr>
            </thead>
            <tbody>
              {data.pairs.slice(0, 40).map((p, i) => (
                <tr key={i} className="border-t border-slate-100 dark:border-slate-800">
                  <td className="py-2">{p.city}</td>
                  <td>{p.stay_date}</td>
                  <td>
                    {p.supplier_a} ${p.price_a}
                  </td>
                  <td>
                    {p.supplier_b} ${p.price_b}
                  </td>
                  <td>{p.spread_pct}%</td>
                  <td>{p.cheaper}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
