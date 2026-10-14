import Link from "next/link";

import type { RequirementStatus } from "@/lib/walkthrough";

export function BuildNav() {
  return (
    <nav className="mb-6 flex gap-4 border-b border-zinc-200 pb-2 text-sm">
      <Link href="/build" className="text-zinc-700 hover:text-zinc-950">
        Method &amp; timeline
      </Link>
      <Link href="/build/specs" className="text-zinc-700 hover:text-zinc-950">
        Specs &amp; tests
      </Link>
      <Link href="/build/decisions" className="text-zinc-700 hover:text-zinc-950">
        Decisions
      </Link>
    </nav>
  );
}

const STATUS: Record<RequirementStatus, string> = {
  verified: "bg-emerald-100 text-emerald-800",
  failing: "bg-red-100 text-red-800",
  untested: "bg-amber-100 text-amber-800",
};

export function RequirementBadge({ status }: { status: RequirementStatus }) {
  return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS[status]}`}>{status}</span>;
}
