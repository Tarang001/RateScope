import { ErrorBox, Loading } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";

export default function Health() {
  const { data, error, loading, reload } = useAsync(() => api.health(), [], 6000);

  if (loading) return <Loading label="Checking systems" />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return null;

  const rows = [
    ["API", data.api_health],
    ["PostgreSQL", data.postgres ? "up" : "down"],
    ["Redis", data.redis ? "up" : "down"],
    ["Kafka", data.kafka ? "up" : "down"],
    ["Events processed", data.events_processed],
    ["Processing latency (ms)", data.processing_latency_ms],
    ["Consumer lag", data.consumer_lag],
    ["DLQ count", data.dlq_count],
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">System Health</h2>
          <p className="text-sm text-slate-500">Pipeline and dependency status for the local stack.</p>
        </div>
        <button className="btn btn-ghost" onClick={() => void reload()}>
          Refresh
        </button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {rows.map(([k, v]) => (
          <div key={String(k)} className="card">
            <p className="text-xs uppercase tracking-wide text-slate-500">{k}</p>
            <p className="mt-2 text-2xl font-semibold">{String(v)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
