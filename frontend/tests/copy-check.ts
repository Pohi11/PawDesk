// The mechanical half of the copy guide (docs/style/interface-copy.md, decision record 0018):
// banned words and em dashes in text a user can see. It walks the TypeScript syntax tree, so
// comments, imports, types, object keys, and class names are never mistaken for copy.

import { readFileSync } from "node:fs";

import ts from "typescript";

export interface CopyIssue {
  file: string;
  line: number;
  found: string;
}

const RULES = new URL("../../docs/style/copy-rules.json", import.meta.url);

/** The shared banned list, also read by the backend's demo sample check. */
export function bannedList(): string[] {
  return (JSON.parse(readFileSync(RULES, "utf8")) as { banned: string[] }).banned;
}

const NOT_TEXT_ATTRIBUTES = new Set(["className", "style"]);

function isSkipped(node: ts.Node): boolean {
  if (ts.isImportDeclaration(node) || ts.isExportDeclaration(node) || ts.isTypeNode(node)) return true;
  // Directives such as "use client".
  if (ts.isExpressionStatement(node) && ts.isStringLiteral(node.expression)) return true;
  if (ts.isJsxAttribute(node) && NOT_TEXT_ATTRIBUTES.has(node.name.getText())) return true;
  const parent = node.parent;
  return parent !== undefined && ts.isPropertyAssignment(parent) && parent.name === node;
}

function isText(node: ts.Node): node is ts.JsxText | ts.StringLiteral | ts.NoSubstitutionTemplateLiteral | ts.TemplateLiteralLikeNode {
  return (
    ts.isJsxText(node) ||
    ts.isStringLiteral(node) ||
    ts.isNoSubstitutionTemplateLiteral(node) ||
    ts.isTemplateHead(node) ||
    ts.isTemplateMiddle(node) ||
    ts.isTemplateTail(node)
  );
}

function matcher(banned: string[]): RegExp {
  const escaped = banned.map((b) => b.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  return new RegExp(`\\b(?:${escaped.join("|")})\\b`, "gi");
}

/** Every banned word and every em dash inside a sentence, with its file and line. */
export function copyIssues(file: string, source: string, banned: string[]): CopyIssue[] {
  const kind = file.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, kind);
  const words = matcher(banned);
  const issues: CopyIssue[] = [];
  const lineAt = (pos: number) => sf.getLineAndCharacterOfPosition(pos).line + 1;

  const visit = (node: ts.Node) => {
    if (isSkipped(node)) return;
    if (isText(node)) {
      const start = node.getStart(sf);
      // Search the raw source slice, so each finding's line is exact.
      const raw = source.slice(start, node.end).replaceAll("’", "'");
      for (const m of raw.matchAll(words)) {
        issues.push({ file, line: lineAt(start + m.index), found: m[0] });
      }
      // A string that is only an em dash marks a missing value, and is allowed.
      const dash = raw.indexOf("—");
      if (dash !== -1 && node.text.trim() !== "—") {
        issues.push({ file, line: lineAt(start + dash), found: "—" });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return issues;
}
