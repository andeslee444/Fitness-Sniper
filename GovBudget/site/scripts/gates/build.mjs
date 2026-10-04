/**
 * gate 1 — build_gate (mechanical checks on out/)
 *
 * Checks:
 * - program pages == programs.json count (data-driven: dim_programs +
 *   trajectory-only feed programs)
 * - agency pages == distinct orgs from agencies.json
 * - company pages == 200 (entities_top.json count)
 * - core pages present (/, /programs, /companies, /data, /flow, /downloads, /methodology, /glossary, /about)
 * - out/pagefind/pagefind.js exists
 * - sitemap URL count == emitted pages AND every URL starts with SITE_URL origin
 * - robots.txt present
 * - llms.txt contains /methodology/, /downloads/, ≥1 /program/ URL
 * - placeholder-origin scan (backlog #18): sitemap.xml / llms.txt /
 *   robots.txt / index.html must NOT contain govbudget-placeholder.example —
 *   UNCONDITIONAL (env-independent), unlike the sitemap-origin leg below
 *   which compares against the verify-time NEXT_PUBLIC_SITE_URL and would
 *   false-pass a placeholder build verified without the env
 * - citations.json key count == manifest citation total (from site_meta.json, data-driven)
 * - download cards: citations.parquet href == /citations/citations.parquet (not /data/)
 * - stale-literal check: built downloads page must NOT contain hardcoded "44,754"
 * - fact-permalink route (PM Sprint 1 Task 5, §P0-4): out/vercel.json exists
 *   AND carries the `/fact/:id` → `/fact/` rewrite AND out/fact/index.html
 *   exists — the deploy can never ship footnote permalinks that 404
 * - fonts leg (2026-09-12, the type system): every url(/fonts/…) in the built
 *   CSS resolves to a file under out/fonts/ whose SHA-256 and byte count match
 *   the PROVENANCE.md beside it; every .woff2 under out/fonts/ is referenced by
 *   some @font-face (no dead assets — Barlow shipped unreferenced for days);
 *   out/vercel.json carries the immutable Cache-Control header for /fonts/;
 *   and both preload hrefs in out/index.html exist. The CDN-state half (a
 *   re-vendor at the same path serving stale bytes for a year) is why the path
 *   carries a version directory — this leg cannot see the CDN.
 * - (f1) fact-permalink trailing slash (ROADMAP #61, Sprint C Task C2):
 *   out/vercel.json ALSO carries the `/fact/:id/` → `/fact/` rewrite — the
 *   unslashed form alone left /fact/{id}/ 404ing, the one form external
 *   citations (CMSes, link-checkers) normalize onto. Config-shape only; see
 *   the leg's own comment for what it does and does not prove
 * - page-weight budget (PM Sprint 3 §P2-1): per-page raw AND gzip ceilings
 *   over the singleton pages and the heaviest instance of each templated
 *   class — see PAGE_WEIGHT_BUDGET below for why it is per-page and not a
 *   total over out/
 * - shard-only citations (R-DEC-GATE-SHARDS, 2026-09-26): every built
 *   /company/{slug}/ and /district/{code}/ page (and /district/) ships an EMPTY
 *   embedded citations object — in index.html's RSC flight payload and in
 *   every RSC .txt payload beside it — so the weight fix (Task 28b; decisions
 *   fix round 5 for company pages) cannot regress silently under the
 *   ceilings. See shard-only-citations.mjs
 */

import fs from "fs";
import path from "path";
import zlib from "zlib";
import { createHash } from "crypto";
import { fileURLToPath } from "url";
import { runShardOnlyCitationsLeg } from "./shard-only-citations.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, "..", "..");
const outDir = path.resolve(siteRoot, "out");
const dataDir = path.resolve(siteRoot, "..", "data", "site");
const jsonDir = path.resolve(dataDir, "json");

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function fileExists(p) {
  return fs.existsSync(p) && fs.statSync(p).isFile();
}

function dirExists(p) {
  return fs.existsSync(p) && fs.statSync(p).isDirectory();
}

