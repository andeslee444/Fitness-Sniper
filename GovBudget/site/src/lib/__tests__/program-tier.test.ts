import { describe, it, expect, afterEach } from "vitest";

import {
  decadeProgramRow,
  deriveExhibitFamily,
  isDecadeDetails,
  isIngestedServiceOrg,
  isRollupDetails,
  isWorkbookOnlyDetails,
  isZeroContentDetails,
  rollupProgramRow,
  serviceOrgName,
  setIngestedServiceOrgs,
  getOrgAbsence,
  orgAbsenceWording,
  setOrgAbsences,
  type OrgAbsence,
  type OrgAbsenceRule,
} from "@/lib/program-tier";
import type { ProgramDetails } from "@/lib/data";

/** Minimal rollup sidecar factory (shape of Batch A rollup exports). */
function rollupDetails(overrides: Partial<ProgramDetails> = {}): ProgramDetails {
  return {
    awards: [],
    budget_lines: [
      {
        account_title: "Industrial Preparedness",
        amount_thousands: 793,
        amount_type: "fy_2024_actuals",
        exhibit: "R-1",
        fact_id: "78b0453bb190f251",
        organization: "F",
        source_cells: "A1:B2",
        source_sheet: "Exhibit R-1",
        units: "USD thousands",
        basis: "toa",
        fy: 2024,
        measure: "actuals",
        edition: 2026,
        entity: "0708011F",
      },
    ],
    details: [],
    mentions: [],
    narratives: [],
    summary: {
      edition: 2026,
      basis_preference: "toa",
      cards: [],
      reconciliation: [],
      named_primes: [],
    },
    tier: "rollup",
    service_org: "F",
    title: "Industrial Preparedness/Pol Prevention",
    trajectory: {
      n_org_components: 1,
      fy2024_actuals: 793,
      fy2025_total: null,
      fy2026_total: 917,
      fy2526_change: null,
      fy2526_pct_change: null,
    },
    trajectory_fact_ids: {
      fy2024_actuals: "78b0453bb190f251",
      fy2025_total: null,
      fy2026_total: "9a7a0e4bb33799d4",
      fy2526_change: null,
    },
    ...overrides,
  };
}

describe("serviceOrgName", () => {
  it("maps the three service workbook codes to service names", () => {
    expect(serviceOrgName("A")).toBe("Army");
    expect(serviceOrgName("N")).toBe("Navy");
    expect(serviceOrgName("F")).toBe("Air Force");
  });

  it("passes other org codes through unchanged (honest fallback)", () => {
    expect(serviceOrgName("DHA")).toBe("DHA");
    expect(serviceOrgName("OSD")).toBe("OSD");
    expect(serviceOrgName("")).toBe("");
  });
});

describe("isIngestedServiceOrg (data-derived from site_meta.ingested_service_orgs)", () => {
  // The set is injected at build time from the exporter payload (data.ts calls
  // setIngestedServiceOrgs). Restore the safe default after each test so the
  // suite stays order-independent.
  afterEach(() => {
    setIngestedServiceOrgs(["A", "N", "F"]);
  });

  it("reads the injected payload — defense-wide agency books are ingested too", () => {
    // The live FY2026 set spans 27 loaded books collapsing to 25 workbook-org
    // codes: the three services PLUS every defense-wide agency (OSD, DCSA, MDA,
    // DISA, DARPA, …). The old hardcoded A/N/F set lied for all of them.
    setIngestedServiceOrgs([
      "A", "N", "F", "OSD", "DCSA", "MDA", "DISA", "DARPA", "CYBER", "SOCOM",
    ]);
    // Services.
    expect(isIngestedServiceOrg("N")).toBe(true);
    expect(isIngestedServiceOrg("A")).toBe(true);
    expect(isIngestedServiceOrg("F")).toBe(true);
    // Defense-wide agencies whose pages used to FALSELY say "not yet ingested".
    expect(isIngestedServiceOrg("DCSA")).toBe(true);
    expect(isIngestedServiceOrg("OSD")).toBe(true);
    expect(isIngestedServiceOrg("MDA")).toBe(true);
  });

  it("is false for orgs with NO loaded FY2026 book (must stay 'not yet ingested')", () => {
    setIngestedServiceOrgs([
      "A", "N", "F", "OSD", "DCSA", "MDA", "DISA", "DARPA", "CYBER", "SOCOM",
    ]);
    // DHA / DEFW / IG appear in budget_lines but have no J-book — they MUST
    // keep the honest generic wording.
    expect(isIngestedServiceOrg("DHA")).toBe(false);
    expect(isIngestedServiceOrg("DEFW")).toBe(false);
    expect(isIngestedServiceOrg("IG")).toBe(false);
    expect(isIngestedServiceOrg("")).toBe(false);
    // 'SF' is never an org code (Space Force folds under 'F'); guard against a
    // regression that mistakes the PE-number suffix for an org.
    expect(isIngestedServiceOrg("SF")).toBe(false);
  });

  it("falls back to the A/N/F default before any payload is injected", () => {
    // Universal module: unit tests / any consumer that never injects still get
    // sensible service-only behavior rather than an empty set.
    expect(isIngestedServiceOrg("A")).toBe(true);
    expect(isIngestedServiceOrg("N")).toBe(true);
    expect(isIngestedServiceOrg("F")).toBe(true);
    expect(isIngestedServiceOrg("DHA")).toBe(false);
  });
});

