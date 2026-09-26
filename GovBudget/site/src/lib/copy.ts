/**
 * copy.ts — the one place authored (uncited) copy lives.
 *
 * Nine independent design critics read the site's prose as "model prose":
 * imperative triplets ("Explore. Understand. Follow."), slogan headlines,
 * "a different way into", "follow every figure to its source". The fix is a
 * SYSTEM, not a rewrite: every reusable slot (headline, deck, eyebrow, section
 * title, lede, caption, empty state, link, button, label, nav item) reads from
 * here, through a formatter or a template filled from data — so a new program
 * page, a new family page, a new exhibit inherits the voice without anyone
 * writing a sentence. docs/superpowers/VOICE.md is the house style this file
 * implements; scripts/gates/copy.mjs (gate 27) holds every built page to it.
 *
 * What is NOT here, on purpose: cited sentences. Narratives, topic texts,
 * scope notes, absence notes bound to a fact, the receipt-moment
 * reconciliation sentence, the [data-stat] corpus sentence, what-it-is tails
 * and coverage.ts notes stay beside their data — they say what a number means
 * and are never paraphrased from a copy module.
 *
 * No React, no "server-only": importable from server and client components
 * and from the gate.
 */

import { PROGRAM_SECTIONS, type ProgramSectionId } from "@/components/program-section";
import { serviceOrgName } from "./program-tier";
import { agencyDisplayName } from "./agency-names";
import { answerFamilyPlain } from "./what-it-is";
import { TRAJECTORY_FY_LABEL } from "./site";

// ── Formatters (VOICE rule 23: one formatter each) ───────────────────────────

const ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];

/** "1 record" · "6 records" · "1,938 lines". Never "(s)". */
export function count(n: number, noun: string, plural = `${noun}s`): string {
  return `${n.toLocaleString("en-US")} ${n === 1 ? noun : plural}`;
}

/** One to nine spelled out (headings, decks, ledes); digits with separators above. */
export function countWord(n: number): string {
  return n >= 0 && n <= 9 ? ONES[n] : n.toLocaleString("en-US");
}

