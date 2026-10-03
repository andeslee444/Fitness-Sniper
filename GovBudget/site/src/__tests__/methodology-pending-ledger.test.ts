/**
 * /methodology/'s citation-tier paragraph names the pending ledger's one
 * dataset (families piece 1, Task 19; the owner's decision of Step 19).
 * p1_era_line_map ships on the uncited ledger (spec §4.4: its rows are
 * decisions, not money), so its /data/ row shows "tier pending" and "the
 * pending ledger is empty" stops being true when it ships. The clause is
 * replaced at its exact rendered length: /methodology/ sits near its gate-1
 * ceiling.
 */
import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const PAGE = path.resolve(__dirname, "..", "app", "methodology", "page.tsx");
const OLD = "every published dataset carries a citation tier (the pending ledger is empty)";
const NEW = "only p1_era_line_map is on the pending ledger, as it holds no amounts to cite";

/** The citation-tier definition as rendered: tags drop, whitespace collapses. */
function rendered(): string {
  const src = fs.readFileSync(PAGE, "utf8");
  const a = src.indexOf("<strong>Citation tier pending</strong>");
  expect(a, "citation-tier definition not found").toBeGreaterThan(-1);
  const b = src.indexOf("</p>", a);
  return src.slice(a, b).replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
}

describe("/methodology/ pending-ledger clause", () => {
  it("names p1_era_line_map as the pending ledger's only dataset", () => {
    expect(rendered()).toContain(`As of this build ${NEW}; the state remains defined`);
  });

  it("no longer says the ledger is empty", () => {
    expect(rendered()).not.toContain("the pending ledger is empty");
  });

  it("keeps the clause's rendered length", () => {
    expect(Buffer.byteLength(NEW)).toBe(Buffer.byteLength(OLD));
    expect(Buffer.byteLength(NEW)).toBe(77);
  });
});
