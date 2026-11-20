import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";

const links = [
  { to: "/", label: "Overview" },
  { to: "/alerts", label: "Live Alerts" },
  { to: "/explorer", label: "Price Explorer" },
  { to: "/parity", label: "Parity Analysis" },
  { to: "/ask", label: "Ask RateScope" },
  { to: "/health", label: "System Health" },
];

export default function Layout() {
  const [dark, setDark] = useState(() => localStorage.getItem("rs-theme") !== "light");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("rs-theme", dark ? "dark" : "light");
  }, [dark]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-ink-950">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-ink-900 md:block">
        <div className="mb-8">
          <p className="text-xs uppercase tracking-[0.2em] text-brand-500">Agoda-style intel</p>
          <h1 className="mt-1 text-xl font-semibold">RateScope</h1>
        </div>
        <nav className="space-y-1">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 text-sm ${
                  isActive
                    ? "bg-brand-500/10 font-semibold text-brand-600 dark:text-brand-400"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-ink-800"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="md:pl-64">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white/80 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-ink-900/80">
          <div className="flex gap-2 overflow-x-auto md:hidden">
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} className="whitespace-nowrap rounded-full border px-3 py-1 text-xs dark:border-slate-700">
                {l.label}
              </NavLink>
            ))}
          </div>
          <p className="hidden text-sm text-slate-500 md:block">Hotel rate intelligence · demo key enabled</p>
          <button className="btn btn-ghost" onClick={() => setDark((d) => !d)}>
            {dark ? "Light" : "Dark"}
          </button>
        </header>
        <main className="p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
