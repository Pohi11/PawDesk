import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PawDesk",
  description: "Booking intake desk for pet care businesses",
};

const NAV = [
  { href: "/", label: "Requests" },
  { href: "/demo", label: "Demo" },
  { href: "/reviews", label: "Review queue" },
  { href: "/metrics", label: "Metrics" },
  { href: "/evals", label: "Evals" },
] as const;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <header className="border-b border-zinc-200 bg-white">
          <nav className="mx-auto flex max-w-7xl items-center gap-6 px-6 py-3">
            <Link href="/" className="text-lg font-semibold tracking-tight">
              PawDesk
            </Link>
            <ul className="flex gap-4 text-sm text-zinc-600">
              {NAV.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="hover:text-zinc-950">
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
