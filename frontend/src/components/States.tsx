export function Loading({ label = "Loading" }: { label?: string }) {
  return <div className="card animate-pulse text-sm text-slate-500">{label}…</div>;
}

export function Empty({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="card text-center">
      <p className="font-medium">{title}</p>
      <p className="mt-1 text-sm text-slate-500">{hint}</p>
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
      <p className="font-medium">Something went wrong</p>
      <p className="mt-1 text-sm">{message}</p>
      {onRetry && (
        <button className="btn btn-ghost mt-3" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function SeverityBadge({ value }: { value: string }) {
  const map: Record<string, string> = {
    HIGH: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200",
    MEDIUM: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200",
    LOW: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  };
  return <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${map[value] || map.LOW}`}>{value}</span>;
}