describe("isRollupDetails", () => {
  it("is true only for tier:'rollup' sidecars", () => {
    expect(isRollupDetails(rollupDetails())).toBe(true);
    expect(
      isRollupDetails({
        awards: [],
        budget_lines: [],
        details: [],
        mentions: [],
        narratives: [],
        summary: {
          edition: 2026,
          basis_preference: "toa",
          cards: [],
          reconciliation: [],
          named_primes: [],
        },
      }),
    ).toBe(false);
  });
});

describe("deriveExhibitFamily", () => {
  it("maps R-1 lines to rdte and P-1/P-1R lines to procurement", () => {
    expect(deriveExhibitFamily([{ exhibit: "R-1" }])).toBe("rdte");
    expect(deriveExhibitFamily([{ exhibit: "P-1" }])).toBe("procurement");
    expect(deriveExhibitFamily([{ exhibit: "P-1R" }])).toBe("procurement");
  });

  it("picks the family with more lines when mixed, and 'budget' when empty", () => {
    expect(
      deriveExhibitFamily([
        { exhibit: "P-1" },
        { exhibit: "P-1R" },
        { exhibit: "R-1" },
      ]),
    ).toBe("procurement");
    expect(deriveExhibitFamily([])).toBe("budget");
  });
});

describe("rollupProgramRow", () => {
  it("synthesizes a ProgramRow-shaped record from a rollup sidecar", () => {
    const row = rollupProgramRow("0708011F", rollupDetails());
    expect(row.pe_bli).toBe("0708011F");
    expect(row.title).toBe("Industrial Preparedness/Pol Prevention");
    // ProgramRow.org is the org CODE, never the display name: the GAO overlay
    // lookup, the /agency/{org}/ href and the agencies.json membership test
    // all key by code, and only display humanizes.
    expect(row.org).toBe("F");
    expect(serviceOrgName(row.org)).toBe("Air Force");
    expect(row.exhibit_family).toBe("rdte");
    expect(row.fully_reconciled).toBe(false);
    expect(row.fy2024_actual_millions).toBeNull();
    expect(row.fy2024_fact_id).toBeNull();
    expect(row.fy2024_xml_path).toBeNull();
    expect(row.hhi).toBeNull();
    expect(row.trajectory?.fy2026_total).toBe(917);
    expect(row.trajectory_fact_ids?.fy2026_total).toBe("9a7a0e4bb33799d4");
    expect(row.award_count).toBe(0);
    expect(row.narrative_count).toBe(0);
    expect(row.project_count).toBe(0);
  });

  it("falls back to the PE code when the sidecar has no title", () => {
    const row = rollupProgramRow("000042", rollupDetails({ title: undefined }));
    expect(row.title).toBe("000042");
  });

  it("falls back to the DoD umbrella when the sidecar declares no service", () => {
    // One live sidecar (9999999999) carries service_org "". "DoD" is the
    // honest umbrella, and deliberately not a service code — it matches no
    // agency page and no GAO overlay, which is the right answer for a line
    // with no declared service.
    const row = rollupProgramRow("000042", rollupDetails({ service_org: "" }));
    expect(row.org).toBe("DoD");
    expect(serviceOrgName(row.org)).toBe("DoD");
  });

  it("keeps Space Force under org F — 'SF' is a PE suffix, never an org", () => {
    // 0601102SF-style PE numbers carry an SF suffix, but every Space Force
    // line is published in the Air Force book under workbook org "F".
    const row = rollupProgramRow("0601102SF", rollupDetails({ service_org: "F" }));
    expect(row.org).toBe("F");
    expect(serviceOrgName(row.org)).toBe("Air Force");
  });
});

