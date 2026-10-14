import Link from "next/link";
import { Suspense } from "react";

import { PetAvatar } from "@/components/pet-avatar";
import { Loading, StateTag } from "@/components/ui";
import { backendJson } from "@/lib/backend";
import { formatCost, formatService, formatStay } from "@/lib/format";
import type { RequestRow } from "@/lib/types";

export default function Home() {
  return (
    <Suspense fallback={<Loading label="Loading requests" />}>
      <Desk />
    </Suspense>
  );
}

async function Desk() {
  const rows = await backendJson<RequestRow[]>("/requests?limit=50");
  const waiting = rows.filter((r) => r.status === "needs_review").length;

  return (
    <>
      <section className="mb-12 flex flex-wrap items-end justify-between gap-6">
        <div className="max-w-2xl">
          <h1 className="text-4xl leading-[1.05] font-extrabold sm:text-5xl">
            {waiting === 0
              ? "Nothing is waiting for you."
              : `${waiting} ${waiting === 1 ? "request is" : "requests are"} waiting for you.`}
          </h1>
          <p className="mt-3 text-lg text-muted">
            {waiting === 0
              ? "Every request so far was decided by the checks or already handled by staff."
              : "Each one needs a person before anything is sent. The rest were decided by the checks."}
          </p>
        </div>
        {waiting > 0 ? (
          <Link href="/reviews" className="rounded-full bg-signal px-5 py-2.5 font-medium text-white hover:brightness-110">
            Open the review queue
          </Link>
        ) : (
          <Link href="/demo" className="rounded-full bg-ink px-5 py-2.5 font-medium text-white hover:brightness-125">
            Try a request
          </Link>
        )}
      </section>

      {rows.length === 0 ? (
        <p className="text-muted">
          No requests yet. <Link href="/demo" className="text-code underline">Send one from the demo</Link>{" "}
          and watch it run.
        </p>
      ) : (
        <ol className="divide-y divide-rule overflow-hidden rounded-2xl bg-surface ring-1 ring-rule">
          {rows.map((row) => (
            <li key={row.id}>
              <Link
                href={`/requests/${row.id}`}
                className="grid grid-cols-[1fr_auto] items-center gap-x-6 gap-y-1 px-5 py-4 hover:bg-wash sm:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_auto_5rem]"
              >
                <div className="flex min-w-0 items-center gap-4">
                  <PetAvatar pet={row} />
                  <div className="min-w-0">
                    <div className="truncate font-display text-lg font-semibold">
                      {row.pet ?? <span className="text-muted">Pet not on file</span>}
                    </div>
                    <div className="truncate text-sm text-muted">{row.owner}</div>
                  </div>
                </div>
                <div className="hidden text-sm sm:block">
                  <div>{formatService(row.service)}</div>
                  <div className="text-muted">{formatStay(row.start_date, row.end_date)}</div>
                </div>
                <div className="justify-self-end">
                  <StateTag status={row.status} />
                </div>
                <div className="hidden text-right text-sm text-faint sm:block">{formatCost(row.cost_usd)}</div>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}