// ── Page-weight budget (PM-review Sprint 3 §P2-1) ───────────────────────────
//
// WHY THIS EXISTS. The PM review found the index pages shipping multi-megabyte
// documents. Measured at the start of Sprint 3, /programs/ was 5,875,345 bytes
// (442,874 gzipped) with all 1,741 rows inline — and it had GROWN, because
// Sprint 2's filter/sort/CSV work added markup nobody weighed. Weight is the
// kind of regression that arrives one honest feature at a time and is never
// anybody's bug, so it gets a number and a gate like every other claim here.
//
// WHAT IT PINS. A ceiling per PAGE, never a total over out/ — the corpus grows
// (1,993 program pages today, more with each service book) and a total-bytes
// budget would fail on growth rather than on weight. The templated classes are
// covered by their HEAVIEST built instance, so the whole fleet is measured
// without pretending a fixed instance stays the fattest.
//
// Ceilings sit a few percent above what the Sprint 3 build actually achieves
// (recorded in each entry) — close enough to catch a regression, loose enough
// that ordinary data movement does not trip it. RAISING one is a deliberate
// act that has to be justified in the same breath as the change that needs it.
//
// gzip is measured with zlib level 9 — the transfer size a reader pays. Raw is
// the parse/DOM cost, which is what actually hurts a phone, so both are pinned.
//
// WHERE THE BYTES ACTUALLY GO, on the two tightest pages (measured
// 2026-08-28 with this file's own weigh()/resolveBudgetTarget, so the next
// person does not repeat the search):
//
//   /data/               92,468 raw / 13,172 gzip — 328 bytes of headroom.
//                        49,326 raw of it is the RSC flight payload, which
//                        costs 6,635 gzip: HALF the page is Next's second
//                        copy of the same server tree, and it is what makes
//                        the page hydrate. The other half is prose plus one
//                        16-row inventory table.
//   /companies/families/ 223,384 / 25,502 — 498 bytes of headroom. 141,423
//                        raw / ~14,548 gzip is the flight payload; 21,023 of
//                        that is the embedded citation slice.
//
// Four candidates were measured and REJECTED, each for a stated reason:
//   · Empty the citation slice, as /programs/, /feed/, /years/ and /flow/ all
//     do. Would save ~2 KB gzip — but those pages have no derived-input
//     drill-down, and this one does: all 29 rows are `derived`, the panel's
//     hasCitation() is synchronous, and /companies/families/ promises in
//     prose that a reader can "drill into each member". Emptying the slice
//     silently makes those chips unclickable. That is trimming disclosure.
//   · Drop `description` from the <Explorer> props on /data/ (the 16 scope
//     sentences, already in the inventory table above it). Measured at 3,534
//     raw / 194 gzip — and the explorer renders the selected dataset's scope
//     under its picker, so this removes disclosure for 194 bytes.
//   · Drop data-external-source / data-source-form on /companies/families/
//     (1,998 + 593 raw, duplicating the anchor's own href and text). They are
//     the hooks gate 3's mobile leg and gate 24 read. Removing them weakens
//     two gates.
//   · Drop role="cell"/role="row" from the mobile-card tables. The rows are
//     `display:block` below sm, which drops the implicit table semantics —
//     the roles are what restores them.
//
// So: nothing honest was removed. The finding is that these two pages are
// small documents whose weight is mostly framework duplication, not payload
// anyone chose. The next real change here needs a justified raise, not a
// hunt for slack that is not there.
export const PAGE_WEIGHT_BUDGET = [
  // Singleton pages. Measurements below are refreshed as pages change.
  // Re-baselined 2026-08-21 (Sprint E). The key split gives each
  // (account, pe_bli) pair its own row: 10 legitimate new programs worth
  // $5.35B — LPD Flight II $2.60B, Medium Landing Ship $1.96B — plus
  // corrected figures on the six rows that were previously publishing a
  // fused total. 277,357 -> 279,513 gzip.
  //
  // NOTE THE HEADROOM, not just the number. This entry's gzip ceiling was
  // set at 278,000 against a 261,871 measurement — 6.2% headroom — and
  // ordinary corpus growth ate it down to 0.23% (643 bytes) without anyone
  // noticing, which is why ten new rows breached it instantly. Restoring
  // 6.2% rather than the 0.23% that had drifted in: re-baselining to the
  // CURRENT proportional headroom would hand the next change the same
  // cliff. Gate 1's near-ceiling note (added 2026-08-14) is what stops
  // this recurring silently.
  //
  // RE-BASELINED 2026-08-29 (tri-persona Wave 5) — CEILINGS RAISED, AND THE
  // CHANGE THAT NEEDS THEM IS THIS ONE. Wave 5 parsed the five FY2026 Navy
  // procurement appropriations the pipeline had been discarding (APN, PMC,
  // WPN, SCN, PANMC — six masters where a filename rule had kept one), and
  // programs.json went from 1,755 entries to 1,938. This page is the index
  // of every one of them, so it grew by construction: 2,686,677 / 281,116 ->
  // 2,962,701 / 311,339, breaching both ceilings.
  //
  // Nothing was trimmed to fit and nothing should be: 183 more rows on the
  // program index is the entire point of the ingestion. Same ~6% headroom
  // rule the Sprint E entry above established (re-baselining to the CURRENT
  // proportional headroom hands the next change the same cliff): 3,150,000
  // is 6.32% over the raw measurement, 330,000 is 7.05% over the gzip one.
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 2,962,743 / 308,292 -> 2,968,731 / 310,063. CEILINGS UNCHANGED;
  // 181,269 raw / 19,937 gzip left.
  { label: "/programs/", file: "programs/index.html", maxRaw: 3_150_000, maxGzip: 330_000, measured: "2,968,731 / 310,063" },
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 33,170 / 6,685 -> 37,390 / 7,708. CEILINGS UNCHANGED;
  // 7,610 raw / 1,292 gzip left.
  // RE-MEASURED 2026-10-04 (final-review fixes, T4: the procurement
  // tooltip and edition-legend sentence render in the client island, so only
  // chunk hashes move in this HTML; build of ea1c4071 on the S5 proof export
  // with datasets.json's two fixed scopes; gate 1's weigh(), zlib level 9):
  // 37,390 / 7,708 -> 37,362 / 7,668. CEILINGS UNCHANGED; 7,638 raw / 1,332
  // gzip left.
  { label: "/years/", file: "years/index.html", maxRaw: 45_000, maxGzip: 9_000, measured: "37,362 / 7,668" },
  // Re-baselined 2026-09-01 (FPDS-AP expansion): the crosswalked-PE universe
  // grew 24 → ~186 and the feed derives from it — cards 160 → ~720. Corpus
  // growth, not template bloat (the per-card markup is unchanged). Ceilings
  // follow the ~6% convention over the expansion build's measure. A 4MB raw
  // feed is at the edge of reasonable — pagination is filed as follow-up,
  // and this ceiling must NOT be raised again without it.
  // 2026-09-02: the do-not-raise-again note above is honored — the feed page
  // is now a per-section digest (cap 75 — since #88 published by the
  // exporter as feed.json `section_cap`, read by feed/page.tsx; full set in
  // feed.json + RSS/Atom) and the ceiling comes DOWN. Provisional
  // ceilings from the expected ≤300-card page; `measured` is updated from
  // the first capped build.
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 1,283,116 / 68,688 -> 1,283,380 / 74,272. CEILINGS UNCHANGED;
  // 1,916,620 raw / 75,728 gzip left.
  { label: "/feed/", file: "feed/index.html", maxRaw: 3_200_000, maxGzip: 150_000, measured: "1,283,380 / 74,272" },
  // RE-BASELINED 2026-08-29 (tri-persona Wave 5) — CEILINGS RAISED, SAME
  // CHANGE. 1,260,784 / 80,771 -> 1,389,568 / 89,557, breaching both.
  //
  // Where the bytes are, measured rather than assumed: 1,341,090 of the
  // page's 1,389,357 raw bytes are inline <script>, and 1,239,952 of those
  // are one RSC flight chunk carrying the page's citation slice — 1,802
  // citations, whose first entry on this build is Virginia Class Submarine's
  // 10,656.927. The homepage cites its hero, its movers and its agency grid,
  // and every one of those slices is drawn from the corpus Wave 5 grew. The
  // page renders 17 program links; the weight is disclosure payload, not
  // markup, and there is nothing to trim that would not remove a citation.
  //
  // ~6% headroom against the new measurement: 1,475,000 is 6.16% over raw,
  // 95,000 is 7.88% over gzip.
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 1,389,234 / 88,003 -> 1,379,988 / 89,021. CEILINGS UNCHANGED;
  // 95,012 raw / 5,979 gzip left.
  // RE-MEASURED 2026-10-04 (final-review fixes, T1: the trust anchor claims
  // a tier only for datasets that hold amounts; build of ea1c4071 on the S5
  // proof export with datasets.json's two fixed scopes; gate 1's weigh(),
  // zlib level 9): 1,379,988 / 89,021 -> 1,379,989 / 89,162. CEILINGS
  // UNCHANGED; 95,011 raw / 5,838 gzip left.
  { label: "/", file: "index.html", maxRaw: 1_475_000, maxGzip: 95_000, measured: "1,379,989 / 89,162" },
  // RE-MEASURED 2026-09-18 (chain D): 684,005 / 67,188 -> 692,931 / 68,099.
  // The drift leg caught this one: the stale entry claimed 1,812 gzip bytes
  // of headroom where 901 were left. CEILINGS UNCHANGED; nothing trimmed.
  // RE-MEASURED 2026-09-25 (chain C run 4, build of 118228f8): 692,931 /
  // 68,099 -> 700,649 / 68,999. Chain C run 3 measured 68,572 on 2026-09-24,
  // before Task 29's reviewed family labels and the 2026-09-06 FY2026 refresh
  // reached this page; this build carries both. The drift leg caught it (the
  // stale entry claimed 901 gzip left). CEILINGS UNCHANGED, and ONE BYTE of
  // gzip headroom is left: swapping 2,000 random build ids into this build's
  // HTML weighed 68,991-69,002, so Next's random build id alone can push it
  // over. The next sentence, label or row added here needs a trim of its own
  // or an owner-ruled raise argued in the same breath — a chain may not
  // raise it.
  // RE-MEASURED 2026-09-25 (chain E, build of 594d1f0c): 700,649 / 68,999 ->
  // 700,393 / 68,855, the Task 26 fix wave's shorter /companies/ prose. 145
  // gzip left; the drift leg now fires at about 68,928. CEILINGS UNCHANGED.
  // R-INT-1 (integration ruling 2026-09-25, the controller under the owner's
  // delegation): max of the two reviewed branches — this branch 6c3c07e1
  // 710,000 / 69,000, live 81929a6b 740,000 / 73,500 (its 2026-09-12 type
  // system: two font preloads, t-* class names and data-prose attributes on
  // every page, measured there at +265…+370 gzip a page); production already
  // serves these pages under the live ceiling; any merged page above it is
  // trimmed, never raised. The `measured` stamp is still this branch's
  // (chain E): re-measure it on the first merged build, never from an
  // estimate.
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 700,393 / 68,855 -> 704,789 / 70,217. CEILINGS UNCHANGED;
  // 35,211 raw / 3,283 gzip left.
  { label: "/companies/", file: "companies/index.html", maxRaw: 740_000, maxGzip: 73_500, measured: "704,789 / 70,217" },
  // New page from codex/f15-family-browser (merged 2026-09-25), entry and
  // ceilings exactly as that branch set them. A six-record aircraft register
  // with its sourced inspection topics and the cited funding-year matrix;
  // the wider research desk, the model engine and the older annual receipts
  // load separately on demand. That branch stamped 713,183 / 69,954 (its
  // 55c36484 build); its production build (81929a6b, deployed 2026-09-24)
  // weighs 701,244 / 67,746 with this file's own weigh(). The merged build
  // renders this page from this branch's data/site and must be re-measured.
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 713,183 / 69,954 -> 701,316 / 67,757. CEILINGS UNCHANGED;
  // 23,684 raw / 2,243 gzip left. The old stamp was the live branch's (its
  // 55c36484 build); this is the first measurement of the merged page.
  // RE-MEASURED 2026-10-04 (families piece 1, S5: the F015E0 label, its
  // cited Lot 1 note and two coverage notes; build of 937e6c84 plus the
  // S5 working tree on the S5 proof export, this file's own weigh() —
  // zlib level 9): 701,316 / 67,757 -> 703,427 / 68,538. CEILINGS UNCHANGED;
  // 21,573 raw / 1,462 gzip left.
  { label: "/families/f-15/", file: "families/f-15/index.html", maxRaw: 725_000, maxGzip: 70_000, measured: "703,427 / 68,538" },
  // New page, ROADMAP #29(c) — the lineage identity map. 32 family diagrams
  // (80 identity boxes, 49 stated ribbons), 3 candidate diagrams, and two
  // table views totalling 86 identity rows and 52 link rows. The weight is
  // overwhelmingly the RSC flight payload: the whole lineage_flow.json
  // payload (33,649 bytes on disk) crosses the server→client boundary as
  // props, because the diagram is an island that opens the citation panel
  // from a ribbon.
  //
  // Same ~8% headroom convention as the other new-page entries (/agency/,
  // /district/, /companies/families/) rather than a round-number guess:
  // 340,000 against 315,463 is 7.78% raw; 36,000 against 33,369 is 7.89%
  // gzip. Measured with this file's OWN weigh() — zlib level 9 — on the
  // 2026-08-28 build, and on a build run WITH NEXT_PUBLIC_SITE_URL set: an
  // earlier measuring pass without it wrote the placeholder origin into 16
  // hrefs and read 176 raw / 37 gzip bytes light. Three agents have got a
  // page-weight annotation wrong by measuring with a different tool; this
  // one imports the gate's and states which build it read.
  //
  // RAISED 2026-08-31 (ROADMAP #29(a) — LLM lineage extraction). The page
  // draws the whole corpus, and the corpus doubled: stated edges 49 -> 98,
  // families 32 -> 52, identities 86 -> 154. 539,883 / 50,438 against the
  // 340,000 / 36,000 above. This is the change the page exists to show, so
  // the ceiling follows it, at the same ~8% convention: 585,000 is 8.36%
  // over raw, 54,500 is 8.05% over gzip.
  //
  // TRIMMING WAS TRIED FIRST AND MEASURED, so nobody repeats the experiment.
  // Two candidates dominate the markup — the `font-family` attribute repeated
  // verbatim on 154 text elements (9,394 bytes) and the 444-character
  // Fact-ID chip class repeated on 98 edges (43,414 bytes; the chip's weight
  // is already filed as backlog #43 and is a shared component, out of scope
  // here). Removing BOTH, measured with this file's own weigh():
  //     baseline           539,883 / 50,438
  //     minus font-family  530,489 / 50,223   (-9,394 raw, -215 gzip)
  //     minus chip class   496,469 / 49,957   (-43,414 raw, -481 gzip)
  //     both               487,075 / 49,739   (-52,808 raw, -699 gzip)
  // 52,808 raw bytes buy 699 gzip bytes — 1.4% — because repeated identical
  // strings are exactly what gzip already collapses. The gzip weight is
  // DISTINCT content: 98 evidence sentences, 154 identity labels, 101 edge
  // descriptions, none of which repeat. No amount of markup tidying reaches
  // 36,000, and removing a citation to fit a ceiling is not on the table.
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 540,425 / 50,611 -> 536,194 / 50,898. CEILINGS UNCHANGED;
  // 48,806 raw / 3,602 gzip left.
  { label: "/lineage/", file: "lineage/index.html", maxRaw: 585_000, maxGzip: 54_500, measured: "536,194 / 50,898" },
  // Re-baselined 2026-09-01 (FPDS-AP expansion): district universe 41 → 181
  // pages and the index states them all. Same corpus-growth rationale as
  // /feed/ above; ~6% convention over the expansion build's measure.
  // Re-measured again 2026-09-02: announcement-verified links (wave 1) took
  // districts 181 → 204; the index states them all. ~6% over the measure.
  // 2026-09-03: districts 204 → 225 with wave-2 links; ~6% over the measure.
  // RE-MEASURED 2026-09-18 (chain D): 515,448 / 48,126 -> 359,669 / 36,072.
  // The page got SMALLER, by a lot, so the drift leg (which only fires on an
  // overstated headroom) stayed quiet and the entry went on claiming a
  // weight the page has not carried since Group C/D. All 153 district rows
  // and 612 cells are still rendered — the shrink is payload, not content.
  // RE-MEASURED 2026-09-25 (chain C run 4, stamped below): 359,669 / 36,072
  // -> 279,612 / 30,367 (run 3 first read 279,590 / 30,342). Smaller again
  // although the index went from 153 district rows to 189: Task 28b stopped
  // embedding a citation slice in the page (the built index carries
  // citations={}, per run 4's static check), which outweighs the 36 added
  // rows. The ceiling now sits ~95% raw / ~68% gzip over the measure; it is
  // left there because this wave rewrites the index's link-mechanism
  // sentence — re-base it once a build has weighed that (backlog #145).
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 279,413 / 30,232 -> 286,293 / 31,407. CEILINGS UNCHANGED;
  // 259,707 raw / 19,593 gzip left.
  { label: "/district/", file: "district/index.html", maxRaw: 546_000, maxGzip: 51_000, measured: "286,293 / 31,407" },
  // Re-baselined 2026-09-01: grew +2,319 raw since the ceiling was set via
  // ordinary curated-events/table growth (#10 relabel note, adjudication
  // tier changes), tipping a 159-byte breach. ~6% convention.
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 227,973 / 27,082 -> 202,880 / 27,290. CEILINGS UNCHANGED;
  // 36,820 raw / 610 gzip left. The gate-fix wave moved this table's per-row
  // utility classes into a page-local CSS module (families.module.css).
  // RE-MEASURED 2026-09-26 (decisions chain G, BUILD 1 of 0176fa6e, built
  // 2026-09-26T16:51:29Z; gate 1's own weigh()): 202,880 / 27,290 ->
  // 203,889 / 27,678. CEILINGS UNCHANGED; 35,811 raw / 222 gzip left. The
  // drift leg fired at 2.7x (+388 gzip over the integration stamp, on chain
  // G's lake and export). Any further growth here needs a trim, not a raise.
  { label: "/companies/families/", file: "companies/families/index.html", maxRaw: 239_700, maxGzip: 27_900, measured: "203,889 / 27,678" },
  // RE-BASELINED 2026-08-29 (tri-persona Wave 5) — CEILINGS RAISED, SAME
  // CHANGE. 93,911 / 13,340 -> 94,741 / 13,619, and the gate's own run on the
  // pre-fix build read 13,657 against a 13,500 ceiling — over by 157, with 259
  // bytes of raw headroom left, which is the same cliff rather than a pass.
  // This page renders the dataset inventory, and Wave 5 moved it:
  // jbook_details went from 21,028 rows to 21,993 and gained an `account`
  // column (the appropriation each detail figure was filed under — without
  // it, summing that table by pe_bli adds ten pairs of unrelated Navy
  // programs together), and its scope sentence now says so.
  //
  // ~6% headroom against the new measurement: 101,000 is 6.34% over raw,
  // 14,450 is 6.02% over gzip.
  // R-INT-1 (integration ruling 2026-09-25, the controller under the owner's
  // delegation): max of the two reviewed branches — this branch 6c3c07e1
  // 101,000 / 14,450, live 81929a6b 105,000 / 15,600 (the same type-system
  // re-baseline as /companies/); production already serves these pages under
  // the live ceiling; any merged page above it is trimmed, never raised. The
  // `measured` stamp below is still this branch's: re-measure it on the first
  // merged build.
  // RE-MEASURED 2026-09-18 (chain D): 94,830 / 13,678 -> 96,649 / 14,272.
  // Also caught by the drift leg (claimed 772 gzip left, 178 remain).
  // CEILINGS UNCHANGED. 178 bytes is thin — the next sentence added to the
  // dataset inventory needs a trim of its own, not a raise.
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 96,652 / 14,278 -> 101,038 / 15,314. CEILINGS UNCHANGED; 3,962
  // raw / 286 gzip left. 286 gzip bytes left: the next sentence added here
  // needs a trim of its own, not a raise.
  // RE-MEASURED 2026-09-26 (decisions chain G final re-run, BUILD 1 of
  // 93a4a061, built 2026-09-27T02:37:28Z; gate 1's own weigh()): 101,038 /
  // 15,314 -> 101,707 / 15,559. CEILINGS UNCHANGED; 3,293 raw / 41 gzip left.
  // The drift leg fired at 7.0x (+245 gzip: the final review's fct_influence
  // and dim_geography descriptions, R-DEC-LDATOTAL). 41 gzip bytes left: any
  // further text here needs a trim first, never a raise.
  // FAMILIES PIECE 1 (2026-10-03, Task 19 Part A): the inventory rows'
  // utility strings moved into src/app/data/data.module.css (the
  // coverage.module.css move). p1_era_line_map adds a 17th inventory row and
  // Explorer option, and one row weighs more than the 42 gzip bytes this
  // page had left (live 2026-10-01: 101,696 / 15,558). Production-origin
  // builds against the 2026-10-02 export: 101,696 / 15,557 -> 81,748 /
  // 13,515 (-19,948 raw / -2,042 gzip); scripts/computed-style-snapshot.mjs
  // found 0 computed-style differences (390/1440, light/dark, screen/print,
  // row hover). The new row (simulated +381 to +605 gzip by scope length)
  // ships with the map; Task 21's S4 build re-measures it. The per-edition
  // era table does not render here: as built it weighed +3,647 gzip on this
  // page even after the hoist. CEILINGS UNCHANGED. RE-MEASURED 2026-10-03
  // (Task 19 Part A build of 5e317a38 plus the Part A edits, built
  // 2026-10-03T17:29:32Z, before the map ships; gate 1's own weigh()):
  // 81,748 / 13,515; 23,252 raw / 2,085 gzip left.
  // RE-MEASURED 2026-10-04 (Task 21, the S4 proof build of 45281589 on
  // the S4 export, with the p1_era_line_map row; gate 1's weigh(), zlib level
  // 9): 81,748 / 13,515 -> 84,798 / 14,401. CEILINGS UNCHANGED; 20,202
  // raw / 1,199 gzip left.
  // RE-MEASURED 2026-10-04 (final-review fixes, T3/T5: the longer
  // budget_lines_decade and p1_era_line_map scopes, each rendered three times
  // here; build of ea1c4071 on the S5 proof export with datasets.json's two
  // fixed scopes; gate 1's weigh(), zlib level 9): 84,798 / 14,401 -> 85,358
  // / 14,530. CEILINGS UNCHANGED; 19,642 raw / 1,070 gzip left.
  { label: "/data/", file: "data/index.html", maxRaw: 105_000, maxGzip: 15_600, measured: "85,358 / 14,530" },
  // New page, Sprint C Task C3 (ROADMAP #62) — the /agency/ index (23 rows,
  // two <Cite> figures each). Same ~8% headroom convention as the other
  // section indexes above (/district/, /companies/families/) rather than a
  // round-number guess.
  //
  // RE-MEASURED 2026-08-29 (tri-persona Wave 3). CEILING UNCHANGED. The 24
  // rows carry their components' NAMES now, not bare acronyms ("TJS" was 21
  // of 24 cards on this list and the <h1> of the page each one links to), and
  // longer strings on an index page cost real bytes: 180,412 -> 184,181 raw.
  // An earlier draft ALSO gave each row a workbook-code chip and landed at
  // 189,750 of 190,000 — 250 bytes, 99.9%, the same cliff /coverage/ hit at
  // nine and /programs/ at 643. The chip came off this page instead of the
  // ceiling coming up (every row's href and title already carry the code, and
  // the destination states it outright). 5,819 raw bytes of room now, and the
  // recorded pair says so: the drift leg below reads THIS string, and the old
  // one would have promised 9,588.
  //
  // RE-BASELINED 2026-08-29 (tri-persona Wave 5) — CEILINGS RAISED, SAME
  // CHANGE. 185,075 / 47,214 -> 192,318 / 52,220, breaching both.
  //
  // AND THE PAGE'S PROSE GOT SHORTER, so the growth is worth naming exactly.
  // Every agency total on this index is a DERIVED sum and cites its inputs.
  // Wave 5 gave the Navy 183 more programs, and the two Navy derived facts'
  // input lists grew with them: the FY2024 and FY2026 citations for org N
  // are 12,887 and 12,154 bytes of JSON on this build (11,180 and 10,520
  // input ids), and the whole slice this page carries is 102,551 bytes. That
  // is the derivation a reader clicks a total to see. Shrinking it means
  // publishing a sum whose inputs are not listed.
  //
  // The §P0-6 note above this table was rewritten SHORTER in the same wave
  // (the ranking is no longer uneven — N 97.0%, F 99.0%, A 99.5% of their
  // workbook totals), so none of this growth is prose.
  //
  // ~6% headroom against the new measurement: 204,000 is 6.13% over raw,
  // 53,700 is 6.12% over gzip. (A first pass set the gzip pair from a
  // measurement taken with Python's zlib.compress instead of the gate's
  // zlib.gzipSync — 52,220 against the gate's own 50,601 — and would have
  // banked 9.5% of unearned headroom. This file has now recorded three
  // agents mis-measuring this table with the wrong tool; the numbers above
  // are the gate's, read by importing PAGE_WEIGHT_BUDGET and calling its
  // weigh().)
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 192,370 / 50,631 -> 90,611 / 13,767. CEILINGS UNCHANGED;
  // 113,389 raw / 39,933 gzip left.
  { label: "/agency/", file: "agency/index.html", maxRaw: 204_000, maxGzip: 53_700, measured: "90,611 / 13,767" },
  // Re-baselined 2026-08-08 (Sprint A′). The 2026-08-08 corrections table added
  // ~16.3 KB raw / ~4.1 KB gzip: six was/now rows recording the figures this
  // sprint moved (district $8.01B→$5.58B, mentions 34,538→10,447, the /programs/
  // denominator, stated lineage edges 31→29, the FY2026 reconciliation split,
  // and the R-1 basis chip). The page is heavier because it now documents six
  // corrections — that is this page's job, and trimming the disclosure to fit a
  // budget would be the wrong trade. Ceilings carry the SAME proportional
  // headroom the previous pair did (raw ×1.1215, gzip ×1.0986), so the budget
  // still catches unintended growth from here.
  //
  // Re-baselined 2026-08-24 (ROADMAP #69) — CEILING RAISED, STATED PLAINLY.
  // The 2026-08-08 pair above was set against 125,112 / 33,863. By this
  // build the page had drifted to 127,800 / 34,494 WITHOUT the #69 row:
  // SIX bytes of gzip headroom (0.017%), the identical cliff /coverage/ hit
  // at nine bytes and /programs/ at 643. The near-ceiling note added
  // 2026-08-14 is doing its job — this page has been reported at 99.9% —
  // but a note is not a re-baseline, and any addition at all now fails.
  //
  // #69's seventh corrections row costs 853 raw / 267 gzip. The 2026-08-08
  // entry's own rule applies unchanged: "The page is heavier because it now
  // documents six corrections — that is this page's job, and trimming the
  // disclosure to fit a budget would be the wrong trade." It documents
  // seven now. So the row stays and the ceiling moves, rather than the
  // correction being written short enough to fit.
  //
  // Restoring ~6% headroom against the new measurement (the /programs/
  // Sprint E rule: re-baselining to the CURRENT proportional headroom hands
  // the next change the same cliff), not a round-number guess.
  //
  // CORRECTION 2026-08-28: that last sentence is false, and it is the exact
  // species of error the drift leg below was built for — except the drift leg
  // reads `measured`, not prose, so it could not see it. The pair below does
  // NOT deliver ~6%: 36,900 against 36,156 is 744 bytes, 2.06%; 136,500
  // against 132,816 is 3,684 bytes, 2.77%. #69 wrote down the intent and not
  // the arithmetic, so /methodology/ has been sitting at 98.0% of its gzip
  // ceiling since — reported by the near-ceiling note every build, while this
  // comment told anyone who read it there was three times that much room.
  // The smaller true number is published here rather than the ceiling being
  // widened to make the claim come true: the ceiling is UNCHANGED, and the
  // next sentence that needs to go on this page still has to be argued for
  // in the same breath as the raise it needs.
  //
  // RE-MEASURED AGAIN 2026-08-29 (tri-persona Wave 3). CEILING UNCHANGED.
  // Wave 3 put /glossary/ in the desktop nav — the tenth link, shipping on
  // 6,700+ pages — and this is the page that pays most dearly for a sitewide
  // addition. It cost ELEVEN gzip bytes here (36,642 -> 36,653), and the pair
  // below is re-measured to what the page now weighs rather than left to rot:
  // 247 bytes of headroom, which is what the next sentence on this page has
  // to argue against. Same rule as the note below it: the smaller true number
  // gets published, the ceiling does not move.
  //
  // RE-MEASURED 2026-08-29 (tri-persona review Wave 2). CEILING UNCHANGED at
  // 136,500 / 36,900. The recorded pair was 132,816 / 36,156 and the page had
  // already drifted to 134,024 / 36,389 before this wave touched it; Wave 2's
  // reconciliation-scope sentence (the badge covers four scenarios, not the
  // never-checked AllPriorYears) added 253 raw / 253 gzip. The annotation-drift
  // leg below caught the stale string on the first post-fix build, which is
  // what it was written for. 258 bytes of gzip headroom is the tightest this
  // page has ever run: the next sentence here needs a ceiling raise argued in
  // the same breath, and this comment is the warning, not an invitation.
  // RE-MEASURED 2026-08-29 (tri-persona Wave 5). CEILING UNCHANGED, AND THE
  // NUMBER IS STILL ALARMING: 135,373 / 36,870 -> 135,373 / 36,866. The page
  // did not grow at all — it came in FOUR bytes lighter — so Wave 5 raised
  // five ceilings on this build and deliberately not this one. 34 bytes of
  // gzip headroom. The rule from the 2026-08-28 correction above stands: a
  // raise is argued in the same breath as the change that needs it, and no
  // sentence was added here to argue for one.
  // RAISED 2026-08-29 for ROADMAP #28, justified by the change that needed
  // it. gzip 36,900 -> 39,100. The page breached by EIGHT bytes because 553
  // decade-only pages moved the corpus counts this page derives from — it
  // states them, so growing the corpus grows the page. Nothing was trimmed;
  // headroom restored to ~6% (the /programs/ convention) rather than to the
  // breach. Raw was NOT raised: 135,373 of 136,500 is comfortable.
  // Re-baselined 2026-09-01: §4 gained two disclosure paragraphs (the
  // hand-adjudication method with its 9.1% measured precision, and the
  // FPDS-AP acquisition-program evidence path). Deliberate prose growth on
  // the page whose job is to disclose method; ~6% convention over the
  // expansion build's measure.
  // Re-measured 2026-09-03 (announcement + subaward evidence-path paragraphs).
  // RE-MEASURED 2026-09-11 (chain B — the first full build after Tasks 7, 6c
  // and 11). CEILING UNCHANGED, AND THE PAGE IS NOW OVER IT: 154,527 / 43,042,
  // which is 542 gzip bytes past the 42,500 ceiling (raw still has 473 to
  // spare). The page gained 4,188 raw / 1,180 gzip since the 2026-09-03
  // measurement. Tasks 7 and 6c each added §4 prose and predicted roughly
  // +266 raw between them, so MOST of this growth is something else — the
  // corpus counts this page states moved too, and no one has attributed the
  // remainder; do not read the two task numbers as an account of it. This
  // file's rule stands either way: the ceiling does NOT move to fit the page.
  // The trim (§4 / the flow clause) is the owner's call; this string records
  // what the page actually weighs so nobody reads 638 bytes of headroom that
  // do not exist.
  // TRIMMED 2026-09-12 (chain-B fix 1, the owner's call taken). CEILINGS
  // UNCHANGED at 155,000 / 42,500; the page is back inside them at
  // 151,851 / 42,299 — 2,676 raw / 743 gzip removed, 201 gzip bytes of
  // headroom. What came out was REDUNDANCY, not disclosure: the
  // concentration floor now lives in §4 alone and the concentration_shift
  // feed entry points at it; the announcement path's match-basis rule is
  // stated once, not twice; "an account match is an association" is stated
  // where the Medium tier is defined and not again beside the unmeasured
  // tiers; /companies/ keeps the chip-suppression rationale and §6 the
  // supersede pledge. Every figure, date, evidence path and gated passage
  // is still here — see chain-B-report.md §"Chain-B fix 1" for the
  // sentence-by-sentence list.
  // MEASURED COST OF PROSE ON THIS PAGE, for whoever adds the next sentence:
  // 743 gzip for 1,850 characters removed from page.tsx = 0.40 gzip per
  // source character (each character ships twice — once in the HTML, once in
  // the RSC payload). So the 201 bytes left is about 500 characters, and the
  // ≤42,000 this trim aimed at would have needed ~750 characters MORE than
  // the page had left in redundancy — i.e. cutting disclosure, which this
  // file's /coverage/ note already rules out. Markup is not the lever here:
  // every repeated class string on the page is worth 12-46 gzip bytes in
  // total, and all 275 React text-boundary comments together only 327.
  // TRIMMED 2026-09-18 (chain D fix round 1, controller ruling R-D-1).
  // CEILINGS UNCHANGED at 155,000 / 42,500 — NO RAISE was ordered and none was
  // taken. The chain-D build measured 152,483 / 42,562: 62 gzip OVER, from
  // +3,568 source bytes across eight Group C/D commits (cfad4e75, c17f4f90,
  // 7e304d81, 2946c210, 6c3cb61d, 428623ad, a1e8dc86, ee9dbee0).
  //
  // Four clauses came off, each one a restatement of a sentence beside it or
  // of the section that sentence points at — items 2 and 4 below are pointers
  // to §4, not to a neighbouring line —
  // no number, no tier name, no cited claim, and nothing that docs/
  // methodology.md mirrors (its mirrored passage is §4's concentration
  // paragraph, which is untouched):
  //   1. "Only the current edition is matched; " — the clause after it says
  //      the same rule from the other side.
  //   2. "— below it, no pooled index at all" — §4, which that very sentence
  //      points at, states the below-floor behaviour in full.
  //   3. "rather than implying a narrative exists" — the paragraph's closing
  //      sentence says it outright two sentences later.
  //   4. "; the tier is built from announcements naming a program and
  //      adjudicator-pinned account matches" — a one-clause summary of §4 in
  //      a sentence that has just said §4 grades this evidence.
  //
  // MEASURED COST, for whoever adds the next sentence here: 202 source
  // characters removed = 142 gzip, measured as 42,562 on the chain-D build
  // against 42,420 on fix-round build 1, the pair fix round 1 stamped. Every
  // build of this page since has landed between 42,414 and 42,420: a few bytes
  // of build-id jitter, plus the 1 gzip fix round 2 gave back when it moved
  // one of the four trim comments out from between two text runs and React
  // stopped emitting a <!-- --> separator there. So read the trim as 142 gzip
  // ±5; 0.70 gzip per source
  // character, NOT the 0.40 the note above records. That 0.40 came
  // from a 1,850-character trim whose text repeated elsewhere on the page and
  // so compressed as back-references; short, unique clauses cost nearly twice
  // that. Budget with 0.7, and re-measure.
  //
  // AND THE CEILING THIS ROUND COULD NOT REACH: R-D-1 asked for ≥250 gzip of
  // headroom. It is arithmetically unreachable from those eight commits — all
  // of them together moved this page 42,299 → 42,562, so reverting every
  // character of their prose would land at 201 bytes of headroom, and part of
  // that 263 is the corpus counts this page derives, not prose at all. Going
  // further means cutting disclosure written before them, which this file's
  // /coverage/ note rules out. The smaller true number is published here.
  //
  // AND THE BUDGET IS SMALLER STILL THAN THAT HEADROOM. The annotation-drift
  // leg below errors when a recorded `measured:` gzip overstates live headroom
  // by 2x, i.e. as soon as the page weighs more than maxGzip - (maxGzip -
  // recorded)/2. At the 42,415 stamped below against a 42,500 ceiling that is
  // 42,458 — about +43 gzip on a page weighing what this one weighs, half the
  // headroom the entry appears to offer. So the next editor has ~43 bytes
  // before gate 1 goes red, not 85, and the fix when it fires is a RESTAMP of
  // the pair below, never a raise. Same arithmetic on /coverage/: it trips at
  // 20,598, ~150 above the stamp, not 305.
  //
  // The stamped pair is one build's (fix round 2's first). Three builds of
  // that same source weighed 42,415, 42,417 and 42,414 gzip, and /coverage/
  // 20,445, 20,447 and 20,445 — so read a stamp as ±3 and do not spend a
  // build chasing the byte: the leg errors only past 2x, and understating
  // headroom costs nothing.
  //
  // RAISED 2026-09-25 (chain C run 4, controller ruling R-C-1): maxGzip
  // 42,500 -> 43,000. maxRaw is UNCHANGED at 155,000: raw did not trip. This
  // is the branch's SECOND AND LAST ceiling change (the first was /coverage/,
  // R-D-2), and it is a raise, so it is argued here.
  //
  // Measured with this file's own weigh() on the chain C run 4 build of
  // 118228f8: 153,970 / 42,913, i.e. 413 gzip over 42,500. R-C-1 allows ONE
  // raise when the overshoot is 500 gzip or less; past 500 the ruling is a
  // trim round, never a further raise. The builds that led here: 42,415 at
  // chain D's end, then 42,913 on chain C run 2's build, 42,880 on run 3's
  // (after Task 28's prose) and 42,913 on this one (after Task 29's
  // provenance and census sentences).
  //
  // The growth is plan-mandated DISCLOSURE, added to the page whose job is to
  // state how every figure is made:
  //   - Task 16: the GAO census.
  //   - Tasks 17b/17c: the organisation absences.
  //   - Task 19: the SAM.gov registry cross-check.
  //   - Task 21b: the crosswalk-count registry.
  //   - Task 25b: the announcement-tier scope and precision frame (ten
  //     derived figures, which gate 24 leg q binds clause by clause).
  //   - Task 29: the source-freshness sentence now names the least recently
  //     refreshed dataset, and the narrow-label census is derived.
  // Each piece is bound to an artifact by a gate, so none of it can be
  // shortened into a vaguer sentence.
  //
  // THE ALTERNATIVE, RECORDED FOR THE OWNER RATHER THAN TAKEN: trim prose
  // that predates Group C to buy the bytes back instead. That is an
  // editorial decision about disclosure already on the page, and this
  // file's /coverage/ note rules it out for a chain.
  //
  // New headroom is 87 gzip, and the drift leg below fires about half-way
  // there: at roughly 42,957, only +44 over this stamp. The next sentence
  // needs a same-section trim. No further raise is permitted under R-C-1.
  // RE-MEASURED 2026-09-25 (chain E, build of 594d1f0c): 153,970 / 42,913 ->
  // 153,570 / 42,935. The Task 26 fix wave cut 400 raw bytes, yet gzip GREW
  // by 22 (the wave's simulation predicted -111). 65 gzip left; the drift leg
  // now fires at about 42,968. CEILING UNCHANGED — R-C-1 is spent.
  // R-INT-1 (integration ruling 2026-09-25, the controller under the owner's
  // delegation): max of the two reviewed branches — this branch 6c3c07e1
  // 155,000 / 43,000, live 81929a6b 162,000 / 45,400 (the type-system
  // re-baseline; it also moved the gate count on the page 24 -> 25);
  // production already serves these pages under the live ceiling; any merged
  // page above it is trimmed, never raised. This is an owner-delegated
  // ruling, not a chain raise: R-C-1 stays spent. The `measured` stamp below
  // is still this branch's (chain E): re-measure it on the first merged
  // build.
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 153,570 / 42,935 -> 156,560 / 43,901. CEILINGS UNCHANGED; 5,440
  // raw / 1,499 gzip left.
  // RE-MEASURED 2026-09-26 (decisions chain G, BUILD 1 of 0176fa6e, built
  // 2026-09-26T16:51:29Z; gate 1's own weigh()): 156,560 / 43,901 ->
  // 160,836 / 45,147. CEILINGS UNCHANGED; 1,164 raw / 253 gzip left. The
  // drift leg fired at 5.9x (+1,246 gzip over the integration stamp, on the
  // decisions branch with chain G's lake and export). The next paragraph
  // here needs a trim first, not a raise.
  // RE-MEASURED 2026-10-03 (families piece 1 S0, build of 53d8c5ae, built
  // 2026-10-03T07:35:36Z, on the 2026-10-02T01:30:21Z export of 125,409
  // citations; gate 1's own weigh()): 160,836 / 45,147 -> 161,166 / 45,270.
  // CEILINGS UNCHANGED; 834 raw / 130 gzip left (the old stamp claimed 253).
  // Production served 161,166 / 45,270 the same day. Piece 1 replaces one
  // sentence here at equal length and adds a link (spec §6.4); its era table
  // renders wherever it fits without a ceiling raise, decided in Task 19.
  // FAMILIES PIECE 1 (2026-10-03, Task 19 Part A): the "PB2024 boundary"
  // sentence became the era-procurement gap sentence at its exact rendered
  // length (312 bytes); only its p1_era_line_map link is new. RE-MEASURED
  // 2026-10-03 (production-origin build of 5e317a38 plus the Part A edits,
  // built 2026-10-03T17:29:32Z; gate 1's own weigh()): 161,166 / 45,270 ->
  // 161,354 / 45,328 (+188 raw / +58 gzip). CEILINGS UNCHANGED; 646 raw /
  // 72 gzip left. The era table does not render here.
  // RE-MEASURED 2026-10-04 (Task 21, the S4 proof build of 45281589 on
  // the S4 export: the pending-ledger clause and the S4 dbt-assertion count;
  // gate 1's weigh(), zlib level 9): 161,354 / 45,328 -> 161,353 / 45,339.
  // CEILINGS UNCHANGED; 647 raw / 61 gzip left.
  // RE-MEASURED 2026-10-04 (final-review fixes, T2: "the rest have no
  // program page" at the sentence's same 312 bytes; build of ea1c4071 on the
  // S5 proof export with datasets.json's two fixed scopes; gate 1's weigh(),
  // zlib level 9): 161,353 / 45,339 -> 161,353 / 45,336. CEILINGS UNCHANGED;
  // 647 raw / 64 gzip left.
  { label: "/methodology/", file: "methodology/index.html", maxRaw: 162_000, maxGzip: 45_400, measured: "161,353 / 45,336" },
  // Task 6 (§Coverage). Twelve rows of prose; it grows a paragraph at a time
  // as features land, which is exactly the shape §P2-1 wants weighed.
  //
  // Re-baselined 2026-08-13 (Sprint C). This page had drifted to 16,491 of its
  // 16,500 gzip ceiling — NINE bytes of headroom — through ordinary prose growth
  // across prior sprints, without anyone noticing it was that close. Sprint C's
  // sitewide footer link to the new /glossary/ costs ~22 gzip bytes on every
  // page and tipped it to 16,513 (+13).
  //
  // The link is not optional: a glossary a reader cannot find is not shipped,
  // and the alternative — trimming /coverage/'s prose to buy back 13 bytes —
  // would cut disclosure to satisfy a budget, which is the wrong direction on
  // the page whose job is stating what the corpus does and does not cover.
  // Verified irreducible: a plain <a> costs the same as next/link, because the
  // layout's Server Component tree is duplicated into the RSC flight payload
  // regardless of element type.
  //
  // Both ceilings re-derived at the SAME proportional headroom the previous
  // pair carried (raw ×1.0708, gzip ×1.0742), so the budget still catches
  // unintended growth from here rather than being merely widened.
  // RE-BASELINED 2026-08-29 (tri-persona Wave 5) — CEILINGS RAISED, AND THIS
  // ONE NEEDS SAYING PLAINLY BECAUSE IT LOOKS LIKE A PASS.
  //
  // Wave 5 REPLACED this page's program-pages blocker rather than adding to
  // it: the unparsed-volume backlog it confessed no longer exists, and the
  // row now says so. The replacement plus the recomputed figures beside it
  // still took the page from 95,638 / 17,638 to 95,952 / 17,708 — over the
  // 17,700 ceiling by 8 bytes, measured by the gate on that build. It came
  // back UNDER (95,766 / 17,694, six bytes clear) only because a later edit
  // shortened one sentence, and that edit was made for accuracy — the old
  // wording attributed the residual excluded lines to "the services", which
  // is wrong for the Defense Health and reconciliation lines in it — not to
  // fit a budget. Six bytes is not headroom either way, and leaving the
  // ceiling where it is would mean this page's next true sentence has to be
  // paid for by deleting another one.
  //
  // So the ceiling moves, on the breach this change caused, restored to ~6%
  // against the current measurement (101,500 is 5.99% over raw, 18,750 is
  // 5.97% over gzip) rather than to the 0.03% it had drifted to.
  // RE-MEASURED 2026-09-11 (chain B). CEILINGS UNCHANGED and the page is
  // inside them: 98,581 / 18,320, 430 gzip bytes of headroom — up 1,683 raw /
  // 215 gzip since 2026-09-03, unattributed. Nothing trimmed, nothing raised.
  // RAISED 2026-09-18 (chain D fix round 1, controller ruling R-D-2) — THE
  // ONLY CEILING CHANGE ON THIS BRANCH when it was made, and it is a raise,
  // so it is argued in the same breath as the change that needed it. (One
  // more followed on 2026-09-25: /methodology/ under R-C-1, argued at that
  // entry. That was the branch's second and last.)
  //
  // The chain-D build measured this page at 102,194 / 20,473 against
  // 101,500 / 18,750 — 694 raw and 1,723 gzip over. All of the growth is
  // three plan-mandated DISCLOSURE tasks, each of which added prose this page
  // exists to carry:
  //   a1e8dc86 (Task 21b) +1,698 source bytes — the crosswalk-count registry
  //     under #crosswalk: five counts, each with the unit one of them counts,
  //     because "crosswalked" ships with two denominators and neither is the
  //     other's subset. Gate 24 leg (p1) binds those data-crosswalk-count ids
  //     to the shipped artifacts, so they cannot be shortened into one number.
  //   c531fd14 (Task 21d) +854 — the caveat moved to sit directly under the
  //     data it qualifies rather than above it. A move, not an addition, but
  //     the wrapper it needed is not free.
  //   0539aa9d (Task 22a) +2,494 — every promise row now says whether it is
  //     scheduled, and the File C negative result is published with its public
  //     evidence link instead of being left a silence.
  // At this page's measured ~0.4 gzip per source character that predicts
  // +2,018 gzip; the build measured +2,153. The earlier estimates (+26, +228)
  // counted NET RENDERED characters and missed that every character ships
  // twice, in the HTML and again in the RSC flight payload, with its markup.
  //
  // This file's /coverage/ note above rules out the obvious lever: "trimming
  // /coverage/'s prose to buy back 13 bytes would cut disclosure to satisfy a
  // budget, which is the wrong direction on the page whose job is stating what
  // the corpus does and does not cover." That rule is why the ceiling moves
  // and the disclosure does not.
  //
  // THE ALTERNATIVE, RECORDED FOR THE OWNER RATHER THAN TAKEN: move the
  // #crosswalk section — its prose, the File C note and the five-count
  // registry — to its own route, leaving /coverage/ the map table and the
  // corpus counts. That is a routing change with its own gate work (leg (p1)
  // and leg cm[bridge]'s restated-figure check both address /coverage/ by
  // name today), so it is a decision, not a fix-round edit.
  //
  // What WAS bought back on the page itself, in the same round (R-D-2a/b):
  //   - the bridge row's blocker and target rendered TWICE (the map table's
  //     cells and again under #crosswalk). The long form now renders once, in
  //     the table cell where gate 14 leg cm reads it, and #crosswalk points at
  //     it.
  //   - §22a's third trim, "— the same files the pages themselves render
  //     from —" in the ScopeNote's first paragraph: −50 rendered characters.
  //     (Fix round 2 put a four-words-shorter form of that clause back: the
  //     <h2> it was trimmed against claims recomputation, not provenance. It
  //     cost +88 raw — 39 rendered characters, each shipped twice with its
  //     markup — and 14 to 20 gzip, which is the honest width of two builds
  //     either side: 20,431 and 20,427 on fix round 1's two builds, 20,445 and
  //     20,447 on fix round 2's. About 0.4 gzip per rendered character, this
  //     page's own rate.)
  //   MEASURED TOGETHER, because no build isolated them: 102,194 / 20,473 on
  //   the chain-D build → 99,736 / 20,431 on fix-round build 1 = −2,458 raw
  //   and −42 gzip for both edits. The dedupe is what moved the raw — it
  //   removed two paragraphs of 1,073 rendered characters, each shipped twice
  //   (DOM plus RSC payload) — while the gzip barely moved, because a verbatim
  //   second copy compresses to a back-reference. THAT is the number to start
  //   from before anyone budgets a dedupe for gzip headroom: duplication is a
  //   raw-weight problem and almost never a gzip one.
  //
  // New pair, 3,676 raw and 305 gzip above the measurement stamped below
  // rather than a round-number guess. The gzip headroom is deliberately the
  // tighter of the two: this page grows a paragraph at a time and the next
  // sentence on it should have to argue for itself.
  //
  // maxRaw REVERTED 2026-09-25 (Task 26 fix wave, R-D-2 as amended
  // 2026-09-18): 103,500 -> 101,500, the pre-raise value. The dedupe above
  // brought raw back under 101,500 on fix-round build 1 (99,736), so the raw
  // half of the raise was never needed; only the gzip half was. Chain C run
  // 4's final build (git_head 71d3e053) weighed this page at 99,824 raw —
  // 1,676 bytes under the restored ceiling. A lowered ceiling, not a raise;
  // maxGzip 20,750 stands.
  // R-INT-1 (integration ruling 2026-09-25, the controller under the owner's
  // delegation): max of the two reviewed branches — this branch 6c3c07e1
  // 101,500 / 20,750, live 81929a6b 103,000 / 20,200 (the type-system
  // re-baseline from the pre-R-D-2 101,500 / 18,750), so raw 103,000 is the
  // live branch's and gzip 20,750 is this branch's (the live branch's gzip
  // was derived from a page without this branch's Task 21b/21d/22a
  // disclosure; this branch's own stamp below, 20,450, is already over it);
  // production already serves these pages under the live ceiling; any merged
  // page above it is trimmed, never raised. The `measured` stamp below is
  // still this branch's: re-measure it on the first merged build.
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 99,824 / 20,450 -> 85,710 / 20,288. CEILINGS UNCHANGED; 17,290
  // raw / 462 gzip left. The gate-fix wave moved this table's per-row utility
  // classes into a page-local CSS module (coverage.module.css).
  // RE-MEASURED 2026-10-03 (families piece 1 S0, build of 53d8c5ae, built
  // 2026-10-03T07:35:36Z, on the 2026-10-02T01:30:21Z export of 125,409
  // citations; gate 1's own weigh()): 85,710 / 20,288 -> 86,203 / 20,455.
  // CEILINGS UNCHANGED; 16,797 raw / 295 gzip left (the old stamp claimed
  // 462). Production served 86,203 / 20,458 the same day (3 gzip bytes of
  // normal per-build drift from Next's build ID). Piece 1's per-edition era
  // table (spec §6.4) renders on whichever page fits it without a ceiling
  // raise; Task 19 measures the candidate pages and decides.
  { label: "/coverage/", file: "coverage/index.html", maxRaw: 103_000, maxGzip: 20_750, measured: "86,203 / 20,455" },
  // Templated classes — the heaviest built instance of each.
  // The heaviest instance is /agency/N/ since Wave 5, not /agency/F/ — the
  // Navy overtook the Air Force on this page class for the same reason it
  // overtook it on the index: 183 more programs.
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 1,791,734 / 120,673 -> 1,755,341 / 120,583. CEILINGS UNCHANGED;
  // 304,659 raw / 16,417 gzip left.
  { label: "/agency/*/ (heaviest)", dir: "agency", maxRaw: 2_060_000, maxGzip: 137_000, measured: "1,755,341 / 120,583 (/agency/N/)" },
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 1,111,532 / 142,888 -> 1,157,926 / 145,603. CEILINGS UNCHANGED;
  // 22,074 raw / 5,397 gzip left.
  { label: "/program/*/ (heaviest)", dir: "program", maxRaw: 1_180_000, maxGzip: 151_000, measured: "1,157,926 / 145,603 (/program/0601102A/)" },
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 378,429 / 23,417 -> 383,439 / 24,779. CEILINGS UNCHANGED;
  // 161,561 raw / 221 gzip left. 221 gzip bytes left: the next addition to
  // this page class needs a trim of its own, not a raise.
  { label: "/company/*/ (heaviest)", dir: "company", maxRaw: 545_000, maxGzip: 25_000, measured: "383,439 / 24,779 (/company/boeing/)" },
  // NEW ENTRY 2026-09-10 (ROADMAP #6 — the by-year table). The district DETAIL
  // class has never been weighed: this file's templated-class list covered
  // /agency/*/, /program/*/, /company/*/ and /filing/*/, and /district/ only
  // as the INDEX page above. A page class gaining a table is exactly when it
  // should acquire a ceiling.
  //
  // BASELINE, taken with this file's own weigh() (zlib level 9) against the
  // 2026-09-10 LIVE build at https://fiscalreceipts.com, BEFORE the by-year
  // table existed — the three heaviest detail pages plus a mid-weight control:
  //     /district/VA-11/  98,461 / 14,109   (19 programs — the heaviest)
  //     /district/MO-01/  90,604 / 13,067   (17)
  //     /district/CA-50/  89,829 / 13,148   (16)
  //     /district/AZ-07/  74,690 / 12,158   (11)
  // The table adds up to ten rows, one or two cited figures each with
  // chip={false}, and their derived citations to the page's slice. These
  // ceilings are an ESTIMATE at roughly +40% over the pre-change heaviest —
  // deliberately generous, because the `measured` string below is NOT in the
  // "raw / gzip" shape the annotation-drift leg parses, so that leg SKIPS this
  // entry until the controller re-measures against a build that actually
  // carries the table and rewrites the string in the normal form. That
  // re-measure is a required step of this change, not an optional one.
  // RE-MEASURED 2026-09-11 (chain B) against the first build that actually
  // carries the by-year table — the required step named above, now done.
  // /district/VA-11/ weighs 145,449 / 18,356. The gzip estimate HELD (1,644
  // bytes to spare); the RAW estimate did NOT — the page is 5,449 bytes over
  // the 140,000 that was guessed at +40%, because the table is ten rows of
  // cited, chip-suppressed figures and their derived citations, which costs
  // far more raw than compressed. BOTH CEILINGS ARE LEFT WHERE THEY ARE: a
  // raise is argued in the same breath as the change that needs it, and that
  // argument — raise raw to ~6% headroom over a real measurement, or trim the
  // table — is the owner's to make, not a chain's. The string below is now in
  // the "raw / gzip" shape the annotation-drift leg parses.
  // RULED 2026-09-12 (chain-B fix 1): first real measurement 2026-09-12 of a
  // row whose 140,000 was a pre-table estimate — this is the row's INITIAL
  // ceiling, not a raise; never raise it to fit new content. The 140,000 was
  // written down on 2026-09-10 as an explicit +40% guess taken BEFORE the
  // by-year table existed and against a page class that had never been
  // weighed, and the entry said so in the same breath (its `measured` string
  // was deliberately non-parsing until a real build carried the table). An
  // unmeasured estimate is not an established ceiling, so raw is set from the
  // measurement at this file's own ~6% convention for a new row: 145,449 →
  // 154,000 (5.88% over). maxGzip is UNCHANGED at 20,000 — the gzip estimate
  // held on its own (18,356, 8.2% of room to spare), so it is not re-derived.
  // Next heaviest are MO-01 137,560 / 17,441 and CA-50 136,677 / 17,196
  // (re-measured 2026-09-12 with this file's own weigh(); the earlier
  // 137,573 / 17,432 and 136,674 / 17,194 predate the by-year table's last
  // rebuild), so VA-11 is the row this entry weighs by a wide margin.
  {
    label: "/district/*/ (heaviest)",
    dir: "district",
    maxRaw: 154_000,
    maxGzip: 20_000,
    measured: "129,308 / 19,145 (/district/VA-11/)",
    // RE-MEASURED 2026-09-18 (chain D): was 145,449 / 18,356. Same page,
    // same ceilings (154,000 / 20,000); ordinary by-year table growth.
    // RE-MEASURED 2026-09-25 (chain C run 4): 145,568 / 18,413 -> 122,480 /
    // 17,377. Still VA-11. The page got SMALLER: Task 28b stopped embedding
    // each district's citation map in the page. CEILINGS UNCHANGED (the
    // 154,000 / 20,000 INITIAL pair was never raised).
    // RE-MEASURED 2026-09-25 (chain E, build of 594d1f0c): 122,480 / 17,377
    // -> 122,646 / 17,411. Still VA-11; the Task 26 fix wave rewrote its
    // coverage and partial-year notes. CEILINGS UNCHANGED.
    // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
    // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
    // weigh()): 122,646 / 17,411 -> 129,308 / 19,145. CEILINGS UNCHANGED;
    // 24,692 raw / 855 gzip left.
  },
  // RAISED 2026-08-29, 325,000 -> 347,500 raw. Justified by the change that
  // needed it, per this file's own rule -- not pre-emptively. Two changes
  // landed together: Wave 5's Navy ingestion gave 183 more programs a
  // parseable title, and the LDA re-pull grew program mentions 12,448 ->
  // 14,016 across 499 programs (was 453). Filing pages list the programs a
  // filing names, so the heaviest one gained ~12,000 raw bytes of real,
  // cited content. Nothing was trimmed to avoid this.
  //
  // gzip is UNCHANGED at 27,500 and is not close: 22,532, 18% headroom. Only
  // the raw ceiling moved, restored to ~6% headroom (the /programs/ Sprint E
  // convention) rather than to the drift.
  // RE-MEASURED 2026-09-18 (chain D): 327,829 / 22,572 -> 331,870 / 23,444
  // (/filing/82b97e10-b18b-4a28-a09c-ea49dfff8026/), the cased-name work of
  // Task 21c. CEILINGS UNCHANGED; 15,630 raw / 4,056 gzip still free.
  // RE-MEASURED 2026-09-25 (integration, build of 42eed1e4 plus the
  // 2026-09-25 gate-fix wave, built 2026-09-25T20:39:57Z; gate 1's own
  // weigh()): 331,870 / 23,444 -> 326,100 / 24,906. CEILINGS UNCHANGED;
  // 21,400 raw / 2,594 gzip left.
  { label: "/filing/*/ (heaviest)", dir: "filing", maxRaw: 347_500, maxGzip: 27_500, measured: "326,100 / 24,906" },
];