describe("isZeroContentDetails", () => {
  it("flags a rollup page whose only figures are zeros (noindex policy)", () => {
    const zero = rollupDetails({
      budget_lines: [
        {
          account_title: "x",
          amount_thousands: 0,
          amount_type: "fy_2024_actuals",
          exhibit: "P-1",
          fact_id: "aaaaaaaaaaaaaaaa",
          organization: "N",
          source_cells: "A1",
          source_sheet: "s",
          units: "USD thousands",
          basis: "toa",
          fy: 2024,
          measure: "actuals",
          edition: 2026,
          entity: "000042",
        },
      ],
      trajectory: {
        n_org_components: 1,
        fy2024_actuals: 0,
        fy2025_total: null,
        fy2026_total: 0,
        fy2526_change: null,
        fy2526_pct_change: null,
      },
    });
    expect(isZeroContentDetails(zero)).toBe(true);
  });

  it("keeps pages with any non-zero figure indexable", () => {
    expect(isZeroContentDetails(rollupDetails())).toBe(false);
  });

  it("keeps pages with narratives/details/awards/mentions indexable even when figures are zero", () => {
    const withNarrative = rollupDetails({
      budget_lines: [],
      trajectory: {
        n_org_components: 1,
        fy2024_actuals: 0,
        fy2025_total: null,
        fy2026_total: null,
        fy2526_change: null,
        fy2526_pct_change: null,
      },
      narratives: [
        { body: "text", kind: "mission", title: "Mission", fact_id: "bbbbbbbbbbbbbbbb" },
      ],
    });
    expect(isZeroContentDetails(withNarrative)).toBe(false);
  });
});

// ── ROADMAP #28 — the decade tier ──────────────────────────────────────────

/** Minimal decade sidecar: no FY2026 workbook row, no detail, no
 *  trajectory — only the cited pre-PB2026 series. */
function decadeDetails(overrides: Partial<ProgramDetails> = {}): ProgramDetails {
  return {
    awards: [],
    budget_lines: [],
    details: [],
    mentions: [],
    narratives: [],
    summary: {
      edition: 2026,
      basis_preference: "toa",
      cards: [],
      reconciliation: [],
      named_primes: [],
    },
    tier: "decade",
    service_org: "F",
    exhibit_family: "rdte",
    title: "Ground Based Strategic Deterrent",
    trajectory: null,
    trajectory_fact_ids: null,
    decade_series: {
      actuals: [
        {
          fy: 2016,
          v: 64966,
          fid: "2f5055bcb9d2ea0f",
          edition: 2018,
          basis: "toa",
          measure: "actuals",
        },
      ],
    },
    decade_absent: {
      first_edition: 2018,
      last_edition: 2024,
      edition_count: 5,
      fy_min: 2016,
      fy_max: 2024,
      renumber: false,
      has_successor: false,
    },
    ...overrides,
  } as ProgramDetails;
}

