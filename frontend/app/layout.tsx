import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Sans } from "next/font/google";
import Link from "next/link";
import { Suspense } from "react";

import { backendJson } from "@/lib/backend";
import type { ReviewItem } from "@/lib/types";

import "./globals.css";

// Variable, with the optical size axis: display cuts for headlines, text cuts for labels.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["opsz", "SOFT"],
});

const plex = IBM_Plex_Sans({
  variable: "--font-plex",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "PawDesk",
  description: "Booking intake desk for pet care businesses",
};

const NAV = [
  { href: "/", label: "Try a request" },
  { href: "/requests", label: "Requests" },
  { href: "/metrics", label: "Metrics" },
  { href: "/evals", label: "Evals" },
  { href: "/architecture", label: "Architecture" },
  { href: "/build", label: "How it was built" },
] as const;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${fraunces.variable} ${plex.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <header className="border-b border-rule bg-surface/80 backdrop-blur">
          <nav className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-6 py-3">
            <Link href="/" className="mr-2 flex items-center gap-2 font-display text-xl font-bold">
              <Paw />
              PawDesk
            </Link>
            <Link
              href="/reviews"
              className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium text-ink ring-1 ring-rule hover:bg-wash"
            >
              Review queue
              <Suspense fallback={null}>
                <WaitingCount />
              </Suspense>
            </Link>
            <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted">
              {NAV.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="hover:text-ink">
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">{children}</main>
      </body>
    </html>
  );
}

async function WaitingCount() {
  const waiting = await backendJson<ReviewItem[]>("/reviews").catch(() => null);
  if (!waiting?.length) return null;
  return (
    <span className="rounded-full bg-signal px-2 py-0.5 text-xs font-semibold text-white">
      {waiting.length}
    </span>
  );
}

function Paw() {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="h-6 w-6 text-kennel" fill="currentColor">
      <ellipse cx="6" cy="9" rx="2.2" ry="2.8" />
      <ellipse cx="10.2" cy="5.6" rx="2.2" ry="2.9" />
      <ellipse cx="14.6" cy="5.6" rx="2.2" ry="2.9" />
      <ellipse cx="18.6" cy="9.2" rx="2.2" ry="2.8" />
      <path d="M12.3 11c-3.2 0-6.3 3.6-6.3 6.4 0 1.9 1.4 2.9 3 2.9 1.5 0 2.2-.8 3.3-.8s1.8.8 3.3.8c1.6 0 3-1 3-2.9 0-2.8-3.1-6.4-6.3-6.4z" />
    </svg>
  );
}