/** raw + gzip(level 9) bytes of one built file. */
function weigh(absPath) {
  const buf = fs.readFileSync(absPath);
  return { raw: buf.length, gzip: zlib.gzipSync(buf, { level: 9 }).length };
}

/**
 * Resolve a budget entry to the ONE file it measures: the named file, or the
 * heaviest index.html in a templated directory (raw size picks the candidate —
 * cheap over 4,394 filings — and only that one gets gzipped).
 */
function resolveBudgetTarget(entry) {
  if (entry.file) {
    const p = path.join(outDir, entry.file);
    return fileExists(p) ? { path: p, rel: entry.file } : null;
  }
  const base = path.join(outDir, entry.dir);
  if (!dirExists(base)) return null;
  let worst = null;
  for (const slug of fs.readdirSync(base)) {
    const p = path.join(base, slug, "index.html");
    let size;
    try {
      const st = fs.statSync(p);
      if (!st.isFile()) continue;
      size = st.size;
    } catch {
      continue;
    }
    if (!worst || size > worst.size) {
      worst = { size, path: p, rel: path.join(entry.dir, slug, "index.html") };
    }
  }
  return worst;
}

/** The leg. Returns {errors, notes} so runBuildGate can fold them in. */
/** Gzip-ceiling usage at or above which a page is reported as near-ceiling. */
const NEAR_CEILING_PCT = 90;