describe("decade tier (ROADMAP #28)", () => {
  it("recognises the tier, and does not confuse it with rollup", () => {
    expect(isDecadeDetails(decadeDetails())).toBe(true);
    expect(isRollupDetails(decadeDetails())).toBe(false);
    expect(isDecadeDetails(rollupDetails())).toBe(false);
  });

  it("takes exhibit_family from the sidecar, not from the empty budget_lines", () => {
    // The whole point: deriveExhibitFamily([]) is the generic "budget", which
    // would be what every one of these 553 pages rendered without the
    // exporter-supplied field.
    expect(deriveExhibitFamily([])).toBe("budget");
    expect(decadeProgramRow("0605230F", decadeDetails()).exhibit_family).toBe("rdte");
  });

  it("keeps the org CODE, never the humanized name (the #30 defect)", () => {
    expect(decadeProgramRow("0605230F", decadeDetails()).org).toBe("F");
  });

  it("declares no reconciliation verdict and no trajectory", () => {
    const row = decadeProgramRow("0605230F", decadeDetails());
    expect(row.reconciled_in_scope).toBeNull();
    expect(row.trajectory).toBeNull();
    expect(row.hhi).toBeNull();
  });

  it("is INDEXABLE on its cited decade figures alone", () => {
    // Pre-#28 this page had no budget_lines, no trajectory and no prose, so
    // `figures` was [] and [].every() is true — all 553 pages would have
    // been noindexed and dropped from the sitemap.
    expect(isZeroContentDetails(decadeDetails())).toBe(false);
  });

  it("still calls an all-zero decade series zero-content", () => {
    const zero = decadeDetails({
      decade_series: {
        actuals: [
          {
            fy: 2016,
            v: 0,
            fid: "2f5055bcb9d2ea0f",
            edition: 2018,
            basis: "toa",
            measure: "actuals",
          },
        ],
      },
    });
    expect(isZeroContentDetails(zero)).toBe(true);
  });
});

describe("isWorkbookOnlyDetails (ROADMAP #14 — the liar on the full tier)", () => {
  it("is true for a sidecar with workbook figures and no J-book detail at all", () => {
    // The shape export_site._trajectory_only_feed_programs produces: a
    // programs.json row exists (so resolveProgram returns tier "full") but
    // the sidecar carries no tier, no service_org, and empty details AND
    // narratives. 0603115DHA / 0708083D, measured 2026-09-10.
    const d = rollupDetails({ tier: undefined, service_org: undefined });
    expect(isWorkbookOnlyDetails(d)).toBe(true);
  });

  it("is false once ANY R-2/P-40 detail row exists", () => {
    const d = rollupDetails({
      tier: undefined,
      details: [
        {
          amount_millions: 1,
          fact_id: "cccccccccccccccc",
          project_number: "1",
          project_title: "Widget",
          resolution: "unique",
          scenario: "base",
          units: "USD millions",
          xml_path: "x.xml",
          basis: "jbook-detail",
          fy: 2026,
          measure: "request",
          edition: 2026,
          entity: "0708011F/1",
        },
      ],
    });
    expect(isWorkbookOnlyDetails(d)).toBe(false);
  });

  it("is false when narratives exist without detail rows", () => {
    const d = rollupDetails({
      tier: undefined,
      narratives: [
        { body: "text", kind: "mission", title: "Mission", fact_id: "dddddddddddddddd" },
      ],
    });
    expect(isWorkbookOnlyDetails(d)).toBe(false);
  });

  it("is false for a decade sidecar — it has no workbook line to be 'only'", () => {
    // Every decade sidecar ships budget_lines: [] (export_site.py:9080), so
    // the rollup tier's sentence must never reach it: a decade element is not
    // in the FY2026 books at all.
    expect(isWorkbookOnlyDetails(decadeDetails())).toBe(false);
  });
});

// ───────────────────────────────────────────────────────────────────────────
// site_meta.org_absences — WHY an org has no loaded book (ROADMAP #111)
// ───────────────────────────────────────────────────────────────────────────

/** The live FY2026 record (data/research/edition_manifest.json → org_absences,
 *  published by export_site._org_absences). */
const LIVE_ABSENCES: Record<string, OrgAbsence> = {
  DHA: {
    rule: "book-carries-no-embedded-xml",
    fy: 2026,
    checked_on: "2026-09-12",
    checked_url: "https://comptroller.war.gov/…/00-DHP_Vols_I_and_II_PB26.pdf",
  },
  DEFW: {
    rule: "summary-line-only",
    fy: 2026,
    checked_on: "2026-09-12",
    checked_url: "https://comptroller.war.gov/Budget-Materials/",
  },
  IG: {
    rule: "no-justification-book-published",
    fy: 2026,
    checked_on: "2026-09-12",
    checked_url: "https://comptroller.war.gov/Budget-Materials/",
  },
};

