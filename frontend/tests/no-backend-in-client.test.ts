import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { expect } from "vitest";

import { specTest } from "./spec";

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(name) ? [path] : [];
  });
}

specTest(
  "run-dashboard",
  "The backend is reached only through an allowlisted proxy",
  "no client component reads the backend address",
  () => {
    const files = ["app", "components", "lib"].flatMap(sourceFiles);
    const client = files.filter((f) => /^["']use client["']/m.test(readFileSync(f, "utf8")));
    const clientImports = (text: string) =>
      [...text.matchAll(/from "@\/lib\/([a-z-]+)"/g)].map((m) => m[1]);

    expect(client.length).toBeGreaterThan(0);
    for (const file of client) {
      const text = readFileSync(file, "utf8");
      expect(text, file).not.toMatch(/BACKEND_URL|process\.env/);
      // ...and none imports the server-side backend module that holds it.
      expect(clientImports(text), file).not.toContain("backend");
    }
  },
);
