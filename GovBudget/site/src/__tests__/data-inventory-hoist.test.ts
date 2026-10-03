/**
 * /data/ inventory rows carry no per-row utility strings (families piece 1,
 * Task 19). They live in src/app/data/data.module.css, selected by the hooks
 * already on each cell, because the page ships each row twice (HTML + RSC)
 * and p1_era_line_map's row did not fit the 42 gzip bytes the page had left.
 * A string put back on a row is weight put back on every row.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const PAGE = path.resolve(__dirname, "..", "app", "data", "page.tsx");
const CSS = path.resolve(__dirname, "..", "app", "data", "data.module.css");

const HOISTED = [
  "block sm:table-row border-b border-border last:border-0 hover:bg-muted/30 transition-colors py-3 sm:py-0",
  "t-id block sm:table-cell px-4 py-0 sm:py-2 sm:whitespace-nowrap",
  "inline sm:table-cell px-4 py-0 sm:py-2 text-left sm:text-right tabular-nums text-xs sm:text-sm text-muted-foreground",
  "inline sm:table-cell pr-4 sm:px-4 py-0 sm:py-2 text-left sm:text-right tabular-nums text-xs sm:text-sm text-muted-foreground whitespace-nowrap",
  "inline sm:table-cell px-4 py-0 sm:py-2 text-xs",
  "block sm:table-cell px-4 pt-1 sm:py-2 text-muted-foreground sm:max-w-sm",
];

describe("/data/ inventory rows: utilities hoisted into data.module.css", () => {
  const src = fs.readFileSync(PAGE, "utf8");

  it.each(HOISTED)("page.tsx no longer carries %s", (cls) => {
    expect(src).not.toContain(`"${cls}"`);
  });

  it("the inventory table takes the module class", () => {
    expect(src).toContain('import styles from "./data.module.css";');
    expect(src).toContain("className={`min-w-full text-sm ${styles.inv}`}");
  });

  it("the name cell keeps t-id for the type spec", () => {
    expect(src).toContain('<td role="cell" className="t-id">');
  });

  it("the module styles every cell the rows used to style inline", () => {
    const css = fs.readFileSync(CSS, "utf8");
    for (const sel of [
      ".inv > tbody > tr {",
      ".inv > tbody > tr:last-child {",
      ".inv > tbody > tr:hover {",
      ".inv > tbody > tr > td:first-child {",
      ".inv > tbody > tr > td:nth-child(2),",
      ".inv > tbody > tr > td:nth-child(3) {",
      '.inv [data-primary-value="citation"] {',
      '.inv [data-primary-value="scope"] {',
      "@media (width >= 40rem) {",
    ]) {
      expect(css).toContain(sel);
    }
  });
});