export function checkPageWeight() {
  const errors = [];
  const notes = [];
  const lines = [];
  const nearCeiling = [];

  for (const entry of PAGE_WEIGHT_BUDGET) {
    const target = resolveBudgetTarget(entry);
    if (!target) {
      errors.push(
        `page weight: ${entry.label} — nothing built to measure (${entry.file ?? `out/${entry.dir}/*/index.html`})`
      );
      continue;
    }
    const { raw, gzip } = weigh(target.path);
    if (raw > entry.maxRaw) {
      errors.push(
        `page weight: ${entry.label} is ${raw.toLocaleString()} bytes, over its ${entry.maxRaw.toLocaleString()}-byte ceiling (+${(raw - entry.maxRaw).toLocaleString()}) — measured at ${entry.measured} when the ceiling was set [${target.rel}]`
      );
    }
    if (gzip > entry.maxGzip) {
      errors.push(
        `page weight: ${entry.label} is ${gzip.toLocaleString()} bytes gzipped, over its ${entry.maxGzip.toLocaleString()}-byte ceiling (+${(gzip - entry.maxGzip).toLocaleString()}) — measured at ${entry.measured} when the ceiling was set [${target.rel}]`
      );
    }
    // NEAR-CEILING WARNING (2026-08-14). A ceiling is a cliff: it says nothing
    // until it says FAIL. /coverage/ drifted to NINE bytes of headroom through
    // ordinary prose growth and nobody knew until a one-line footer link tipped
    // it, and /methodology/ did the same thing a week earlier. Worse, every
    // `measured` string in this file had gone stale — /programs/ recorded
    // 261,871 while actually shipping 277,357, so the file itself told a reader
    // there was 6% headroom where there was 0.2%. The strings were refreshed
    // 2026-08-14; this note is what stops them rotting again unnoticed.
    //
    // A NOTE, not an error: six pages are legitimately above 94% today, and
    // failing on that would be inventing a stricter budget than anyone agreed
    // to. It is early warning, so the next person to add a sentence knows
    // before they spend an hour on the build that fails.
    const pctUsed = (100 * gzip) / entry.maxGzip;
    if (pctUsed >= NEAR_CEILING_PCT) {
      nearCeiling.push(
        `${entry.label} ${pctUsed.toFixed(1)}% (${gzip.toLocaleString()}/${entry.maxGzip.toLocaleString()} gzip, ${(entry.maxGzip - gzip).toLocaleString()} bytes left)`
      );
    }
    // ANNOTATION-DRIFT LEG (2026-08-24). The `measured` strings above are
    // the only page-weight facts a human reads WITHOUT running a build, and
    // they have now gone stale twice: /programs/ on 2026-08-14 (261,871
    // recorded against 277,357 shipped) and /filing/*/ today (21,784
    // recorded, 26,526 actual — the file promised 5,716 bytes of room where
    // there were 974). The near-ceiling note above was written to "stop them
    // rotting again unnoticed" and structurally cannot: it reports the LIVE
    // percentage and never compares it to what is written down, so a wrong
    // annotation stays wrong and quietly informs the next person's decision.
    // It informed one on 2026-08-24 — /methodology/ was reported as having
    // 637 bytes of headroom off a stale string when it had 6.
    //
    // Fires only on OVERSTATED headroom, and only past 2x. Understating is
    // harmless (someone trims when they needn't have), and small drift is
    // ordinary data movement — erroring on that would be failing on growth
    // rather than on weight, which this file's own header rules out.
    const ann = /^\s*([\d,]+)\s*\/\s*([\d,]+)/.exec(entry.measured ?? "");
    if (ann) {
      const annGzip = Number(ann[2].replace(/,/g, ""));
      const annLeft = entry.maxGzip - annGzip;
      const realLeft = entry.maxGzip - gzip;
      if (annLeft > 0 && realLeft > 0 && annLeft > 2 * realLeft) {
        errors.push(
          `page weight: ${entry.label}'s recorded measurement overstates its headroom — the entry says ${annGzip.toLocaleString()} gzip (${annLeft.toLocaleString()} bytes left) but the page weighs ${gzip.toLocaleString()} (${realLeft.toLocaleString()} left, ${(annLeft / realLeft).toFixed(1)}x less than recorded). Re-measure the entry — do NOT raise the ceiling to match [${target.rel}]`
        );
      }
    }
    lines.push(
      `${entry.label} ${raw.toLocaleString()}/${gzip.toLocaleString()}`
    );
  }

  if (nearCeiling.length > 0) {
    notes.push(
      `page weight: ${nearCeiling.length} page(s) at or above ${NEAR_CEILING_PCT}% of the gzip ceiling — ${nearCeiling.join("; ")}`
    );
  }
  if (errors.length === 0) {
    notes.push(
      `page weight: ${PAGE_WEIGHT_BUDGET.length} page budgets within ceiling ✓ (raw/gzip: ${lines.slice(0, 3).join("; ")}; …)`
    );
  }
  return { errors, notes };
}

export async function runBuildGate() {
  const errors = [];
  const notes = [];

  // ── Load sidecars ────────────────────────────────────────────────────────
  const programs = readJson(path.join(jsonDir, "programs.json"));
  const entities = readJson(path.join(jsonDir, "entities_top.json"));
  const agencies = readJson(path.join(jsonDir, "agencies.json"));
  const siteMeta = readJson(path.join(jsonDir, "site_meta.json"));

  // Phase 5F §2a: the program-page universe is EVERY program_details sidecar
  // (full tier from programs.json + rollup tier), recomputed here
  // independently of src/. Zero-content pages (no details/narratives/awards/
  // mentions and every figure zero) are built but noindex — excluded from
  // the sitemap, so the two counts differ.
  const detailsDir = path.join(jsonDir, "program_details");
  const programSlugs = dirExists(detailsDir)
    ? fs.readdirSync(detailsDir).filter((f) => f.endsWith(".json"))
    : [];
  const programCount = programSlugs.length;
  let zeroContentCount = 0;
  for (const f of programSlugs) {
    try {
      const d = readJson(path.join(detailsDir, f));
      const hasContent =
        (d.details ?? []).length > 0 ||
        (d.narratives ?? []).length > 0 ||
        (d.awards ?? []).length > 0 ||
        (d.mentions ?? []).length > 0 ||
        // ROADMAP #28: a decade-only page's whole content IS its decade
        // series — cited figures from the editions that do carry the line.
        // Omitting it here counted all 553 of them as "zero-content" and
        // subtracted them from the expected sitemap size, against a sitemap
        // that (correctly) lists them and pages that are not noindex.
        (d.decade_series?.actuals ?? []).length > 0 ||
        (d.decade_series?.request ?? []).length > 0;
      if (hasContent) continue;
      const figures = (d.budget_lines ?? []).map((bl) => bl.amount_thousands);
      const t = d.trajectory;
      if (t) {
        for (const v of [t.fy2024_actuals, t.fy2025_total, t.fy2026_total]) {
          if (v !== null && v !== undefined) figures.push(v);
        }
      }
      // `[].every(...)` is TRUE, so a page with no figures at all read as
      // "every figure is zero". Zero-content means measured-and-zero, not
      // nothing-to-measure — require at least one figure before concluding it.
      if (figures.length > 0 && figures.every((v) => v === 0)) zeroContentCount++;
    } catch {
      errors.push(`program sidecar unreadable: ${f}`);
    }
  }
  // Sprint E, Task E3 (ROADMAP #67): the 8 genuine appropriation-account
  // collisions each get a bare-pe_bli disambiguation STUB page in addition
  // to their program_details sidecars — a stub carries no sidecar of its
  // own (program-skeleton.mjs's gate 21 would otherwise demand the full
  // 13-section skeleton from a page that isn't a program at all), so it is
  // invisible to programCount above. Derived from programs.json's own
  // pe_bli duplicates — never hand-counted — so a future re-key changes
  // this automatically.
  const pesSeen = new Map();
  for (const p of programs) pesSeen.set(p.pe_bli, (pesSeen.get(p.pe_bli) ?? 0) + 1);
  const stubCount = [...pesSeen.values()].filter((n) => n > 1).length;

  const sitemapProgramCount = programCount - zeroContentCount + stubCount;

  const companyCount = entities.length;
  const agencyCount = agencies.length;
  const citationTotal = siteMeta.counts?.citations ?? 0;

  notes.push(
    `sidecars: ${programCount} program pages (${programs.length} full tier, ` +
      `${zeroContentCount} zero-content/noindex), ${companyCount} companies, ` +
      `${agencyCount} agencies, ${citationTotal} citations`
  );

  // ── out/ exists ──────────────────────────────────────────────────────────
  if (!dirExists(outDir)) {
    errors.push(`out/ directory not found at ${outDir}`);
    return { pass: false, errors, notes };
  }

  // ── Build staleness check ─────────────────────────────────────────────────
  // out/.build-meta.json is written by scripts/write-build-meta.mjs (postbuild).
  // Gate verifies: (a) marker exists, (b) git HEAD matches, (c) marker mtime is
  // newer than the newest watched source file — catches stale out/ after src edits.
  {
    const markerPath = path.join(outDir, ".build-meta.json");
    if (!fileExists(markerPath)) {
      errors.push(
        "out/.build-meta.json missing — out/ was not produced by a complete build " +
          "(re-run `npm run build`)"
      );
    } else {
      let marker;
      try {
        marker = readJson(markerPath);
      } catch (e) {
        errors.push(`out/.build-meta.json is corrupt: ${e.message}`);
        marker = null;
      }
      if (marker) {
        // (b) git HEAD check
        let currentHead = "unknown";
        try {
          const { execSync } = await import("child_process");
          currentHead = execSync("git rev-parse HEAD", {
            cwd: siteRoot,
            encoding: "utf8",
            stdio: ["pipe", "pipe", "pipe"],
          }).trim();
        } catch {
          // non-fatal if git unavailable
        }
        if (
          currentHead !== "unknown" &&
          marker.git_head !== "unknown" &&
          currentHead !== marker.git_head
        ) {
          errors.push(
            `out/.build-meta.json git_head mismatch: built from ${marker.git_head.slice(0, 8)}, ` +
              `current HEAD is ${currentHead.slice(0, 8)} — re-run \`npm run build\``
          );
        } else {
          notes.push(`build-meta git_head: ${marker.git_head.slice(0, 8)} ✓`);
        }

        // (c) mtime freshness: marker mtime must be newer than source max mtime.
        // This catches the "touched src file after build" failure mode.
        const markerMtime = fs.statSync(markerPath).mtimeMs;
        function maxMtimeGate(dirOrFile) {
          if (!fs.existsSync(dirOrFile)) return 0;
          const st = fs.lstatSync(dirOrFile);
          if (!st.isDirectory()) return st.mtimeMs;
          let mx = st.mtimeMs;
          for (const entry of fs.readdirSync(dirOrFile, { withFileTypes: true })) {
            if (["node_modules", ".next", "out"].includes(entry.name)) continue;
            mx = Math.max(mx, maxMtimeGate(path.join(dirOrFile, entry.name)));
          }
          return mx;
        }
        const watchedPaths = [
          path.join(siteRoot, "src"),
          path.join(siteRoot, "public"),
          path.join(siteRoot, "package.json"),
          path.join(siteRoot, "next.config.ts"),
          path.join(siteRoot, "tsconfig.json"),
          path.join(siteRoot, "postcss.config.mjs"),
        ];
        const sourceMax = Math.max(...watchedPaths.map(maxMtimeGate));
        if (markerMtime < sourceMax) {
          const staleBy = ((sourceMax - markerMtime) / 1000).toFixed(1);
          errors.push(
            `out/ is stale: a source file is ${staleBy}s newer than out/.build-meta.json ` +
              `(source_max=${new Date(sourceMax).toISOString()}, ` +
              `marker=${new Date(markerMtime).toISOString()}) — re-run \`npm run build\``
          );
        } else {
          notes.push("build freshness: out/ is newer than all watched source files ✓");
        }
      }
    }
  }

  // ── Program pages ────────────────────────────────────────────────────────
  const programOut = path.join(outDir, "program");
  if (!dirExists(programOut)) {
    errors.push("out/program/ directory not found");
  } else {
    const builtPblis = fs.readdirSync(programOut).filter((d) => {
      return fs.statSync(path.join(programOut, d)).isDirectory();
    });
    // Sprint E, Task E3: + stubCount — the 8 split-key bare-pe_bli
    // disambiguation pages are real, built out/program/{pe_bli}/ directories
    // with no program_details sidecar (see stubCount's own comment above).
    const expectedProgramPages = programCount + stubCount;
    if (builtPblis.length !== expectedProgramPages) {
      errors.push(
        `program pages: found ${builtPblis.length}, expected ${expectedProgramPages} ` +
          `(${programCount} sidecar-backed + ${stubCount} split-key stubs)`
      );
    } else {
      notes.push(`program pages: ${builtPblis.length} ✓ (incl. ${stubCount} split-key stubs)`);
    }
  }

  // ── Agency pages ─────────────────────────────────────────────────────────
  const agencyOut = path.join(outDir, "agency");
  if (!dirExists(agencyOut)) {
    errors.push("out/agency/ directory not found");
  } else {
    const builtOrgs = fs.readdirSync(agencyOut).filter((d) => {
      return fs.statSync(path.join(agencyOut, d)).isDirectory();
    });
    if (builtOrgs.length !== agencyCount) {
      errors.push(
        `agency pages: found ${builtOrgs.length}, expected ${agencyCount}`
      );
    } else {
      notes.push(`agency pages: ${builtOrgs.length} ✓`);
    }
  }

  // ── Company pages ─────────────────────────────────────────────────────────
  const companyOut = path.join(outDir, "company");
  if (!dirExists(companyOut)) {
    errors.push("out/company/ directory not found");
  } else {
    const builtSlugs = fs.readdirSync(companyOut).filter((d) => {
      return fs.statSync(path.join(companyOut, d)).isDirectory();
    });
    if (builtSlugs.length !== companyCount) {
      errors.push(
        `company pages: found ${builtSlugs.length}, expected ${companyCount}`
      );
    } else {
      notes.push(`company pages: ${builtSlugs.length} ✓`);
    }
  }

  // ── Shard-only citations (R-DEC-GATE-SHARDS) ──────────────────────────────
  // Company and district pages resolve citation bodies from
  // /json/cite-shards/, never from an embedded slice. Fails any such page
  // whose provider payload (HTML or RSC .txt) embeds one.
  runShardOnlyCitationsLeg({ outDir, errors, notes });

  // ── Core pages ────────────────────────────────────────────────────────────
  const corePages = [
    { path: "index.html", label: "/" },
    { path: path.join("programs", "index.html"), label: "/programs/" },
    { path: path.join("explore", "index.html"), label: "/explore/" },
    { path: path.join("families", "f-15", "index.html"), label: "/families/f-15/" },
    { path: path.join("companies", "index.html"), label: "/companies/" },
    { path: path.join("data", "index.html"), label: "/data/" },
    { path: path.join("flow", "index.html"), label: "/flow/" },
    // ROADMAP #29(c) — the lineage identity diagram.
    { path: path.join("lineage", "index.html"), label: "/lineage/" },
    { path: path.join("downloads", "index.html"), label: "/downloads/" },
    { path: path.join("methodology", "index.html"), label: "/methodology/" },
    { path: path.join("glossary", "index.html"), label: "/glossary/" },
    // Sprint C Task C3 (ROADMAP #62) — the /agency/ index.
    { path: path.join("agency", "index.html"), label: "/agency/" },
    { path: path.join("about", "index.html"), label: "/about/" },
  ];
  for (const { path: rel, label } of corePages) {
    if (!fileExists(path.join(outDir, rel))) {
      errors.push(`core page missing: ${label}`);
    }
  }
  const missingCore = corePages.filter((c) => !fileExists(path.join(outDir, c.path)));
  if (missingCore.length === 0) {
    notes.push(`core pages: all ${corePages.length} present ✓`);
  }

  // ── Pagefind bundle ───────────────────────────────────────────────────────
  const pagefindJs = path.join(outDir, "pagefind", "pagefind.js");
  if (!fileExists(pagefindJs)) {
    errors.push("out/pagefind/pagefind.js not found — run `npm run build` (includes postbuild pagefind)");
  } else {
    notes.push("pagefind/pagefind.js ✓");
  }

  // ── Sitemap ───────────────────────────────────────────────────────────────
  // Next.js static export from app/sitemap.ts → out/sitemap.xml
  let sitemapContent = null;
  const sitemapCandidates = [
    path.join(outDir, "sitemap.xml"),
    path.join(outDir, "sitemap", "index.html"),
  ];
  for (const cand of sitemapCandidates) {
    if (fileExists(cand)) {
      sitemapContent = fs.readFileSync(cand, "utf8");
      break;
    }
  }

  if (!sitemapContent) {
    errors.push("sitemap.xml not found in out/ (tried sitemap.xml and sitemap/index.html)");
  } else {
    // Count <url> entries
    const urlMatches = sitemapContent.match(/<url>/g) || [];
    const sitemapCount = urlMatches.length;

    // Compute district page count from sidecar (0 if not yet generated)
    let districtPageCount = 0;
    try {
      const districtIndex = readJson(path.join(jsonDir, "districts", "index.json"));
      // +1 for /district/ index page, +N for each district detail page
      districtPageCount = 1 + (districtIndex.total_districts ?? 0);
    } catch {
      // sidecars not generated — only count the base /district/ page if it exists
      // but since the route needs params, it won't be in the sitemap when count=0.
    }
    // Compute filing page count from sidecar (Task 6a): /filings/ index +
    // ONLY mention-bearing filings (zero-mention filings are noindex and
    // deliberately excluded from the sitemap).
    let filingPageCount = 0;
    try {
      const filingsIndex = readJson(path.join(jsonDir, "filings_index.json"));
      const withMentions = (filingsIndex.filings ?? []).filter(
        (f) => f.has_mentions
      ).length;
      filingPageCount = 1 + withMentions;
    } catch {
      // sidecars not generated — no filing URLs expected
    }
    // Expected: static(16) + feed(1) + district pages + filing pages + programs + companies + agencies
    // static(16) = /, /programs/, /explore/, /families/f-15/, /companies/, /companies/families/, /data/,
    //              /years/, /flow/, /lineage/, /downloads/, /methodology/,
    //              /glossary/, /agency/, /coverage/, /about/
    // (/flow/ added in Phase 5H; /companies/families/ added in PM Sprint 2
    //  §P1-3 — the curated rename/acquisition table; /coverage/ in Sprint 3
    //  Task 6 — the roadmap page; /glossary/ in Sprint C Task C1 — ROADMAP
    //  #60, term definitions; /agency/ in Sprint C Task C3 — ROADMAP #62,
    //  the /agency/{org}/ index, counted separately from the ${agencyCount}
    //  dynamic /agency/{org}/ pages below; /lineage/ in ROADMAP #29(c) — the
    //  lineage identity diagram, the only surface that renders the nine
    //  stated links whose endpoints have no program page of their own;
    //  /years/ in the tri-persona review Wave 4 — the decade matrix was in
    //  no sitemap at all, on a site whose cross-program "asked vs got"
    //  analysis happens there; /explore/ is the visual-pilot gallery;
    //  /families/f-15/ adds the curated aircraft family browser.)
    // Programs: page universe MINUS zero-content noindex pages (5F policy —
    // built but excluded from the sitemap, like zero-mention filings).
    const STATIC_SITEMAP_PAGES = 16;
    const expectedTotal =
      STATIC_SITEMAP_PAGES + 1 + districtPageCount + filingPageCount + sitemapProgramCount + companyCount + agencyCount;
    if (sitemapCount !== expectedTotal) {
      errors.push(
        `sitemap URL count: found ${sitemapCount}, expected ${expectedTotal} (${STATIC_SITEMAP_PAGES} static + 1 feed + ${districtPageCount} district + ${filingPageCount} filing + ${sitemapProgramCount} programs (${programCount} pages − ${zeroContentCount} zero-content noindex) + ${companyCount} companies + ${agencyCount} agencies)`
      );
    } else {
      notes.push(`sitemap: ${sitemapCount} URLs ✓ (${zeroContentCount} zero-content program page(s) excluded)`);
    }

    // Check all URLs start with SITE_URL origin
    const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://govbudget-placeholder.example";
    const origin = new URL(siteUrl).origin;
    const locMatches = sitemapContent.match(/<loc>([^<]+)<\/loc>/g) || [];
    const badUrls = locMatches.filter((m) => {
      const loc = m.replace(/<\/?loc>/g, "");
      return !loc.startsWith(origin);
    });
    if (badUrls.length > 0) {
      errors.push(
        `sitemap: ${badUrls.length} URLs do not start with origin ${origin}. First: ${badUrls[0]}`
      );
    } else if (locMatches.length > 0) {
      notes.push(`sitemap origins: all start with ${origin} ✓`);
    }
  }

  // ── robots.txt ────────────────────────────────────────────────────────────
  // Next.js static export from app/robots.ts → out/robots.txt
  const robotsCandidates = [
    path.join(outDir, "robots.txt"),
    path.join(outDir, "robots", "index.html"),
  ];
  let robotsFound = false;
  for (const cand of robotsCandidates) {
    if (fileExists(cand)) {
      robotsFound = true;
      notes.push("robots.txt ✓");
      break;
    }
  }
  if (!robotsFound) {
    errors.push("robots.txt not found in out/");
  }

  // ── llms.txt ─────────────────────────────────────────────────────────────
  const llmsTxt = path.join(outDir, "llms.txt");
  if (!fileExists(llmsTxt)) {
    errors.push("llms.txt not found in out/");
  } else {
    const content = fs.readFileSync(llmsTxt, "utf8");
    const checks = [
      { pattern: "/methodology/", label: "/methodology/" },
      { pattern: "/downloads/", label: "/downloads/" },
    ];
    for (const { pattern, label } of checks) {
      if (!content.includes(pattern)) {
        errors.push(`llms.txt missing ${label}`);
      }
    }
    const programLineRe = /\/program\/[A-Z0-9]+\//;
    if (!programLineRe.test(content)) {
      errors.push("llms.txt has no /program/... URL");
    } else {
      notes.push("llms.txt: /methodology/ + /downloads/ + /program/... ✓");
    }
  }

  // ── Placeholder-origin scan (backlog #18) ─────────────────────────────────
  // A build without NEXT_PUBLIC_SITE_URL bakes https://govbudget-placeholder
  // .example into sitemap/llms.txt/canonicals (src/lib/site.ts fallback).
  // The sitemap-origin check above is relative to the verify-time env — and
  // falls back to the SAME placeholder, so a placeholder build verified in a
  // placeholder env would false-pass it. This scan is UNCONDITIONAL: the
  // production artifacts must never contain the placeholder host, no matter
  // what origin this verify run was given.
  {
    const PLACEHOLDER_HOST = "govbudget-placeholder.example";
    const scanTargets = ["sitemap.xml", "llms.txt", "robots.txt", "index.html"];
    let scanned = 0;
    let hits = 0;
    for (const rel of scanTargets) {
      const p = path.join(outDir, rel);
      if (!fileExists(p)) continue; // absence is reported by each file's own leg
      scanned++;
      if (fs.readFileSync(p, "utf8").includes(PLACEHOLDER_HOST)) {
        hits++;
        errors.push(
          `placeholder origin: out/${rel} contains "${PLACEHOLDER_HOST}" — ` +
            "the site was built without NEXT_PUBLIC_SITE_URL; rebuild with the production origin"
        );
      }
    }
    if (hits === 0) {
      notes.push(`placeholder scan: ${scanned}/${scanTargets.length} artifacts free of ${PLACEHOLDER_HOST} ✓`);
    }
  }

  // ── Fact-permalink route (PM Sprint 1 Task 5, spec §P0-4) ─────────────────
  // The footnote formatter emits https://…/fact/{fid8} permalinks (gate 23
  // leg c goldens). Those URLs resolve ONLY when the deploy root carries the
  // Vercel rewrite AND the /fact/ resolver page built. out/ is the deploy
  // root (`vercel --prod` from site/out), and Next copies public/vercel.json
  // into out/ — so both artifacts must be in out/ or the permalinks 404.
  {
    const vercelJsonPath = path.join(outDir, "vercel.json");
    let vercelConfig = null;
    if (!fileExists(vercelJsonPath)) {
      errors.push(
        "fact permalinks: out/vercel.json missing — /fact/{id} URLs will 404 on deploy " +
          "(site/public/vercel.json must ship the /fact/:id rewrite)"
      );
    } else {
      let rewriteOk = false;
      try {
        vercelConfig = readJson(vercelJsonPath);
        rewriteOk = (vercelConfig.rewrites ?? []).some(
          (r) => r.source === "/fact/:id" && r.destination === "/fact/"
        );
      } catch (e) {
        errors.push(`fact permalinks: out/vercel.json is corrupt: ${e.message}`);
      }
      if (!rewriteOk) {
        errors.push(
          'fact permalinks: out/vercel.json lacks the {"source": "/fact/:id", "destination": "/fact/"} rewrite'
        );
      } else {
        notes.push("fact permalinks: /fact/:id rewrite present in out/vercel.json ✓");
      }

      // (f1) ROADMAP #61: /fact/{id}/ (trailing slash) 404ed in production
      // — verified live 2026-08-13: unslashed 200s, slashed 404s, even
      // though every OTHER route on the site canonically ends in a slash
      // (next.config.ts trailingSlash:true) and CMSes/link-checkers
      // normalize trailing slashes onto URLs routinely. Root cause,
      // confirmed against live Vercel routing rather than assumed: a curl
      // of the slashed URL returned Vercel's literal 404.html
      // (content-disposition: filename="404.html"), not the rewritten fact
      // page (content-disposition: filename="fact") — proving the
      // `/fact/:id` rewrite never fires for a slash-terminated request on
      // Vercel's edge, even though the open-source path-to-regexp@6
      // library's OWN default compile of that same source string DOES
      // match a trailing slash (checked locally against
      // node_modules/msw's path-to-regexp@6.3.0) — Vercel's actual
      // matching is stricter than the library's default. The fix is a
      // second, explicit literal rule for the slashed form.
      //
      // WHAT THIS LEG PROVES: only that out/vercel.json's rewrite array
      // carries that second rule (config shape) — NOT that Vercel's edge
      // honors it post-deploy. Nothing in this repo can prove the live
      // routing behaviour: scripts/serve-static.mjs (the server every
      // other local gate drives) never reads vercel.json and implements
      // only its own filesystem trailing-slash fallback
      // ($uri → $uri/index.html → $uri.html → 404.html) — per its own
      // docstring it doesn't apply Vercel rewrites at all, so it 404s on
      // BOTH /fact/{id} and /fact/{id}/ alike (there is no
      // out/fact/{id}/index.html for either) and cannot distinguish
      // "rewrite present" from "rewrite absent" for either form. A gate
      // built on that server would pass for the wrong reason. The live
      // curl above is the only behavioural evidence there is; re-check
      // production the same way after deploy.
      if (vercelConfig) {
        const slashedRewriteOk = (vercelConfig.rewrites ?? []).some(
          (r) => r.source === "/fact/:id/" && r.destination === "/fact/"
        );
        if (!slashedRewriteOk) {
          errors.push(
            'fact permalinks (f1): out/vercel.json lacks the {"source": "/fact/:id/", ' +
              '"destination": "/fact/"} rewrite — /fact/{id}/ (trailing slash) will 404 ' +
              "on deploy (ROADMAP #61)"
          );
        } else {
          notes.push(
            "fact permalinks (f1): /fact/:id/ (trailing-slash) rewrite present in out/vercel.json ✓"
          );
        }
      }
    }
    if (!fileExists(path.join(outDir, "fact", "index.html"))) {
      errors.push(
        "fact permalinks: out/fact/index.html missing — the /fact/ resolver page did not build"
      );
    } else {
      notes.push("fact permalinks: out/fact/index.html present ✓");
    }
  }

  // ── citations.json key count ──────────────────────────────────────────────
  const citationsPath = path.join(jsonDir, "citations.json");
  if (!fileExists(citationsPath)) {
    errors.push("citations.json not found in data/site/json/");
  } else {
    const citations = readJson(citationsPath);
    const citationKeys = Object.keys(citations).length;
    if (citationTotal === 0) {
      errors.push("site_meta.json counts.citations is 0 — re-run export-site");
    } else if (citationKeys !== citationTotal) {
      errors.push(
        `citations.json: ${citationKeys} keys, expected ${citationTotal} (from site_meta.json)`
      );
    } else {
      notes.push(`citations.json: ${citationKeys} keys == ${citationTotal} total ✓`);
    }
  }

  // ── /json/feed.json is SHIPPED, parses, and carries cards ─────────────────
  //
  // Final review I2 / batch review 1.2. /json/feed.json 404'd in production
  // and no link-graph leg could see it: no <a href> points at it. ROADMAP #88
  // moved "show all" to the per-event-type sidecars, so nothing fetches this
  // file at runtime any more — but /feed/'s truncation note still tells the
  // reader the full set is in feed.json, generate-feeds.mjs builds the
  // RSS/Atom feeds from the same payload, and prepare-assets 5g still ships
  // it, so a husk copy still makes a rendered sentence false. Gate 13 leg (i) scans site/src for
  // static fetch targets and asserts each exists; this leg adds the part a
  // path-existence check cannot make: the file must PARSE and carry a real
  // digest, not a zero-card husk written by a half-run prepare-assets.
  //
  // Floor measured 2026-09-04 from data/site/json/feed.json: 1,047 cards.
  // 800 leaves headroom for ordinary corpus movement (feed cards come and go
  // with each export) and still fails on the shape this exists to catch — an
  // empty or truncated copy. RE-MEASURE if the feed's construction changes;
  // do not lower it to whatever the build produced.
  const MIN_SHIPPED_FEED_CARDS = 800;
  const shippedFeedPath = path.join(outDir, "json", "feed.json");
  if (!fileExists(shippedFeedPath)) {
    errors.push(
      "out/json/feed.json not found — /feed/'s truncation note names this " +
        "file as where the full card set lives and nothing links to it, so a " +
        "missing copy 404s silently for every reader who goes looking " +
        "(prepare-assets.mjs 5g copies it into public/json/)"
    );
  } else {
    let shippedFeed;
    try {
      shippedFeed = readJson(shippedFeedPath);
    } catch (e) {
      shippedFeed = null;
      errors.push(`out/json/feed.json is not parseable JSON: ${e.message}`);
    }
    if (shippedFeed) {
      const cards = Array.isArray(shippedFeed.cards) ? shippedFeed.cards : null;
      if (!cards) {
        errors.push(
          "out/json/feed.json has no `cards` array — the published full set " +
            "is empty, and generate-feeds.mjs reads the same shape"
        );
      } else if (cards.length < MIN_SHIPPED_FEED_CARDS) {
        errors.push(
          `out/json/feed.json carries ${cards.length} card(s), floor ` +
            `${MIN_SHIPPED_FEED_CARDS} (measured 2026-09-04 at 1,047). A ` +
            `truncated copy passes every existence check and still makes ` +
            `/feed/'s "the full set is in feed.json" note false. Re-measure ` +
            `the feed; do not lower the floor`
        );
      } else {
        notes.push(
          `out/json/feed.json: ${cards.length} cards (floor ${MIN_SHIPPED_FEED_CARDS}) ✓`
        );
      }
    }
  }

  // ── Download-href check ───────────────────────────────────────────────────
  // The built downloads page must use /citations/citations.parquet (not /data/).
  const downloadsHtml = path.join(outDir, "downloads", "index.html");
  if (!fileExists(downloadsHtml)) {
    errors.push("out/downloads/index.html not found — cannot check download hrefs");
  } else {
    const dlContent = fs.readFileSync(downloadsHtml, "utf8");
    // Verify the citations parquet link points to /citations/ not /data/
    if (dlContent.includes("/data/citations.parquet")) {
      errors.push(
        "downloads page contains stale href /data/citations.parquet — should be /citations/citations.parquet"
      );
    } else if (dlContent.includes("citations.parquet")) {
      notes.push("download href: citations.parquet points to /citations/ ✓");
    } else {
      // Could be asset-URL-resolved at runtime; don't error, just note
      notes.push("download href: citations.parquet not found in static HTML (runtime asset URL)");
    }

    // Stale-literal check: must NOT contain hardcoded "44,754"
    if (dlContent.includes("44,754")) {
      errors.push(
        "downloads page contains stale literal \"44,754\" — counts must be data-driven from site_meta.json"
      );
    } else {
      notes.push("stale-literal check: no hardcoded \"44,754\" in downloads page ✓");
    }
  }

  // ── Page-weight budget (§P2-1) ────────────────────────────────────────────
  {
    const w = checkPageWeight();
    errors.push(...w.errors);
    notes.push(...w.notes);
  }

  // ── Fonts leg (the type system) ───────────────────────────────────────────
  {
    const fontsDir = path.join(outDir, "fonts");
    const chunksDir = path.join(outDir, "_next", "static", "chunks");
    const referenced = new Set();
    if (fs.existsSync(chunksDir)) {
      for (const f of fs.readdirSync(chunksDir).filter((n) => n.endsWith(".css"))) {
        const css = fs.readFileSync(path.join(chunksDir, f), "utf8");
        for (const m of css.matchAll(/url\((["']?)(\/fonts\/[^"')]+)\1\)/g)) referenced.add(m[2]);
      }
    }
    if (referenced.size === 0) {
      errors.push("fonts: no url(/fonts/…) in the built CSS — the @font-face declaration site did not ship");
    }
    const provenance = new Map(); // "/fonts/<family>/<vN>/<file>" → { sha, bytes }
    if (fs.existsSync(fontsDir)) {
      for (const family of fs.readdirSync(fontsDir)) {
        const prov = path.join(fontsDir, family, "PROVENANCE.md");
        if (!fs.existsSync(prov)) { errors.push(`fonts: out/fonts/${family}/ has no PROVENANCE.md`); continue; }
        const md = fs.readFileSync(prov, "utf8");
        for (const m of md.matchAll(/\|\s*`([^`]+\.woff2)`\s*\|\s*https?:\/\/\S+\s*\|\s*([0-9a-f]{64})\s*\|\s*([\d,]+)\s*\|/g)) {
          provenance.set(`/fonts/${family}/${m[1]}`, { sha: m[2], bytes: Number(m[3].replace(/,/g, "")) });
        }
      }
    }
    for (const ref of referenced) {
      const file = path.join(outDir, ref);
      if (!fs.existsSync(file)) { errors.push(`fonts: CSS references ${ref} but out${ref} does not exist`); continue; }
      const buf = fs.readFileSync(file);
      const sha = createHash("sha256").update(buf).digest("hex");
      const p = provenance.get(ref);
      if (!p) errors.push(`fonts: ${ref} has no Integrity row in its PROVENANCE.md (file · source URL · SHA-256 · bytes)`);
      else if (p.sha !== sha || p.bytes !== buf.length) errors.push(`fonts: ${ref} is not the bytes PROVENANCE.md records (sha ${sha.slice(0, 12)}… / ${buf.length} B vs ${p.sha.slice(0, 12)}… / ${p.bytes} B) — re-vendor into a NEW version directory, never overwrite`);
    }
    const shipped = [];
    const walk = (d) => { for (const n of fs.readdirSync(d)) { const q = path.join(d, n); if (fs.statSync(q).isDirectory()) walk(q); else if (n.endsWith(".woff2")) shipped.push("/" + path.relative(outDir, q).split(path.sep).join("/")); } };
    if (fs.existsSync(fontsDir)) walk(fontsDir);
    for (const f of shipped) if (!referenced.has(f)) errors.push(`fonts: out${f} ships but no @font-face references it — a dead asset (delete it and its provenance)`);
    const vercel = path.join(outDir, "vercel.json");
    if (fs.existsSync(vercel)) {
      const v = JSON.parse(fs.readFileSync(vercel, "utf8"));
      const hdr = (v.headers ?? []).find((h) => /fonts/.test(h.source ?? "") && (h.headers ?? []).some((x) => /cache-control/i.test(x.key) && /immutable/.test(x.value)));
      if (!hdr) errors.push("fonts: out/vercel.json has no immutable Cache-Control header for /fonts/(.*) — the versioned paths are meant to be cached for a year");
    }
    const home = path.join(outDir, "index.html");
    if (fs.existsSync(home)) {
      const html = fs.readFileSync(home, "utf8");
      const pre = [...html.matchAll(/<link[^>]+rel="preload"[^>]+href="(\/fonts\/[^"]+)"[^>]*>/g)].map((m) => m[1]);
      if (pre.length < 2) errors.push(`fonts: out/index.html preloads ${pre.length} font(s); the serif and the sans must both be preloaded`);
      for (const h of pre) if (!fs.existsSync(path.join(outDir, h))) errors.push(`fonts: preload ${h} does not resolve under out/`);
    }
    if (!errors.some((e) => e.startsWith("fonts:"))) notes.push(`fonts: ${referenced.size} referenced, ${shipped.length} shipped, all provenance hashes match, immutable header + 2 preloads ✓`);
  }

  return { pass: errors.length === 0, errors, notes };
}