/** Sentence-initial capital for countWord. */
export function capital(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Zero-based index → "01" … "10". Every callout, chapter and plate number. */
export function callout(i: number): string {
  return String(i + 1).padStart(2, "0");
}

/** One-based plate ordinal + domain → "01 / Sea". The plate's register mark. */
export function stamp(n: number, domain: string): string {
  return `${callout(n - 1)} / ${domain}`;
}

/** Exactly two segments, ≤ 30 characters: "Field guide / Air". */
export function eyebrow(group: string, item: string): string {
  const s = `${group} / ${item}`;
  if (process.env.NODE_ENV === "test" && (s.length > 30 || group.includes("/") || item.includes("/"))) {
    throw new Error(`eyebrow(): "${s}" breaks VOICE rule 1/34 (two segments, ≤ 30 chars)`);
  }
  return s;
}

export type PeBliKind = "PE" | "BLI";

/** "PE 0604840F" · "BLI 2013". The identifier lockup, everywhere. */
export function peBliLabel(kind: PeBliKind, code: string): string {
  return `${kind} ${code}`;
}

/** Procurement lines are BLIs; everything else is a program element. */
export function peBliKind(exhibitFamily: string | null): PeBliKind {
  return (exhibitFamily ?? "").toLowerCase() === "procurement" ? "BLI" : "PE";
}

/** "FY2026" — sentences. */
export function fyLabel(fy: number): string {
  return `FY${fy}`;
}

/** "FY26" — table headers and chips only. */
export function fyShort(fy: number): string {
  return `FY${String(fy).slice(-2)}`;
}

/** "PB2026". */
export function pbLabel(edition: number): string {
  return `PB${edition}`;
}

/**
 * The older editions' service codes, as a decade-tier sidecar carries them
 * (program-tier.ts decadeProgramRow: 136 "AF", 100 "ARMY", 57 "NAVY" pages on
 * 2026-09-26), mapped to the FY2026 code space the short form names.
 */
const EDITION_SERVICE_CODE: Record<string, string> = { AF: "F", ARMY: "A", NAVY: "N" };

/** short: "Navy" · "Air Force" · "OSD"; long: the agency's full name. */
export function orgLabel(org: string, form: "short" | "long"): string {
  return form === "short" ? serviceOrgName(EDITION_SERVICE_CODE[org] ?? org) : agencyDisplayName(org);
}

/** The exhibit-family badge — moved here from program-header.tsx so one map serves the site. */
export function exhibitFamilyLabel(family: string | null): string {
  switch ((family ?? "budget").toLowerCase()) {
    case "rdte":
      return "RDT&E";
    case "procurement":
      return "Procurement";
    case "om":
    case "o&m":
      return "O&M";
    case "milpers":
      return "MILPERS";
    case "budget":
      return "Budget";
    default:
      return family!.toUpperCase();
  }
}

/** Plain form for sentences and exhibit titles: "research and development". */
export function exhibitFamilyPlain(family: string | null): string {
  return answerFamilyPlain(family).replace(" & ", " and ");
}

const CITATION_KIND_LABEL: Record<string, string> = {
  jbook_pdf: "Budget Justification PDF",
  pdf: "Budget Justification PDF",
  workbook: "Budget Workbook",
  lda: "LDA Lobbying Filing",
  derived: "Derived Figure",
  usaspending: "USAspending Query",
  state_api: "State Open Data Query",
  state_file: "State Source File",
  narrative: "J-book Narrative",
  announcement: "DoD Contract Announcement",
};

/** Citation kinds are document names — the one place they are capitalised. */
export function citationKindLabel(kind: string): string {
  return CITATION_KIND_LABEL[kind] ?? kind.replace(/_/g, " ");
}

const MEASURE_LABEL: Record<string, string> = {
  actuals: "Actuals",
  enacted: "Enacted",
  request: "Request",
  total: "Total",
  change: "Change",
  "base-request": "Base Request",
  "disc-request": "Discretionary request",
  "reconciliation-request": "Reconciliation request",
};

/** The status word for a measure: "Actuals" · "Enacted" · "Request" · "Total" · "Change". */
export function measureLabel(measure: string): string {
  return MEASURE_LABEL[measure] ?? measure.replace(/-/g, " ");
}

/** "FY2026 request" · "FY2025 enacted" · "FY2024 actuals" — headings and selects. */
export function measureHeading(fy: number, measure: string): string {
  return `${fyLabel(fy)} ${measureLabel(measure).toLowerCase()}`;
}

/** Which document a figure was read from, by basis and exhibit family. */
export function documentForBasis(basis: "toa" | "jbook-detail", exhibitFamily: string | null): "P-1" | "R-1" | "R-2/P-40" {
  if (basis === "jbook-detail") return "R-2/P-40";
  return peBliKind(exhibitFamily) === "BLI" ? "P-1" : "R-1";
}

// ── Lockups (templates with typed params) ───────────────────────────────────

export interface ProgramRowLike {
  pe_bli: string;
  title: string;
  org: string;
  exhibit_family: string | null;
}

/** "Navy · BLI 2013 · Procurement" — under the program h1. Long form for non-service codes. */
export function identityLine(row: ProgramRowLike): string {
  const kind = peBliKind(row.exhibit_family);
  const org = /^(A|N|F|SF)$/.test(row.org) ? orgLabel(row.org, "short") : orgLabel(row.org, "long");
  return `${org} · ${peBliLabel(kind, row.pe_bli)} · ${exhibitFamilyLabel(row.exhibit_family)}`;
}

/** "Navy procurement, BLI 2013" — the exhibit's title; assembled, never authored per exhibit. */
export function exhibitTitle(row: ProgramRowLike): string {
  return `${orgLabel(row.org, "short")} ${exhibitFamilyPlain(row.exhibit_family)}, ${peBliLabel(peBliKind(row.exhibit_family), row.pe_bli)}`;
}

/** What is drawn + the one illustration disclaimer. */
export function exhibitCaption(drawn: string): string {
  return `${drawn} ${FIXED.illustration}`;
}

/** Accessible name of a drawn plate: "Virginia Class Submarine plate[, bow section]". */
export function plateName(exhibitName: string, crop?: string): string {
  return `${exhibitName} plate${crop ? `, ${crop}` : ""}`;
}

/** "F-15EX · BLI F015EX →" — a link to a related line. */
export function relatedLineLink(row: ProgramRowLike): string {
  return `${row.title} · ${peBliLabel(peBliKind(row.exhibit_family), row.pe_bli)} →`;
}

const META_TITLE_MAX = 60;

/** "{title} ({PE|BLI} {code}) · {orgShort}", ≤ 60 chars; the title is cut, never the lockup (VOICE rule 28). */
export function metaTitle(row: ProgramRowLike): string {
  const lockup = ` (${peBliLabel(peBliKind(row.exhibit_family), row.pe_bli)}) · ${orgLabel(row.org, "short")}`;
  const room = META_TITLE_MAX - lockup.length;
  let title = row.title;
  if (title.length > room) {
    const cut = title.slice(0, Math.max(room - 1, 1));
    const atWord = cut.lastIndexOf(" ");
    title = `${(atWord > 8 ? cut.slice(0, atWord) : cut).trimEnd()}…`;
  }
  return `${title}${lockup}`;
}

/** "Summary figures only: …" tail for rollup-tier lines; ends with a space so the fixed tail follows. */
export function tierTail(kind: "ingested" | "uningested", service: string): string {
  return kind === "ingested"
    ? `Summary figures only: the ${service} FY2026 J-book carries no R-2/P-40 detail for this line. `
    : `Summary figures only: the ${service} detail book is not yet ingested. `;
}

/** "{title} ({code}), {orgShort}. {basisTail}{tierTail}Every figure links to the document it is printed in." */
export function metaDescription(row: ProgramRowLike, basisTail: string, tier = ""): string {
  return `${row.title} (${row.pe_bli}), ${orgLabel(row.org, "short")}. ${basisTail}${tier}${FIXED.everyFigure}`;
}

/** "The figure is this line's TOA figure for FY2026, read from the P-1 of PB2026." — never hard-codes the document. */
export function fundingNote(basis: "toa" | "jbook-detail", exhibitFamily: string | null, fy: number, edition: number): string {
  const what = basis === "toa" ? "TOA" : "J-book detail";
  return `The figure is this line's ${what} figure for ${fyLabel(fy)}, read from the ${documentForBasis(basis, exhibitFamily)} of ${pbLabel(edition)}.`;
}

// ── Empty states and absences (VOICE rule 19: one grammar) ──────────────────

/**
 * "No {noun} for {scope}. {Named document} carries no {row|entry|narrative} for {subject}.[ Missing coverage is not zero spending.]"
 * The identifier lockup is the subject of the second sentence.
 */
export function emptyState(p: {
  noun: string;
  scope: string;
  document: string;
  rowWord: "row" | "entry" | "narrative";
  subject: string;
  figure?: boolean;
  tail?: string;
  /** "The R-1 and P-1 workbooks carry" vs "The J-book carries". Inferred from the document phrase when omitted. */
  plural?: boolean;
}): string {
  const plural = p.plural ?? /\b(and|workbooks|books|rows)\b/.test(p.document);
  const base = `No ${p.noun} for ${p.scope}. ${p.document} ${plural ? "carry" : "carries"} no ${p.rowWord} for ${p.subject}.`;
  return `${base}${p.figure ? ` ${FIXED.missingCoverage}` : ""}${p.tail ? ` ${p.tail}` : ""}`;
}

/** "No TOA workbook figure for FY2026. The program dossier carries a separate J-book detail figure. The bases are not interchangeable." */
export function absenceNote(p: { basis: string; fy: number; otherPlace: string; otherBasis: string }): string {
  return `No ${p.basis} figure for ${fyLabel(p.fy)}. ${p.otherPlace} carries a separate ${p.otherBasis} figure. The bases are not interchangeable.`;
}

/** The "What changed" absence, one colon, no dash. */
export function changeAbsence(reason: "no-comparison" | "incomplete"): string {
  return reason === "no-comparison"
    ? `No ${TRAJECTORY_FY_LABEL} comparison: endpoints unavailable or on different bases.`
    : `No ${TRAJECTORY_FY_LABEL} comparison: trajectory incomplete for this line.`;
}

// ── Fixed sentences (VOICE rule 20: one wording per meaning) ────────────────

export const FIXED = {
  illustration: "Numbered callouts are funding topics from the program's J-book narrative, not components or prices.",
  allocation: "Shared records are not allocated by variant.",
  basis: "Reported totals and any discretionary/reconciliation splits are alternative views of the same line; do not add them together.",
  fundingAuthority: "Funding authority, not payments or aircraft unit prices.",
  correlation: "Correlation is shown, not causation.",
  missingCoverage: "Missing coverage is not zero spending.",
  everyFigure: "Every figure links to the document it is printed in.",
  siteExport: (date: string) => `Site export ${date}. Source dates vary by dataset.`,
} as const;

// ── Labels (VOICE rule 25: one vocabulary per surface) ──────────────────────

export const ANSWER_LABELS = { what: "What it is", changed: "What changed", who: "Who gets it" } as const;

/** The 13 program sections: chapter (wayfinding), heading (the h2), short (the shortcut bar, where one exists). */
export const SECTION_LABELS: Record<ProgramSectionId, { chapter: string; heading: string; short?: string }> = {
  "answer-strip": { chapter: "Overview", heading: "Overview", short: "Overview" },
  figures: { chapter: "Budget figures", heading: "Budget figures", short: "Budget & history" },
  trajectory: { chapter: "Budget history", heading: "Budget history" },
  lineage: { chapter: "Program lineage", heading: "Program lineage" },
  description: { chapter: "Purpose", heading: "Purpose" },
  justification: { chapter: "Justification", heading: "Justification", short: "Program detail" },
  "line-items": { chapter: "Line items", heading: "Line items" },
  "follow-dollar": { chapter: "Follow the dollar", heading: "Follow the dollar" },
  awards: { chapter: "Related awards", heading: "Related awards", short: "Contracts & influence" },
  lobbying: { chapter: "Lobbying", heading: "Lobbying" },
  oversight: { chapter: "Oversight", heading: "Oversight", short: "Oversight" },
  dossier: { chapter: "Research dossier", heading: "Research dossier" },
  sources: { chapter: "Primary sources", heading: "Primary sources", short: "Sources" },
};

/** Derived, never hand-listed: the sections that carry a shortcut, in section order. */
export const SHORTCUTS: { id: ProgramSectionId; label: string }[] = PROGRAM_SECTIONS.filter((id) => SECTION_LABELS[id].short).map((id) => ({
  id,
  label: SECTION_LABELS[id].short!,
}));

export const EVIDENCE_PATH = {
  title: "Evidence path",
  steps: [
    ["#program-answer-strip", "Overview"],
    ["#program-figures", "Budget figures"],
    ["#program-figures", "Receipt"],
    ["#program-sources", "Primary sources"],
  ],
  note: "A dotted underline marks a cited figure. Its receipt carries the citation, fiscal year and a shareable footnote.",
} as const;

// ── Navigation (header = footer, one vocabulary) ─────────────────────────────

export interface SiteCounts {
  programs: number;
  companies: number;
  agencies: number;
}

export const NAV_GROUPS = ["Budget", "Investigate", "Places & agencies", "Data & methods"] as const;

/** Nav link labels by href — the only spellings. */
export const NAV_LABELS: Record<string, string> = {
  "/explore/": "Field guide",
  "/programs/": "Programs",
  "/years/": "Budget over time",
  "/companies/": "Companies",
  "/feed/": "Signals",
  "/flow/": "Follow the dollar",
  "/lineage/": "Program lineage",
  "/filings/": "Lobbying filings",
  "/companies/families/": "Corporate families",
  "/district/": "Districts",
  "/agency/": "Agencies",
  "/data/": "Data explorer",
  "/downloads/": "Downloads",
  "/coverage/": "Coverage",
  "/methodology/": "Methodology",
  "/glossary/": "Glossary",
  "/about/": "About",
};

/** Nav link details by href — declaratives, counts interpolated from data. */
export const NAV_DETAILS: Record<string, (c: SiteCounts) => string> = {
  "/explore/": () => `Plates for ${countWord(3)} budget lines`,
  "/programs/": (c) => `${count(c.programs, "R&D and procurement line")}`,
  "/years/": () => "Each line's figures by fiscal year",
  "/companies/": (c) => `${count(c.companies, "contractor")} and their awards`,
  "/feed/": () => "Year-over-year swings and concentration shifts",
  "/flow/": () => "Budget lines matched to awards",
  "/lineage/": () => "Predecessor and successor lines across editions",
  "/filings/": () => "Senate LDA filings naming a line",
  "/companies/families/": () => "Parents and subsidiaries of contractors",
  "/district/": () => "Awards by congressional district",
  "/agency/": (c) => `${count(c.agencies, "agency", "agencies")} and their lines`,
  "/data/": () => "SQL queries in the browser",
  "/downloads/": () => "Dataset files and their citations",
  "/coverage/": () => "What each dataset includes and what is missing",
  "/methodology/": () => "Citation tiers and matching rules",
  "/glossary/": () => "Budget terms defined",
  "/about/": () => "The purpose of Fiscal Receipts",
};

// ── Slot strings ─────────────────────────────────────────────────────────────

export const COPY = {
  chrome: {
    skip: "Skip to content",
    more: "More",
    moreAria: "Browse all sections",
    panelHeading: "All sections",
    mobileTitle: "All sections",
    settingsNote: "Citations open with the toggle on or off.",
    factIdTitle: "Fact ID chips beside each cited figure. Citations open with the chips on or off.",
    coachMark: {
      underline: "A dotted underline marks a figure that opens to its source.",
      toggle: "The Fact IDs toggle shows or hides the id chips.",
    },
    footerCoverage: "Coverage varies by dataset.",
    footerMethodologyLink: "Methodology →",
    notFound: "Page not found",
  },
  layout: {
    titleTemplate: "%s | Fiscal Receipts",
    description: "Defense budget lines from the President's Budget, with USAspending awards and Senate LDA filings. Every figure links to the document it is printed in.",
  },
  home: {
    metaTitle: "Defense budget lines, each with its source",
    metaDescription: (c: SiteCounts) => `${count(c.programs, "defense R&D and procurement line")} from PB2026, with USAspending awards and Senate LDA filings. ${FIXED.everyFigure}`,
    /** The count renders as the footer's [data-stat] link; this is the sentence around it. */
    h1: (c: SiteCounts) => `${count(c.programs, "defense budget line")}, each with its source.`,
    h1Tail: ", each with its source.",
    h1Noun: (n: number) => (n === 1 ? "defense budget line" : "defense budget lines"),
    fieldGuideTitle: (n: number) => `What ${countWord(n)} budget lines fund`,
    fieldGuideLede: (n: number) => `${capital(countWord(n))} budget lines, each drawn as a plate. ${FIXED.illustration}`,
    fieldGuideLink: "Field guide →",
    moversTitle: `Largest ${TRAJECTORY_FY_LABEL} changes`,
    moversLede: (n: number) =>
      `The ${countWord(n)} largest changes between FY2025 enacted and the FY2026 request, in dollars. Increases and decreases rank together without a direction filter. Each delta's citation shows the derived formula and both workbook inputs.`,
    moversViewLink: "Program page →",
    moversMethodologyLink: "Methodology →",
    agenciesTitle: "Programs by agency",
    agenciesLede: (n: number) =>
      `${count(n, "agency", "agencies")}, ranked by the number of programs each has in our corpus. The FY2024 column sums each program's R-2/P-40 actuals. Its citation lists the J-book rows added.`,
    agencyTh: { agency: "Agency", programs: "Programs", fy24: "FY24 actuals" },
    agenciesMore: (n: number) => `All ${n.toLocaleString("en-US")} agencies →`,
    trustMethodologyLink: "methodology",
  },
  exhibit: {
    pilotTag: (ordinal: number, n: number) => `Plate ${callout(ordinal - 1)} of ${n}`,
    allExhibits: "All exhibits →",
    stageHint: "Drag or arrow keys rotate the model. +/− zooms.",
    stageIdle: (n: number) => `Illustrative geometry · ${count(n, "funding topic")}`,
    inspect3d: "Inspect in 3D",
    solidView: "Solid view",
    blueprintView: "Blueprint view",
    stillImage: "Still image",
    loading3d: "Loading 3D model",
    error3d: "3D is unavailable in this browser. The plate, topics and receipts remain below.",
    overline: "Funding topics",
    readSource: "Read source passage",
    fundingLabel: "Program funding",
    budgetLink: "Budget figures →",
    share: "Share view",
    linkCopied: "Link copied",
    copyError: "Link not copied. The address bar holds this view's URL.",
    noscript: "The J-book narratives and receipts follow below. The numbered topics need JavaScript.",
  },
  program: {
    stubMetaTitle: (peBli: string, n: number) => `Budget line ${peBli} · ${count(n, "program")}`,
    stubMetaDescription: (peBli: string, n: number, titles: string) => `${count(n, "program")} share budget line ${peBli}: ${titles}. Their figures are never combined.`,
    stubListHeading: "Programs on this code",
    notFound: "Program not found",
    printByline: (url: string, exportDate: string) => `Printed from ${url}. ${FIXED.siteExport(exportDate)} Each figure's citation opens on the page online.`,
    watchFeed: "Program feed",
    lineageFamilyH3: "Program family funding line",
    lineageMapLink: "Lineage map →",
    rollupBadgeTitle: "Summary figures from the R-1/P-1 workbooks: this line carries no R-2/P-40 J-book detail. The Purpose note states why.",
    oversightLink: (orgShort: string) => `GAO record for ${orgShort} →`,
    oversightLinkTitle: (code: string) => `GAO high-risk areas and improper-payment exposure for ${code}`,
    jbookTail: "Not yet crosswalked to USAspending awards.",
    whoNone: "No company for this line: USAspending award rows carry no program element code for the crosswalk to match.",
    whoNoneLink: "Crosswalk method →",
    sourcesPdf: (page: number | string) => `Budget Justification PDF · page ${page}`,
    sourcesWorkbook: (sheet: string) => `Budget Workbook · sheet ${sheet}`,
    /** Every empty state, one grammar. `subject` is the identifier lockup ("BLI 2013"). */
    empty: {
      trajectory: (subject: string) =>
        emptyState({ noun: "FY2024–FY2026 series", scope: "this line", document: "The FY2026 R-1 and P-1 workbooks", rowWord: "row", subject, figure: true }),
      lineage: (subject: string) => `No lineage for this program element. The ingested J-books state no transfer into or out of ${subject}. None was inferred from the program structure.`,
      descriptionDecade: (subject: string) =>
        `No purpose narrative for this line. The FY2026 President's Budget books carry no R-2/P-40 entry for ${subject}. Its figures are read from earlier editions, which this corpus loads as workbook figures.`,
      descriptionFull: (subject: string) =>
        `No purpose narrative for this line. The R-2/P-40 J-book detail carries no separate mission or description entry for ${subject}. The Justification and Line items below carry its prose.`,
      justificationIngested: (subject: string, service: string) =>
        `No justification narrative for this line. The ${service} FY2026 J-book, already ingested, carries no R-2/P-40 narrative for ${subject}.`,
      justificationUningested: (service: string) =>
        `No justification narrative for this line. Its accomplishments and planned-program prose lives in the ${service} J-book, which is not yet ingested. The Purpose note above carries the roadmap.`,
      justificationDecade: (subject: string) => `No justification narrative for this line. The FY2026 President's Budget books carry no R-2/P-40 entry for ${subject}.`,
      justificationFull: (subject: string) => `No justification narrative for this line. The R-2/P-40 J-book detail for ${subject} carries figures without per-project prose.`,
      lineItemsDecade: (subject: string) =>
        emptyState({ noun: "FY2026 line items", scope: "this program element", document: "The FY2026 R-1 and P-1 workbooks", rowWord: "row", subject, figure: true }),
      lineItemsFull: (subject: string) =>
        `No line items for this program element. The R-1/P-1 workbooks and the J-book detail carry no row linked to ${subject}. Its figures appear in the Budget history alone.`,
      awards: (subject: string) => `No awards for ${subject} at high or medium confidence. The USAspending crosswalk withholds links below medium confidence.`,
      lobbying: (subject: string) => `No lobbying filings for this program element. No Senate LDA filing in our corpus names ${subject} by code or alias.`,
      oversight: (org: string, subject: string) =>
        `No GAO overlay for ${org} and no program-specific GAO finding for ${subject}. The GAO high-risk list and improper-payment data carry no entry for either. Absence from those two lists is not a clean bill of health.`,
      sources: (subject: string) => `No document-tier citations for ${subject}. Its figures carry derived-tier citations, each opening to its derivation chain.`,
    },
  },
  family: {
    metaTitle: (designation: string, orgShort: string) => `${designation} aircraft family · ${orgShort}`,
    metaDescription: (designation: string, orgShort: string, variants: number, lines: number) =>
      `${designation} aircraft family, ${orgShort}. ${capital(countWord(variants))} variants and ${countWord(lines)} P-1 and R-1 budget lines, not allocated by variant. ${FIXED.everyFigure}`,
    heroEyebrow: eyebrow("Field guide", "Air"),
    h1Noun: "aircraft family",
    /** The deck: number-first, names the documents, one verb per sentence. */
    deck: (variants: number, lines: number, firstYear: number, orgShort: string) =>
      `${capital(countWord(variants))} aircraft since ${firstYear} and ${countWord(lines)} ${orgShort} P-1 and R-1 lines for development, procurement and modification, not allocated by variant. Each figure opens to the P-1 or R-1 row it was read from.`,
    tabs: { aircraft: "Aircraft", budget: "Budget & receipts", countries: "Countries & orders", history: (designation: string) => `${designation} history` },
    compare: "Aircraft comparison",
    researchTray: "Research tray",
    inspect: {
      srHeading: "Aircraft",
      topicsAria: "Funding topics",
      budgetConnection: "Budget connection",
      readPassage: "Read source passage",
      followFunding: "Funding record →",
      countries: "Countries & orders →",
      nextChapter: (variant: string) => `${variant} budget & receipts →`,
    },
    funding: {
      h2: "Budget & receipts",
      lede: "Each figure is one record's TOA (total obligation authority) for one fiscal year, read from that edition's P-1 or R-1 workbook.",
      runningHead: (orgShort: string, lockup: string) => eyebrow(orgShort, lockup),
      plateTitleTail: "Budget & receipts",
      plateSummary: "Aircraft, software, testing and modifications are separate lines in the P-1 and R-1 workbooks. Each record keeps its own fiscal year, basis and P-1 or R-1 row.",
      inputsHeading: "Workbook rows in this figure",
      rowFallback: "Workbook row",
      officialDocument: "Official document",
      receipt: "Receipt",
      timelineCaption: (units: string) => `TOA by fiscal year · ${units}`,
      noFigure: "No figure",
      notCovered: "Not covered",
      openReceipt: "Open budget receipt",
      save: "Save receipt",
      saved: "Saved to research",
      absenceEyebrow: "Coverage note",
      absenceH3: (fy: number) => `No matching TOA figure for ${fyLabel(fy)}.`,
      whatThisFunds: "What this funds",
      sourceData: (n: number) => `Source data · ${count(n, "record")}`,
      hideContext: "Hide source context",
      showContext: "Show source context",
      previewFallback: "The receipt lists this figure's workbook inputs.",
      previewUnits: (units: string, date: string) => `Units: ${units} · Retrieved ${date}`,
      tableCaption: (title: string) => `Cited fiscal figures for ${title}. Each row carries its fiscal status.`,
      rowsSummary: (fy: number) => `${fyLabel(fy)} workbook rows`,
      rowsTh: { row: "Workbook row / status", amount: "Cited amount" },
    },
    empty: {
      noLine: (category: string, variant: string) => `No ${category.toLowerCase()} line for ${variant}`,
      noMapped: (variant: string) => `No mapped budget line for ${variant}`,
      showMapped: "Show mapped records",
      showRecords: (variant: string) => `Show ${variant} records`,
      countries: "Countries & orders →",
    },
    history: {
      eyebrow: (designation: string) => eyebrow(`${designation} history`, "Air Force pages"),
      h2: (n: number, first: number, last: number) => `${capital(countWord(n))} milestones, ${first}–${last}`,
      lede: (n: number) =>
        `${capital(countWord(n))} milestones, each dated by an Air Force fact sheet or release. A selected milestone opens its variant in the Aircraft tab.`,
      disclosureSummary: "Aircraft families and program elements",
      disclosureBody:
        "An aircraft family is a browsing group, not a budget category. A single program element (PE) or budget line (BLI) can fund several variants. Each variant can draw development, procurement and modification funding from different lines.",
    },
    compareUi: {
      h2: "Aircraft comparison",
      selectLabel: "Second aircraft",
      selectPlaceholder: "No second aircraft",
      aligned: "Aligned overlay →",
      prompt: "No second aircraft for comparison. A second variant appears as an aligned outline in the 3D model, with its role, crew and funding beside this one.",
      noRecordYear: (fy: number) => `No figure for ${fyLabel(fy)} in this collection.`,
      noMapped: (category: string, variant: string) => `No ${category.toLowerCase()} line for ${variant} in this collection.`,
    },
    research: {
      h2: "Research tray",
      copyAll: "Copy all citations",
      savedNote: "Saved on this device only. Each citation keeps its fiscal year, locator and fact link.",
      empty: "No receipts saved on this device. A saved receipt keeps its figure, fiscal year and P-1 or R-1 locator here.",
      sourcesSummary: "Aircraft references & mapping evidence",
    },
    status: {
      ariaLabel: "Status messages",
      soundUnavailable: "Sound is unavailable in this browser. Other controls are unaffected.",
      alreadySaved: "Receipt already saved to the research tray.",
      trayFull: (limit: number) => `Tray full at ${count(limit, "receipt")}. Removing one frees a slot.`,
      saved: "Receipt saved on this device.",
      savedNoStorage: "Receipt saved for this visit only: local storage is off.",
      copyUnavailable: "Clipboard access is unavailable. The text below is selectable.",
      copyLabel: "Text to copy",
      linkCopied: "Link copied with variant, record, year, topic and comparison.",
      citationsCopied: "Citations copied with fiscal year, locator and fact link.",
    },
    model: {
      shareTitle: "Link carries aircraft, record and year",
      plateAlt: (designation: string) => plateName(`${designation} aircraft family`, "front elevation"),
      aircraftLink: "Aircraft →",
      frontElevation: "Front elevation",
    },
    noscript: (variant: string) =>
      `The ${variant} funding record and its P-1 links render without JavaScript. Variant switching and the 3D model need JavaScript.`,
    noscriptLink: (variant: string) => `${variant} program page →`,
  },
} as const;


export const WATCH_COPY = {
  program: "Published budget signals for this program, with links to receipts.",
  company: "Published signals for this company’s linked programs. These links do not establish supplier revenue.",
  feed: "Published budget signals, with links to their supporting receipts.",
  timing: "Updates appear after a data refresh and publication. No fixed update schedule is available.",
  instruction: "Paste the RSS address into a feed reader. No Fiscal Receipts account is required.",
  unavailable: "No watch feed is available for this program in the current export. Coverage may change in a later publication.",
} as const;

export const BRIEFING_COPY = {
  intro: "PB2026 comparisons with both receipts. The explanations distinguish documented plans from causes the budget books do not establish.",
  dateNote: "Review dates are separate from publication dates.",
};
