/**
 * gate 21 — program_skeleton_gate (Phase 5F §2d)
 *
 * Every program page — full tier, rollup tier AND the ROADMAP #28 decade
 * tier — renders the SAME ordered section skeleton. Sampled pages from every
 * tier are checked for:
 *
 * (a) All 12 [data-section] markers present in the canonical order
 *     (independent copy of src/components/program-section.tsx
 *     PROGRAM_SECTIONS — a drift between the two is a real failure).
 * (b) Every [data-section-empty] element carries a non-trivial explanation
 *     (≥ 40 chars — the quiet line must say WHY the section is empty).
 * (c) Rollup pages carry the honest service-J-book note:
 *     [data-coverage="service-books"] whose text names the page's service
 *     (recomputed from the sidecar's service_org) and whose 'roadmap' word
 *     links to /methodology/#coverage-service-books.
 * (d) Full-tier pages with project detail rows expose #project-{n} anchors
 *     (§2a "PE X, Project Y" reference targets).
 * (e) noindex policy: every zero-content page (recomputed predicate: no
 *     details/narratives/awards/mentions and all figures zero) carries
 *     <meta name="robots" content~="noindex">; sampled content pages do NOT.
 * (f) WHAT-IT-IS card is not a template stub (PM Sprint 2, §P1-2) — see
 *     leg f's own block at the bottom of this file.
 * (g) A program element that PB2026 stopped requesting money for must not
 *     end silently: it carries the [data-fy2026-absent] note, and no other
 *     page does (ROADMAP #32a) — see leg g's own block at the bottom.
 * (h) A GAO program-level finding renders only where a human ratified the
 *     crosswalk, quotes GAO verbatim, cites its own report and its own WSAA
 *     edition, and sits above the department note; an earlier edition stands
 *     only on a ratified anchor for the same program on the same page; every
 *     other page states the absence (ROADMAP #30) — see leg h's own block at
 *     the bottom.
 * (i) The organization a program page names is an org CODE, and the three
 *     things that key off it actually happen: the header's own "Organization
 *     code {X}" claim is true, X links to its agency page when one exists,
 *     and the GAO department note renders exactly where the overlay payload
 *     has one — see leg i's own block at the bottom.
 * (j) The WHO GETS IT card declares which of four tiers it is answering from,
 *     states dollars ONLY on the award tier, and — where it names companies
 *     from lobbying filings — reads as a fixed sentence that puts the absence
 *     of a contract before the names, on evidence tiers strong enough to name
 *     anyone (tri-persona Wave 3) — see leg j's own block at the bottom.
 * (k) A decade-only page (ROADMAP #28: cited pre-PB2026 history, no FY2026
 *     workbook line at all) states its absence, states it about the record
 *     that is actually blank, and states nothing the page itself contradicts
 *     — see leg k's own block at the bottom.
 * (l) The successor clause is checked against the page's OWN narratives, not
 *     only the lineage rail: no note renders the retired corpus-wide denial,
 *     the narrative pointer renders exactly where the page renders prose,
 *     and every no-rail page whose narrative names a forward pointer sends
 *     the reader to it (ROADMAP #32(b) residue) — see leg l's own block.
 * (n) A pe_bli shared by two programs files each member's crosswalk links on
 *     that member's own page, never on both and never on the bare
 *     disambiguation stub (ROADMAP #70); each account-split member's title
 *     block names ITS OWN appropriation and never the sibling's, a
 *     concentration figure withheld because both members are linked is
 *     said on the card, not hidden, and each member publishes only the
 *     J-book narratives and detail rows from its OWN volume — no narrative
 *     or detail fact id on two member pages, and a lobbying mention on a
 *     member page only where that page's own title carries the terms the
 *     mention matched, unless the filing named the shared CODE itself
 *     (ROADMAP #82) — see leg n's own block.
 * (o) The service-books coverage note says the SAME thing the data says —
 *     it renders on exactly the pages with no R-2/P-40 detail (rollup tier
 *     AND the synthesized full-tier pages the 2026-07-05 fix never covered),
 *     it names the page's own org, and the branch it picks agrees with
 *     site_meta.ingested_service_orgs. ROADMAP #14 — see leg o's own block.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { parse } from "node-html-parser";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, "..", "..");
const outDir = path.resolve(siteRoot, "out");
const jsonDir = path.resolve(siteRoot, "..", "data", "site", "json");

// Independent copy of PROGRAM_SECTIONS (src/components/program-section.tsx).
const CANONICAL_SECTIONS = [
  "answer-strip",
  "figures",
  "trajectory",
  "lineage",
  "description",
  "justification",
  "line-items",
  "follow-dollar",
  "awards",
  "lobbying",
  "oversight",
  "dossier",
  "sources",
];

const SAMPLE_PER_TIER = 8;
const MIN_EMPTY_EXPLANATION_CHARS = 40;

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function pageHtmlPath(slug) {
  return path.join(outDir, "program", slug, "index.html");
}

function serviceName(code) {
  return { A: "Army", N: "Navy", F: "Air Force" }[code] ?? (code || "service");
}

/** Independent recompute of the zero-content noindex predicate
 *  (src/lib/program-tier.ts isZeroContentDetails). */
function isZeroContent(d) {
  if (
    (d.details ?? []).length > 0 ||
    (d.narratives ?? []).length > 0 ||
    (d.awards ?? []).length > 0 ||
    (d.mentions ?? []).length > 0
  ) {
    return false;
  }
  const figures = (d.budget_lines ?? []).map((bl) => bl.amount_thousands);
  const t = d.trajectory;
  if (t) {
    for (const v of [t.fy2024_actuals, t.fy2025_total, t.fy2026_total]) {
      if (v !== null && v !== undefined) figures.push(v);
    }
  }
  // ROADMAP #28 widened the figure set here for the same reason the source
  // did: a decade-tier sidecar carries no budget_lines, no trajectory and no
  // prose, so on the pre-#28 predicate `figures` was [] and [].every() is
  // true — all 553 pages would be classed zero-content, noindexed and
  // dropped from sitemap.xml, and this gate would have DEMANDED that.
  for (const points of Object.values(d.decade_series ?? {})) {
    for (const p of points ?? []) {
      if (p.v !== null && p.v !== undefined) figures.push(p.v);
    }
  }
  return figures.every((v) => v === 0);
}

/** First + last N/2 of a sorted list (spread across the alphabet). */
function spreadSample(slugs, n) {
  if (slugs.length <= n) return [...slugs];
  const head = slugs.slice(0, Math.ceil(n / 2));
  const tail = slugs.slice(-Math.floor(n / 2));
  return [...new Set([...head, ...tail])];
}

// ═══════════════════════════════════════════════════════════════════════════
// leg m — the in-table medium caveat is true of EVERY medium species
// ═══════════════════════════════════════════════════════════════════════════
//
// THE DEFECT (#77, corrected by the 2026-09-04 final review, finding C3). The
// caveat under a Related Awards table said medium rows "drew from the same
// appropriation account and agency as this program". That is true of the
// account/sub-agency species (~8,800 mart rows) and FALSE of the ~2,300 that
// rest on an FPDS acquisition-program tag (1,910), a subaward description
// (113) or an unadjudicated keyword match (217) — and /methodology/ describes
// those correctly one page away, so the site contradicted itself. The table
// carries no method column, so the pooled sentence must be true of all four
// species or it is a false sentence about the table.
//
// These are the phrases that make it true; each names a species the old
// sentence excluded. Reword the caveat and this leg fails, which is the
// contract — MIRROR of src/__tests__/program-awards-caveat.test.tsx, which
// asserts the same strings against the component.
const MEDIUM_CAVEAT_PHRASES = [
  "rest on evidence weaker than a program-level match",
  "same appropriation account as this program",
  "not evidence that this program paid for the contract",
  "FPDS acquisition-program tag or a subaward description",
  "which of its budget lines paid is not",
  "high rows rest on evidence that names this program",
];

/** Non-vacuity floor for leg m (added 2026-09-04 with the C3 fix).
 *
 *  MEASURED, and the reason the targeted pass below exists: the leg's own
 *  24-page sample (head+tail of each tier's sorted slug list) reaches ZERO
 *  pages carrying a medium award row, so the presence check had never once
 *  executed since it was added — it was green on every build for the same
 *  reason leg n was green on a corpus of zeroes. Measured 2026-09-04 from
 *  data/site/json/program_details: 247 pages carry a medium row inside the
 *  25 the page renders before "show all". The targeted pass takes 8 of them,
 *  spread head+tail; the floor sits below that with headroom for pages the
 *  build skips, and above the regression it exists to catch (a selector or
 *  slice change that silently stops finding any caveat at all).
 *  RE-MEASURE if the corpus changes; never lower it to whatever the build
 *  produced. */
const MIN_MEDIUM_CAVEATS_SAMPLED = 5;
/** How many medium-carrying pages the targeted pass parses. */
const MEDIUM_CAVEAT_SAMPLE = 8;

/** Check one built program page's medium caveat.
 *  → {checked, ok}: `checked` counts toward the non-vacuity floor (the page
 *  actually renders a medium badge AND a caveat); `ok` is false when the page
 *  broke the contract. */
function checkMediumCaveat(errors, slug, root) {
  const hasMedium =
    root.querySelectorAll('[title="Match confidence: medium"]').length > 0;
  if (!hasMedium) return { checked: false, ok: true };
  const tierNote = root.querySelector('[data-awards-tier-note="medium"]');
  if (!tierNote) {
    errors.push(
      `program-skeleton(m): /program/${slug}/: medium-tier award rows without [data-awards-tier-note]`,
    );
    return { checked: false, ok: false };
  }
  let ok = true;
  const noteText = (tierNote.text ?? "").replace(/\s+/g, " ").trim();
  const missing = MEDIUM_CAVEAT_PHRASES.filter((phrase) => !noteText.includes(phrase));
  if (missing.length > 0) {
    ok = false;
    errors.push(
      `program-skeleton(m): /program/${slug}/: the medium caveat is missing ` +
        `${missing.length} load-bearing phrase(s) — ` +
        `${missing.map((phrase) => `"${phrase}"`).join(", ")}. The table has no ` +
        `method column, so the pooled sentence has to be true of ALL four ` +
        `medium species (account*, fpds-ap, subaward+lexicon)`,
    );
  }
  if (noteText.includes("drew from the same appropriation account and agency")) {
    ok = false;
    errors.push(
      `program-skeleton(m): /program/${slug}/: the medium caveat states the ` +
        `withdrawn pre-C3 sentence ("drew from the same appropriation account ` +
        `and agency"), which is false for FPDS-tagged, subaward-derived and ` +
        `keyword-matched medium rows`,
    );
  }
  return { checked: true, ok };
}

/** Slugs whose sidecar carries a medium award inside the first
 *  PROGRAM_AWARDS_CAP rows — i.e. the pages that actually render the caveat.
 *  Kept in step with program-awards.tsx's CAP and the page's slice(0, CAP). */
const PROGRAM_AWARDS_CAP = 25;
function mediumCaveatCandidates(sidecars) {
  const out = [];
  for (const [slug, d] of sidecars) {
    const shown = (d.awards ?? []).slice(0, PROGRAM_AWARDS_CAP);
    if (shown.some((a) => String(a.confidence ?? "").toLowerCase() === "medium")) {
      out.push(slug);
    }
  }
  return out.sort();
}

export async function runProgramSkeletonGate() {
  const errors = [];
  const notes = [];

  const detailsDir = path.join(jsonDir, "program_details");
  if (!fs.existsSync(detailsDir)) {
    errors.push("program-skeleton: data/site/json/program_details missing");
    return { pass: false, errors, notes };
  }
  if (!fs.existsSync(path.join(outDir, "program"))) {
    notes.push("out/program/ not found — site not yet built (SKIP)");
    return { pass: true, errors, notes };
  }

  // ── Classify sidecars by tier + zero-content ─────────────────────────────
  const fullSlugs = [];
  const rollupSlugs = [];
  const decadeSlugs = [];
  const zeroContentSlugs = [];
  const sidecars = new Map();
  for (const f of fs.readdirSync(detailsDir).filter((x) => x.endsWith(".json")).sort()) {
    const slug = f.replace(/\.json$/, "");
    let d;
    try {
      d = readJson(path.join(detailsDir, f));
    } catch {
      errors.push(`program-skeleton: unreadable sidecar ${f}`);
      continue;
    }
    sidecars.set(slug, d);
    // ROADMAP #28: a THIRD tier. Left unclassified it would fall into
    // fullSlugs, and leg (d) would look for project anchors on a page with
    // no project rows while leg (f) demanded a field-sourced WHAT-IT-IS card
    // from a page that has no fields to build one from.
    if (d.tier === "rollup") rollupSlugs.push(slug);
    else if (d.tier === "decade") decadeSlugs.push(slug);
    else fullSlugs.push(slug);
    if (isZeroContent(d)) zeroContentSlugs.push(slug);
  }
  notes.push(
    `universe: ${fullSlugs.length} full + ${rollupSlugs.length} rollup + ` +
      `${decadeSlugs.length} decade pages, ` +
      `${zeroContentSlugs.length} zero-content (noindex)`
  );

  const sample = [
    ...spreadSample(fullSlugs, SAMPLE_PER_TIER),
    ...spreadSample(rollupSlugs, SAMPLE_PER_TIER),
    ...spreadSample(decadeSlugs, SAMPLE_PER_TIER),
  ];

  // ── (a)+(b)+(c)+(d) per sampled page ─────────────────────────────────────
  // Leg (c) accepts a recorded-absence wording, and two of the three MARKERS
  // name the edition: read the years the payload records once, never type one.
  const absenceFys = absenceFiscalYears();
  let pagesOk = 0;
  let mediumCaveatsChecked = 0;
  for (const slug of sample) {
    const p = pageHtmlPath(slug);
    if (!fs.existsSync(p)) {
      errors.push(`program-skeleton: sampled page /program/${slug}/ not built`);
      continue;
    }
    const root = parse(fs.readFileSync(p, "utf8"), { comment: false });
    const d = sidecars.get(slug);
    const tier =
      d.tier === "rollup" ? "rollup" : d.tier === "decade" ? "decade" : "full";
    let pageOk = true;

    // (a) canonical section order
    const sections = root
      .querySelectorAll("[data-section]")
      .map((el) => el.getAttribute("data-section"));
    if (JSON.stringify(sections) !== JSON.stringify(CANONICAL_SECTIONS)) {
      pageOk = false;
      const missing = CANONICAL_SECTIONS.filter((s) => !sections.includes(s));
      errors.push(
        `program-skeleton(a): /program/${slug}/ (${tier}) sections != canonical order — ` +
          `got [${sections.join(", ")}]${missing.length ? `; missing: ${missing.join(", ")}` : ""}`
      );
    }

    // (b) empty states carry explanations
    for (const emptyEl of root.querySelectorAll("[data-section-empty]")) {
      const text = (emptyEl.text ?? "").trim();
      if (text.length < MIN_EMPTY_EXPLANATION_CHARS) {
        pageOk = false;
        errors.push(
          `program-skeleton(b): /program/${slug}/ empty state without explanation: "${text.slice(0, 60)}"`
        );
      }
    }

    // (c) rollup honesty note
    if (tier === "rollup") {
      const note = root.querySelector('[data-coverage="service-books"]');
      if (!note) {
        pageOk = false;
        errors.push(
          `program-skeleton(c): /program/${slug}/ (rollup) missing [data-coverage="service-books"] note`
        );
      } else {
        const svc = serviceName(d.service_org ?? "");
        const text = note.text ?? "";
        // The note must name the service and its book, in one of THREE honest
        // wordings. (1) Phase 5G's UNINGESTED wording ("…lives in the {svc}
        // J-book, which is not yet ingested…") and (2) its INGESTED wording
        // ("The {svc} FY2026 J-books are ingested, but this program element
        // carries no R-2/P-40 narrative…") — Army 'A', Navy 'N' and Air Force
        // / Space Force 'F' render the second, most other codes the first.
        // (3) Task 17c's RECORDED-ABSENCE wordings, one per rule in
        // site_meta.org_absences: no RDT&E or procurement book published, a
        // summary line no book narrates, or a book downloaded with no embedded
        // payload. THIS LEG only asks that the note states one of them about
        // THIS page's org and is never generic; leg (o) is the one that checks
        // it is the RIGHT one for the payload, and it reads every page rather
        // than this 8-page-per-tier sample. Without case 3 this leg fails on
        // the DEFW pages, which sort into the sample's tail. Two of those
        // markers name the edition, so they are built for every year the
        // payload records — which year belongs to which org is leg (o)'s
        // question, not this one's.
        const namesUningested = text.includes(`lives in the ${svc} J-book`);
        const namesIngested =
          text.includes(`The ${svc} FY2026 J-book`) &&
          text.includes("no R-2/P-40 narrative");
        const namesAbsence = absenceFys.some((fy) =>
          Object.values(ABSENCE_MARKERS).some((marker) =>
            text.includes(marker(svc, fy)),
          ),
        );
        if (!namesUningested && !namesIngested && !namesAbsence) {
          pageOk = false;
          errors.push(
            `program-skeleton(c): /program/${slug}/ note does not name the ${svc} justification book / J-book (got: "${text.slice(0, 100)}")`
          );
        }
        const roadmapLink = note
          .querySelectorAll("a[href]")
          .find(
            (a) =>
              (a.getAttribute("href") ?? "").includes("/methodology/#coverage-service-books") &&
              (a.text ?? "").trim() === "roadmap"
          );
        if (!roadmapLink) {
          pageOk = false;
          errors.push(
            `program-skeleton(c): /program/${slug}/ note's 'roadmap' word is not linked to /methodology/#coverage-service-books`
          );
        }
      }
    }

    // (d) project anchors on full-tier pages with project rows
    if (tier === "full") {
      const firstProject = (d.details ?? []).find((r) => r.project_number);
      if (firstProject) {
        const anchorId = `project-${String(firstProject.project_number).replace(/[^A-Za-z0-9-]/g, "_")}`;
        if (!root.querySelector(`[id="${anchorId}"]`)) {
          pageOk = false;
          errors.push(
            `program-skeleton(d): /program/${slug}/ missing project anchor #${anchorId}`
          );
        }
      }
    }

    // (m) a Related Awards table showing any medium badge must carry the
    // in-table caveat, and that caveat must be TRUE of every medium species.
    // See checkMediumCaveat + the targeted pass below the sample loop.
    const caveat = checkMediumCaveat(errors, slug, root);
    if (caveat.checked) mediumCaveatsChecked++;
    if (!caveat.ok) pageOk = false;

    if (pageOk) pagesOk++;
  }
  notes.push(`sampled ${sample.length} pages (${SAMPLE_PER_TIER}/tier target): ${pagesOk} fully conformant`);
  // ── (m) targeted pass: the pages that actually render the caveat ─────────
  // The 24-page sample above reaches none of them (see the floor's comment),
  // so the check that matters runs here or nowhere.
  const mediumCandidates = mediumCaveatCandidates(sidecars);
  for (const slug of spreadSample(mediumCandidates, MEDIUM_CAVEAT_SAMPLE)) {
    const p = pageHtmlPath(slug);
    if (!fs.existsSync(p)) continue;
    const root = parse(fs.readFileSync(p, "utf8"), { comment: false });
    if (checkMediumCaveat(errors, slug, root).checked) mediumCaveatsChecked++;
  }
  if (mediumCaveatsChecked < MIN_MEDIUM_CAVEATS_SAMPLED) {
    errors.push(
      `program-skeleton(m): only ${mediumCaveatsChecked} sampled page(s) ` +
        `rendered a medium-tier caveat (floor ${MIN_MEDIUM_CAVEATS_SAMPLED}, ` +
        `measured 2026-09-04: 247 pages render a medium row, of which this leg ` +
        `parses ${MEDIUM_CAVEAT_SAMPLE}). Below the floor the wording check ` +
        `has nothing to read and would pass on a build that renders no ` +
        `caveat at all — the same vacuity leg n had. Re-measure the ` +
        `population; do not lower the floor`,
    );
  } else if (errors.some((e) => e.startsWith("program-skeleton(m)"))) {
    notes.push(
      `leg m: ${mediumCaveatsChecked} built page(s) carry a medium-tier caveat ` +
        `(floor ${MIN_MEDIUM_CAVEATS_SAMPLED}) — see the leg m error(s) above`,
    );
  } else {
    notes.push(
      `leg m: ${mediumCaveatsChecked} built page(s) carry a medium-tier caveat ` +
        `(floor ${MIN_MEDIUM_CAVEATS_SAMPLED}), each stating all ` +
        `${MEDIUM_CAVEAT_PHRASES.length} load-bearing phrases ✓`,
    );
  }

  // ── (e) noindex policy ────────────────────────────────────────────────────
  const hasNoindex = (root) =>
    root
      .querySelectorAll('meta[name="robots"]')
      .some((m) => (m.getAttribute("content") ?? "").includes("noindex"));

  for (const slug of zeroContentSlugs) {
    const p = pageHtmlPath(slug);
    if (!fs.existsSync(p)) {
      errors.push(`program-skeleton(e): zero-content page /program/${slug}/ not built`);
      continue;
    }
    const root = parse(fs.readFileSync(p, "utf8"), { comment: false });
    if (!hasNoindex(root)) {
      errors.push(
        `program-skeleton(e): zero-content page /program/${slug}/ is missing robots noindex`
      );
    }
  }
  // Sampled content pages must NOT be noindexed.
  for (const slug of sample.filter((s) => !zeroContentSlugs.includes(s)).slice(0, 6)) {
    const p = pageHtmlPath(slug);
    if (!fs.existsSync(p)) continue;
    const root = parse(fs.readFileSync(p, "utf8"), { comment: false });
    if (hasNoindex(root)) {
      errors.push(
        `program-skeleton(e): content page /program/${slug}/ is wrongly noindexed`
      );
    }
  }
  notes.push(
    `noindex: ${zeroContentSlugs.length} zero-content page(s) checked` +
      (zeroContentSlugs.length ? ` (${zeroContentSlugs.join(", ")})` : "")
  );

  // ── (f) WHAT-IT-IS card is not a template stub (§P1-2) ────────────────────
  runWhatItIsLeg({ errors, notes });

  // ── (g) the PB2026 renumber note (ROADMAP #32a) ───────────────────────────
  runFy2026AbsentLeg({ errors, notes, sidecars });

  // ── (l) the successor clause against the page's own narratives (#32b) ────
  runNarrativeSuccessorLeg({ errors, notes, sidecars });

  // ── (h) the GAO program tier (ROADMAP #30) ────────────────────────────────
  runGaoProgramLeg({ errors, notes, sidecars });

  // ── (i) the org a page names is an org CODE (#30's cause) ─────────────────
  runOrgCodeLeg({ errors, notes, sidecars });

  // ── (j) WHO GETS IT: lobbying evidence is never award evidence ───────────
  runWhoGetsItLeg({ errors, notes, sidecars });

  // ── (k) the decade-only tier's absence claims (ROADMAP #28) ─────────────
  runDecadeOnlyLeg({ errors, notes, sidecars });

  // ── (n) a shared BLI code's members own their own awards (#70) and their
  //        own J-book narratives, details and mentions (#82) ───────────────
  runSplitKeyAwardsLeg({ errors, notes, sidecars });

  // ── (o) the coverage note agrees with the loaded-book set (ROADMAP #14) ──
  runCoverageNoteLeg({ errors, notes, sidecars });

  return { pass: errors.length === 0, errors, notes };
}

