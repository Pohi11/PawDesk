import { Suspense } from "react";

// Read on the server only. No NEXT_PUBLIC_ prefix, so it is never bundled into browser JS.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

type Check = { label: string; ok: boolean };

async function checkBackend(): Promise<Check[]> {
  const probe = async (path: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}${path}`, { cache: "no-store" });
      return res.ok;
    } catch {
      return false;
    }
  };
  const [api, db] = await Promise.all([probe("/health"), probe("/health/db")]);
  return [
    { label: "Backend API", ok: api },
    { label: "Postgres", ok: db },
  ];
}

async function SystemStatus() {
  const checks = await checkBackend();
  return (
    <ul className="space-y-2">
      {checks.map((check) => (
        <li key={check.label} className="flex items-center gap-3">
          <span
            className={`h-2.5 w-2.5 rounded-full ${check.ok ? "bg-emerald-500" : "bg-red-500"}`}
          />
          <span>{check.label}</span>
          <span className="text-zinc-500">{check.ok ? "ok" : "unreachable"}</span>
        </li>
      ))}
    </ul>
  );
}

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-8 px-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">PawDesk</h1>
        <p className="mt-2 text-zinc-600 dark:text-zinc-400">
          Booking intake desk for pet care businesses.
        </p>
      </div>
      {/* Uncached data must stream inside a Suspense boundary when Cache Components is on. */}
      <Suspense fallback={<p className="text-zinc-500">Checking services…</p>}>
        <SystemStatus />
      </Suspense>
    </main>
  );
}