describe("setOrgAbsences / getOrgAbsence", () => {
  afterEach(() => setOrgAbsences(undefined));

  it("is empty before any payload — an absence is a recorded probe, never a default", () => {
    expect(getOrgAbsence("DHA")).toBeNull();
    expect(getOrgAbsence("IG")).toBeNull();
  });

  it("reads the injected payload, and only for the orgs it names", () => {
    setOrgAbsences(LIVE_ABSENCES);
    expect(getOrgAbsence("IG")?.rule).toBe("no-justification-book-published");
    expect(getOrgAbsence("DEFW")?.rule).toBe("summary-line-only");
    expect(getOrgAbsence("DHA")?.checked_on).toBe("2026-09-12");
    // An org with a loaded book, and the empty-org sidecar (9999999999).
    expect(getOrgAbsence("A")).toBeNull();
    expect(getOrgAbsence("")).toBeNull();
  });

  it("drops an entry whose rule this module has no sentence for", () => {
    // Dropping it leaves the org on the generic wording rather than rendering
    // a branch nobody wrote; gate 21 leg (o) then fails on the payload, which
    // is where an unknown rule is actually fixable.
    setOrgAbsences({
      ...LIVE_ABSENCES,
      IG: { ...LIVE_ABSENCES.IG, rule: "book-is-classified" as OrgAbsenceRule },
    });
    expect(getOrgAbsence("IG")).toBeNull();
    expect(getOrgAbsence("DHA")).not.toBeNull();
  });

  it("clears on an absent payload — a pre-17c export must not keep a stale set", () => {
    setOrgAbsences(LIVE_ABSENCES);
    setOrgAbsences(undefined);
    expect(getOrgAbsence("DHA")).toBeNull();
  });

  it("keeps an entry with no fy — the SENTENCE is what refuses to render", () => {
    // An export that predates ROADMAP #111's fy field. Dropping the entry
    // (what an unknown rule gets) would put the org back on "not yet
    // ingested"; rendering it would print "No FY RDT&E or procurement
    // justification book…". Both publish, so neither is the answer — but the
    // refusal belongs at the sentence, not here: data.ts injects this payload
    // once for the whole build, and a throw here would take down the ~2,500
    // pages that render no absence at all (and every test that loads a
    // shipped site_meta). The 19 pages that would print "FY" throw instead.
    const noFy: Partial<OrgAbsence> = { ...LIVE_ABSENCES.IG };
    delete noFy.fy;
    setOrgAbsences({ ...LIVE_ABSENCES, IG: noFy });
    expect(getOrgAbsence("IG")).not.toBeNull();
    expect(() => orgAbsenceWording(getOrgAbsence("IG")!, "IG")).toThrow(
      /carries no integer fy/,
    );
    // …and the orgs whose entries ARE complete still render.
    expect(orgAbsenceWording(getOrgAbsence("DHA")!, "DHA").description).toContain(
      "FY2026",
    );
  });
});

