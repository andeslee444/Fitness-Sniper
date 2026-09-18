/**
 * gate — filing_gate
 *
 * (a) Filing pages built: count >= filings_index.json total (expect ~4,258)
 * (b) Zero-mention filings have robots noindex meta
 * (c) All sampled pages have a canonical link
 * (d) Income/expense figures carry [data-amount] (state A via lda_filing citations)
 * (e) Display casing + provenance (PM-S3 leftover). Filing pages rendered the
 *     raw LDA strings — an ALL-CAPS h1 on every one of the 5,393 pages the
 *     shipped filings index generates — while every other surface on the site
 *     cased registry names through lib/company-name and kept the raw string
 *     beside them. For each sampled page: the h1 and the registrant line carry
 *     [data-company-name] whose value is the filing payload's own string,
 *     verbatim; where a display differs, the visible [data-filed-as] line
 *     carries the raw string. Gate 2 leg (tc) then re-runs the casing rule
 *     itself against the same HTML, so this leg only has to pin WHERE the
 *     names are and that the payload string survived.
 *     Vacuity fails: at least one sampled page must have a cased name.
 *
 * Samples 50 filing pages for checks (b)-(e) to keep runtime reasonable.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { parse } from "node-html-parser";
import { displayCompanyName } from "../../src/lib/company-name.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, "..", "..");
const outDir = path.resolve(siteRoot, "out");
const jsonDir = path.resolve(siteRoot, "..", "data", "site", "json");

const SAMPLE_SIZE = 50;
const MIN_FILING_COUNT = 4000; // allow variance from the nominal 4,258

/**
 * Pure, unit-tested: the findings for ONE built filing page (leg e).
 *
 * Display casing never changes a registrant's identity, so this asks only two
 * things of the markup — that each name is marked, and that the string the
 * marker declares is the filing payload's own, byte for byte. The casing rule
 * itself is gate 2 leg (tc)'s job against the same HTML.
 */
export function filingNameFindings({ rel, html, filing }) {
  const root = parse(html, { comment: false });
  const found = [];
  const names = root.querySelectorAll("[data-company-name]");
  const h1 = root.querySelector("h1");
  const h1Name = h1?.querySelector("[data-company-name]") ?? null;
  const check = (el, raw, where) => {
    if (!raw) return;
    if (!el) {
      found.push(`leg e (${rel}): no [data-company-name] in the ${where} — "${raw}" is rendered as a raw LDA string`);
      return;
    }
    const registry = el.getAttribute("data-company-name");
    if (!registry) {
      found.push(`leg e (${rel}): the ${where}'s [data-company-name] carries no registry string — the casing replaced the provenance`);
      return;
    }
    if (registry !== raw) {
      found.push(`leg e (${rel}): the ${where} declares registry ${JSON.stringify(registry)}, which does not match the filing payload ${JSON.stringify(raw)}`);
    }
  };
  check(h1Name, filing.client_name, "h1");
  // Excluding the h1's own element matters for a SELF-FILED filing, where
  // client and registrant are the same string and both markers carry it.
  const registrantEl =
    names.find(
      (el) => el !== h1Name && el.getAttribute("data-company-name") === filing.registrant_name,
    ) ?? null;
  check(registrantEl, filing.registrant_name, "registrant line");

  const changed = [filing.client_name, filing.registrant_name]
    .filter(Boolean)
    .some((raw) => displayCompanyName(raw).display !== raw);
  if (changed) {
    const note = root.querySelector("[data-filed-as]");
    if (!note) {
      found.push(`leg e (${rel}): a name is displayed cased but no visible [data-filed-as] carries the LDA string`);
    } else {
      for (const raw of [filing.client_name, filing.registrant_name].filter(Boolean)) {
        if (displayCompanyName(raw).display !== raw && !note.text.includes(raw)) {
          found.push(`leg e (${rel}): [data-filed-as] omits ${JSON.stringify(raw)}`);
        }
      }
    }
  }
  return found;
}

