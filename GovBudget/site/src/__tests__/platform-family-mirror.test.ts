/**
 * The F-15 registry rows mirror the F-15 TypeScript (families piece 2, spec
 * 2026-10-20 §13; the CLAUDE.md mirror rule).
 *
 * data-seeds/platform_family_members.csv carries, on each paged counted F-15
 * member, the purpose, variant ids and scope note that RECORD_CONFIG in
 * site/src/lib/f15-family-data.ts renders, and the paged members in
 * member_order are F15_RECORD_SLUGS. Neither TypeScript file is edited (§3):
 * RECORD_CONFIG is not exported and f15-family-data.ts imports server-only,
 * so the test reads that file's source text and walks its syntax tree rather
 * than importing it. The other three copies of the record slugs (RECORDS in
 * site/src/lib/f15-browser-state.ts, the F15_ENTRY_VARIANTS keys in
 * site/src/components/family-entry.tsx and the RECORD_GUIDES keys in
 * site/src/components/f15-family-browser.tsx) are not exported either and
 * are read the same way.
 */

import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import ts from "typescript";
import { parseCsv } from "../../scripts/gates/basis.mjs";
import { F15_RECORD_SLUGS } from "@/lib/f15-family";

const ROOT = resolve(__dirname, "../../..");   // GovBudget/
type Config = Record<string, { purpose: string; variantIds: string[]; scopeNote: string }>;

/** RECORD_CONFIG read from the source text (it is not exported; the file stays unedited): the
 *  VariableDeclaration named RECORD_CONFIG → ObjectLiteralExpression → PropertyAssignment whose
 *  name is an Identifier or StringLiteral, each value an object literal with purpose (StringLiteral),
 *  scopeNote (StringLiteral) and variantIds (ArrayLiteralExpression of StringLiteral). */
