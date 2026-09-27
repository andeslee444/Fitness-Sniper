/**
 * The site's withheld-claim types mirror what export-site writes into a
 * dossier sidecar's `withheld_claims` (final integration pass, 2026-09-27).
 *
 * R-DEC-DOSSIERLDA added a sixth contradicts_citation sub-reason,
 * `lobbying_mention`, and a per-claim `unlisted_lobbying_filers` list
 * (src/govbudget/dossiers/claim_drift.py, export_site._filter_dossier_claims).
 * site/src/lib/dossier.ts still declared five reasons and no filer list, so a
 * sidecar the exporter writes today did not match the type the site reads it
 * as. The page renders only the counts, never this list, so nothing broke at
 * runtime — which is why the pairing needs a test.
 *
 * - The runtime check reads both sources and requires the same reason set.
 * - `tsc --noEmit -p .` compiles the typed literal below (excess-property and
 *   union checks), so it fails the day either side drifts from this shape.
 */
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { DossierWithheldClaim } from "@/lib/dossier";

const ROOT = resolve(__dirname, "../../..");

/** The shape export_site writes for 2004's withheld FedEx key-player claim. */
const WITHHELD: DossierWithheldClaim = {
  section: "players",
  claim: 2,
  text: "FedEx Corporation lobbied on the program.",
  fact_id: "0123456789abcdef",
  kind: "lda_filing",
  units: null,
  cited_value: null,
  cited_family: null,
  reasons: ["lobbying_mention"],
  unlinked_recipients: [],
  unlisted_lobbying_filers: ["FedEx Corporation"],
};

describe("dossier withheld-claim types", () => {
  it("declare exactly the sub-reasons claim_drift.claim_contradictions emits", () => {
    const py = readFileSync(resolve(ROOT, "src/govbudget/dossiers/claim_drift.py"), "utf8");
    const emitted = new Set([...py.matchAll(/reasons\.append\("([a-z_]+)"\)/g)].map((m) => m[1]));
    const ts = readFileSync(resolve(ROOT, "site/src/lib/dossier.ts"), "utf8");
    const union = /export type DossierWithheldReason =([^;]+);/.exec(ts);
    expect(union, "DossierWithheldReason is declared").not.toBeNull();
    const declared = new Set([...union![1].matchAll(/"([a-z_]+)"/g)].map((m) => m[1]));
    expect(emitted.size).toBeGreaterThanOrEqual(6);
    expect([...declared].sort()).toEqual([...emitted].sort());
  });

  it("carry every per-claim list export_site writes", () => {
    const py = readFileSync(resolve(ROOT, "src/govbudget/export_site.py"), "utf8");
    for (const key of ["unlinked_recipients", "unlisted_lobbying_filers"]) {
      expect(py, `export_site writes ${key}`).toContain(`"${key}": (`);
      expect(Object.keys(WITHHELD)).toContain(key);
    }
    expect(WITHHELD.reasons).toEqual(["lobbying_mention"]);
  });
});
