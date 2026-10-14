import Link from "next/link";

import type { RequirementStatus } from "@/lib/walkthrough";

const PAGES = [
  { href: "/build", label: "Method and changes" },
  { href: "/build/specs", label: "Requirements and tests" },
  { href: "/build/decisions", label: "Decisions" },
];

export function BuildNav() {
  return (
    <nav className="mb-10 flex flex-wrap gap-2">
      {PAGES.map((p) => (
        <Link key={p.href} href={p.href} className="rounded-full px-4 py-1.5 text-sm ring-1 ring-rule hover:bg-surface">
          {p.label}
        </Link>
      ))}
    </nav>
  );
}

const STATUS: Record<RequirementStatus, { label: string; style: string }> = {
  verified: { label: "Proven", style: "bg-kennel-soft text-kennel" },
  failing: { label: "Failing", style: "bg-error-soft text-error" },
  untested: { label: "No test", style: "bg-signal-soft text-signal" },
};

export function RequirementBadge({ status }: { status: RequirementStatus }) {
  const { label, style } = STATUS[status];
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>{label}</span>;
}