// ═══════════════════════════════════════════════════════════════════════════
// leg n — a shared BLI code's two members own their own awards (ROADMAP #70)
// ═══════════════════════════════════════════════════════════════════════════
//
// Ten pe_bli values are shared by TWO real programs that differ only by
// appropriation account ('3010' is LPD Flight II in Shipbuilding & Conversion,
// Navy AND Shipboard Tactical Communications in Other Procurement, Navy).
// Sprint E gave each member its own page and made the bare /program/{pe}/ a
// disambiguation stub; #70 makes their crosswalk links land on the right
// member by carrying the account the link's own evidence identified.
//
// The failure this leg exists to catch is the #56 fusion shape, relocated
// into the Related Awards table: an exporter keyed on the BARE pe_bli hands
// BOTH members every award on the shared code, so a reader sees one program's
// contracts filed under the other's name — with every number↔citation gate
// still green, because each link is individually true. Eight checks:
//
//   1. no award PIID appears on more than one member of one shared code;
//   2. each member's programs.json award_count equals its own sidecar's
//      awards array (the count and the table cannot disagree);
//   3. the bare key owns no sidecar and its stub page renders no awards
//      table — the stub is a chooser, and it must never state award facts
//      about a program the reader has not chosen yet;
//   4. a non-vacuity floor, because all three checks above pass perfectly on
//      a corpus where every member page shows ZERO awards.
//   5. (ROADMAP #82) each ACCOUNT-split member page renders exactly one
//      [data-program-account] whose text names that member's own
//      account_title and account code and never the sibling's; an
//      organization-split member (one account, e.g. 0300D on '20'/'30'/'500')
//      renders none — the org link discriminates there and the account
//      would read the same on both pages; the stub renders none;
//   6. a member with a sidecar and no built page is an error, not a skip —
//      otherwise check 5 is satisfied by a corpus with no pages;
//   7. (ROADMAP #82) renderer ↔ payload for the withheld concentration
//      state: a sidecar whose summary.concentration_withheld is true must
//      declare the "none" tier AND render [data-who-withheld], and no page
//      may render that marker without the payload. The tier clause is not
//      decoration: a withheld member carries linked awards by construction
//      (that is WHY the bare-line figure is nobody's), so the award tier is
//      impossible — its block is the withheld one — and the J-book and
//      lobbying tiers' closing sentences ("not yet crosswalked to award
//      data"; "No contract award is linked to this line") are false above
//      that member's own Related Awards table. The exporter's per-member
//      awards guard is what keeps those two off the page; this check is
//      what notices if it is ever dropped. The card's "no company is linked"
//      sentence is false there too, and the exporter is the only party that
//      knows the figure exists and is nobody's.
//   8. (ROADMAP #82, the narrative axis) on a shared code, no J-book
//      narrative or detail fact id appears on more than one member page.
//
//      The rule, per axis, and why the answer differs by source:
//        * narratives and details are J-BOOK rows, and a J-book is one
//          program's book — the SCN volume and the OPN volume are different
//          documents, and each row's own document carries the appropriation
//          (account axis) or the component (organization axis) that says
//          which member it is about. So a fact id belongs to exactly one
//          member page and appearing on two is the defect.
//        * mentions are LOBBYING rows, and the basis is PER ROW — the row's
//          own evidence_kind (#52) says which, and the sidecar declares it
//          as `mentions_shared_code: {evidence_kind: basis}`:
//            - `pe_literal` -> "code". The filing's activity description
//              contains the budget-line code ("30"), which names the LINE
//              and nothing finer, so the row is evidence about the CODE,
//              true of every program that uses it. Both members render it
//              and the /filing/ page carries the note saying the mention
//              cannot tell them apart. Exempt from the no-repeat rule.
//            - `multi_token`/`alias` -> "title". The row qualified by
//              matching ONE program title's tokens, and the page renders the
//              badge "at least two distinct, non-generic words from this
//              program's title". This check re-derives that test from
//              programs.json's own titles: every term in matched_term must
//              appear in the page's title, or the badge is false and the row
//              does not belong on the page. Checked like a narrative — the
//              declaration is read, never trusted, so a sidecar that
//              declares "code" for a multi_token row fails here.
//          An undeclared mention is an error either way: a silent repeat is
//          indistinguishable from the narrative defect.
//
//      Measured 2026-09-18, BEFORE this check's mention half: 7 rendered
//      rows failed it — /program/0145-APN/ "F/A-18E/F (Fighter) Hornet"
//      badged 5 rows "matched 2+ title words" for `General|Purpose` (its
//      SIBLING is "General Purpose Bombs") and /program/1350-WPN/ "Missile
//      Industrial Facilities" badged 2 for `Weapons|Ammunition`. 2292's two
//      members carry identical titles, so all 18 of theirs are true on both.
//      No floor is written for the mention half: unlike the J-book axis,
//      an exporter that drops every title-basis row fails safe (a page loses
//      rows it should not render, never gains a false badge), and the
//      J-book floor below already pins the same member population.
//
//      Measured 2026-09-12, BEFORE the fix, on the shipped corpus: all 13
//      shared codes published identical narratives and identical details on
//      every member — 55 narrative and 139 detail fact ids on more than one
//      member page. /program/3010-SCN/ rendered "Shipboard Tactical
//      Communications" prose and the OPN volume's money under the LPD
//      Flight II heading, every citation resolving, because each row is
//      individually true of SOMETHING.

/** Non-vacuity floor for leg n (added 2026-09-04, #70 fix round 1 — the
 *  leg's first standalone run printed "0 member page(s) carry 0 award row(s)"
 *  and PASSED).
 *
 *  Measured 2026-09-04 from Postgres, not from a build: budget_line_awards
 *  where account is not null, left-joined to award_pe_adjudications and
 *  filtered to the tiers fct_budget_to_awards publishes (published
 *  confidence high or medium) — SEVEN shared-code member pages carrying
 *  EIGHTY-SIX award rows:
 *
 *    0145-PANMC  3   (announcement+lexicon, high)
 *    2101-WPN   23   (fpds-ap, medium)
 *    3010-SCN    5   (fpds-ap, medium)
 *    3010-OPN    3   (fpds-ap, medium)
 *    3050-OPN   50   (4 announcement+lexicon high, 46 subaward+lexicon medium)
 *    3215-OPN    1   (fpds-ap, medium)
 *    4217-OPN    1   (fpds-ap, medium)
 *
 *  All 86 rows are unadjudicated, so no adjudication drops or demotes any of
 *  them, and each (pe_bli, account) pair has a dim_programs row, so each
 *  resolves to a page that exists.
 *
 *  The floor sits below that with headroom for ordinary corpus movement
 *  (re-derivation of the FPDS account narrowing, a new adjudication) but
 *  above the regression it exists to catch: split_key drift between the mart
 *  and the sidecar writer files every one of these links under a key no page
 *  reads, and all three checks above stay green on the resulting corpus of
 *  zeroes. RE-MEASURE and re-derive these numbers if the corpus changes;
 *  never lower them to whatever the build produced. */
const MIN_SPLIT_MEMBER_PAGES_WITH_AWARDS = 5;
const MIN_SPLIT_AWARD_ROWS = 60;

/** Non-vacuity floor on the split UNIVERSE (added 2026-09-04, final review
 *  I4). The two floors above are reached only after `splits.length === 0`
 *  returns early with a friendly note — so a programs.json that lost its
 *  shared-code members entirely (an exporter regression that stops emitting
 *  the account-qualified rows, a slug-shape change that makes every pe_bli
 *  look unique) made the whole leg say "nothing to check" and pass. The
 *  emptiness IS the regression.
 *
 *  Measured 2026-09-04 from data/site/json/programs.json: THIRTEEN pe_bli
 *  codes carry more than one dim_programs row. The floor sits below that with
 *  headroom for ordinary corpus movement and above zero.
 *  RE-MEASURE if the corpus changes; do not lower it to fit a build. */
const MIN_SHARED_BLI_CODES = 10;

/** Non-vacuity floor for check 5 (added 2026-09-05, ROADMAP #82).
 *
 *  Measured 2026-09-05 from data/site/json/programs.json, re-measured
 *  2026-09-11 (unchanged): TEN account-split codes × 2 members = TWENTY
 *  member pages carry a non-null account_title and a sibling in another
 *  account. The 3 organization-split codes' 7 members share one account
 *  (0300D) and render no appropriation line, so they do not count here. The
 *  floor sits below 20 with headroom for ordinary corpus movement and above
 *  the regression it exists to catch: a header that stops emitting
 *  [data-program-account] makes every per-page assertion in check 5 vacuous.
 *  RE-MEASURE if the corpus changes; never lower it to fit a build. */
const MIN_ACCOUNT_SPLIT_MEMBER_PAGES = 16;

/** Non-vacuity floor for check 8 (added 2026-09-12, ROADMAP #82 narrative
 *  axis).
 *
 *  Measured 2026-09-12 from Postgres and from the shipped sidecars: every one
 *  of the TWENTY-SEVEN shared-code member pages carries at least one J-book
 *  narrative or detail fact id of its own, because every member has its own
 *  volume in the PB2026 corpus:
 *
 *    0145-APN   APN_BA1-4_Book (1506N)   0145-PANMC PANMC_Book (1508N)
 *    1350-WPN   WPN_Book (1507N)         1350-PANMC PANMC_Book (1508N)
 *    2101-PMC   PMC_Book (1109N)         2101-WPN   WPN_Book (1507N)
 *    2210-WPN / 2292-WPN / 3215-WPN / 3302-WPN / 4217-WPN  WPN_Book (1507N)
 *    2210-OPN / 3010-OPN / 3050-OPN / 3215-OPN / 3302-OPN / 4217-OPN
 *                                        OPN_BA1_Book (1810N)
 *    2292-PMC   PMC_Book (1109N)         3010-SCN / 3050-SCN  SCN_Book (1611N)
 *    20-DCSA / 20-DTRA / 30-OSD / 30-DTRA / 30-DMACT / 500-DHRA / 500-DLA
 *                                        one PROC_{ORG}_PB_2026 volume each
 *
 *  Check 8 is a no-duplicate assertion, and a corpus where every member page
 *  publishes NOTHING satisfies it perfectly — which is exactly what a
 *  split_key drift between the J-book indexes and the sidecar writer
 *  produces: every row files under a key no page reads and all 27 pages go
 *  silent. The floor sits below 27 with headroom for ordinary corpus movement
 *  (a volume withdrawn, a member that stops publishing detail) and above that
 *  regression. RE-MEASURE if the corpus changes; never lower it to whatever
 *  the build produced. */
const MIN_SPLIT_MEMBER_PAGES_WITH_JBOOK_ROWS = 22;

/** Default page reader — the gate reads site/out; the unit test injects its
 *  own `pageHtml` so a corpus the build does not contain can be checked. */
function readPageHtml(slug) {
  const p = pageHtmlPath(slug);
  return fs.existsSync(p) ? fs.readFileSync(p, "utf8") : null;
}

/** `programs` and `pageHtml` are injected only by this leg's unit test
 *  (__tests__/split-key-awards.test.mjs), which has to be able to hand the leg
 *  a corpus the build does not contain — a floor that has never been seen to
 *  trip is not a floor. The gate itself always passes them undefined and reads
 *  the shipped programs.json and site/out. */
/** The terms a mention had to match, from its `matched_term`.
 *  Mirrors src/govbudget/export_site.py `_mention_terms`: multi_token joins
 *  its tokens with "|" (influence/mentions.py find_mentions); every other
 *  tier stores a single term. */
function mentionTerms(matchedTerm) {
  return String(matchedTerm ?? "")
    .split("|")
    .filter(Boolean);
}

/** Does `title` carry `term` as a whole word (case-insensitive)?
 *  Mirrors influence/mentions.py `_build_word_boundary_re`, which is the test
 *  that put the row in the mart in the first place — the gate re-derives it
 *  here from programs.json's own title rather than trusting the exporter's
 *  declaration. */
function titleCarriesTerm(title, term) {
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(?<![A-Za-z0-9])${escaped}(?![A-Za-z0-9])`, "i").test(
    String(title ?? ""),
  );
}

/** The module whose table the mention rows actually render. Read as TEXT, the
 *  way basis.mjs reads src/lib/footnote.ts: a gate cannot import the site's
 *  TypeScript, and a hand-copied sentence in a gate message is the same
 *  species of drift these legs exist to catch. */
const evidenceModulePath = path.resolve(siteRoot, "src", "lib", "evidence.ts");

/**
 * The per-tier badge the page shows, read out of src/lib/evidence.ts.
 *
 * WHAT THE ROW RENDERS. program-mentions.tsx (and /filing/[uuid]/) prints
 * `evidenceKindLabel(kind)` as the badge and hangs `evidenceKindTitle(kind)`
 * off it as the hover title. Those two are what a reader sees, so those two
 * are what a finding quotes. (`evidenceKindLongExplanation` is the third form
 * in that module — the full-sentence rationale evidence.ts:66-69 keeps "for a
 * one-time explanation", which NO page imports, so it renders on no surface at
 * all today: /methodology/ writes the same multi-token rule out in its own
 * prose at page.tsx:577-580 rather than reading it from there. The leg quoted
 * multi_token's version of it, for every tier, until 2026-09-18.)
 *
 * Throws if the table cannot be read or a tier is missing from it: a gate that
 * silently fell back to a hand-copy would be asserting the very drift it is
 * here to find.
 */
export function evidenceBadges(modulePath = evidenceModulePath) {
  let src;
  try {
    src = fs.readFileSync(modulePath, "utf8");
  } catch {
    throw new Error(
      `program-skeleton(n): cannot read the evidence-badge table at ${modulePath} — ` +
        `the leg quotes the badge the page renders and will not hand-copy it`,
    );
  }
  /** The `case "<kind>": return "<text>";` arm inside one named function. */
  const arm = (fnName, kind) => {
    const fn = new RegExp(`function ${fnName}\\b[\\s\\S]*?\\n}`, "m").exec(src);
    if (!fn) return null;
    const m = new RegExp(`case "${kind}":\\s*\\n?\\s*return\\s*"((?:[^"\\\\]|\\\\.)*)"`, "m").exec(fn[0]);
    return m ? m[1].replace(/\\(.)/g, "$1") : null;
  };
  const table = {};
  for (const kind of ["pe_literal", "alias", "multi_token"]) {
    const label = arm("evidenceKindLabel", kind);
    const title = arm("evidenceKindTitle", kind);
    if (!label || !title) {
      throw new Error(
        `program-skeleton(n): src/lib/evidence.ts no longer yields a badge for "${kind}" ` +
          `(label ${label ? "ok" : "missing"}, title ${title ? "ok" : "missing"}) — ` +
          `re-point this reader at the table the mention row now renders`,
      );
    }
    table[kind] = { label, title };
  }
  return table;
}

