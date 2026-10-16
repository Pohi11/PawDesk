import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Sans } from "next/font/google";
import Link from "next/link";
import { Suspense, type ReactNode } from "react";

import { BackToTop } from "@/components/back-to-top";
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
  // The Try panel on the home page (spec: run-dashboard "The navigation's Try a request
  // link opens the Try panel").
  { href: "/#try", label: "Try a request" },
  { href: "/requests", label: "Requests" },
  { href: "/metrics", label: "Metrics" },
  { href: "/evals", label: "Evals" },
  { href: "/architecture", label: "Architecture" },
  { href: "/build", label: "How it was built" },
] as const;

// Links that leave the dashboard (spec: run-dashboard "The navigation links to the source
// code and the portfolio").
const SOURCE_URL = "https://github.com/Pohi11/PawDesk";
const PORTFOLIO_URL = "https://pohi.me/";

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
            <div className="ml-auto flex items-center gap-2">
              <ExternalLink
                href={SOURCE_URL}
                className="text-ink ring-1 ring-rule hover:bg-wash"
                icon={<GitHubMark />}
              >
                Source code
              </ExternalLink>
              <ExternalLink href={PORTFOLIO_URL} className="bg-ink text-white hover:bg-ink/85">
                Portfolio
              </ExternalLink>
            </div>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">{children}</main>
        <BackToTop />
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

// Opens in a new tab; noopener keeps the new page from reaching back into this window.
function ExternalLink({
  href,
  className,
  icon,
  children,
}: {
  href: string;
  className: string;
  icon?: ReactNode;
  children: ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`group inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium transition-colors ${className}`}
    >
      {icon}
      {children}
      <span className="sr-only"> (opens in a new tab)</span>
      <svg
        aria-hidden
        viewBox="0 0 16 16"
        className="h-3 w-3 opacity-60 transition-transform group-hover:translate-x-px group-hover:-translate-y-px"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M5 11 11 5M6 5h5v5" />
      </svg>
    </a>
  );
}

function GitHubMark() {
  return (
    <svg aria-hidden viewBox="0 0 16 16" className="h-4 w-4" fill="currentColor">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
    </svg>
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
