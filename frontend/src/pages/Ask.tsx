import { useState } from "react";
import { ErrorBox } from "../components/States";
import { api } from "../services/api";

const EXAMPLES = [
  "Which suppliers have the highest price differences in Delhi?",
  "Show high-severity alerts from the last seven days.",
  "Which hotels experienced unusual price increases?",
  "Compare average supplier prices in Bangkok.",
];

export default function Ask() {
  const [question, setQuestion] = useState(EXAMPLES[0]);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(q: string) {
    setLoading(true);
    setError(null);
    try {
      setResult(await api.ask(q));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ask failed");
    } finally {
      setLoading(false);
    }
  }

  const filters = (result?.filters || {}) as Record<string, unknown>;
  const results = (result?.results || {}) as Record<string, unknown>;
  const items = (results.items as unknown[]) || (results.pairs as unknown[]) || [];

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Ask RateScope</h2>
        <p className="text-sm text-slate-500">
          Natural language is mapped to validated filters. The model never writes SQL.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button key={ex} className="btn btn-ghost" onClick={() => setQuestion(ex)}>
            {ex}
          </button>
        ))}
      </div>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void submit(question);
        }}
      >
        <input className="card flex-1 py-3" value={question} onChange={(e) => setQuestion(e.target.value)} />
        <button className="btn btn-primary" disabled={loading}>
          {loading ? "Asking…" : "Ask"}
        </button>
      </form>
      {error && <ErrorBox message={error} />}
      {result && (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="card lg:col-span-1">
            <h3 className="font-medium">Interpreted filters</h3>
            <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(filters, null, 2)}</pre>
            <p className="mt-3 text-sm text-slate-500">{String(result.explanation ?? "")}</p>
            {Boolean(result.fallback) && (
              <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">
                Running without a live LLM key. Set OPENAI_API_KEY to enable model parsing.
              </p>
            )}
          </div>
          <div className="card lg:col-span-2 overflow-auto">
            <h3 className="font-medium">Results</h3>
            {Array.isArray(items) && items.length === 0 && (
              <p className="mt-2 text-sm text-slate-500">No matching rows for those filters.</p>
            )}
            <pre className="mt-2 max-h-[28rem] overflow-auto text-xs">{JSON.stringify(results, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