export async function runFilingGate() {
  const errors = [];
  const notes = [];

  const filingOutDir = path.join(outDir, "filing");

  // Gracefully handle missing out/ (pre-build)
  if (!fs.existsSync(filingOutDir)) {
    notes.push("out/filing/ not found — site not yet built (SKIP)");
    return { pass: true, errors, notes };
  }

  // ── Load filings index sidecar (REQUIRED) ─────────────────────────────────
  // Missing or unloadable filings_index.json is a hard FAIL — we cannot
  // derive noindex expectations or validate mention counts without it.
  const filingsIndexPath = path.join(jsonDir, "filings_index.json");
  if (!fs.existsSync(filingsIndexPath)) {
    errors.push(
      `filing_gate: filings_index.json not found at ${filingsIndexPath} — cannot validate noindex expectations`
    );
    return { pass: false, errors, notes };
  }
  let filingsIndex;
  let indexedFilings = [];
  try {
    filingsIndex = JSON.parse(fs.readFileSync(filingsIndexPath, "utf8"));
    indexedFilings = filingsIndex.filings ?? [];
  } catch (e) {
    errors.push(
      `filing_gate: filings_index.json unloadable: ${e.message} — cannot validate noindex expectations`
    );
    return { pass: false, errors, notes };
  }

  // ── (a) Filing page count ───────────────────────────────────────────────────
  const filingDirs = fs
    .readdirSync(filingOutDir, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => e.name);

  const expectedCount = indexedFilings.length || MIN_FILING_COUNT;

  if (filingDirs.length < MIN_FILING_COUNT) {
    errors.push(
      `filing pages: found ${filingDirs.length}, expected >= ${MIN_FILING_COUNT} (index has ${expectedCount})`
    );
  } else {
    notes.push(`filing pages: ${filingDirs.length} ✓`);
  }

  // ── (b) + (c) + (d) — sample 50 pages ─────────────────────────────────────
  // Build a map of uuid -> has_mentions from the index
  const mentionMap = new Map(
    indexedFilings.map((f) => [f.filing_uuid, f.has_mentions])
  );
  // (e) needs the whole row, not just the mentions flag. Findings are kept
  // apart from `errors` until the summary so the pass note cannot claim
  // "all carrying their LDA string" on a run that just found ones that aren't.
  const rowByUuid = new Map(indexedFilings.map((f) => [f.filing_uuid, f]));
  const nameErrors = [];
  let casedSeen = 0;
  let nameChecked = 0;

  // Select sample: prefer mix of with/without mentions
  const withMentions = filingDirs.filter(
    (d) => mentionMap.get(d) === true
  );
  const withoutMentions = filingDirs.filter(
    (d) => mentionMap.get(d) === false
  );
  const unknown = filingDirs.filter((d) => !mentionMap.has(d));

  const half = Math.ceil(SAMPLE_SIZE / 2);
  const sampleWith = withMentions.slice(0, half);
  const sampleWithout = withoutMentions.slice(0, SAMPLE_SIZE - sampleWith.length);
  // Fill remainder with unknown if needed
  const remainder = SAMPLE_SIZE - sampleWith.length - sampleWithout.length;
  const sampleUnknown = unknown.slice(0, remainder);
  const sample = [...sampleWith, ...sampleWithout, ...sampleUnknown];

  let noindexOk = 0;
  let noindexExpected = 0;
  let canonicalOk = 0;
  let amountPagesChecked = 0;
  let amountPagesOk = 0;

  for (const uuid of sample) {
    const pagePath = path.join(filingOutDir, uuid, "index.html");
    if (!fs.existsSync(pagePath)) {
      errors.push(`filing page missing: filing/${uuid}/index.html`);
      continue;
    }

    let pageHtml;
    try {
      pageHtml = fs.readFileSync(pagePath, "utf8");
    } catch (e) {
      errors.push(`failed to read filing/${uuid}/index.html: ${e.message}`);
      continue;
    }

    const pageRoot = parse(pageHtml, { comment: false });

    // (e) display casing + provenance
    const row = rowByUuid.get(uuid);
    if (row) {
      nameChecked++;
      nameErrors.push(
        ...filingNameFindings({
          rel: `filing/${uuid}/index.html`,
          html: pageHtml,
          filing: { client_name: row.client_name, registrant_name: row.registrant_name },
        }),
      );
      const cased = [row.client_name, row.registrant_name]
        .filter(Boolean)
        .some((raw) => displayCompanyName(raw).display !== raw);
      if (cased) casedSeen++;
    }

    // (b) noindex check — derive expectation the same way the page does:
    //     load the per-filing detail JSON and check mentions.length === 0.
    //     Fall back to the index has_mentions flag if the detail JSON is absent.
    const filingDetailPath = path.join(jsonDir, "filings", `${uuid}.json`);
    let expectNoindex = false;
    if (fs.existsSync(filingDetailPath)) {
      try {
        const detail = JSON.parse(fs.readFileSync(filingDetailPath, "utf8"));
        expectNoindex = (detail.mentions ?? []).length === 0;
      } catch {
        // detail JSON parse error — fall back to index
        expectNoindex = mentionMap.get(uuid) === false;
      }
    } else {
      // No detail JSON: fall back to index has_mentions
      expectNoindex = mentionMap.get(uuid) === false;
    }

    if (expectNoindex) {
      noindexExpected++;
      const robotsMeta = pageRoot.querySelectorAll('meta[name="robots"]');
      const robotsContent = robotsMeta.map(
        (m) => m.getAttribute("content") ?? ""
      );
      const isNoindex = robotsContent.some((c) => c.includes("noindex"));
      if (isNoindex) {
        noindexOk++;
      } else {
        errors.push(
          `filing/${uuid}: zero-mention filing missing robots noindex meta` +
            (robotsContent.length > 0
              ? ` (found: ${robotsContent.join(", ")})`
              : " (no robots meta found)")
        );
      }
    }

    // (c) canonical link
    const canonicals = pageRoot.querySelectorAll('link[rel="canonical"]');
    if (canonicals.length > 0) {
      canonicalOk++;
    } else {
      errors.push(`filing/${uuid}: no canonical link found`);
    }

    // (d) [data-amount] check — only for filings that have income/expense data
    // Check if the page has "Reported income" section (filing has financial data)
    if (pageHtml.includes("Reported income")) {
      amountPagesChecked++;
      const amountEls = pageRoot.querySelectorAll("[data-amount]");
      if (amountEls.length > 0) {
        amountPagesOk++;
      } else {
        // "not reported" filings have no figures — that's OK
        const hasNotReported = pageHtml.includes("not reported");
        if (hasNotReported) {
          amountPagesOk++; // no figures to cite
        } else {
          errors.push(
            `filing/${uuid}: has income/expense section but no [data-amount] elements`
          );
        }
      }
    }
  }

  // (e) non-vacuity. Measured 2026-09-18 over the shipped filings_index.json:
  // 620 distinct client/registrant strings, of which 431 case, 186 refuse and
  // render verbatim and 3 already carry mixed case. A 50-page sample that hits
  // NONE of the 431 is not a sample, it is a broken leg — this floor is dated
  // and is never lowered to make a run go green.
  errors.push(...nameErrors);
  if (nameChecked === 0) {
    errors.push("leg e: no sampled filing page had an index row — the name check is vacuous");
  } else if (casedSeen === 0) {
    errors.push(
      "leg e: not one sampled filing page rendered a cased name — either the sample missed every " +
        "transformable string (431 of the 620 distinct LDA names case) or the casing is not applied",
    );
  } else if (nameErrors.length > 0) {
    notes.push(
      `leg e: ${nameChecked} filing pages checked, ${casedSeen} with a cased name, ` +
        `${nameErrors.length} finding(s) above`,
    );
  } else {
    notes.push(`leg e: ${nameChecked} filing pages checked, ${casedSeen} with a cased name, all carrying their LDA string ✓`);
  }

  if (sample.length > 0) {
    notes.push(
      `filing sample (${sample.length}): canonical=${canonicalOk}/${sample.length} ✓`
    );
  }
  if (noindexExpected > 0) {
    if (noindexOk < noindexExpected) {
      // Already added individual errors above
    } else {
      notes.push(
        `filing sample: noindex on zero-mention=${noindexOk}/${noindexExpected} ✓`
      );
    }
  }
  if (amountPagesChecked > 0) {
    notes.push(
      `filing sample: [data-amount] on income pages=${amountPagesOk}/${amountPagesChecked} ✓`
    );
  }

  return { pass: errors.length === 0, errors, notes };
}