describe("orgAbsenceWording", () => {
  /** The substrings gate 21 leg (o) matches (ABSENCE_MARKERS in
   *  scripts/gates/program-skeleton.mjs). The leg looks for the SAME marker in
   *  the description note and inside the justification section — that is how
   *  one literal binds both render sites — so each rule's two sentences must
   *  share this opening, and it must stay free of "&" (the gate reads decoded
   *  text). Reword the sentences freely; break this pairing and the build's
   *  own gate reds with no unit test to explain why. */
  const GATE_MARKERS: Record<
    OrgAbsenceRule,
    (svc: string, fy: number) => string
  > = {
    "no-justification-book-published": (svc) =>
      `justification book was published for ${svc}`,
    "summary-line-only": (svc, fy) =>
      `No ${svc}-specific FY${fy} justification book is published`,
    "book-carries-no-embedded-xml": (svc, fy) =>
      `The ${svc} FY${fy} justification book was downloaded`,
  };

  it.each(Object.keys(GATE_MARKERS) as OrgAbsenceRule[])(
    "%s: the description and the justification share the gate's marker",
    (rule) => {
      const w = orgAbsenceWording(
        { rule, fy: 2026, checked_on: "2026-09-12", checked_url: "https://x" },
        "DHA",
      );
      const marker = GATE_MARKERS[rule]("DHA", 2026);
      expect(w.description).toContain(marker);
      expect(w.justification).toContain(marker);
      expect(marker).not.toContain("&");
    },
  );

  it.each(Object.keys(GATE_MARKERS) as OrgAbsenceRule[])(
    "%s: names the edition the PAYLOAD records, not a year typed in the module",
    (rule) => {
      // The rollover case, which no fixture of the live record can show: the
      // FY2027 probe publishes fy: 2027 and every surface follows it. Typed
      // as "FY2026" (as all four were until ROADMAP #111) each sentence would
      // go on naming a book that is no longer the current one.
      const w = orgAbsenceWording(
        { rule, fy: 2027, checked_on: "2027-04-01", checked_url: "https://x" },
        "DHA",
      );
      for (const surface of [w.description, w.justification, w.cardTail, w.metaTail]) {
        expect(surface).not.toContain("FY2026");
      }
      expect(w.description).toContain(GATE_MARKERS[rule]("DHA", 2027));
      // And never a yearless "FY", which is what a missing field would render.
      expect(w.description).not.toMatch(/FY\D/);
    },
  );

  it("states the DoD IG's case: no book was published, so none is awaited", () => {
    const w = orgAbsenceWording(LIVE_ABSENCES.IG, "IG");
    expect(w.description).toBe(
      "No FY2026 RDT&E or procurement justification book was published for IG" +
        " (justification index checked 2026-09-12), so this corpus carries no" +
        " detailed justification for this program.",
    );
    expect(w.justification).toBe(
      "No FY2026 RDT&E or procurement justification book was published for IG," +
        " so there are no accomplishments or planned-program narratives to show" +
        " — see the description note above.",
    );
    expect(w.cardTail).toBe(
      "Summary figures only: no FY2026 RDT&E or procurement justification book" +
        " was published for IG.",
    );
    expect(w.metaTail).toBe(
      "Workbook-tier line: no FY2026 RDT&E or procurement justification book" +
        " was published for IG. ",
    );
  });

  it("states DEFW's case: summary rows, and no DEFW-specific book", () => {
    const w = orgAbsenceWording(LIVE_ABSENCES.DEFW, "DEFW");
    expect(w.description).toBe(
      "No DEFW-specific FY2026 justification book is published (justification" +
        " index checked 2026-09-12) — its workbook rows are reconciliation," +
        " undistributed or roll-up summary lines — so this corpus carries no" +
        " detailed justification for this program.",
    );
    expect(w.justification).toBe(
      "No DEFW-specific FY2026 justification book is published, so there are no" +
        " accomplishments or planned-program narratives to show — see the" +
        " description note above.",
    );
    expect(w.cardTail).toBe(
      "Summary figures only: no DEFW-specific FY2026 justification book is" +
        " published.",
    );
  });

  it("states DHA's case precisely: downloaded, and carrying no payload", () => {
    // NOT "not yet ingested": the book is in hand. What is missing is the
    // jb-2009 payload, and saying so is the smaller true claim.
    const w = orgAbsenceWording(LIVE_ABSENCES.DHA, "DHA");
    expect(w.description).toBe(
      "The DHA FY2026 justification book was downloaded, but its PDF carries no" +
        " embedded data payload (checked 2026-09-12), so no R-2/P-40 detail" +
        " could be extracted from it.",
    );
    expect(w.justification).toBe(
      "The DHA FY2026 justification book was downloaded, but its PDF carries no" +
        " embedded data payload, so no accomplishments or planned-program" +
        " narratives could be extracted from it — see the description note" +
        " above.",
    );
    expect(w.metaTail).toBe(
      "Workbook-tier line: the DHA FY2026 justification book was downloaded and" +
        " carries no embedded data payload. ",
    );
  });

  it("never says 'not yet ingested', on any surface, for any rule", () => {
    for (const absence of Object.values(LIVE_ABSENCES)) {
      const w = orgAbsenceWording(absence, "DHA");
      for (const surface of [w.description, w.justification, w.cardTail, w.metaTail]) {
        expect(surface).not.toContain("not yet ingested");
      }
    }
  });

  it("humanizes a service code and drops the stamp when the probe carries no date", () => {
    const w = orgAbsenceWording(
      {
        rule: "no-justification-book-published",
        fy: 2026,
        checked_on: "",
        checked_url: "",
      },
      "A",
    );
    expect(w.description).toContain("published for Army");
    expect(w.description).not.toContain("checked ");
  });
});
