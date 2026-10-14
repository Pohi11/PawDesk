import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "vitest";

import { bannedList, copyIssues } from "./copy-check";
import { specTest } from "./spec";

const BANNED = ["simply", "exactly", "it's worth noting"];
const WORDS = "Dashboard text contains no banned words or phrases";
const DASHES = "Dashboard text uses no em dash inside a sentence";

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(name) && !name.endsWith(".test.ts") ? [path] : [];
  });
}

specTest("interface-copy", WORDS, "a banned word in rendered text is reported with its file and line", () => {
  const source = ["export function Intro() {", "  return <p>Pick a sample.\n  Simply send it.</p>;", "}"].join("\n");

  expect(copyIssues("intro.tsx", source, BANNED)).toEqual([{ file: "intro.tsx", line: 3, found: "Simply" }]);
});

specTest("interface-copy", WORDS, "string values and phrases are checked, with curly apostrophes too", () => {
  const source = 'const note = "It’s worth noting the cost";\nconst label = `Costs are ${"exactly"} billed`;';

  expect(copyIssues("labels.ts", source, BANNED).map((i) => i.found)).toEqual(["It's worth noting", "exactly"]);
});

specTest("interface-copy", WORDS, "class names, imports, comments, types, and object keys are not text", () => {
  const source = [
    '"use client";',
    'import { simply } from "./simply";',
    "// exactly as reported",
    'type Mode = "simply";',
    'const map = { "exactly": 1 };',
    'export const A = () => <div className="justify-self-end simply" style={{ font: "exactly" }} />;',
  ].join("\n");

  expect(copyIssues("a.tsx", source, BANNED)).toEqual([]);
});

specTest("interface-copy", DASHES, "an em dash inside a sentence is reported", () => {
  const source = 'export const label = "Costs — as reported";';

  expect(copyIssues("label.ts", source, BANNED)).toEqual([{ file: "label.ts", line: 1, found: "—" }]);
});

specTest("interface-copy", DASHES, "a lone em dash marking a missing value is allowed", () => {
  const source = 'export const missing = (v: number | null) => (v === null ? "—" : String(v));';

  expect(copyIssues("format.ts", source, BANNED)).toEqual([]);
});

test("the shared list is read from docs/style", () => {
  expect(bannedList()).toContain("simply");
});

test.fails("the current dashboard passes (turned on once the rewrite lands)", () => {
  const banned = bannedList();
  const issues = ["app", "components", "lib"]
    .flatMap(sourceFiles)
    .flatMap((file) => copyIssues(file, readFileSync(file, "utf8"), banned));

  expect(issues.map((i) => `${i.file}:${i.line} ${i.found}`)).toEqual([]);
});