export function runSplitKeyAwardsLeg({
  errors,
  notes,
  sidecars,
  programs,
  pageHtml = readPageHtml,
  badges = evidenceBadges(),
}) {
  let programRows = programs;
  if (!programRows) {
    const programsPath = path.join(jsonDir, "programs.json");
    if (!fs.existsSync(programsPath)) {
      errors.push("program-skeleton(n): data/site/json/programs.json missing");
      return;
    }
    programRows = readJson(programsPath);
  }
  const byPe = new Map();
  for (const p of programRows) {
    if (!byPe.has(p.pe_bli)) byPe.set(p.pe_bli, []);
    byPe.get(p.pe_bli).push(p);
  }
  const splits = [...byPe.entries()]
    .filter(([, rows]) => rows.length > 1)
    .sort(([a], [b]) => (a < b ? -1 : 1));
  if (splits.length < MIN_SHARED_BLI_CODES) {
    errors.push(
      `program-skeleton(n): programs.json carries ${splits.length} shared BLI ` +
        `code(s) (floor ${MIN_SHARED_BLI_CODES}, measured 2026-09-04 at 13). ` +
        `Every check in this leg is satisfied by a corpus with no shared ` +
        `codes at all, so an exporter that stops emitting account-qualified ` +
        `members would read as "nothing to check" instead of as the ` +
        `regression it is. Re-measure the population from dim_programs; do ` +
        `not lower the floor`,
    );
    return;
  }

  let membersWithAwards = 0;
  let awardRows = 0;
  let accountSplitPagesChecked = 0;
  let membersWithJbookRows = 0;
  let mentionTitleRows = 0;
  for (const [pe, rows] of splits) {
    // Independent recompute of site/src/app/program/[peBli]/page.tsx's
    // stubDimension — the predicate the header itself used to decide whether
    // to render an appropriation line. Same rule, computed from the payload.
    const distinctAccounts = new Set(rows.map((r) => r.account).filter(Boolean));
    const accountSplit = distinctAccounts.size > 1;
    const ownerOfPiid = new Map();
    // check 8 (ROADMAP #82, narrative axis): J-book fact id → the one member
    // page that may publish it; mention identity → the members that do.
    const ownerOfJbookFid = new Map();
    // mention identity -> {kind, slugs}: which members published the row, and
    // the evidence tier it claims (which decides whether a repeat is honest).
    const membersOfMention = new Map();
    // slug -> the sidecar's {evidence_kind: basis} declaration.
    const mentionDeclarations = new Map();
    for (const r of rows) {
      const d = sidecars.get(r.slug);
      if (!d) {
        errors.push(
          `program-skeleton(n): shared-code member /program/${r.slug}/ has no ` +
            `program_details sidecar`,
        );
        continue;
      }
      const awards = d.awards ?? [];
      if (awards.length) membersWithAwards++;
      awardRows += awards.length;
      for (const a of awards) {
        const piid = a.award_piid;
        if (!piid) continue;
        const prior = ownerOfPiid.get(piid);
        if (prior !== undefined && prior !== r.slug) {
          errors.push(
            `program-skeleton(n): award ${piid} is listed on BOTH ` +
              `/program/${prior}/ and /program/${r.slug}/ — the two programs ` +
              `sharing code ${pe} are different programs and their money is ` +
              `never combined`,
          );
        }
        ownerOfPiid.set(piid, r.slug);
      }
      if (
        typeof r.award_count === "number" &&
        r.award_count !== awards.length
      ) {
        errors.push(
          `program-skeleton(n): /program/${r.slug}/ programs.json award_count ` +
            `is ${r.award_count} but its sidecar lists ${awards.length} award(s)`,
        );
      }

      // ── (8) ROADMAP #82, the narrative axis ──────────────────────────────
      // A J-book row belongs to the ONE member whose own volume carries it.
      let ownJbookFids = 0;
      for (const kind of ["narratives", "details"]) {
        for (const row of d[kind] ?? []) {
          const fid = row.fact_id;
          if (!fid) continue;
          ownJbookFids++;
          const prior = ownerOfJbookFid.get(fid);
          if (prior !== undefined && prior !== r.slug) {
            errors.push(
              `program-skeleton(n): J-book ${kind.slice(0, -1)} ${fid} is ` +
                `published on BOTH /program/${prior}/ and /program/${r.slug}/ ` +
                `— the programs sharing code ${pe} are documented in ` +
                `different J-book volumes, so a row from one volume is not ` +
                `the other program's justification. Every citation on it ` +
                `still resolves, which is why only this check sees it`,
            );
          }
          ownerOfJbookFid.set(fid, r.slug);
        }
      }
      if (ownJbookFids) membersWithJbookRows++;
      // Mentions carry a PER-ROW basis, declared by the sidecar and
      // re-derived here from programs.json's own titles — see the block
      // comment above. Three things are checked: the declaration is coherent
      // with the evidence tiers it names, every "title"-basis row is true of
      // THIS page's title, and no row is published with no declaration at all.
      const mentions = d.mentions ?? [];
      const decl = d.mentions_shared_code;
      const declOk = decl !== null && typeof decl === "object" && !Array.isArray(decl);
      if (declOk) mentionDeclarations.set(r.slug, decl);
      if (mentions.length && !declOk) {
        errors.push(
          `program-skeleton(n): /program/${r.slug}/ publishes ` +
            `${mentions.length} lobbying mention(s) on shared code ${pe} but ` +
            `its sidecar declares no per-row mentions_shared_code basis ` +
            `(${JSON.stringify(decl ?? null)}) — a mention rendered on a ` +
            `member page is only honest as a stated basis, "the filing names ` +
            `the line" or "this page's own title carries the matched terms", ` +
            `never as a silent repeat. A blanket \`true\` is the retired ` +
            `shape: it asserted the first rule over rows that qualified under ` +
            `the second`,
        );
      }
      for (const [kind, basis] of Object.entries(declOk ? decl : {})) {
        const expected = kind === "pe_literal" ? "code" : "title";
        if (basis !== expected) {
          errors.push(
            `program-skeleton(n): /program/${r.slug}/ declares ` +
              `mentions_shared_code ${kind}="${basis}" — a ${kind} row ` +
              `publishes on the "${expected}" basis. Only a pe_literal ` +
              `filing names the shared code itself; every other tier ` +
              `qualified by matching one program title's terms and is ` +
              `evidence about THAT program`,
          );
        }
      }
      for (const m of mentions) {
        const kind = String(m.evidence_kind);
        const id = `${m.filing_uuid}|${m.client_name}|${m.matched_term}`;
        if (!membersOfMention.has(id)) membersOfMention.set(id, { kind, slugs: new Set() });
        membersOfMention.get(id).slugs.add(r.slug);
        if (declOk && decl[kind] === undefined) {
          errors.push(
            `program-skeleton(n): /program/${r.slug}/ publishes a ${kind} ` +
              `lobbying mention (${id}) on shared code ${pe} that its ` +
              `mentions_shared_code declares no basis for`,
          );
          continue;
        }
        if (!declOk || decl[kind] === "code") continue;
        // "title" basis — re-derived, not trusted. The badge the page renders
        // says the terms come from THIS program's title, so they must.
        const missing = mentionTerms(m.matched_term).filter(
          (t) => !titleCarriesTerm(r.title, t),
        );
        if (!missing.length && mentionTerms(m.matched_term).length) mentionTitleRows++;
        if (missing.length || !mentionTerms(m.matched_term).length) {
          // The badge is quoted per TIER, out of the table the row renders:
          // an alias failure that quoted multi_token's wording sent the reader
          // looking for text this page does not show.
          const badge = badges[kind];
          errors.push(
            `program-skeleton(n): /program/${r.slug}/ publishes a ${kind} ` +
              `lobbying mention matched \`${m.matched_term}\` but its own ` +
              `title "${r.title}" does not carry ` +
              `${missing.length ? missing.join(", ") : "any matched term"} — ` +
              `the row renders the badge "${badge ? badge.label : kind}"` +
              `${badge ? ` ("${badge.title}")` : ""}, which is false here. On a ` +
              `shared code the mart is keyed on the bare code, so a row that ` +
              `matched the SIBLING's title arrives at this page too`,
          );
        }
      }

      // ── (5)/(6) ROADMAP #82: the title block names THIS member's account ──
      // The `continue` below deliberately skips only the rest of THIS
      // member's per-page checks: its awards were already counted and its
      // PIIDs already filed above.
      const html = pageHtml(r.slug);
      if (html === null) {
        errors.push(
          `program-skeleton(n): shared-code member /program/${r.slug}/ has a ` +
            `sidecar but no built page`,
        );
        continue;
      }
      const root = parse(html, { comment: false });
      const accountEls = root.querySelectorAll("[data-program-account]");
      if (accountSplit) {
        if (accountEls.length !== 1) {
          errors.push(
            `program-skeleton(n): /program/${r.slug}/ renders ${accountEls.length} ` +
              `[data-program-account] element(s) (expected exactly 1) — an ` +
              `account-split member must name its own appropriation in the ` +
              `title block`,
          );
        } else {
          const text = (accountEls[0].text || "").replace(/\s+/g, " ").trim();
          if (
            !r.account_title ||
            !text.includes(r.account_title) ||
            !r.account ||
            !text.includes(r.account)
          ) {
            errors.push(
              `program-skeleton(n): /program/${r.slug}/ title block reads ` +
                `"${text}" — expected its own appropriation "${r.account_title}" ` +
                `and code ${r.account}`,
            );
          }
          for (const s of rows) {
            if (s.slug === r.slug || !s.account_title || s.account_title === r.account_title) {
              continue;
            }
            if (text.includes(s.account_title)) {
              errors.push(
                `program-skeleton(n): /program/${r.slug}/ title block names its ` +
                  `sibling's appropriation "${s.account_title}" — one program's ` +
                  `page must not wear the other's account`,
              );
            }
          }
          accountSplitPagesChecked++;
        }
      } else if (accountEls.length > 0) {
        errors.push(
          `program-skeleton(n): /program/${r.slug}/ is an organization-split ` +
            `member (one account, ${[...distinctAccounts][0] ?? "none"}) yet ` +
            `renders [data-program-account] — the account is identical on every ` +
            `member of code ${pe} and discriminates nothing`,
        );
      }

      // ── (7) ROADMAP #82: withheld concentration, renderer ↔ payload ──
      const withheldPayload = d.summary?.concentration_withheld === true;
      const tierEl = root.querySelector("[data-who-tier]");
      const tier = tierEl ? tierEl.getAttribute("data-who-tier") : null;
      const withheldRendered = root.querySelector("[data-who-withheld]") !== null;
      if (withheldPayload && (tier !== "none" || !withheldRendered)) {
        errors.push(
          `program-skeleton(n): /program/${r.slug}/ sidecar says ` +
            `concentration_withheld=true but its WHO GETS IT card declares ` +
            `tier "${tier}"${withheldRendered ? "" : " and renders no [data-who-withheld]"}` +
            ` — this member carries linked awards (that is why the shared ` +
            `line's figure is nobody's), so every stronger tier's sentence is ` +
            `false above its own Related Awards table and the honest-absence ` +
            `tier must state the withholding instead`,
        );
      }
      if (withheldRendered && !withheldPayload) {
        errors.push(
          `program-skeleton(n): /program/${r.slug}/ renders [data-who-withheld] ` +
            `but its sidecar carries no concentration_withheld=true — a withheld ` +
            `figure is the exporter's claim, not the renderer's`,
        );
      }
    }

    // check 8, the mention half, across members: a repeat is honest only
    // where every member rendering it declared the row's OWN basis — "code"
    // (the filing names the shared line) or "title" (each of those pages'
    // titles carries the matched terms, which the per-page check above
    // verified against programs.json). A member that declares nothing for
    // the tier is the silent repeat this check exists to see.
    for (const [id, { kind, slugs }] of membersOfMention) {
      if (slugs.size < 2) continue;
      const undeclared = [...slugs].filter(
        (s) => (mentionDeclarations.get(s) ?? {})[kind] === undefined,
      );
      if (undeclared.length) {
        errors.push(
          `program-skeleton(n): ${kind} lobbying mention ${id} appears on ` +
            `${[...slugs].sort().join(", ")} for shared code ${pe}, and ` +
            `${undeclared.sort().join(", ")} declare no mentions_shared_code ` +
            `basis for ${kind}`,
        );
      }
    }

    if (sidecars.has(pe)) {
      errors.push(
        `program-skeleton(n): bare shared code ${pe} owns a program_details ` +
          `sidecar — /program/${pe}/ is a disambiguation stub, not a program page`,
      );
    }
    const stubHtml = pageHtml(pe);
    if (stubHtml !== null) {
      const root = parse(stubHtml, { comment: false });
      if (root.querySelector('[data-sort-table="program-awards"]')) {
        errors.push(
          `program-skeleton(n): the /program/${pe}/ disambiguation stub renders ` +
            `an awards table — it cannot say whose awards those are`,
        );
      }
      if (root.querySelector("[data-program-account]")) {
        errors.push(
          `program-skeleton(n): the /program/${pe}/ disambiguation stub renders ` +
            `[data-program-account] — it is a chooser between accounts, not a ` +
            `page in one`,
        );
      }
    }
  }
  if (
    membersWithAwards < MIN_SPLIT_MEMBER_PAGES_WITH_AWARDS ||
    awardRows < MIN_SPLIT_AWARD_ROWS
  ) {
    errors.push(
      `program-skeleton(n): only ${membersWithAwards} shared-code member ` +
        `page(s) carry ${awardRows} award row(s) (floor: >= ` +
        `${MIN_SPLIT_MEMBER_PAGES_WITH_AWARDS} page(s), >= ` +
        `${MIN_SPLIT_AWARD_ROWS} row(s), measured 2026-09-04 at 7 pages / 86 ` +
        `rows). The three checks above are all satisfied by a corpus of ` +
        `zeroes, which is exactly what split_key drift between the mart and ` +
        `the sidecar writer produces — the links exist and reach no page. ` +
        `Re-measure the population from budget_line_awards and re-derive the ` +
        `floor; do not lower it to fit the build`,
    );
    return;
  }
  if (accountSplitPagesChecked < MIN_ACCOUNT_SPLIT_MEMBER_PAGES) {
    errors.push(
      `program-skeleton(n): only ${accountSplitPagesChecked} account-split ` +
        `member page(s) rendered a checkable title block (floor ` +
        `${MIN_ACCOUNT_SPLIT_MEMBER_PAGES}, measured 2026-09-05 at 20). Check 5 ` +
        `is satisfied by a corpus whose headers render no appropriation at ` +
        `all. Re-measure the population from programs.json (rows whose pe_bli ` +
        `has siblings in another account); do not lower the floor`,
    );
    return;
  }

  if (membersWithJbookRows < MIN_SPLIT_MEMBER_PAGES_WITH_JBOOK_ROWS) {
    errors.push(
      `program-skeleton(n): only ${membersWithJbookRows} shared-code member ` +
        `page(s) publish a J-book narrative or detail fact id of their own ` +
        `(floor ${MIN_SPLIT_MEMBER_PAGES_WITH_JBOOK_ROWS}, measured ` +
        `2026-09-12 at 27 — every member has its own PB2026 volume). Check 8 ` +
        `is a no-duplicate assertion and is satisfied perfectly by a corpus ` +
        `where every member page publishes nothing, which is what split_key ` +
        `drift between the J-book indexes and the sidecar writer produces. ` +
        `Re-measure the population from budget_line_details/detail_narratives ` +
        `joined to jbook_documents; do not lower the floor`,
    );
    return;
  }

  notes.push(
    `leg n: ${splits.length} shared BLI code(s) checked; ` +
      `${membersWithAwards} member page(s) carry ${awardRows} award row(s) ` +
      `(floor ${MIN_SPLIT_MEMBER_PAGES_WITH_AWARDS}/${MIN_SPLIT_AWARD_ROWS}), ` +
      `no PIID shared between siblings, no stub rendering awards; ` +
      `${accountSplitPagesChecked} account-split member page(s) name their own ` +
      `appropriation (floor ${MIN_ACCOUNT_SPLIT_MEMBER_PAGES}), none its sibling's; ` +
      `withheld concentration said wherever the sidecar withholds it; ` +
      `${membersWithJbookRows} member page(s) publish their own J-book rows ` +
      `(floor ${MIN_SPLIT_MEMBER_PAGES_WITH_JBOOK_ROWS}), no narrative or ` +
      `detail fact id on two members; every lobbying mention declares its ` +
      `basis, and ${mentionTitleRows} title-basis row(s) carry every matched ` +
      `term in their own page's programs.json title`,
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// leg f — the WHAT-IT-IS card speaks from a real source (§P1-2)
// ═══════════════════════════════════════════════════════════════════════════
//
// The defect: /program/ATA000/ — the largest program in the corpus — opened
// with "F-35 – a procurement program run by Air Force." while a genuinely
// good, fact-cited sentence sat ~3,000px below in its dossier.
//
// The contract this leg enforces, on the BUILT artifact, for EVERY program
// that ships a gated dossier (all 50 — the population is small enough to
// check exhaustively, and these are the site's showcase pages):
//
//   1. [data-testid="answer-what"] exists and declares
//      data-what-source="dossier" — the card knows which tier it spoke from.
//   2. Its text CONTAINS the dossier's own first what_it_is claim, verbatim
//      (read here from data/site/json/dossiers/{pe}.json, not from the page).
//      Verbatim is the point: a paraphrase is a new uncited claim.
//   3. Every hoisted claim carries a citation anchor whose fact_id RESOLVES
//      (checked against the page's own embedded citation slice — the same
//      payload the runtime panel reads, so a chip that would 404 at runtime
//      fails here).
//   4. The card does NOT match the template-stub shape
//      ("{name} — a {family} program run by {org}."). Belt and braces with
//      (2): if the hoist silently regressed to the template AND the dossier
//      sentence happened to be a substring, this still fails.
//
// It also spot-checks the non-dossier tiers on the sampled pages: a full-tier
// card must be field-sourced and name something beyond name-plus-org; a
// rollup card must carry its honest summary-figures tail.
//
// Reads rendered text, never a data-* mirror of the sentence — a page that
// rendered the stub could not satisfy this by also emitting a correct
// attribute.

/** The stub shape the card must never render again. */
const TEMPLATE_STUB_RE = /—\s*an?\s+[^.]{1,40}\s+program run by\s+/i;

/** fact_ids embedded in the page's own citation slice (the runtime payload). */
function pageCitationFactIds(html) {
  const ids = new Set();
  for (const m of html.matchAll(/\\?"([0-9a-f]{16})\\?"\s*:\s*\{/g)) {
    ids.add(m[1]);
  }
  return ids;
}

function runWhatItIsLeg({ errors, notes }) {
  const dossierDir = path.join(jsonDir, "dossiers");
  if (!fs.existsSync(dossierDir)) {
    errors.push(
      "program-skeleton(f): data/site/json/dossiers/ missing — the §P1-2 hoist source is gone"
    );
    return;
  }
  const dossierFiles = fs
    .readdirSync(dossierDir)
    .filter((f) => f.endsWith(".json"))
    .sort();
  if (dossierFiles.length === 0) {
    errors.push("program-skeleton(f): no dossiers on disk — leg f would be vacuous");
    return;
  }

  let checked = 0;
  for (const file of dossierFiles) {
    const slug = file.replace(/\.json$/, "");
    const p = pageHtmlPath(slug);
    if (!fs.existsSync(p)) {
      errors.push(`program-skeleton(f): dossier page /program/${slug}/ not built`);
      continue;
    }
    let dossier;
    try {
      dossier = readJson(path.join(dossierDir, file));
    } catch {
      errors.push(`program-skeleton(f): unreadable dossier ${file}`);
      continue;
    }
    const claims = dossier?.dossier?.what_it_is?.claims ?? [];
    if (claims.length === 0) continue; // no what_it_is → the card falls back by design

    const html = fs.readFileSync(p, "utf8");
    const root = parse(html, { comment: false });
    const card = root.querySelector('[data-testid="answer-what"]');
    if (!card) {
      errors.push(
        `program-skeleton(f): /program/${slug}/ has no [data-testid="answer-what"] card`
      );
      continue;
    }

    // 1. tier declaration
    const marker = card.querySelector("[data-what-source]");
    const source = marker?.getAttribute("data-what-source") ?? null;
    if (source !== "dossier") {
      errors.push(
        `program-skeleton(f): /program/${slug}/ WHAT-IT-IS is data-what-source=${JSON.stringify(source)} — ` +
          `a program with a gated dossier must hoist it (§P1-2)`
      );
      continue;
    }

    // 2. the dossier's own first sentence, verbatim
    const cardText = (card.text ?? "").replace(/\s+/g, " ").trim();
    const wanted = String(claims[0].text).replace(/\s+/g, " ").trim();
    if (!cardText.includes(wanted)) {
      errors.push(
        `program-skeleton(f): /program/${slug}/ WHAT-IT-IS does not contain the dossier's ` +
          `first sentence verbatim — wanted "${wanted.slice(0, 70)}…", got "${cardText.slice(0, 90)}…"`
      );
    }

    // 3. every hoisted claim's citation resolves in the page's own slice
    const sliceIds = pageCitationFactIds(html);
    const hoisted = card.querySelectorAll("[data-what-claim]");
    if (hoisted.length === 0) {
      errors.push(
        `program-skeleton(f): /program/${slug}/ WHAT-IT-IS claims to be dossier-sourced ` +
          `but renders no [data-what-claim] element`
      );
    }
    for (const el of hoisted) {
      const fid = el.getAttribute("data-cite-fact-id");
      const url = el.getAttribute("data-cite-url");
      if (!fid && !url) {
        errors.push(
          `program-skeleton(f): /program/${slug}/ hoisted sentence carries no citation anchor`
        );
        continue;
      }
      if (fid && !sliceIds.has(fid)) {
        errors.push(
          `program-skeleton(f): /program/${slug}/ hoisted sentence cites ${fid}, which does not ` +
            `resolve in the page's embedded citation slice — the chip would dead-end at runtime`
        );
      }
    }

    // 4. never the template stub
    if (TEMPLATE_STUB_RE.test(cardText)) {
      errors.push(
        `program-skeleton(f): /program/${slug}/ WHAT-IT-IS rendered the template stub again: ` +
          `"${cardText.slice(0, 90)}…"`
      );
    }
    checked++;
  }
  notes.push(`leg f: ${checked}/${dossierFiles.length} dossier cards hoist their own cited prose ✓`);

  // ── the other two tiers, on the sampled pages ────────────────────────────
  const detailsDir = path.join(jsonDir, "program_details");
  const dossierSlugs = new Set(dossierFiles.map((f) => f.replace(/\.json$/, "")));
  const allSlugs = fs
    .readdirSync(detailsDir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => f.replace(/\.json$/, ""))
    .sort();
  const fullNoDossier = [];
  const rollups = [];
  const decades = [];
  for (const slug of allSlugs) {
    if (dossierSlugs.has(slug)) continue;
    let d;
    try {
      d = readJson(path.join(detailsDir, `${slug}.json`));
    } catch {
      continue;
    }
    if (d.tier === "rollup") rollups.push(slug);
    else if (d.tier === "decade") decades.push(slug);
    else fullNoDossier.push(slug);
  }

  for (const [slugs, wantSource, label] of [
    [spreadSample(fullNoDossier, 6), "fields", "full-tier (no dossier)"],
    [spreadSample(rollups, 6), "rollup", "rollup-tier"],
    [spreadSample(decades, 6), "decade", "decade-tier"],
  ]) {
    for (const slug of slugs) {
      const p = pageHtmlPath(slug);
      if (!fs.existsSync(p)) continue;
      const root = parse(fs.readFileSync(p, "utf8"), { comment: false });
      const card = root.querySelector('[data-testid="answer-what"]');
      if (!card) {
        errors.push(`program-skeleton(f): /program/${slug}/ has no WHAT-IT-IS card`);
        continue;
      }
      const source =
        card.querySelector("[data-what-source]")?.getAttribute("data-what-source") ?? null;
      if (source !== wantSource) {
        errors.push(
          `program-skeleton(f): /program/${slug}/ (${label}) WHAT-IT-IS is ` +
            `data-what-source=${JSON.stringify(source)}, expected "${wantSource}"`
        );
        continue;
      }
      const text = (card.text ?? "").replace(/\s+/g, " ").trim();
      if (TEMPLATE_STUB_RE.test(text)) {
        errors.push(
          `program-skeleton(f): /program/${slug}/ (${label}) rendered the template stub: "${text.slice(0, 90)}…"`
        );
      }
      if (wantSource === "rollup" && !text.includes("Summary figures only")) {
        errors.push(
          `program-skeleton(f): /program/${slug}/ (rollup) WHAT-IT-IS lost its honest tail ` +
            `("Summary figures only: …") — got "${text.slice(0, 90)}…"`
        );
      }
      // ROADMAP #28: the decade tail is a DIFFERENT sentence, and the rollup
      // one would be false here — it says the service book carries no
      // R-2/P-40 detail for this line, when no FY2026 book carries the line
      // at all. Both directions checked, so a copy-paste of the rollup tail
      // onto this tier fails.
      if (wantSource === "decade") {
        if (!text.includes("History only")) {
          errors.push(
            `program-skeleton(f): /program/${slug}/ (decade) WHAT-IT-IS lost its honest tail ` +
              `("History only: …") — got "${text.slice(0, 90)}…"`
          );
        }
        if (text.includes("Summary figures only")) {
          errors.push(
            `program-skeleton(f): /program/${slug}/ (decade) WHAT-IT-IS carries the ROLLUP tail ` +
              `("Summary figures only: …"), which claims an FY2026 book that has no line for ` +
              `this element — got "${text.slice(0, 120)}…"`
          );
        }
      }
    }
  }
  notes.push(
    `leg f: sampled ${Math.min(6, fullNoDossier.length)} field-sourced + ` +
      `${Math.min(6, rollups.length)} rollup + ${Math.min(6, decades.length)} decade cards ✓`
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// leg g — a program element PB2026 stopped requesting must not end silently
// ═══════════════════════════════════════════════════════════════════════════
//
// The defect (ROADMAP #32a, surfaced by PM Sprint 3 Task 1b). PB2026
// renumbered program elements at scale. Counting pages whose PB2026 R-1/P-1
// workbook rows carry FY2024/FY2025 money and NO FY2026 row at all: Army
// 113, Air Force 77, Navy 69, OSD 18, DARPA 14, and 28 across the smaller
// components — 319 pages. A reader who followed /program/0601101E/ (Defense
// Research Sciences) for a decade hit a page whose figures stopped at FY2025
// and said nothing about why.
//
// This is NOT an ingestion gap: data/raw_docs/fy2026/dod/r1_display.xlsx
// shows the FY2026 cells for those lines genuinely blank, and the new PB2026
// lines genuinely carry no FY2024/FY2025 history. The parser is right; the
// MODEL has no way to say "renumbered". Successor edges are #32b (folded
// into backlog #29) — they do not exist yet, and this leg exists partly to
// make sure nobody ships a guess at one in the meantime.
//
// What this leg pins, on the BUILT artifact, for the WHOLE page universe
// (2,016 pages — one read pass, no sampling; the negative direction is the
// half a sample would miss):
//
//   1. The exporter's flag agrees with an INDEPENDENT recompute of the
//      predicate from the sidecar's own workbook rows, on every page, both
//      directions and including last_fy. Same convention as CANONICAL_SECTIONS
//      above: a drift between the two implementations is a real failure.
//   2. Every page in the population renders [data-fy2026-absent].
//   3. NO page outside it does. A note that appears on a page still funded in
//      FY2026 is a false claim about that page's money, which is worse than
//      the silence it was written to fix.
//   4. The note says all four things it must say, verbatim: that there is no
//      FY2026 request; where the record actually stops (and that year must
//      MATCH the recomputed last_fy — the note may not name a year the
//      workbook does not support); that PB2026 renumbered at scale; and that
//      the page names no successor.
//   5. The note never claims the program ended. "zeroed", "cancelled",
//      "terminated", "defunded" are exactly the words the 87 withdrawn feed
//      cards used, and absence in one edition supports none of them.
//   6. The note names no OTHER program element. Naming a successor the corpus
//      cannot prove would be a fabricated citation — the defect species
//      ROADMAP #53 and #69 closed. Until #32b ships there is nothing to name,
//      and this is the check that says so mechanically.

/** Non-vacuity floor: the shipped PB2026 corpus holds exactly 319 such pages
 *  (measured 2026-08-26; 160 last funded FY2024, 159 FY2025). A drop means
 *  either the predicate broke or the corpus changed — RE-MEASURE and re-derive
 *  this number, never lower it to whatever the build produced.
 *
 *  Not the "165" in ROADMAP #32's 2026-08-07 correction: that figure counts
 *  pe_blis with FY2025 money and no FY2026 row across ALL editions, while the
 *  note is a claim about ONE edition and is rendered per PAGE. Fenced to
 *  PB2026 and counted per page, FY2025-only is 159 and FY2024-or-FY2025 — the
 *  entry's own definition, the one that reproduces its per-service figures —
 *  is 319. */
// 319 -> 316 on 2026-08-27. NOT a relaxation: three pages
// (0603669D8Z, 0602669D8Z, 0604669D8Z -- Microelectronics Commons) were
// removed from the population because they publish POSITIVE cited FY2026
// money and must never carry an absence note. The floor tracks the true
// population; lowering it here is the fix landing, not the bar moving.
//
// 316 -> 313 on 2026-08-29 (Wave 5), RE-MEASURED, not fitted. The Navy
// procurement ingestion gave five pages in the population a POSITIVE cited
// FY2026 J-book figure, which is precisely the condition that must remove a
// page from it — the note may not say "no FY2026 request" over money the
// page itself prints:
//   1350-WPN  Missile Industrial Facilities        $180.867M
//   2101-PMC  Tomahawk                              $12.593M
//   2127      Littoral Combat Ship (LCS)             $5.766M
//   5087      Oceanographic Ships                    $6.015M
//   5035      Towing, Salvage, and Rescue Ship (ATS) $4.650M
// Five left and the net is three, because the same ingestion also added
// pages to the corpus and two of them satisfy the predicate. The two are not
// named here: identifying them individually needs the pre-wave sidecar set,
// which this build replaced, and inventing a confident list would be worse
// than saying so. The DEPARTURES are named because they were measured
// directly, per page, from the shipped sidecars.
const MIN_FY2026_ABSENT_PAGES = 313;

/** The stable hook the page must carry. */
const FY2026_ABSENT_ATTR = "data-fy2026-absent";

/** Every sentence the note must actually say (whitespace-normalized).
 *
 * Retargeted 2026-08-27 to the corrected wording. NOT a relaxation -- the
 * properties pinned are the same or stronger:
 *
 *  - the headline now names the record that is actually blank
 *    ("R-1/P-1 request line"), because the old "No FY2026 request" was
 *    false on three pages publishing cited FY2026 J-book money;
 *  - the renumber sentence is unchanged;
 *  - the successor sentence moved OUT of this list because it is now
 *    conditional, and is checked per-page below against the lineage rail
 *    instead. Pinning it unconditionally here is what forced the note to
 *    deny a successor on five pages that named one with a citation.
 */
const FY2026_ABSENT_REQUIRED = [
  "No FY2026 R-1/P-1 request line for this program element.",
  "PB2026 renumbered program elements at scale",
];

/** The successor clause, which must match the page's own lineage rail.
 *
 * RETARGETED 2026-09-05 (#32(b) residue). The old denial — "No ingested
 * budget document in this corpus states a successor for this line" — was a
 * claim about the DOCUMENTS that this leg checked against the RAIL, and it
 * was false on 19 of the 287 pages that rendered it: pages whose own
 * narrative names the successor (leg l lists them). The clause is now a
 * claim about THIS SITE, true by construction whenever the rail is empty.
 * Leg (l) pins that the old sentence never returns. Leg (k) aliases these
 * two constants for the decade note, so both notes move together. */
const FY2026_SUCCESSOR_DENIAL =
  "No successor is linked for this line: this site's program-lineage layer holds no keyed edge pointing forward from here.";
const FY2026_SUCCESSOR_POINTER =
  "Where this line's funding went is recorded under Program Lineage below.";

/** Words that would turn an absence into a claim the corpus cannot support. */
const FY2026_ABSENT_FORBIDDEN =
  /\b(zeroed|defunded|cancell?ed|cancellation|terminat(ed|ion))\b/i;

/** Candidate program-element token in the note's prose. Not a shape guess —
 *  every match is looked up in the page universe (the sidecar slugs) so
 *  "FY2026" and "PB2026" are not mistaken for codes and "ATA000", "HCMC00",
 *  "1203154SF" are not missed. Used ONLY to prove the note names no
 *  successor. */
const PE_TOKEN_RE = /\b[A-Z0-9][A-Z0-9]{4,}\b/g;

/**
 * Independent recompute of the exporter's predicate
 * (src/govbudget/export_site.py, _fy2026_absent_block).
 *
 * Reads the sidecar's `budget_lines` — the PB2026 R-1/P-1 workbook rows this
 * very page renders in its Budget Line Items table, already scoped to the
 * page's own account/organization grain for the split keys. So "no FY2026
 * row" here means exactly what the primary source shows: blank cells on this
 * line, in this edition.
 *
 * Returns {last_fy} or null.
 */
function recomputeFy2026Absent(d) {
  const rows = d.budget_lines ?? [];
  if (rows.some((r) => r.fy === 2026)) return null;
  const prior = rows
    .filter(
      (r) => (r.fy === 2024 || r.fy === 2025) && Number(r.amount_thousands) > 0,
    )
    .map((r) => r.fy);
  if (prior.length === 0) return null;

  // WIDENED 2026-08-27 after two independent reviews found the note false
  // on 179 of the 319 pages it rendered on. This function previously read
  // ONLY budget_lines -- the same workbook-only predicate the exporter
  // used -- so it mirrored the exporter's blind spot instead of checking
  // it. Two implementations of one wrong scope agreeing is not
  // corroboration, and that is exactly why leg (g) passed on every page
  // the reviewers flagged.
  //
  // The page's OWN J-book detail rows are the record the note was
  // contradicting, so they are now part of the predicate.
  const fy26Details = (d.details ?? []).filter((r) => r.fy === 2026);
  // Positive J-book money => the page publishes an FY2026 request, so no
  // note may render. /program/0603669D8Z/ and its two Microelectronics
  // Commons siblings rendered "No FY2026 request" over cited FY26 Request
  // figures of $260.7M / $79.7M / $59.6M.
  if (fy26Details.some((r) => Number(r.amount_millions) > 0)) return null;
  return {
    last_fy: Math.max(...prior),
    // A documented $0 is a record, not a silence. 173 pages carry an
    // FY2026 J-book row at exactly 0.000.
    jbook_fy2026_zero: fy26Details.length > 0,
    // 5 pages render a cited "Successors (funding flowed out)" rail while
    // the note denied any document named one.
    has_successor: Boolean(d.lineage?.rail?.successors?.length),
    // #32(b) residue: the page renders narratives → the note points at them
    // instead of speaking for them. Same predicate isZeroContent uses. Leg
    // (l) compares this against the exporter's flag AND the rendered note.
    has_narrative: (d.narratives ?? []).length > 0,
  };
}

function runFy2026AbsentLeg({ errors, notes, sidecars }) {
  // ── 1. exporter flag vs. independent recompute, on every sidecar ─────────
  const expected = new Map(); // slug -> {last_fy}
  let flagDrift = 0;
  for (const [slug, d] of sidecars) {
    const want = recomputeFy2026Absent(d);
    const got = d.fy2026_absent ?? null;
    if (want) expected.set(slug, want);
    if (Boolean(want) !== Boolean(got)) {
      flagDrift++;
      if (flagDrift <= 5) {
        errors.push(
          `program-skeleton(g): /program/${slug}/ sidecar fy2026_absent is ` +
            `${got ? JSON.stringify(got) : "absent"} but the gate's own recompute says ` +
            `${want ? JSON.stringify(want) : "absent"} — the exporter and the gate disagree ` +
            `about whether PB2026 still requests money for this line`,
        );
      }
    } else if (want && got && want.last_fy !== got.last_fy) {
      flagDrift++;
      if (flagDrift <= 5) {
        errors.push(
          `program-skeleton(g): /program/${slug}/ sidecar says last_fy=${got.last_fy}, ` +
            `recompute says ${want.last_fy}`,
        );
      }
    }
  }
  if (flagDrift > 5) {
    errors.push(
      `program-skeleton(g): ${flagDrift} sidecars disagree with the recompute in total ` +
        `(first 5 listed)`,
    );
  }

  if (expected.size < MIN_FY2026_ABSENT_PAGES) {
    errors.push(
      `program-skeleton(g): only ${expected.size} page(s) match the renumber predicate ` +
        `(expected >= ${MIN_FY2026_ABSENT_PAGES}) — the leg would be vacuous. Re-measure ` +
        `the population and re-derive the floor; do not lower it to fit the build`,
    );
    return;
  }

  // ── 2/3/4/5/6. one read pass over the WHOLE page universe ────────────────
  let withNote = 0;
  let missing = 0;
  let stray = 0;
  let badNotes = 0;
  const lastFyCounts = new Map();
  for (const [slug, d] of sidecars) {
    const p = pageHtmlPath(slug);
    if (!fs.existsSync(p)) {
      if (expected.has(slug)) {
        errors.push(`program-skeleton(g): /program/${slug}/ not built`);
      }
      continue;
    }
    const html = fs.readFileSync(p, "utf8");
    const marked = html.includes(FY2026_ABSENT_ATTR);
    const want = expected.get(slug) ?? null;

    if (!want) {
      // 3. the negative direction.
      if (marked) {
        stray++;
        if (stray <= 5) {
          // Name WHICH record contradicts the note. The original message
          // said "its PB2026 workbook DOES carry an FY2026 row" for every
          // stray, which is itself false for the case that actually
          // shipped: the Microelectronics Commons pages' workbook is
          // blank; their J-BOOK DETAIL carries the money. An error message
          // that misexplains its own finding sends the next reader to the
          // wrong file.
          // LARGEST single row, never a sum: the detail carries the same
          // money under several scenarios (BudgetYearOne and
          // BudgetYearOneBase) and at both project and rollup grain, so
          // adding them double-counts. A first cut of this message summed
          // them and reported $1042.9M where the page's largest FY26
          // Request figure is $260.7M -- an inflated number inside the
          // very diagnostic that exists to catch inflated claims.
          const fy26Pos = (d.details ?? [])
            .filter((r) => r.fy === 2026 && Number(r.amount_millions) > 0)
            .reduce((a, r) => Math.max(a, Number(r.amount_millions)), 0);
          const why = fy26Pos > 0
            ? `its PB2026 J-book detail publishes FY2026 money on this page (largest single row $${fy26Pos.toFixed(1)}M)`
            : `its PB2026 workbook DOES carry an FY2026 row`;
          errors.push(
            `program-skeleton(g): /program/${slug}/ renders the "no FY2026 request" note ` +
              `but ${why} — the note is a false claim about this page's money`,
          );
        }
      }
      continue;
    }

    // 2. the positive direction.
    if (!marked) {
      missing++;
      if (missing <= 5) {
        errors.push(
          `program-skeleton(g): /program/${slug}/ has PB2026 money through FY${want.last_fy} ` +
            `and no FY2026 workbook row, but renders no [${FY2026_ABSENT_ATTR}] note — the ` +
            `page ends silently (ROADMAP #32a)`,
        );
      }
      continue;
    }

    const root = parse(html, { comment: false });
    const el = root.querySelector(`[${FY2026_ABSENT_ATTR}]`);
    if (!el) {
      errors.push(
        `program-skeleton(g): /program/${slug}/ mentions ${FY2026_ABSENT_ATTR} but no ` +
          `element carries it`,
      );
      continue;
    }
    const text = (el.text ?? "").replace(/\s+/g, " ").trim();

    // The note comes from ONE component, so a wording regression hits all 319
    // pages at once. Report the first few and count the rest — 1,200 identical
    // lines would bury the other legs' findings.
    const say = (msg) => {
      badNotes++;
      if (badNotes <= 5) errors.push(msg);
    };

    // 4. it says all four things.
    for (const frag of FY2026_ABSENT_REQUIRED) {
      if (!text.includes(frag)) {
        say(
          `program-skeleton(g): /program/${slug}/ note is missing the required sentence ` +
            `"${frag}" — got "${text.slice(0, 140)}…"`,
        );
      }
    }
    // "in this edition" -> "workbook figure": the old phrasing claimed the
    // whole EDITION stopped at that year, contradicted on 173 pages whose
    // J-book carries an FY2026 row at zero in the same edition.
    const yearFrag = `its last workbook figure is FY${want.last_fy}`;
    if (!text.includes(yearFrag)) {
      say(
        `program-skeleton(g): /program/${slug}/ note does not say "${yearFrag}" — the ` +
          `note must name the year the workbook actually stops at, not a different one ` +
          `(got "${text.slice(0, 140)}…")`,
      );
    }
    // 4b. the documented zero must be disclosed exactly where it exists.
    const saysZero = text.includes("recorded as zero");
    if (want.jbook_fy2026_zero && !saysZero) {
      say(
        `program-skeleton(g): /program/${slug}/ has an FY2026 J-book row at zero but the ` +
          `note does not disclose it — a workbook blank and a documented zero are ` +
          `different records, and hiding the second is the 87-feed-card error`,
      );
    }
    if (!want.jbook_fy2026_zero && saysZero) {
      say(
        `program-skeleton(g): /program/${slug}/ note claims a documented FY2026 zero that ` +
          `this page's J-book detail does not carry`,
      );
    }
    // 4c. the successor clause must agree with the page's own lineage rail.
    if (want.has_successor) {
      if (text.includes(FY2026_SUCCESSOR_DENIAL)) {
        say(
          `program-skeleton(g): /program/${slug}/ note says this site links no successor, ` +
            `but the page renders a cited successor rail — the denial contradicts the ` +
            `page's own lineage layer`,
        );
      }
      if (!text.includes(FY2026_SUCCESSOR_POINTER)) {
        say(
          `program-skeleton(g): /program/${slug}/ has a successor rail but the note does ` +
            `not point the reader at it`,
        );
      }
    } else if (!text.includes(FY2026_SUCCESSOR_DENIAL)) {
      say(
        `program-skeleton(g): /program/${slug}/ has no successor rail but the note omits ` +
          `the denial — the limit must be stated, not left silent`,
      );
    }

    // 5. it never claims an ending.
    const bad = FY2026_ABSENT_FORBIDDEN.exec(text);
    if (bad) {
      say(
        `program-skeleton(g): /program/${slug}/ note says "${bad[0]}" — absence from one ` +
          `edition supports no such claim (this is the wording the 87 withdrawn feed ` +
          `cards used)`,
      );
    }

    // 6. it names no other program element. Every candidate token is checked
    // against the PAGE UNIVERSE itself, so this cannot be fooled by a code
    // shape nobody anticipated, and cannot fire on "FY2026"/"PB2026".
    const named = [...new Set(text.match(PE_TOKEN_RE) ?? [])].filter(
      (c) => c !== slug && sidecars.has(c),
    );
    if (named.length > 0) {
      say(
        `program-skeleton(g): /program/${slug}/ note names program element(s) ` +
          `${named.join(", ")} — the lineage layer did not key a successor for this ` +
          `renumbered line, so the note must not name one (#32b / backlog #29)`,
      );
    }

    withNote++;
    lastFyCounts.set(want.last_fy, (lastFyCounts.get(want.last_fy) ?? 0) + 1);
  }

  if (missing > 5) {
    errors.push(
      `program-skeleton(g): ${missing} page(s) in the renumber population render no note ` +
        `in total (first 5 listed)`,
    );
  }
  if (stray > 5) {
    errors.push(
      `program-skeleton(g): ${stray} page(s) outside the population render the note in ` +
        `total (first 5 listed)`,
    );
  }
  if (badNotes > 5) {
    errors.push(
      `program-skeleton(g): ${badNotes} note-content failure(s) in total across the ` +
        `population (first 5 listed) — one component renders all of them, so this is ` +
        `one wording regression, not ${badNotes} page defects`,
    );
  }
  const byYear = [...lastFyCounts.entries()]
    .sort()
    .map(([fy, n]) => `${n} last funded FY${fy}`)
    .join(", ");
  notes.push(
    `leg g: ${withNote}/${expected.size} renumbered-away program page(s) carry the ` +
      `"no FY2026 request" note (${byYear}); ${sidecars.size - expected.size} other ` +
      `page(s) correctly do not ✓`,
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// leg l — the successor clause against the page's OWN narratives (#32b residue)
// ═══════════════════════════════════════════════════════════════════════════
//
// Leg (g) checks the successor clause against the lineage RAIL: denial where
// the rail is empty, pointer where it is not. That is the right check for the
// rail and the wrong check for the claim the note used to make. "No ingested
// budget document in this corpus states a successor for this line" is a
// statement about the DOCUMENTS, and on 19 of the 287 pages that rendered it
// (measured 2026-09-05 from the shipped sidecars' own narratives) the page's
// PB2026 narrative — rendered three sections below — names where the money
// went:
//   2900 → LI 2361, 2176 → BLI 2136, 2026 → LI 2981 (Navy OPN consolidation);
//   C01200 C02500 C03200 C03700 C04000 CFIN00 → BLI OSAEA0 (AF OSA-EA mods);
//   FET000 → PE 0303131F (Space Force → Air Force transfer);
//   0128B63000 → PE 0608041A ($16.144M realigned, partial);
//   0601101E 0601117E 0602115E 0602303E 0602715E 0603286E 0603287E 0603760E
//     → "Beginning in FY 2026, … will be funded in PE …" — DARPA's renumber
//     sentence, verbatim, including Defense Research Sciences → 0601122E
//     Emerging Opportunities, the case ROADMAP #32 called unprovable.
// That is 19 pages and 23 pointers: 14 PE-shaped, 9 line-item/WSC-shaped.
// The lineage layer keys none of them: numeric line items are refused at
// V3-shape (pe_bli is not unique for them), WSC codes are not PE-shaped, and
// "will be funded in" is not one of lineage/extract.py's _RULES (backlog #105).
// The exporter and leg (g) both read the rail, so both agreed the denial was
// fine. Two implementations of one wrong scope agreeing is not corroboration
// — the leg (g) lesson of 2026-08-27, in a new place.
//
// The note now says only what THIS SITE holds and, where the page renders
// narratives, points at them. This leg reads the narratives the sidecar
// itself ships — the verbatim detail_narratives bodies the page renders —
// over the WHOLE page universe, and pins:
//
//   0. The exporter's has_narrative equals this gate's own recompute of it.
//      Leg (g) compares only last_fy between the two implementations.
//   1. The retired corpus-wide denial appears in NO note, fy2026 or decade.
//      Where the page's narrative names a forward pointer, the error quotes
//      it, so the failure reads as the contradiction it is.
//   2. The narrative pointer renders IFF the page renders narratives, and
//      never beside a successor rail.
//   3. On every no-rail page whose narrative names a forward pointer, the
//      note carries the pointer — the reader is sent to the record the site
//      did not key, never told there is none.
//   4. Non-vacuity: at least MIN_NARRATIVE_FORWARD_POINTER_PAGES no-rail
//      pages carry such a narrative. Zero would mean the scan broke.
//
// The scan is deliberately WIDER than extract.py's _RULES — that is the
// point: it finds what the extractor does not key — and is used ONLY to
// check and count. It never mints an edge and never puts a code in prose;
// leg (g) step 6 still fails the build if the note names any program
// element.

/** The sentence the note may never say again (#32(b) residue). */
export const FY2026_SUCCESSOR_DENIAL_RETIRED =
  "No ingested budget document in this corpus states a successor for this line.";
/** The narrative pointer, rendered iff the page renders narratives. */
export const FY2026_NARRATIVE_POINTER =
  "it is quoted below in the document's own words";

/** Non-vacuity floor: 19 no-rail fy2026_absent pages whose own narratives
 *  name a forward pointer, measured 2026-09-05 against the 2026-09-04 20:06
 *  export (23 pointers: 14 PE-shaped, 9 line-item/WSC-shaped; slugs in the
 *  block comment above). A DROP is either the scan breaking or backlog #105
 *  keying some of these as edges, which moves them OUT of the no-rail set —
 *  the fix landing, not the bar moving. The floor sits AT its measurement,
 *  so either one reds this leg. Only the second is a reason to re-derive it:
 *  that is an owner-ruled change recorded in the ledger with #105's commit
 *  and the new measurement (Task 26, 2026-09-25, replaced this comment's
 *  standing leave to "lower with a dated note"). Never lower it to fit a
 *  build. */
export const MIN_NARRATIVE_FORWARD_POINTER_PAGES = 19;

const NARR_CODE_PREFIX =
  "(?:PE|program element|LI|BLI|budget line item(?:\\s*\\(BLI\\))?|line item|WSC)";
const NARR_CODE = "([A-Z0-9]{4,10})";
/** Forward-pointer forms. Mirrors the 'succ' direction of lineage/extract.py
 *  _RULES (transferred/realigned … to PE X) and widens it to the three forms
 *  the extractor does not key: line-item/WSC destinations, "will be funded
 *  in PE X", and "will continue … in PE X". Clause-bounded on [^.:;] —
 *  extract.py's _SENT bounds on [^.:], and ';' is added here because the AF
 *  OSA-EA sentences run several clauses — so "transferred from (PE A …) to
 *  (PE B …)" yields B. Present-tense "is funded in PE X" is deliberately NOT
 *  a form: on 0602303E it names concurrent funding, not a move. */
const NARR_FORWARD_RES = [
  new RegExp(
    "\\b(?:transferred|realigned|moved|consolidated|merged|migrated)\\b[^.:;]*?" +
      "\\b(?:to|into|under)\\b[^.:;]*?\\b" +
      NARR_CODE_PREFIX +
      "\\s*#?\\s*" +
      NARR_CODE +
      "\\b",
    "gi",
  ),
  new RegExp(
    "\\bwill be (?:funded|budgeted|requested)\\s+(?:in|under)\\s+" +
      NARR_CODE_PREFIX +
      "\\s*#?\\s*" +
      NARR_CODE +
      "\\b",
    "gi",
  ),
  new RegExp(
    "\\bwill continue\\b[^.:;]*?\\bin\\s+" + NARR_CODE_PREFIX + "\\s*#?\\s*" + NARR_CODE + "\\b",
    "gi",
  ),
];
/** Same shape as lineage/extract.py's _PE (:25). */
const NARR_PE_SHAPE = /^\d{7}(?:[A-Z][A-Z0-9]{0,3})?$/;

/** The page universe as a membership test: an exact sidecar slug, or the
 *  bare code of an E3 composite / -L split member (`2136-OPN` ⇒ `2136`). */
export function pageUniverse(sidecars) {
  const exact = new Set(sidecars.keys());
  const composite = new Set();
  for (const s of exact) {
    const i = s.indexOf("-");
    if (i > 0) composite.add(s.slice(0, i));
  }
  return { has: (code) => exact.has(code) || composite.has(code) };
}

/**
 * Forward pointers the page's OWN narratives name: destination codes ≠ this
 * page that exist in the page universe. Returns
 * [{code, shape: "pe"|"line", kind, sentence}], deduped by code, in narrative
 * order. `sentence` is a ~120-char window around the match for diagnostics —
 * it is quoted in errors, never rendered.
 */
export function narrativeForwardPointers(d, slug, universe) {
  const self = new Set([slug, slug.split("-")[0]]);
  const out = new Map();
  for (const n of d.narratives ?? []) {
    const body = String(n.body ?? "");
    for (const re of NARR_FORWARD_RES) {
      for (const m of body.matchAll(re)) {
        const code = m[1].toUpperCase();
        if (self.has(code) || out.has(code) || !universe.has(code)) continue;
        const start = Math.max(0, m.index - 80);
        out.set(code, {
          code,
          shape: NARR_PE_SHAPE.test(code) ? "pe" : "line",
          kind: n.kind ?? null,
          sentence: body
            .slice(start, m.index + m[0].length + 40)
            .replace(/\s+/g, " ")
            .trim(),
        });
      }
    }
  }
  return [...out.values()];
}

/** The rendered note texts of one built page, or null when it is not built.
 *  Injected in unit tests. */
function readNoteTexts(slug) {
  const p = pageHtmlPath(slug);
  if (!fs.existsSync(p)) return null;
  const html = fs.readFileSync(p, "utf8");
  // Parsing a megabyte of HTML to find two <p>s is this leg's whole cost; a
  // page carrying neither attribute has no note to read.
  if (!html.includes(FY2026_ABSENT_ATTR) && !html.includes(DECADE_ONLY_ATTR)) {
    return { absent: null, decade: null };
  }
  const root = parse(html, { comment: false });
  const grab = (attr) => {
    const el = root.querySelector(`[${attr}]`);
    return el ? (el.text ?? "").replace(/\s+/g, " ").trim() : null;
  };
  return { absent: grab(FY2026_ABSENT_ATTR), decade: grab(DECADE_ONLY_ATTR) };
}

export function runNarrativeSuccessorLeg({
  errors,
  notes,
  sidecars,
  noteTexts = readNoteTexts,
}) {
  const universe = pageUniverse(sidecars);
  let retired = 0;
  let drift = 0;
  let flagged = 0;
  let noRailPointerPages = 0;
  let pePointers = 0;
  let linePointers = 0;
  let withRailPointerPages = 0;
  let checked = 0;
  // One component renders every note, so a wording regression hits hundreds
  // of pages at once: report the first 5 of each kind and count the rest.
  const say = (n, msg) => {
    if (n <= 5) errors.push(msg);
  };

  for (const [slug, d] of sidecars) {
    const fa = d.fy2026_absent ?? null;
    const da = d.decade_absent ?? null;
    if (!fa && !da) continue;
    const narrCount = (d.narratives ?? []).length;
    const hasNarr = narrCount > 0;

    // 0. the exporter's flag vs this gate's own recompute of it.
    if (fa) {
      flagged++;
      if (fa.has_narrative !== hasNarr) {
        drift++;
        say(
          drift,
          `program-skeleton(l): /program/${slug}/ sidecar says has_narrative=` +
            `${fa.has_narrative} but ships ${narrCount} narrative(s) — the exporter and ` +
            `the gate disagree about whether there is prose below to point at`,
        );
      }
    }

    const texts = noteTexts(slug);
    if (!texts) continue; // legs (g)/(k) already fail an unbuilt page
    checked++;
    const ptrs = narrativeForwardPointers(d, slug, universe);

    // 1. the retired corpus-wide denial, on either note.
    for (const [which, text] of [
      ["fy2026-absent", texts.absent],
      ["decade-only", texts.decade],
    ]) {
      if (text && text.includes(FY2026_SUCCESSOR_DENIAL_RETIRED)) {
        retired++;
        say(
          retired,
          `program-skeleton(l): /program/${slug}/ ${which} note renders the retired ` +
            `corpus-wide successor denial "${FY2026_SUCCESSOR_DENIAL_RETIRED}"` +
            (ptrs.length ? ` while its own narrative says "…${ptrs[0].sentence}…"` : "") +
            ` — the note may claim only what this site holds (#32(b) residue)`,
        );
      }
    }

    if (!fa || !texts.absent) continue;
    const saysPointer = texts.absent.includes(FY2026_NARRATIVE_POINTER);
    const hasRail = Boolean(d.lineage?.rail?.successors?.length);

    if (hasRail) {
      if (ptrs.length) withRailPointerPages++;
      // 2b. the narrative pointer belongs to the no-rail branch only.
      if (saysPointer) {
        drift++;
        say(
          drift,
          `program-skeleton(l): /program/${slug}/ renders the narrative pointer beside a ` +
            `successor rail — the note must point at Program Lineage there, not at the prose`,
        );
      }
      continue;
    }

    if (ptrs.length) {
      noRailPointerPages++;
      for (const p of ptrs) {
        if (p.shape === "pe") pePointers++;
        else linePointers++;
      }
      // 3. a named forward pointer the site did not key ⇒ the reader is sent
      //    to the record, never told there is none.
      if (!saysPointer) {
        drift++;
        say(
          drift,
          `program-skeleton(l): /program/${slug}/ narrative names a forward pointer ` +
            `(${ptrs.map((p) => p.code).join(", ")}: "…${ptrs[0].sentence}…") that the ` +
            `lineage layer did not key, but the note does not send the reader to the narrative`,
        );
        continue;
      }
    }
    // 2. the pointer renders iff there is prose below to point at.
    if (hasNarr && !saysPointer) {
      drift++;
      say(
        drift,
        `program-skeleton(l): /program/${slug}/ renders ${narrCount} narrative(s) but its ` +
          `note omits the narrative pointer "${FY2026_NARRATIVE_POINTER}"`,
      );
    } else if (!hasNarr && saysPointer) {
      drift++;
      say(
        drift,
        `program-skeleton(l): /program/${slug}/ note says a narrative "is quoted below" but ` +
          `the page renders no narrative — the pointer points at nothing`,
      );
    }
  }

  if (retired > 5) {
    errors.push(
      `program-skeleton(l): ${retired} note(s) render the retired corpus-wide denial in total ` +
        `(first 5 listed) — one component renders all of them, so this is one wording regression`,
    );
  }
  if (drift > 5) {
    errors.push(
      `program-skeleton(l): ${drift} narrative-pointer defect(s) in total (first 5 listed)`,
    );
  }
  if (noRailPointerPages < MIN_NARRATIVE_FORWARD_POINTER_PAGES) {
    errors.push(
      `program-skeleton(l): only ${noRailPointerPages} no-rail page(s) carry a narrative that ` +
        `names a forward pointer (expected >= ${MIN_NARRATIVE_FORWARD_POINTER_PAGES}) — the ` +
        `leg would be vacuous. Re-measure the population (backlog #105 keying edges moves pages ` +
        `out of it) and re-derive the floor with a dated note; do not lower it to fit the build`,
    );
  }
  notes.push(
    `leg l: ${checked} note(s) read, ${flagged} has_narrative flag(s) recomputed; ` +
      `${noRailPointerPages} no-rail page(s) whose own narrative names a forward pointer the ` +
      `lineage layer did not key (${pePointers} PE-shaped, ${linePointers} ` +
      `line-item/WSC-shaped) all send the reader to the narrative; ${withRailPointerPages} ` +
      `rail page(s) also name one; ${retired} retired denial(s) ✓`,
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// leg h — a GAO finding sits on the program it is about (ROADMAP #30)
// ═══════════════════════════════════════════════════════════════════════════
//
// The department tier ("DOD — 5 high-risk areas") is not about the program
// whose page it renders on, says so, and is de-emphasized for it. #30 added
// the tier that IS: GAO's per-program Weapon Systems Annual Assessment and
// the program-specific GAO reports that volume cites.
//
// The failure this leg exists to catch is not a formatting slip. Attributing
// a real GAO audit finding to the wrong weapons program is a defamation-
// shaped error, so the design puts a human verdict on every attribution
// (data-seeds/gao_program_xwalk.csv) and the exporter does no matching at
// all. That means this leg cannot "independently reimplement" the exporter's
// rule — there is no rule to reimplement — and it does not try. It asserts
// the CONTRACT, against the built artifact:
//
//   h1. RATIFIED <-> RENDERED, exactly. Every verdict-"y" row whose page is
//       built renders its GAO item; every rendered item traces back to a
//       verdict-"y" row. Nothing reaches a reader that a person did not
//       ratify, and nothing ratified silently stops rendering.
//   h2. The quoted assessment is VERBATIM the ingested GAO paragraph, read
//       from the sidecar, not from the page. A paraphrase would be a new
//       uncited claim about a weapons program.
//   h3. Every item's citation resolves to its own GAO product page.
//   h4. The GAO item's service agrees with the org the PAGE itself links to
//       (its /agency/{org}/ oversight link). An Air Force assessment on an
//       Army budget line is the ROADMAP #55 defect — "Sentinel" the ICBM
//       against "Sentinel Mods" the Army procurement line — and this is the
//       check that refuses it. It shares a premise with the matcher's
//       service filter, deliberately: the premise is a fact about the world,
//       and the two artifacts compared are different ones.
//   h5. CORROBORATION the matcher never consults: the GAO program's name and
//       the page's own title must share a DISTINCTIVE word — one appearing
//       in <= 0.5% of the site's program titles. Measured over the shipped
//       crosswalk, all 62 items clear it.
//   h6. The honest denial. Every program page with no ratified item must
//       still say, verbatim, that no program-specific GAO finding for that
//       line is in the ingested data — and no page may say both.
//   h7. The program tier renders ABOVE the department note, which is the
//       placement #30 asked for and the reason the department note was
//       allowed to give up its emphasis.
//   h8. EDITIONS (#30 "and its predecessors"). Every rendered assessment is
//       stamped with its edition, that stamp equals the ingested edition of
//       its product, and the sentence a reader sees names it. An item whose
//       (product, slug) no person ratified may render ONLY as an inherited
//       older edition: its anchor is ratified on this page, is rendered on
//       this page, is the same program (same normalized common name, same
//       service family), and is NEWER — inheritance never flows forward and
//       never crosses a rename or a service. Inherited items are exempt from
//       h5 because h8 binds them to an anchor that already passed it.
//       Finally the DELIVERABLE is bound both ways: the number of inherited
//       items the pages render equals stats.inherited_items in the sidecar —
//       the number /methodology/ prints — so priors that stop rendering fail
//       the build instead of leaving that sentence claiming them.
//
// Non-vacuity is structural rather than a pinned literal: the leg fails if
// the ratified set is empty, and the population it checks IS the ratified
// set, so a shrinking crosswalk cannot quietly stop exercising it.

const GAO_SEED = path.resolve(
  siteRoot, "..", "data-seeds", "gao_program_xwalk.csv",
);
const GAO_DENIAL =
  "No program-specific GAO finding for this line is in the ingested data.";
/** A word in <= this share of program titles is "distinctive" for h5. */
const GAO_RARE_TOKEN_SHARE = 0.005;
/** GAO service -> the org code its budget lines live under. */
const GAO_SERVICE_ORGS = {
  "Air Force": ["F"],
  "Space Force": ["F"],
  Army: ["A"],
  Navy: ["N"],
  "Marine Corps": ["N"],
};

function gaoTokens(text) {
  return String(text ?? "").toLowerCase().match(/[a-z]+|[0-9]+/g) ?? [];
}

/** Minimal CSV reader for the ratified seed (quoted fields, embedded ""). */
function readCsvRows(text) {
  const rows = [];
  let field = "";
  let row = [];
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else quoted = false;
      } else field += c;
      continue;
    }
    if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
    else if (c !== "\r") field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  if (rows.length === 0) return [];
  const header = rows[0];
  return rows.slice(1).filter((r) => r.length === header.length).map((r) =>
    Object.fromEntries(header.map((h, i) => [h, r[i]])),
  );
}

/**
 * Leg h8 over one page's rendered GAO assessment items (see the contract
 * comment above).  Pure: items are `{kind, product, program, common,
 * service, editionYear, inheritedFrom, text}` read off the DOM by the
 * caller; `ratified` is the "<product> <slug>" set; `editionYearByProduct`
 * maps each ingested WSAA edition to its year; `serviceFamilies` is the
 * sidecar's own `service_families` map.
 */
export function checkGaoEditionItems({
  slug,
  items,
  ratified,
  editionYearByProduct,
  serviceFamilies,
}) {
  const errors = [];
  const key = (s) => gaoTokens(s).join("");
  // "Same program" needs GAO's service labels collapsed to book families —
  // "Joint" in the 2025 volume and "DOD" in 2024/2023 name one lead (the
  // F-35's). That map is gao_programs._SERVICE_FAMILY, emitted into the
  // sidecar by the exporter and read here rather than copied: the copy drifted
  // once already. Unknown labels stand for themselves, as _family() does.
  // Deliberately NOT GAO_SERVICE_ORGS, which h4 uses for a different job —
  // naming a real org CODE a page can link to.
  const family = (svc) => serviceFamilies.get(svc) ?? svc;
  const anchors = items.filter(
    (it) => it.kind === "assessment" && !it.inheritedFrom,
  );
  for (const it of items) {
    if (it.kind !== "assessment") continue;
    const at = `program-skeleton(h8): /program/${slug}/ GAO ${it.product} ("${it.program}")`;
    const want = editionYearByProduct.get(it.product);
    if (want === undefined) {
      errors.push(
        `${at} is not an ingested Weapon Systems Annual Assessment edition`,
      );
      continue;
    }
    if (it.editionYear !== want) {
      errors.push(
        `${at} stamps edition ${it.editionYear}; the ingested edition of ` +
          `${it.product} is ${want}`,
      );
    } else if (!it.text.includes(`${want} Weapon Systems Annual Assessment`)) {
      errors.push(
        `${at} does not name its edition in the sentence a reader sees ` +
          `(expected "${want} Weapon Systems Annual Assessment")`,
      );
    }
    if (!it.inheritedFrom) continue;
    if (!ratified.has(`${it.inheritedFrom} ${slug}`)) {
      errors.push(
        `${at} is inherited from ${it.inheritedFrom}, which no ratified ` +
          `crosswalk places on this page`,
      );
      continue;
    }
    const anchor = anchors.find(
      (a) =>
        a.product === it.inheritedFrom &&
        key(a.common) === key(it.common) &&
        family(a.service) === family(it.service),
    );
    if (!anchor) {
      errors.push(
        `${at} is inherited from ${it.inheritedFrom} but no rendered anchor ` +
          `on this page is the same program (same common name and service family)`,
      );
      continue;
    }
    const anchorYear = editionYearByProduct.get(anchor.product);
    if (!(want < anchorYear)) {
      errors.push(
        `${at} (edition ${want}) inherits from edition ${anchorYear} — ` +
          `inheritance flows from a newer ratified edition to older ones only`,
      );
    }
  }
  return errors;
}

/**
 * Leg h8's reverse direction, for the half of the deliverable the ratified
 * set cannot cover: inherited older editions are by construction NOT ratified
 * pairs, so h1's reverse leg never iterates them. Without this, every prior
 * could stop rendering and the build would stay green while /methodology/
 * went on reporting stats.inherited_items of them.
 */
export function checkGaoInheritedCount({ rendered, expected }) {
  if (!Number.isFinite(expected)) {
    return [
      "program-skeleton(h8): gao_program_findings.json stats carries no " +
        "inherited_items — re-run `oversight gao-programs` and export-site",
    ];
  }
  if (rendered !== expected) {
    return [
      `program-skeleton(h8): the sidecar carries ${expected} inherited ` +
        `older-edition item(s) but the built pages render ${rendered} — ` +
        `/methodology/ states the sidecar's count, so an edition that stops ` +
        `rendering makes that sentence false`,
    ];
  }
  return [];
}

function runGaoProgramLeg({ errors, notes, sidecars }) {
  const sidecarPath = path.join(jsonDir, "gao_program_findings.json");
  if (!fs.existsSync(GAO_SEED) || !fs.existsSync(sidecarPath)) {
    errors.push(
      "program-skeleton(h): missing " +
        (!fs.existsSync(GAO_SEED)
          ? "data-seeds/gao_program_xwalk.csv"
          : "gao_program_findings.json") +
        " — the program tier cannot be verified",
    );
    return;
  }

  // ── the human record ─────────────────────────────────────────────────────
  const seedRows = readCsvRows(fs.readFileSync(GAO_SEED, "utf8"));
  const ratified = new Set();
  for (const r of seedRows) {
    const verdict = (r.verdict ?? "").trim();
    if (verdict !== "y" && verdict !== "n") {
      errors.push(
        `program-skeleton(h): seed row ${r.gao_program} -> ${r.slug} carries ` +
          `verdict "${verdict}" — an unadjudicated crosswalk must not exist`,
      );
      continue;
    }
    if (verdict === "y") ratified.add(`${r.product_number} ${r.slug}`);
  }
  if (ratified.size === 0) {
    errors.push(
      "program-skeleton(h): no ratified crosswalk in the seed — the leg would " +
        "be vacuous. If the crosswalk really is empty the program tier must " +
        "not render at all; do not weaken this check to pass a build",
    );
    return;
  }

  // ── the ingested GAO text (h2's source of truth — not the page) ──────────
  const side = readJson(sidecarPath);
  const quoteFor = new Map();
  const serviceFor = new Map();
  for (const bucket of Object.values(side.by_slug ?? {})) {
    for (const a of bucket.assessments ?? []) {
      quoteFor.set(`${a.product_number} ${a.gao_program}`, a.description);
      serviceFor.set(`${a.product_number} ${a.gao_program}`, a.service);
    }
  }
  const editionYearByProduct = new Map(
    (side.source ?? [])
      .filter((e) => Number.isFinite(Number(e.edition_year)))
      .map((e) => [e.product_number, Number(e.edition_year)]),
  );
  if (editionYearByProduct.size === 0) {
    errors.push(
      "program-skeleton(h8): gao_program_findings.json source[] carries no " +
        "edition_year — re-run `oversight gao-programs` and export-site",
    );
    return;
  }
  // gao_programs._SERVICE_FAMILY, as the exporter wrote it. Empty means a
  // sidecar from before that map shipped; h8 would then read every service
  // label as its own family and pass inheritances it must refuse.
  const serviceFamilies = new Map(
    Object.entries(side.service_families ?? {}),
  );
  if (serviceFamilies.size === 0) {
    errors.push(
      "program-skeleton(h8): gao_program_findings.json carries no " +
        "service_families — re-run export-site so h8 reads the same map " +
        "gao_programs uses instead of guessing",
    );
    return;
  }

  // ── corpus title statistics for h5 ───────────────────────────────────────
  const programs = readJson(path.join(jsonDir, "programs.json"));
  const titleBySlug = new Map(programs.map((p) => [p.slug, p.title ?? ""]));
  const docFreq = new Map();
  for (const p of programs) {
    for (const t of new Set(gaoTokens(p.title))) {
      docFreq.set(t, (docFreq.get(t) ?? 0) + 1);
    }
  }
  const rareLimit = GAO_RARE_TOKEN_SHARE * programs.length;

  // ── one pass over the whole page universe ────────────────────────────────
  let rendered = 0;
  let pagesWithBlock = 0;
  let missingDenial = 0;
  let bothClaims = 0;
  const seenPairs = new Set();
  const unratified = { n: 0 };
  const badQuote = { n: 0 };
  const badCite = { n: 0 };
  const badService = { n: 0 };
  const badCorroboration = { n: 0 };
  const badEdition = { n: 0 };
  let inheritedRendered = 0;
  const say = (bucket, msg) => {
    bucket.n++;
    if (bucket.n <= 5) errors.push(msg);
  };

  for (const slug of sidecars.keys()) {
    const p = pageHtmlPath(slug);
    if (!fs.existsSync(p)) continue;
    const html = fs.readFileSync(p, "utf8");
    const hasBlock = html.includes('data-gao-scope="program"');
    const hasDenial = html.includes(GAO_DENIAL);

    // h6 — the honest denial, on every page with nothing ratified.
    if (!hasBlock) {
      if (!hasDenial) {
        missingDenial++;
        if (missingDenial <= 5) {
          errors.push(
            `program-skeleton(h6): /program/${slug}/ carries no ratified GAO ` +
              `item and does not say "${GAO_DENIAL}" — the page must state ` +
              `the absence, not go quiet about it`,
          );
        }
      }
      continue;
    }
    if (hasDenial) {
      bothClaims++;
      if (bothClaims <= 5) {
        errors.push(
          `program-skeleton(h6): /program/${slug}/ renders GAO program-level ` +
            `work AND denies that any is ingested — both cannot be true`,
        );
      }
    }
    pagesWithBlock++;

    const root = parse(html, { comment: false });
    const block = root.querySelector('[data-gao-scope="program"]');
    const dept = root.querySelector('[data-gao-scope="department"]');

    // h7 — placement.
    if (dept) {
      const order = root
        .querySelectorAll("[data-gao-scope]")
        .map((el) => el.getAttribute("data-gao-scope"));
      if (order.indexOf("program") > order.indexOf("department")) {
        errors.push(
          `program-skeleton(h7): /program/${slug}/ renders the department ` +
            `note ABOVE the program-specific finding — #30 requires the reverse`,
        );
      }
    }

    // The org the PAGE itself claims, from its own agency link (h4).
    const agencyHref =
      root
        .querySelectorAll("a[href]")
        .map((a) => a.getAttribute("href") ?? "")
        .find((h) => /^\/agency\/[^/]+\/#oversight$/.test(h)) ?? "";
    const pageOrg = agencyHref.split("/")[2] ?? "";
    const pageTitleTokens = new Set(gaoTokens(titleBySlug.get(slug) ?? ""));

    const pageItems = [];
    for (const item of block.querySelectorAll("[data-gao-item]")) {
      const product = item.getAttribute("data-gao-product") ?? "";
      const program = item.getAttribute("data-gao-program") ?? "";
      const inheritedFrom = item.getAttribute("data-gao-inherited-from") || null;
      rendered++;
      if (inheritedFrom) inheritedRendered++;
      pageItems.push({
        kind: item.getAttribute("data-gao-item"),
        product,
        program,
        common: item.getAttribute("data-gao-common") ?? "",
        service: item.getAttribute("data-gao-service") ?? "",
        editionYear: Number(item.getAttribute("data-gao-edition")),
        inheritedFrom,
        text: item.text.replace(/\s+/g, " ").trim(),
      });
      const pairKey = `${product} ${slug}`;
      seenPairs.add(pairKey);

      // h1 — nothing renders that a person did not ratify. An inherited
      // older edition is not in the ratified set by construction; h8 below
      // decides whether its anchor entitles it to be here.
      if (!ratified.has(pairKey) && !inheritedFrom) {
        say(
          unratified,
          `program-skeleton(h1): /program/${slug}/ renders GAO ${product} ` +
            `("${program}") but no verdict-"y" row in ` +
            `data-seeds/gao_program_xwalk.csv ratifies that attribution`,
        );
        continue;
      }

      // h3 — the citation resolves to this product's own GAO page.
      const cite = item.querySelector("[data-gao-cite]");
      const want = `https://www.gao.gov/products/${product.toLowerCase()}`;
      if (!cite || (cite.getAttribute("href") ?? "") !== want) {
        say(
          badCite,
          `program-skeleton(h3): /program/${slug}/ item ${product} cites ` +
            `"${cite ? cite.getAttribute("href") : "(no link)"}", expected ${want}`,
        );
      }

      if (item.getAttribute("data-gao-item") === "assessment") {
        // h2 — the quote is GAO's paragraph, verbatim.
        const expectedQuote = quoteFor.get(`${product} ${program}`);
        const quoteEl = item.querySelector("[data-gao-quote]");
        const shown = (quoteEl?.text ?? "").replace(/\s+/g, " ").trim();
        if (!expectedQuote) {
          say(
            badQuote,
            `program-skeleton(h2): /program/${slug}/ quotes GAO on "${program}" ` +
              `(${product}) but no such assessment is in the ingested data`,
          );
        } else if (!shown.includes(expectedQuote.replace(/\s+/g, " ").trim())) {
          say(
            badQuote,
            `program-skeleton(h2): /program/${slug}/ renders a GAO quote that ` +
              `is not the ingested paragraph verbatim — a paraphrase of an ` +
              `audit finding is a new uncited claim (shown: "${shown.slice(0, 90)}…")`,
          );
        }

        // h4 — services must agree with the page's own org.
        const service = serviceFor.get(`${product} ${program}`) ?? "";
        const allowed = GAO_SERVICE_ORGS[service];
        if (allowed && pageOrg && !allowed.includes(pageOrg)) {
          say(
            badService,
            `program-skeleton(h4): /program/${slug}/ (org ${pageOrg}) renders ` +
              `${/^[aeiou]/i.test(service) ? "an" : "a"} ${service} GAO ` +
              `assessment of "${program}" — that service's program assessment ` +
              `cannot be about a line in another service's book`,
          );
        }
      }

      // h5 — corroboration the matcher never used. Inherited items are bound
      // to their anchor by h8 instead (the anchor already passed h5).
      if (inheritedFrom) continue;
      const shared = [...new Set(gaoTokens(program))].filter(
        (t) => pageTitleTokens.has(t) && (docFreq.get(t) ?? 0) <= rareLimit,
      );
      if (shared.length === 0) {
        say(
          badCorroboration,
          `program-skeleton(h5): /program/${slug}/ ("${titleBySlug.get(slug)}") ` +
            `renders GAO work on "${program}" with no distinctive word in ` +
            `common — the crosswalk is not corroborated by the page's own title`,
        );
      }
    }

    for (const msg of checkGaoEditionItems({
      slug,
      items: pageItems,
      ratified,
      editionYearByProduct,
      serviceFamilies,
    })) {
      say(badEdition, msg);
    }
  }

  // h1, the other direction — a ratified row that stopped rendering.
  let notRendered = 0;
  for (const key of ratified) {
    const [product, slug] = key.split(" ");
    if (!sidecars.has(slug)) continue; // no page exists for this budget line
    if (!fs.existsSync(pageHtmlPath(slug))) continue;
    if (seenPairs.has(key)) continue;
    notRendered++;
    if (notRendered <= 5) {
      errors.push(
        `program-skeleton(h1): GAO ${product} is ratified for /program/${slug}/ ` +
          `but the built page renders no such item`,
      );
    }
  }

  for (const msg of checkGaoInheritedCount({
    rendered: inheritedRendered,
    expected: Number(side.stats?.inherited_items),
  })) {
    errors.push(msg);
  }

  for (const [bucket, label] of [
    [unratified, "h1 unratified attribution"],
    [badQuote, "h2 quote mismatch"],
    [badCite, "h3 citation mismatch"],
    [badService, "h4 service mismatch"],
    [badCorroboration, "h5 uncorroborated crosswalk"],
    [badEdition, "h8 edition/inheritance"],
  ]) {
    if (bucket.n > 5) {
      errors.push(
        `program-skeleton(${label}): ${bucket.n} occurrence(s) in total ` +
          `(first 5 listed)`,
      );
    }
  }
  if (missingDenial > 5) {
    errors.push(
      `program-skeleton(h6): ${missingDenial} page(s) with no ratified GAO ` +
        `item omit the denial sentence in total (first 5 listed)`,
    );
  }
  if (notRendered > 5) {
    errors.push(
      `program-skeleton(h1): ${notRendered} ratified crosswalk(s) render ` +
        `nowhere in total (first 5 listed)`,
    );
  }

  notes.push(
    `leg h: ${rendered} GAO item(s) on ${pagesWithBlock} program page(s), ` +
      `${inheritedRendered} inherited from an earlier edition, each traced ` +
      `to a verdict-"y" row of ${ratified.size} in ` +
      `data-seeds/gao_program_xwalk.csv (${editionYearByProduct.size} ` +
      `editions); ${sidecars.size - pagesWithBlock} other page(s) state ` +
      `that no program-specific GAO finding for that line is ingested ✓`,
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// leg i — the org a program page names is an org CODE (ROADMAP #30's cause)
// ═══════════════════════════════════════════════════════════════════════════
//
// The defect this exists to stop recurring: rollupProgramRow synthesized
// ProgramRow.org by running the sidecar's service_org through serviceOrgName,
// storing "Air Force" where every LOOKUP downstream keys by "F". Display kept
// working (serviceOrgName passes a name through unchanged), so nothing looked
// broken — while 226 pages silently resolved no GAO department overlay, showed
// their organization as dead plain text instead of a link to an /agency/ page
// that does exist, and told the reader "Organization code Air Force". #30
// patched the visible silence; nothing pinned the contract.
//
// The contract, asserted against the BUILT artifact for every program page:
//
//   i1 — the header's own claim is true. It renders title="Organization code
//        {X}"; X must EQUAL the org the page's data source carries. Full tier:
//        programs.json's `org`. Rollup tier: the sidecar's `service_org`, or
//        the "DoD" umbrella when it declares none. (That `|| "DoD"` is the one
//        line mirrored from rollupProgramRow — the sidecar's documented
//        fallback for its one service-less line, not the resolution logic
//        under test.) Every occurrence on the page must agree, so the RSC
//        flight copy cannot disagree with the rendered header.
//   i2 — a code with an agency page LINKS to it. out/agency/{X}/index.html
//        existing and the header not carrying href="/agency/{X}/" is the
//        exact shape the name-for-code swap produced.
//   i3 — the GAO department note renders exactly where gao_overlays.json has
//        a non-empty overlay for X. Both directions: a page with an overlay
//        that stays quiet is #30's silence returning; a page without one that
//        renders a note is citing an overlay that is not in the payload.
//
// Reads the org from the page's own tooltip text, not a data-* mirror: the
// page ASSERTS "Organization code X" to the reader, and this checks that
// assertion. A page that rendered the wrong org could not satisfy it by also
// emitting a correct attribute somewhere.

/** Display names serviceOrgName produces — never valid values for `org`. */
const SERVICE_DISPLAY_NAMES = new Set(["Army", "Navy", "Air Force"]);

function runOrgCodeLeg({ errors, notes, sidecars }) {
  const programsPath = path.join(jsonDir, "programs.json");
  const overlaysPath = path.join(jsonDir, "gao_overlays.json");
  if (!fs.existsSync(programsPath)) {
    errors.push("program-skeleton(i): programs.json missing — org codes cannot be verified");
    return;
  }
  const orgBySlug = new Map(
    readJson(programsPath).map((p) => [p.slug ?? p.pe_bli, p.org]),
  );

  // The overlay payload, read as data. `getGaoOverlayForOrg` returns null for
  // an org whose overlay carries neither a high-risk area nor an improper
  // row; that is a shape fact about this payload, mirrored here so i3 states
  // the same "has an overlay" the page does.
  let overlayOrgs = null;
  if (fs.existsSync(overlaysPath)) {
    const ov = readJson(overlaysPath);
    overlayOrgs = new Set();
    for (const [org, code] of Object.entries(ov.agency_code_by_org ?? {})) {
      const a = (ov.agencies ?? {})[code];
      if (!a) continue;
      if ((a.high_risk_areas ?? []).length > 0 || a.improper) overlayOrgs.add(org);
    }
  }

  const orgClaim = /Organization code ([A-Za-z0-9 &._-]+?)(?=["\\])/g;
  const bad = { n: 0 };
  const noLink = { n: 0 };
  const noNote = { n: 0 };
  const strayNote = { n: 0 };
  const say = (bucket, msg) => {
    bucket.n++;
    if (bucket.n <= 5) errors.push(msg);
  };

  let checked = 0;
  let linked = 0;
  let withNote = 0;
  const seenOrgs = new Map();

  for (const [slug, d] of sidecars) {
    const p = pageHtmlPath(slug);
    if (!fs.existsSync(p)) continue;
    const html = fs.readFileSync(p, "utf8");

    const full = orgBySlug.get(slug);
    // The one mirrored line — see the block comment above.
    const expected = full ?? (d.service_org || "DoD");
    const tier = full ? "full" : "rollup";

    const claimed = new Set();
    orgClaim.lastIndex = 0;
    let m;
    while ((m = orgClaim.exec(html)) !== null) claimed.add(m[1]);
    if (claimed.size === 0) {
      say(
        bad,
        `program-skeleton(i1): /program/${slug}/ (${tier}) renders no ` +
          `"Organization code …" header claim at all — the org is unstated`,
      );
      continue;
    }
    const wrong = [...claimed].filter((c) => c !== expected);
    if (wrong.length > 0) {
      const nameSwap = wrong.find((c) => SERVICE_DISPLAY_NAMES.has(c));
      say(
        bad,
        `program-skeleton(i1): /program/${slug}/ (${tier}) claims ` +
          `"Organization code ${wrong.join('" / "')}" but its data source ` +
          `carries org "${expected}"` +
          (nameSwap
            ? ` — "${nameSwap}" is the DISPLAY NAME of a code, not a code. ` +
              `Something humanized the org before storing it (the ROADMAP #30 ` +
              `cause: lib/program-tier.ts rollupProgramRow). Every lookup ` +
              `keyed by org resolves nothing on this page.`
            : ""),
      );
      continue;
    }
    // Counted only once the page's own claim is TRUE — a note that folded
    // the mismatches in would report the number of pages it just failed.
    checked++;
    seenOrgs.set(expected, (seenOrgs.get(expected) ?? 0) + 1);

    // i2 — an org with an agency page must be linked to it.
    const agencyPage = path.join(outDir, "agency", expected, "index.html");
    if (fs.existsSync(agencyPage)) {
      if (!html.includes(`href="/agency/${expected}/"`)) {
        say(
          noLink,
          `program-skeleton(i2): /program/${slug}/ (${tier}, org ${expected}) ` +
            `renders its organization as plain text, but /agency/${expected}/ ` +
            `is a built page — the header's orgHasPage test is keyed by code ` +
            `and only fails to match when the org is not one`,
        );
      } else {
        linked++;
      }
    }

    // i3 — the department overlay note, both directions.
    if (overlayOrgs) {
      const hasNote = html.includes('data-gao-scope="department"');
      const wantsNote = overlayOrgs.has(expected);
      if (wantsNote && !hasNote) {
        say(
          noNote,
          `program-skeleton(i3): /program/${slug}/ (${tier}) has org ` +
            `"${expected}", which gao_overlays.json carries an overlay for, ` +
            `but the page renders no [data-gao-scope="department"] note`,
        );
      } else if (!wantsNote && hasNote) {
        say(
          strayNote,
          `program-skeleton(i3): /program/${slug}/ (${tier}) renders a GAO ` +
            `department note, but gao_overlays.json has no non-empty overlay ` +
            `for its org "${expected}" — the note cites something absent`,
        );
      }
      if (hasNote) withNote++;
    }
  }

  for (const [bucket, label] of [
    [bad, "i1 org-code mismatch"],
    [noLink, "i2 unlinked agency"],
    [noNote, "i3 missing department note"],
    [strayNote, "i3 unbacked department note"],
  ]) {
    if (bucket.n > 5) {
      errors.push(
        `program-skeleton(${label}): ${bucket.n} occurrence(s) in total ` +
          `(first 5 listed)`,
      );
    }
  }

  const orgList = [...seenOrgs.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([o, n]) => `${o}:${n}`)
    .join(" ");
  notes.push(
    `leg i: ${checked} of ${sidecars.size} program page(s) name an org code ` +
      `matching their own data source; of those, ${linked} link to their ` +
      `agency page and ${withNote} carry the GAO department note the overlay ` +
      `payload backs — ${orgList}`,
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// leg j — WHO GETS IT may never present lobbying evidence as award evidence
// ═══════════════════════════════════════════════════════════════════════════
//
// THE DEFECT THIS LEG WAS BUILT AGAINST (tri-persona review, layman pass).
// /program/ATA000/ — the F-35 — rendered "WHO GETS IT — No award linkage at
// high confidence" on a page carrying 29 Lockheed Martin strings of its own.
// USAspending publishes no program element on award records, so the crosswalk
// covers 24 of 1,741 programs and structurally always will: the dead end is
// permanent. Wave 3 turned the card into a tiered answer whose third tier
// names the companies whose Senate LDA filings cite the program.
//
// AND THE DEFECT THAT FIX COULD INTRODUCE, which is what this leg actually
// guards. "Lobbied about it" and "was paid for it" are different claims. The
// whole tri-persona remediation exists because this site keeps shipping a
// true, correctly-cited number wearing a false label; naming Lockheed under a
// heading that reads WHO GETS IT, without an unmissable separation, would be
// the purest example of it yet. So the separation is a machine contract, in
// the built HTML, on EVERY program page — not a code review promise:
//
//   1. Exactly one declared tier per card (data-who-tier ∈ award | jbook |
//      lobbying | none). A card that declares nothing is a failure: it means
//      a branch was added without deciding what it claims.
//   2. MONEY ONLY WHERE AWARDS ARE. The award tier must carry a
//      [data-amount] from fct_program_concentration. The other three must
//      carry NO [data-amount] at all. A dollar figure inside a lobbying-tier
//      card is the conflation, whatever the words around it say.
//   3. The lobbying tier's rendered text must match a FIXED TEMPLATE — read
//      as text, the way a reader (or a screen reader) reads it, not as a
//      data-* attribute mirroring what the markup was supposed to say. The
//      template pins the order too: the absence is stated, then the badge,
//      then the names. A rewrite that moves the names above the disclaimer,
//      or drops "not a contract", fails.
//   4. EVIDENCE TIER PER NAME. Every named company carries data-evidence-kind
//      ∈ {pe_literal, alias} — the program's own code verbatim in the filing
//      text, or a curated human-verified alias. `multi_token` (two or more
//      non-generic title words) is real evidence, and it is labelled on every
//      mention row, but it may not put a company's name in an answer box.
//   5. RENDERER ↔ PAYLOAD. The set of pages rendering the lobbying tier
//      equals the set of sidecars carrying summary.lobbied_by. Neither a
//      silently-dropped tier nor a tier rendered off nothing.
//
// It reads a bounded SLICE of each page rather than parsing 2,005 documents
// whose heaviest is 1.1 MB: from the answer-who testid to the figures
// section that follows it. The slice is the card and nothing else, which is
// also what makes (2) meaningful — an [data-amount] found in it is IN it.

const WHO_TIERS = new Set(["award", "jbook", "lobbying", "none"]);
const WHO_NAME_EVIDENCE = new Set(["pe_literal", "alias"]);

/**
 * The lobbying tier's whole sentence, fixed. Groups: (1) the names clause.
 * Written against textContent with runs of whitespace collapsed.
 */
const WHO_LOBBY_TEMPLATE =
  /^No contract award is linked to this line\.\s+Lobbying — not a contract\s+(.+?) named this program in Senate lobbying filings\.\s+See the filings/;

/** The card's own HTML: [data-testid="answer-who"] up to the figures section. */
function answerWhoSlice(html) {
  const at = html.indexOf('data-testid="answer-who"');
  if (at === -1) return null;
  const open = html.lastIndexOf("<", at);
  const stop = html.indexOf('data-section="figures"', at);
  return html.slice(open === -1 ? at : open, stop === -1 ? at + 12000 : stop);
}

function runWhoGetsItLeg({ errors, notes, sidecars }) {
  const census = { award: 0, jbook: 0, lobbying: 0, none: 0 };
  const problems = { n: 0 };
  const renderedLobbying = new Set();
  const payloadLobbying = new Set();
  let checked = 0;

  const fail = (msg) => {
    problems.n += 1;
    if (problems.n <= 8) errors.push(msg);
  };

  for (const [slug, d] of sidecars) {
    if (d?.summary?.lobbied_by) payloadLobbying.add(slug);
    const p = pageHtmlPath(slug);
    if (!fs.existsSync(p)) continue;
    const slice = answerWhoSlice(fs.readFileSync(p, "utf8"));
    if (slice === null) {
      // A split-key stub renders no answer strip; a real program page must.
      if (d) fail(`program-skeleton(j): /program/${slug}/ has no [data-testid="answer-who"]`);
      continue;
    }
    checked += 1;
    const root = parse(slice, { comment: false });
    const tierEls = root.querySelectorAll("[data-who-tier]");
    if (tierEls.length !== 1) {
      fail(
        `program-skeleton(j): /program/${slug}/ WHO GETS IT declares ` +
          `${tierEls.length} tiers (expected exactly 1)`,
      );
      continue;
    }
    const tier = tierEls[0].getAttribute("data-who-tier");
    if (!WHO_TIERS.has(tier)) {
      fail(`program-skeleton(j): /program/${slug}/ unknown data-who-tier="${tier}"`);
      continue;
    }
    census[tier] += 1;

    // (2) money only where awards are
    const amounts = root.querySelectorAll("[data-amount]");
    if (tier === "award") {
      const conc = amounts.filter(
        (a) => a.getAttribute("data-dataset") === "fct_program_concentration",
      );
      if (conc.length === 0) {
        fail(
          `program-skeleton(j): /program/${slug}/ claims tier "award" with no ` +
            `fct_program_concentration [data-amount] behind it`,
        );
      }
    } else if (amounts.length > 0) {
      fail(
        `program-skeleton(j): /program/${slug}/ tier "${tier}" renders ` +
          `${amounts.length} [data-amount] — a non-award tier may state no dollars`,
      );
    }

    const names = root.querySelectorAll("[data-who-name]");

    if (tier === "lobbying") {
      renderedLobbying.add(slug);
      // (3) the fixed template, read as text
      const text = (tierEls[0].text || "").replace(/\s+/g, " ").trim();
      const m = text.match(WHO_LOBBY_TEMPLATE);
      if (!m) {
        fail(
          `program-skeleton(j): /program/${slug}/ lobbying tier does not read as ` +
            `the declared sentence — got "${text.slice(0, 160)}"`,
        );
      }
      // order: disclaimer and badge both precede the first named company
      const iDisc = slice.indexOf("data-who-disclaimer");
      const iBadge = slice.indexOf("data-who-lobby-badge");
      const iName = slice.indexOf("data-who-name");
      if (iDisc === -1 || iBadge === -1) {
        fail(
          `program-skeleton(j): /program/${slug}/ lobbying tier is missing its ` +
            `${iDisc === -1 ? "disclaimer" : "not-a-contract badge"}`,
        );
      } else if (!(iDisc < iName && iBadge < iName)) {
        fail(
          `program-skeleton(j): /program/${slug}/ names a company before the ` +
            `disclaimer/badge — a reader meets the claim before the caveat`,
        );
      }
      // (4) evidence tier per name
      if (names.length === 0) {
        fail(`program-skeleton(j): /program/${slug}/ lobbying tier names nobody`);
      }
      for (const n of names) {
        const kind = n.getAttribute("data-evidence-kind");
        if (!WHO_NAME_EVIDENCE.has(kind)) {
          fail(
            `program-skeleton(j): /program/${slug}/ names "${(n.text || "").trim()}" ` +
              `on evidence tier "${kind}" — only ${[...WHO_NAME_EVIDENCE].join("/")} may name a company`,
          );
        }
      }
    } else if (names.length > 0) {
      fail(
        `program-skeleton(j): /program/${slug}/ tier "${tier}" carries ` +
          `${names.length} [data-who-name] element(s), which only the lobbying tier may`,
      );
    }

    if (tier === "jbook" && !/Named in the J-book/.test(tierEls[0].text || "")) {
      fail(`program-skeleton(j): /program/${slug}/ jbook tier does not say so`);
    }
  }

  // (5) renderer ↔ payload
  const missed = [...payloadLobbying].filter((s) => !renderedLobbying.has(s));
  const stray = [...renderedLobbying].filter((s) => !payloadLobbying.has(s));
  if (missed.length) {
    errors.push(
      `program-skeleton(j5): ${missed.length} sidecar(s) carry summary.lobbied_by ` +
        `but their page renders another tier (first: ${missed.slice(0, 5).join(", ")})`,
    );
  }
  if (stray.length) {
    errors.push(
      `program-skeleton(j5): ${stray.length} page(s) render the lobbying tier with ` +
        `no summary.lobbied_by behind it (first: ${stray.slice(0, 5).join(", ")})`,
    );
  }
  if (problems.n > 8) {
    errors.push(`program-skeleton(j): ${problems.n} occurrence(s) in total (first 8 listed)`);
  }

  notes.push(
    `leg j: ${checked} WHO GETS IT card(s) checked — award ${census.award}, ` +
      `J-book ${census.jbook}, lobbying ${census.lobbying}, honest absence ` +
      `${census.none}; every non-award tier states no dollars and every named ` +
      `company is ${[...WHO_NAME_EVIDENCE].join("/")}-tier`,
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// leg k — the decade-only tier's absence claims (ROADMAP #28)
// ═══════════════════════════════════════════════════════════════════════════
//
// 553 program elements carry cited President's Budget history and no FY2026
// R-1/P-1 workbook line at all. Before #28 they generated no page: the
// decade existed in the warehouse and was not browsable. They have pages
// now, and EVERYTHING those pages say is about absence — which makes them
// the most exposed surface on this site to the defect #32(a) shipped and two
// independent reviews caught: a note that was true of the predicate the
// exporter used and false of the page it rendered on, 179 times.
//
// This leg is written against that post-mortem. What it pins, on the BUILT
// artifact, over the WHOLE page universe (no sampling — the negative
// direction is the half a sample would miss):
//
//   1. POPULATION, both directions. Every tier:"decade" sidecar renders
//      [data-decade-only]; no other page does. A page carrying this note
//      while its own budget_lines hold an FY2026 row would be making a false
//      claim about its own money.
//   2. THE TIER'S PREMISE, recomputed from the sidecar rather than trusted:
//      budget_lines empty, details empty, a non-empty cited decade_series.
//      Those three are what make every sentence in the note true; if the
//      exporter ever ships a decade sidecar with an FY2026 workbook row on
//      it, the note's first sentence is a lie and this fails.
//   3. THE BLOCK, recomputed independently from the sidecar's OWN
//      decade_series and lineage rail — first/last edition, edition count,
//      fy span, the renumber flag and the successor flag. Same convention as
//      CANONICAL_SECTIONS and leg (g): two implementations, and a drift
//      between them is a real failure.
//   4. THE SENTENCE says all of it, verbatim, with the recomputed numbers —
//      and the CONDITIONAL clauses render only where they hold:
//        · the PB2026-renumber explanation ONLY when the line survived to
//          PB2025. #32(a) told 319 pages "PB2026 renumbered at scale" as the
//          reason their record stops; on a line last carried in PB2019 that
//          blames an event six editions later, and both directions are
//          checked here so it cannot creep back;
//        · the successor POINTER where the page renders a cited successor
//          rail, the DENIAL where it does not — the fix that closed the five
//          #32(a) pages denying a successor they named three inches below.
//   5. THE FY SPAN IS CHECKED AGAINST THE RENDERED TABLE, not only against
//      the sidecar: the note's FY{min}–FY{max} must be the first and last
//      fiscal year the page's own decade grid actually draws a cited figure
//      for. This is the "check the claim against what the page displays"
//      rule that leg (g) had to learn.
//   6. It never claims an ending, and never names another program element —
//      the same two rules, and the same two mechanisms, as leg (g).
//   7. The two absence notes are MUTUALLY EXCLUSIVE. A page may not carry
//      both [data-decade-only] and [data-fy2026-absent]: they are claims
//      about different blank records, and a page making both is making one
//      of them falsely.

/** Non-vacuity floor: the shipped corpus holds exactly 553 decade-only pages
 *  (measured 2026-08-31 from fct_decade_series — keys with a positive grain,
 *  no PB2026 page, not an era procurement key, route-safe: 3,771 candidates
 *  − 1,994 that already have a page − 1,214 era keys − 8 all-zero − 2
 *  route-unsafe). A drop means either the predicate broke or the corpus
 *  changed — RE-MEASURE and re-derive this number, never lower it to
 *  whatever the build produced. */
const MIN_DECADE_ONLY_PAGES = 553;

/** The stable hook a decade page must carry. */
const DECADE_ONLY_ATTR = "data-decade-only";

/** Sentences every decade note must contain, whatever the page. */
const DECADE_REQUIRED = [
  "No FY2026 R-1/P-1 workbook line for this program element.",
  "carry no row for it at all",
  "The summary cards above read that one edition",
];

/** The renumber explanation — must render iff the line survived to PB2025. */
const DECADE_RENUMBER =
  "PB2026 renumbered program elements at scale across the services and defense agencies";
/** Its mutually exclusive alternative. */
const DECADE_NO_LATER =
  "no later President's Budget edition in this corpus carries it";

/** Successor clauses — shared verbatim with the #32(a) note (leg g). */
const DECADE_SUCCESSOR_DENIAL = FY2026_SUCCESSOR_DENIAL;
const DECADE_SUCCESSOR_POINTER = FY2026_SUCCESSOR_POINTER;

/**
 * Independent recompute of the exporter's `decade_absent` payload
 * (src/govbudget/export_site.py, _decade_absent_block) from the sidecar's
 * OWN decade_series — the exact points the page's decade grid draws.
 */
function recomputeDecadeAbsent(d) {
  const editions = new Set();
  const fys = new Set();
  for (const points of Object.values(d.decade_series ?? {})) {
    for (const p of points ?? []) {
      if (p.edition != null) editions.add(Number(p.edition));
      if (p.fy != null) fys.add(Number(p.fy));
    }
  }
  if (editions.size === 0 || fys.size === 0) return null;
  const lastEdition = Math.max(...editions);
  return {
    first_edition: Math.min(...editions),
    last_edition: lastEdition,
    edition_count: editions.size,
    fy_min: Math.min(...fys),
    fy_max: Math.max(...fys),
    // PB2026 − 1. The note may blame the PB2026 renumbering only where the
    // line was actually in the edition PB2026 replaced.
    renumber: lastEdition === 2025,
    has_successor: Boolean(d.lineage?.rail?.successors?.length),
  };
}

/** First/last fiscal year the page's own decade grid draws a CITED figure
 *  for — read from the rendered table, not from the sidecar. */
function renderedDecadeFySpan(root) {
  const fys = [];
  const grid = root.querySelector('[data-testid="decade-grid"]');
  if (!grid) return null;
  for (const cell of grid.querySelectorAll("[data-decade-cell]")) {
    if (!cell.querySelector("[data-amount]")) continue;
    const m = /-(\d{4})$/.exec(cell.getAttribute("data-decade-cell") ?? "");
    if (m) fys.push(Number(m[1]));
  }
  if (fys.length === 0) return null;
  return { fy_min: Math.min(...fys), fy_max: Math.max(...fys) };
}

function runDecadeOnlyLeg({ errors, notes, sidecars }) {
  // ── 1/2/3. the population and its premise, from the sidecars ────────────
  const expected = new Map(); // slug -> recomputed block
  let premiseBreaks = 0;
  let blockDrift = 0;
  for (const [slug, d] of sidecars) {
    if (d.tier !== "decade") continue;

    // 2. the premise. Each of these is what makes a sentence in the note
    // true; report the first few and count the rest.
    const why = [];
    if ((d.budget_lines ?? []).length > 0) {
      why.push(`${d.budget_lines.length} FY2026 workbook row(s)`);
    }
    if ((d.details ?? []).length > 0) {
      why.push(`${d.details.length} J-book detail row(s)`);
    }
    const want = recomputeDecadeAbsent(d);
    if (!want) why.push("no cited decade point");
    if (why.length > 0) {
      premiseBreaks++;
      if (premiseBreaks <= 5) {
        errors.push(
          `program-skeleton(k): /program/${slug}/ is tier "decade" but has ${why.join(" and ")} — ` +
            `the note says the FY2026 workbooks carry no row for this element and that its ` +
            `figures come from earlier editions; that page contradicts it`,
        );
      }
      continue;
    }

    // 3. the exporter's block vs. this recompute, field for field.
    const got = d.decade_absent ?? null;
    if (!got) {
      blockDrift++;
      if (blockDrift <= 5) {
        errors.push(
          `program-skeleton(k): /program/${slug}/ is tier "decade" but carries no ` +
            `decade_absent block — the page would render its history with no statement ` +
            `of why it stops`,
        );
      }
      continue;
    }
    const diffs = Object.keys(want).filter((f) => want[f] !== got[f]);
    if (diffs.length > 0) {
      blockDrift++;
      if (blockDrift <= 5) {
        errors.push(
          `program-skeleton(k): /program/${slug}/ decade_absent disagrees with the gate's own ` +
            `recompute from this page's decade series on ${diffs.join(", ")} — ` +
            `exporter ${JSON.stringify(got)}, recompute ${JSON.stringify(want)}`,
        );
      }
      continue;
    }
    expected.set(slug, want);
  }
  if (premiseBreaks > 5) {
    errors.push(
      `program-skeleton(k): ${premiseBreaks} decade sidecars break the tier's premise in total ` +
        `(first 5 listed)`,
    );
  }
  if (blockDrift > 5) {
    errors.push(
      `program-skeleton(k): ${blockDrift} decade sidecars disagree with the recompute in total ` +
        `(first 5 listed)`,
    );
  }

  if (expected.size < MIN_DECADE_ONLY_PAGES) {
    errors.push(
      `program-skeleton(k): only ${expected.size} page(s) qualify as decade-only ` +
        `(expected >= ${MIN_DECADE_ONLY_PAGES}) — the leg would be vacuous. Re-measure the ` +
        `population from fct_decade_series and re-derive the floor; do not lower it to fit ` +
        `the build`,
    );
    return;
  }

  // ── 4/5/6/7. one read pass over the WHOLE page universe ─────────────────
  let withNote = 0;
  let missing = 0;
  let stray = 0;
  let badNotes = 0;
  let spanChecked = 0;
  const renumberCounts = { renumber: 0, earlier: 0 };
  for (const [slug, d] of sidecars) {
    const p = pageHtmlPath(slug);
    if (!fs.existsSync(p)) {
      if (expected.has(slug)) {
        errors.push(`program-skeleton(k): /program/${slug}/ not built`);
      }
      continue;
    }
    const html = fs.readFileSync(p, "utf8");
    const marked = html.includes(DECADE_ONLY_ATTR);
    const want = expected.get(slug) ?? null;

    if (!want) {
      // 1, negative direction. The note claims this element has no FY2026
      // workbook line; on a page that has one, that is false about the
      // page's own money.
      if (marked) {
        stray++;
        if (stray <= 5) {
          const fy26 = (d.budget_lines ?? []).filter((r) => r.fy === 2026).length;
          const why = fy26 > 0
            ? `its PB2026 workbook carries ${fy26} FY2026 row(s) on this page`
            : `it is tier ${JSON.stringify(d.tier ?? "full")}, not the decade tier`;
          errors.push(
            `program-skeleton(k): /program/${slug}/ renders the decade-only note but ${why} — ` +
              `the note is a false claim about this page`,
          );
        }
      }
      continue;
    }

    // 1, positive direction.
    if (!marked) {
      missing++;
      if (missing <= 5) {
        errors.push(
          `program-skeleton(k): /program/${slug}/ publishes only PB${want.first_edition}–` +
            `PB${want.last_edition} figures and renders no [${DECADE_ONLY_ATTR}] note — the ` +
            `page shows a decade of money that stops, with nothing to say why (ROADMAP #28)`,
        );
      }
      continue;
    }

    const root = parse(html, { comment: false });
    const el = root.querySelector(`[${DECADE_ONLY_ATTR}]`);
    if (!el) {
      errors.push(
        `program-skeleton(k): /program/${slug}/ mentions ${DECADE_ONLY_ATTR} but no element ` +
          `carries it`,
      );
      continue;
    }
    const text = (el.text ?? "").replace(/\s+/g, " ").trim();
    const say = (msg) => {
      badNotes++;
      if (badNotes <= 5) errors.push(msg);
    };

    // 7. the two absence notes are mutually exclusive.
    if (html.includes(FY2026_ABSENT_ATTR)) {
      say(
        `program-skeleton(k): /program/${slug}/ carries BOTH the decade-only note and the ` +
          `#32a renumber note — they are claims about different blank records (no row at ` +
          `all vs. a blank FY2026 cell on a line that is listed), so one of them is false here`,
      );
    }

    // 4. the fixed sentences.
    for (const frag of DECADE_REQUIRED) {
      if (!text.includes(frag)) {
        say(
          `program-skeleton(k): /program/${slug}/ note is missing the required sentence ` +
            `"${frag}" — got "${text.slice(0, 160)}…"`,
        );
      }
    }
    // 4. the year the record stops at, and the span the page publishes.
    const lastFrag = `It last appears in the PB${want.last_edition} workbook`;
    if (!text.includes(lastFrag)) {
      say(
        `program-skeleton(k): /program/${slug}/ note does not say "${lastFrag}" — it must name ` +
          `the edition this page's own figures actually stop at (got "${text.slice(0, 160)}…")`,
      );
    }
    const spanFrag = `FY${want.fy_min} to FY${want.fy_max}`;
    if (!text.includes(spanFrag)) {
      say(
        `program-skeleton(k): /program/${slug}/ note does not report fiscal years ` +
          `"${spanFrag}" — got "${text.slice(0, 160)}…"`,
      );
    }
    if (want.edition_count > 1) {
      const editionsFrag =
        `cited to ${want.edition_count} President's Budget editions, the earliest ` +
        `PB${want.first_edition} and the latest PB${want.last_edition}`;
      if (!text.includes(editionsFrag)) {
        say(
          `program-skeleton(k): /program/${slug}/ note does not state its edition span ` +
            `("${editionsFrag}") — got "${text.slice(0, 200)}…"`,
        );
      }
    } else if (!text.includes("that single edition")) {
      say(
        `program-skeleton(k): /program/${slug}/ publishes figures from exactly one edition but ` +
          `the note does not say so — got "${text.slice(0, 160)}…"`,
      );
    }

    // 4. the renumber clause, BOTH directions.
    const saysRenumber = text.includes(DECADE_RENUMBER);
    const saysNoLater = text.includes(DECADE_NO_LATER);
    if (want.renumber) {
      renumberCounts.renumber++;
      if (!saysRenumber) {
        say(
          `program-skeleton(k): /program/${slug}/ last appears in PB2025 — the edition PB2026 ` +
            `replaced — but the note omits the renumbering explanation`,
        );
      }
      if (saysNoLater) {
        say(
          `program-skeleton(k): /program/${slug}/ note says no later edition carries it, but its ` +
            `own record runs to PB2025 and PB2026 is the only later edition — say which one it is`,
        );
      }
    } else {
      renumberCounts.earlier++;
      if (saysRenumber) {
        say(
          `program-skeleton(k): /program/${slug}/ blames the PB2026 renumbering for a record that ` +
            `stops at PB${want.last_edition} — the line was already gone ` +
            `${2026 - want.last_edition} edition(s) before PB2026, so PB2026 did not do this. ` +
            `This is the #32a defect (319 pages told the same story about their own year)`,
        );
      }
      if (!saysNoLater) {
        say(
          `program-skeleton(k): /program/${slug}/ note does not state that no later edition ` +
            `carries this line — the limit must be stated, not left silent`,
        );
      }
    }

    // 4. the successor clause must agree with the page's own lineage rail.
    if (want.has_successor) {
      if (text.includes(DECADE_SUCCESSOR_DENIAL)) {
        say(
          `program-skeleton(k): /program/${slug}/ note says this site links no successor, ` +
            `but the page renders a cited successor rail — the denial contradicts the ` +
            `page's own lineage layer`,
        );
      }
      if (!text.includes(DECADE_SUCCESSOR_POINTER)) {
        say(
          `program-skeleton(k): /program/${slug}/ has a successor rail but the note does not ` +
            `point the reader at it`,
        );
      }
    } else if (!text.includes(DECADE_SUCCESSOR_DENIAL)) {
      say(
        `program-skeleton(k): /program/${slug}/ has no successor rail but the note omits the ` +
          `denial — the limit must be stated, not left silent`,
      );
    }

    // 6. it never claims an ending.
    const bad = FY2026_ABSENT_FORBIDDEN.exec(text);
    if (bad) {
      say(
        `program-skeleton(k): /program/${slug}/ note says "${bad[0]}" — absence from the ` +
          `editions this corpus holds supports no such claim (this is the wording the 87 ` +
          `withdrawn feed cards used)`,
      );
    }

    // 6. it names no other program element.
    const named = [...new Set(text.match(PE_TOKEN_RE) ?? [])].filter(
      (c) => c !== slug && sidecars.has(c),
    );
    if (named.length > 0) {
      say(
        `program-skeleton(k): /program/${slug}/ note names program element(s) ${named.join(", ")} ` +
          `— the corpus cannot prove a successor for a line that left the workbooks, so the ` +
          `note must not name one`,
      );
    }

    // 5. the FY span against the RENDERED grid, not only the sidecar.
    const rendered = renderedDecadeFySpan(root);
    if (!rendered) {
      say(
        `program-skeleton(k): /program/${slug}/ renders the decade-only note but its decade grid ` +
          `draws no cited figure — the note describes figures the page does not show`,
      );
    } else {
      spanChecked++;
      if (
        rendered.fy_min !== want.fy_min ||
        rendered.fy_max !== want.fy_max
      ) {
        say(
          `program-skeleton(k): /program/${slug}/ note reports FY${want.fy_min}–FY${want.fy_max} ` +
            `but the decade grid on the page draws cited figures for ` +
            `FY${rendered.fy_min}–FY${rendered.fy_max}`,
        );
      }
    }

    withNote++;
  }

  if (missing > 5) {
    errors.push(
      `program-skeleton(k): ${missing} decade-only pages render no note in total (first 5 listed)`,
    );
  }
  if (stray > 5) {
    errors.push(
      `program-skeleton(k): ${stray} pages outside the decade tier render the note in total ` +
        `(first 5 listed)`,
    );
  }
  if (badNotes > 5) {
    errors.push(
      `program-skeleton(k): ${badNotes} note defects in total (first 5 listed)`,
    );
  }
  notes.push(
    `leg k: ${withNote}/${expected.size} decade-only page(s) state their absence ` +
      `(${renumberCounts.renumber} last carried in PB2025 and say PB2026 renumbered; ` +
      `${renumberCounts.earlier} stopped earlier and say no later edition carries them); ` +
      `${spanChecked} FY spans matched against the page's own decade grid; ` +
      `${stray} stray note(s) outside the tier`,
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// leg o — the coverage note tells the truth about ingestion (ROADMAP #14)
// ═══════════════════════════════════════════════════════════════════════════
//
// THE SPECIES, twice. (1) 2026-07-05: `program-tier.ts` pinned
// INGESTED_SERVICE_ORGS = {A,N,F} by hand, so every defense-wide agency page
// whose FY2026 book WAS loaded said "the {org} J-book is not yet ingested".
// The fix made the set a payload (site_meta.ingested_service_orgs) — and
// added NO gate, so nothing checks the rendered sentence against it. Leg (c)
// accepts EITHER wording on a rollup page regardless of what the payload
// says. (2) 2026-09-10: the honest wording only ever existed on the ROLLUP
// branch. export_site._trajectory_only_feed_programs synthesizes a
// programs.json row for a feed PE with a trajectory and no dim_programs row,
// so 0603115DHA (Medical Development, DHA) and 0708083D (Assembled Chemical
// Weapons Alternatives, A) render as FULL tier and told readers "The J-book
// detail for this line carries no separate mission or description narrative"
// about a line whose budget_line_details count is zero.
//
// What this leg pins, on the BUILT artifact, over the WHOLE page universe
// (no sampling — the negative direction is the half a sample would miss):
//
//   1. POPULATION, both directions. A page renders [data-coverage=
//      "service-books"] iff its own sidecar has no detail row, no narrative
//      and at least one FY2026 workbook row — recomputed here, not trusted
//      from the `tier` field, because tier is exactly what was wrong.
//   2. THE ORG. The note names the page's own coverage org: the sidecar's
//      service_org on the rollup tier, programs.json's `org` on a
//      workbook-only full-tier page (those sidecars carry no service_org).
//   3. THE BRANCH. The wording it picks agrees with the loaded-book set. An
//      org IN the set gets "The {svc} FY2026 J-books are ingested, but this
//      program element carries no R-2/P-40 narrative"; an org OUT of it gets
//      "Detailed justification … lives in the {svc} J-book, which is not yet
//      ingested". Both directions fail. This is the check the 2026-07-05 fix
//      shipped without.
//   4. THE WITHDRAWN SENTENCES. Neither full-tier empty state may appear on
//      a page with no J-book detail behind it.
//   5. THE PAYLOAD ITSELF. An absent or empty site_meta.ingested_service_orgs
//      makes program-tier.ts fall back to its A/N/F default — i.e. restores
//      the 2026-07-05 bug silently. That is a hard failure here.
//   6. THE RECORDED ABSENCES (Task 17c, ROADMAP #111). "Not yet ingested"
//      presupposes a book exists. It was FALSE on 5 pages — the DoD IG
//      published no RDT&E or procurement justification book at all, and DEFW
//      publishes none for its reconciliation / undistributed / roll-up rows —
//      and imprecise on the 14 DHA pages, whose book WAS downloaded and
//      carries no jb-2009 payload. site_meta.org_absences records each case
//      with a rule; a page whose org is in it must state that rule's own
//      sentence, in the description note AND in the justification section,
//      and must not say "not yet ingested" ANYWHERE on the page — the same
//      phrase also renders in the WHAT-IT-IS card tail and in the page's
//      <meta name="description">, two surfaces the 2026-09-12 audit of the
//      note itself did not look at. The payload key must be present for the
//      same reason as check 5: losing it silently restores the false
//      sentence on 19 pages.
//
// NO NUMERIC FLOOR on the note population, deliberately: it SHRINKS as books
// land (73 pages today; 59 if the Defense Health Program book extracts), so a
// floor would fail on success. The non-vacuity anchor is the negative
// direction — the pages with detail that must carry no note — plus check 5,
// which is the condition under which the leg would be reading the wrong set
// entirely.

/** Below this many detail-carrying pages the negative direction is not a
 *  check. Re-measured 2026-09-12 over data/site/json/program_details (2,562
 *  sidecars: 553 decade, 73 workbook-only): 1,936 non-decade sidecars carry a
 *  detail row and/or a narrative — unchanged from the 2026-09-10 reading.
 *  Ingestion only ADDS to this number, so it is safe to hold.
 *  DO NOT LOWER (2026-09-12). */
const MIN_DETAIL_PAGES_CHECKED = 1500;

const SERVICE_BOOKS_ATTR = 'data-coverage="service-books"';
/** The two full-tier empty states, which claim a J-book detail exists. */
const WITHDRAWN_FULL_TIER_SENTENCES = [
  "The J-book detail for this line carries no separate mission",
  "some exhibits carry figures without per-project prose",
];

/**
 * One marker per absence rule: the clause src/lib/program-tier.ts
 * orgAbsenceWording opens BOTH the description note and the justification
 * empty state with. Checking the same marker in the two elements is what
 * binds the two render sites with one literal.
 *
 * Deliberately free of "&" and of any em dash: this is matched against
 * DECODED element text, and "RDT&E" arrives as "RDT&E" or "RDT&amp;E"
 * depending on the parser's entity handling. The sentences themselves keep
 * their full wording; only the marker is narrowed.
 *
 * `fy` is the second argument because two of the three MARKERS name the
 * edition — every absence SENTENCE does, but "no-justification-book-published"
 * is deliberately narrowed to the part that carries no year — and they read it
 * from site_meta.org_absences[...].fy. A year typed here would keep matching a
 * page that had moved on (or stop matching the one that had not), which is a
 * gate agreeing with a literal instead of with the payload the page renders
 * from.
 */
export const ABSENCE_MARKERS = {
  "no-justification-book-published": (svc) =>
    `justification book was published for ${svc}`,
  "summary-line-only": (svc, fy) =>
    `No ${svc}-specific FY${fy} justification book is published`,
  "book-carries-no-embedded-xml": (svc, fy) =>
    `The ${svc} FY${fy} justification book was downloaded`,
};

/**
 * The edition years site_meta.org_absences records, for the markers that name
 * one. Read from the payload rather than typed, for the reason the payload
 * exists. Empty when nothing is probed — which is also when no page can carry
 * an absence wording at all, because program-tier's map is then empty.
 *
 * `payload` is injected by __tests__/coverage-note.test.mjs and defaults to
 * the shipped site_meta.json: leg (c)'s acceptance of an absence note depends
 * on this set, so it is pinned the way leg (o)'s payload checks are rather
 * than left to whatever the build happens to have on disk.
 */
export function absenceFiscalYears(payload) {
  let entries = payload;
  if (entries === undefined) {
    const metaPath = path.join(jsonDir, "site_meta.json");
    if (!fs.existsSync(metaPath)) return [];
    entries = readJson(metaPath).org_absences;
  }
  if (!entries || typeof entries !== "object") return [];
  return [
    ...new Set(
      Object.values(entries)
        .map((e) => e?.fy)
        .filter((fy) => Number.isInteger(fy)),
    ),
  ].sort((a, b) => a - b);
}

/** The wording no page with a recorded absence may carry, anywhere. */
const NOT_YET_INGESTED = "not yet ingested";

/** Recompute of src/lib/program-tier.ts isWorkbookOnlyDetails. */
function isWorkbookOnly(d) {
  return (
    (d.details ?? []).length === 0 &&
    (d.narratives ?? []).length === 0 &&
    (d.budget_lines ?? []).length > 0
  );
}

/** `programs`, `ingestedOrgs` and `pages` are injected by
 *  __tests__/coverage-note.test.mjs, which has to hand the leg corpora the
 *  build does not contain — a check that has never been seen to fail is not
 *  a check. The gate itself passes only `sidecars` and reads the rest off
 *  disk. */
export function runCoverageNoteLeg({
  errors,
  notes,
  sidecars,
  programs,
  ingestedOrgs,
  absences,
  pages,
}) {
  let orgList = ingestedOrgs;
  if (!orgList) {
    const metaPath = path.join(jsonDir, "site_meta.json");
    if (!fs.existsSync(metaPath)) {
      errors.push("program-skeleton(o): data/site/json/site_meta.json missing");
      return;
    }
    orgList = readJson(metaPath).ingested_service_orgs;
  }
  if (!Array.isArray(orgList) || orgList.length === 0) {
    errors.push(
      "program-skeleton(o): site_meta.ingested_service_orgs is absent or empty. " +
        "program-tier.ts then falls back to its hardcoded A/N/F default and every " +
        "defense-wide agency page silently resumes saying 'not yet ingested' about " +
        "a book that IS loaded — the exact 2026-07-05 defect the payload replaced. " +
        "Re-run export-site; do not relax this check",
    );
    return;
  }
  const ingested = new Set(orgList);

  // site_meta.org_absences — {org: {rule, fy, checked_on, checked_url}}. `{}` is
  // legitimate (nothing probed yet); a MISSING key is not, for the same
  // reason as the check above: every org silently drops back to the generic
  // "not yet ingested", which is false for five of them.
  let absenceMap = absences;
  if (absenceMap === undefined) {
    const metaPath = path.join(jsonDir, "site_meta.json");
    absenceMap = fs.existsSync(metaPath)
      ? readJson(metaPath).org_absences
      : undefined;
  }
  if (absenceMap === undefined || absenceMap === null ||
      typeof absenceMap !== "object" || Array.isArray(absenceMap)) {
    errors.push(
      "program-skeleton(o): site_meta.org_absences is absent or not an object. " +
        "Without it every org with no loaded book falls back to 'Detailed " +
        "justification … lives in the {org} J-book, which is not yet ingested' " +
        "— a sentence that presupposes a book exists, and that is false for " +
        "IG and DEFW (no FY2026 book was published at all) and imprecise for " +
        "DHA (downloaded, no embedded payload). Re-run export-site; the " +
        "exporter derives it from data/research/edition_manifest.json",
    );
    return;
  }
  const absenceByOrg = new Map(Object.entries(absenceMap));
  for (const [org, entry] of absenceByOrg) {
    if (!ABSENCE_MARKERS[entry?.rule]) {
      errors.push(
        `program-skeleton(o): site_meta.org_absences["${org}"] carries rule ` +
          `"${entry?.rule}", which this leg (and program-tier.orgAbsenceWording) ` +
          `has no sentence for. The org's pages fall back to "not yet ingested"`,
      );
    }
    // The edition the org's sentences name. Without it the page renders a
    // yearless "FY" — program-tier.setOrgAbsences KEEPS such an entry on
    // purpose (program-tier.ts:153-160); the refusal is at the sentence, in
    // orgAbsenceWording, so an org whose pages are never rendered never
    // reaches it and this check is the only door that sees the record. The
    // leg would also match a marker built from `undefined` against every
    // page it reads.
    if (!Number.isInteger(entry?.fy)) {
      errors.push(
        `program-skeleton(o): site_meta.org_absences["${org}"] carries fy ` +
          `${JSON.stringify(entry?.fy)}. Every absence sentence names the ` +
          `edition (two of the three MARKERS this leg matches carry it), and ` +
          `all of them take the year from this field — re-run export-site; an ` +
          `export made before the fiscal year joined the payload (Group C ` +
          `polish, 2026-09-18) does not write it`,
      );
    }
    if (ingested.has(org)) {
      // The edition comes from the entry, like every other year in this leg:
      // a literal here would name the wrong book at rollover, in the one
      // message a reader opens when the two payloads disagree. When there is
      // no year the check above has already said so, so this message drops
      // the edition rather than printing "FYundefined".
      const edition = Number.isInteger(entry?.fy) ? `FY${entry.fy} ` : "";
      errors.push(
        `program-skeleton(o): "${org}" is in BOTH ingested_service_orgs and ` +
          `org_absences. One says its ${edition}book loaded detail, the other says ` +
          `it has no usable book — the page renders the absence, so a stale ` +
          `absence record would outlive the ingestion that ended it. Re-run the ` +
          `edition probe (jbooks) and export-site`,
      );
    }
  }

  let programRows = programs;
  if (!programRows) {
    const programsPath = path.join(jsonDir, "programs.json");
    if (!fs.existsSync(programsPath)) {
      errors.push("program-skeleton(o): data/site/json/programs.json missing");
      return;
    }
    programRows = readJson(programsPath);
  }
  const orgBySlug = new Map(programRows.map((p) => [p.slug ?? p.pe_bli, p.org]));

  const readHtml = (slug) => {
    if (pages) return pages.get(slug) ?? null;
    const p = pageHtmlPath(slug);
    return fs.existsSync(p) ? fs.readFileSync(p, "utf8") : null;
  };

  let noteCount = 0;
  let detailPagesChecked = 0;
  let stray = 0;
  let missing = 0;
  let badBranch = 0;
  let withdrawn = 0;
  const branchCounts = { ingested: 0, absence: 0, uningested: 0 };
  const byRule = new Map();
  const unprobed = new Map();
  const say = (msg) => {
    if (errors.filter((e) => e.startsWith("program-skeleton(o)")).length < 12) {
      errors.push(msg);
    }
  };

  for (const [slug, d] of sidecars) {
    if (d.tier === "decade") continue; // its own tier, its own wording (leg k)
    const want = isWorkbookOnly(d);
    const html = readHtml(slug);
    if (html === null) {
      if (want) say(`program-skeleton(o): /program/${slug}/ not built`);
      continue;
    }
    const hasNote = html.includes(SERVICE_BOOKS_ATTR);

    // ── 1. the negative direction ─────────────────────────────────────────
    if (!want) {
      detailPagesChecked++;
      if (hasNote) {
        stray++;
        say(
          `program-skeleton(o): /program/${slug}/ carries the service-books ` +
            `coverage note but its sidecar holds ${(d.details ?? []).length} detail ` +
            `row(s) and ${(d.narratives ?? []).length} narrative(s) — the note says ` +
            `this line has no R-2/P-40 detail, and it does`,
        );
      }
      continue;
    }

    // ── 1. the positive direction ─────────────────────────────────────────
    if (!hasNote) {
      missing++;
      say(
        `program-skeleton(o): /program/${slug}/ has no R-2/P-40 detail (0 detail ` +
          `rows, 0 narratives, ${(d.budget_lines ?? []).length} workbook row(s)) but ` +
          `renders no [data-coverage="service-books"] note. A full-tier page in this ` +
          `state renders the full-tier empty state instead, which asserts a J-book ` +
          `detail that does not exist — ROADMAP #14, the 0603115DHA/0708083D defect`,
      );
      continue;
    }
    noteCount++;

    // ── 4. neither withdrawn full-tier sentence may appear ────────────────
    for (const sentence of WITHDRAWN_FULL_TIER_SENTENCES) {
      if (html.includes(sentence)) {
        withdrawn++;
        say(
          `program-skeleton(o): /program/${slug}/ has no J-book detail yet states ` +
            `"${sentence}…" — that sentence claims a detail record behind the page`,
        );
      }
    }

    // ── 2/3. the org and the branch ───────────────────────────────────────
    const org =
      d.tier === "rollup" ? (d.service_org ?? "") : (orgBySlug.get(slug) ?? "");
    const svc = serviceName(org);
    const root = parse(html, { comment: false });
    const note = root.querySelector(`[data-coverage="service-books"]`);
    const text = (note?.text ?? "").replace(/\s+/g, " ").trim();

    // ── 6. a RECORDED absence states its own case, on both surfaces ───────
    const absence = absenceByOrg.get(org);
    if (absence) {
      branchCounts.absence++;
      const key = `${org} ${absence.rule}`;
      byRule.set(key, (byRule.get(key) ?? 0) + 1);
      const marker = ABSENCE_MARKERS[absence.rule]?.(svc, absence.fy);
      if (!marker) continue; // already reported against the payload
      if (!text.includes(marker)) {
        badBranch++;
        say(
          `program-skeleton(o): /program/${slug}/ — "${org}" has a recorded ` +
            `absence (${absence.rule}) but its coverage note does not state it ` +
            `(expected to contain "${marker}", got: "${text.slice(0, 120)}")`,
        );
      }
      if (html.includes(NOT_YET_INGESTED)) {
        badBranch++;
        say(
          `program-skeleton(o): /program/${slug}/ says "${NOT_YET_INGESTED}" ` +
            `while "${org}" has a recorded absence (${absence.rule}). That ` +
            `wording presupposes a book exists and is merely awaiting work. ` +
            `Check the WHAT-IT-IS card tail and <meta name="description"> too — ` +
            `both render the same phrase from the same decision`,
        );
      }
      const just = root.querySelector('[data-section="justification"]');
      const justText = (just?.text ?? "").replace(/\s+/g, " ").trim();
      if (!justText.includes(marker)) {
        badBranch++;
        say(
          `program-skeleton(o): /program/${slug}/ states the ${absence.rule} ` +
            `absence in its description note but not in its justification ` +
            `section (expected to contain "${marker}", got: ` +
            `"${justText.slice(0, 120)}")`,
        );
      }
      continue;
    }

    const saysUningested = text.includes(`lives in the ${svc} J-book`);
    const saysIngested =
      text.includes(`The ${svc} FY2026 J-book`) &&
      text.includes("no R-2/P-40 narrative");
    if (!saysUningested && !saysIngested) {
      badBranch++;
      say(
        `program-skeleton(o): /program/${slug}/ note does not name the ${svc} ` +
          `J-book in either honest wording (org "${org}", got: "${text.slice(0, 120)}")`,
      );
      continue;
    }
    if (ingested.has(org)) {
      branchCounts.ingested++;
      if (saysUningested) {
        badBranch++;
        say(
          `program-skeleton(o): /program/${slug}/ says the ${svc} J-book is "not yet ` +
            `ingested", but "${org}" IS in the loaded set — the 2026-07-05 species. ` +
            `The set is site_meta.ingested_service_orgs, derived from the FY2026 ` +
            `documents with extracted detail`,
        );
      }
    } else {
      branchCounts.uningested++;
      if (org) unprobed.set(org, (unprobed.get(org) ?? 0) + 1);
      if (saysIngested) {
        badBranch++;
        say(
          `program-skeleton(o): /program/${slug}/ says the ${svc} FY2026 J-book "is ` +
            `ingested", but "${org}" is NOT in the loaded set. A registered or ` +
            `downloaded file is not a loaded narrative — this is what happens when ` +
            `a book is acquired and nothing extracts`,
        );
      }
    }
  }

  if (detailPagesChecked < MIN_DETAIL_PAGES_CHECKED) {
    errors.push(
      `program-skeleton(o): only ${detailPagesChecked} page(s) with detail were ` +
        `checked for a stray coverage note (floor ${MIN_DETAIL_PAGES_CHECKED}, ` +
        `measured 2026-09-12 at 1,936). Below the floor the negative direction has ` +
        `nothing to read and the leg would pass on a build that renders the note ` +
        `everywhere. Re-measure the population; do not lower the floor`,
    );
  }
  notes.push(
    `leg o: ${noteCount} page(s) render the service-books note ` +
      `(${branchCounts.ingested} on a loaded book, ${branchCounts.absence} on a ` +
      `recorded absence, ${branchCounts.uningested} still "not yet ingested"), ` +
      `over ${ingested.size} loaded org code(s) and ${absenceByOrg.size} ` +
      `recorded absence(s); ${detailPagesChecked} page(s) with detail carry none` +
      (stray + missing + badBranch + withdrawn === 0
        ? " ✓"
        : ` — ${missing} missing, ${stray} stray, ${badBranch} wrong-branch, ` +
          `${withdrawn} withdrawn sentence(s)`),
  );
  // The breakdown chain C reads to confirm which page got which sentence.
  // Named orgs still on the generic wording are listed rather than failed:
  // an org whose book is downloaded and unprobed is exactly what that
  // wording is for. An org that should have been probed shows up here as a
  // name, not as a silence.
  notes.push(
    `leg o branches: ` +
      ([...byRule.entries()]
        .sort()
        .map(([k, n]) => `${k} ${n}`)
        .join("; ") || "no recorded absence on any page") +
      (unprobed.size
        ? ` | unprobed: ${[...unprobed.entries()].sort().map(([o, n]) => `${o} ${n}`).join(", ")}`
        : "") +
      (branchCounts.uningested - [...unprobed.values()].reduce((a, b) => a + b, 0)
        ? ` | ${branchCounts.uningested - [...unprobed.values()].reduce((a, b) => a + b, 0)} with no org code`
        : ""),
  );
}