function readRecordConfig(source: string): Config {
  const file = ts.createSourceFile("f15-family-data.ts", source, ts.ScriptTarget.Latest, true);
  let literal: ts.ObjectLiteralExpression | undefined;
  const visit = (node: ts.Node): void => {
    if (literal) return;
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.name.text === "RECORD_CONFIG"
        && node.initializer && ts.isObjectLiteralExpression(node.initializer)) {
      literal = node.initializer;
      return;
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  if (!literal) throw new Error("f15-family-data.ts: no RECORD_CONFIG object literal");

  const config: Config = {};
  for (const entry of literal.properties) {
    if (!ts.isPropertyAssignment(entry) || !(ts.isIdentifier(entry.name) || ts.isStringLiteral(entry.name))
        || !ts.isObjectLiteralExpression(entry.initializer)) {
      throw new Error(`RECORD_CONFIG: unexpected entry ${entry.getText(file)}`);
    }
    const slug = entry.name.text;
    const fields = new Map<string, ts.Expression>();
    for (const field of entry.initializer.properties) {
      if (ts.isPropertyAssignment(field) && ts.isIdentifier(field.name)) fields.set(field.name.text, field.initializer);
    }
    const text = (key: string): string => {
      const value = fields.get(key);
      if (!value || !ts.isStringLiteral(value)) throw new Error(`RECORD_CONFIG.${slug}.${key} is not a string literal`);
      return value.text;
    };
    const variants = fields.get("variantIds");
    if (!variants || !ts.isArrayLiteralExpression(variants)) throw new Error(`RECORD_CONFIG.${slug}.variantIds is not an array literal`);
    const variantIds = variants.elements.map((element) => {
      if (!ts.isStringLiteral(element)) throw new Error(`RECORD_CONFIG.${slug}.variantIds holds a non-string element`);
      return element.text;
    });
    config[slug] = { purpose: text("purpose"), variantIds, scopeNote: text("scopeNote") };
  }
  return config;
}

/** The slugs a non-exported constant holds, read from its source text: the VariableDeclaration
 *  named `name` whose initializer is an ArrayLiteralExpression of StringLiterals (its elements)
 *  or an ObjectLiteralExpression (its PropertyAssignment names, Identifier or StringLiteral). */
function readSlugs(path: string, name: string): string[] {
  const file = ts.createSourceFile(path, readFileSync(resolve(ROOT, path), "utf8"), ts.ScriptTarget.Latest, true);
  let init: ts.Expression | undefined;
  const visit = (node: ts.Node): void => {
    if (init) return;
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.name.text === name && node.initializer) {
      init = node.initializer;
      return;
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  if (init && ts.isArrayLiteralExpression(init)) {
    return init.elements.map((element) => {
      if (!ts.isStringLiteral(element)) throw new Error(`${path}: ${name} holds a non-string element`);
      return element.text;
    });
  }
  if (init && ts.isObjectLiteralExpression(init)) {
    return init.properties.map((entry) => {
      if (!ts.isPropertyAssignment(entry) || !(ts.isIdentifier(entry.name) || ts.isStringLiteral(entry.name))) {
        throw new Error(`${path}: ${name}: unexpected entry ${entry.getText(file)}`);
      }
      return entry.name.text;
    });
  }
  throw new Error(`${path}: no ${name} array or object literal`);
}

/** One finding per paged member whose purpose / variant_ids (";"-split) / scope_note differ. */
function recordConfigProblems(rows: Record<string, string>[], config: Config): string[] {
  const problems: string[] = [];
  for (const row of rows) {
    const slug = row.page_slug;
    const entry = config[slug];
    if (!entry) {
      problems.push(`${slug}: no RECORD_CONFIG entry`);
      continue;
    }
    if (row.purpose !== entry.purpose) problems.push(`${slug}: purpose differs from RECORD_CONFIG`);
    if (JSON.stringify(row.variant_ids.split(";")) !== JSON.stringify(entry.variantIds)) {
      problems.push(`${slug}: variant_ids differ from RECORD_CONFIG`);
    }
    if (row.scope_note !== entry.scopeNote) problems.push(`${slug}: scope_note differs from RECORD_CONFIG`);
  }
  return problems;
}

const rows = parseCsv(readFileSync(resolve(ROOT, "data-seeds/platform_family_members.csv"), "utf8"));
const paged = rows.filter((r) => r.platform_family === "f-15" && r.role === "counted" && r.verdict === "approved" && r.page_slug !== "")
                  .sort((a, b) => Number(a.member_order) - Number(b.member_order));
const config = readRecordConfig(readFileSync(resolve(ROOT, "site/src/lib/f15-family-data.ts"), "utf8"));

describe("the F-15 registry rows mirror the F-15 TypeScript (CLAUDE.md mirror rule; spec §13)", () => {
  it("lists the paged counted members, in member_order, as F15_RECORD_SLUGS", () => {
    expect(paged.map((r) => r.page_slug)).toEqual([...F15_RECORD_SLUGS]);
  });
  it("reads one RECORD_CONFIG entry per record slug from the source", () => {
    expect(Object.keys(config).sort()).toEqual([...F15_RECORD_SLUGS].sort());
    expect(config.F15EWS).toEqual({ purpose: "upgrade", variantIds: ["E"], scopeNote: "The procurement narrative describes EPAWSS installation and related support for F-15E aircraft. This amount is not assigned to F-15EX." });
  });
  it("carries RECORD_CONFIG's purpose, variant ids and scope note on every paged member", () => {
    expect(recordConfigProblems(paged, config)).toEqual([]);
  });
  it("ties RECORDS, the F15_ENTRY_VARIANTS keys and the RECORD_GUIDES keys to the paged counted members", () => {
    const slugs = paged.map((r) => r.page_slug).sort();
    expect(readSlugs("site/src/lib/f15-browser-state.ts", "RECORDS").sort()).toEqual(slugs);
    expect(readSlugs("site/src/components/family-entry.tsx", "F15_ENTRY_VARIANTS").sort()).toEqual(slugs);
    expect(readSlugs("site/src/components/f15-family-browser.tsx", "RECORD_GUIDES").sort()).toEqual(slugs);
  });
  it("catches a drifted scope note", () => {
    const drifted = paged.map((r) => (r.page_slug === "F15EWS" ? { ...r, scope_note: "Edited." } : r));
    expect(recordConfigProblems(drifted, config)).toEqual(["F15EWS: scope_note differs from RECORD_CONFIG"]);
  });
});
