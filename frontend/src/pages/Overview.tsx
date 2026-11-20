import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Empty, ErrorBox, Loading } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";

export default function Overview() {
  const { data, error, loading, reload } = useAsync(() => api.overview(), [], 8000);

  if (loading) return <Loading label="Loading dashboard" />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return <Empty title="No overview yet" hint="Start Docker Compose so the simulator can publish rates." />;

  const kpis = [
    { label: "Hotels monitored", value: data.hotels },
    { label: "Active alerts", value: data.active_alerts },
    { label: "Suppliers", value: data.suppliers },
    { label: "Events processed", value: data.events_processed },
  ];
  const chart = data.recent.map((r) => ({ name: `#${r.id}`, usd: r.price_usd, city: r.city }));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Overview</h2>
        <p className="text-sm text-slate-500">Live hotel rate intelligence across Agoda, Booking, and Expedia.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((k) => (
          <div key={k.label} className="card">
            <p className="text-xs uppercase tracking-wide text-slate-500">{k.label}</p>
            <p className="mt-2 text-3xl font-semibold">{k.value}</p>
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card h-80">
          <h3 className="mb-3 font-medium">Recent pricing activity (USD)</h3>
          {chart.length === 0 ? (
            <Empty title="Waiting for events" hint="The demo simulator publishes rates every few seconds." />
          ) : (
            <ResponsiveContainer width="100%" height="90%">
              <BarChart data={chart}>
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="usd" fill="#14b8a6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="card">
          <h3 className="mb-3 font-medium">Latest observations</h3>
          <div className="max-h-72 overflow-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-slate-500">
                  <th className="py-2">City</th>
                  <th>Stay</th>
                  <th>USD</th>
                  <th>Scenario</th>
                </tr>
              </thead>
              <tbody>
                {data.recent.map((r) => (
                  <tr key={r.id} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="py-2">{r.city}</td>
                    <td>{r.stay_date}</td>
                    <td>${r.price_usd.toFixed(0)}</td>
                    <td>{r.scenario}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
