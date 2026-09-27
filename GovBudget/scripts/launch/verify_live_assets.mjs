#!/usr/bin/env node
/**
 * verify_live_assets.mjs — POST-DEPLOY check that the CDN actually has the
 * assets the freshly-deployed pages cite.
 *
 * WHY THIS IS NOT A GATE IN `npm run verify`.
 *
 *   The `npm run verify` gate suite reads `site/out/` and a local static server. It is
 *   hermetic on purpose: it runs offline, it is deterministic, and a network
 *   flake must never turn it red for reasons that have nothing to do with the
 *   site. This check is the opposite of all three — it asks a remote host a
 *   question whose answer depends on the network.
 *
 *   More decisively: the property it checks is PRODUCTION CDN STATE, which
 *   cannot be true before a deploy. Asserting it inside a pre-deploy gate
 *   would be vacuous at best (the asset legitimately is not up yet) and wrong
 *   at worst (green because it checked the previous deploy's assets). It
 *   belongs AFTER the upload, and it must run by itself rather than sit in a
 *   doc as a step someone remembers — which is exactly how PDF citations
 *   silently degraded in production for every post-launch phase until the
 *   2026-07-04 catch (ROADMAP backlog #27).
 *
 *   So: scripts/launch/deploy.sh runs it automatically as the last step, and a
 *   failure here fails the deploy loudly. It is also runnable on its own to
 *   audit what is live right now.
 *
 * WHAT IT ASSERTS
 *   1. The N most recently added `jbook_pdf` assets (newest PDFs under
 *      data/site/pdfs/ that a jbook_pdf citation actually points at) each
 *      return 200/206 from the asset host, with a non-zero body that begins
 *      with the `%PDF-` magic. "Recently added" is the failure mode: an
 *      ingestion phase mints new citations, the deploy ships pages that cite
 *      them, and the binaries were never synced — the citation panel falls
 *      back to "open official source" and nothing notices.
 *   2. EVERY budget book behind the verified PDF receipts, and every workbook
 *      those receipts offer for download, is on the asset host (same
 *      200/206 + non-empty + magic test: `%PDF-` for books, the zip `PK\x03\x04`
 *      for .xlsx workbooks). The receipt books are NOT jbook_pdf citations —
 *      citations.json never names them — so assertion 1 cannot see them
 *      (backlog finding #19, 2026-09-25: its five probes landed on older
 *      jbook PDFs while all 21 receipt books went unchecked). The set is read
 *      from the receipt shards (data/site/json/budget-pdf-receipts/v2/, the
 *      export, unioned with site/out/json/budget-pdf-receipts/v2/, the copy the
 *      deployed pages fetch): every `parts[].hosted_pdf_url` and
 *      `parts[].workbook_sha256`. ALL of them, not the newest N: which books
 *      were added since the last deploy is not recorded anywhere locally, so
 *      the only set guaranteed to contain them is the whole set — and each
 *      probe is a 1 KB ranged GET.
 *   3. citations/citations.parquet is reachable (the Explorer + citation
 *      lookups read it). Reachability only: the previous deploy's object
 *      answers 200 too, so this alone never showed that a sync landed —
 *      assertion 5 compares the content.
 *   4. The site host's /fact/ rewrite resolves — this comes from
 *      site/out/vercel.json and silently dies if the wrong directory was
 *      deployed. Any deployment that carries the rewrite passes it (every
 *      /fact/<id> returns the /fact/ shell), so it does not tell this deploy
 *      from the one before it — assertion 6 does.
 *   5. THE R2 SYNC LANDED (R-DEC-DEPLOYSAFE, final-review finding #14).
 *      Every fixed-name object upload_r2.sh copies — each file under
 *      data/site/data/ and data/site/citations/ — is served by the asset
 *      host with the local file's sha256 and size (a full GET of each; they
 *      total about 13 MB on 2026-09-26). These keys are overwritten in place
 *      (`rclone copy --checksum`), so a 200 proves nothing: the old object
 *      answers 200 too, and an upload sent to another bucket (an R2_BUCKET
 *      override) left the old checks green. After a successful sync every
 *      one of them equals the local file, whether or not this deploy changed
 *      it, so all of them are compared rather than a guessed subset. A
 *      mismatch means the sync did not land here, or a cache in front of
 *      the bucket still serves the old copy — readers get that copy too.
 *   6. THE VERCEL STEP LANDED (R-DEC-DEPLOYSAFE). The site host's
 *      /.build-meta.json (write-build-meta.mjs writes it into site/out/)
 *      reports git_head == the checkout's HEAD (`git rev-parse HEAD` in the
 *      checkout this script lives in, as deploy.sh's preflight reads it; or
 *      --expect-head), and the same build stamp (built_at) as the local
 *      site/out/.build-meta.json. The stamp matters for a data-only refresh,
 *      which rebuilds at the same commit: git_head alone cannot tell that
 *      deployment from the previous one. Skipped with --skip-site.
 *
 * USAGE
 *   node scripts/launch/verify_live_assets.mjs
 *   node scripts/launch/verify_live_assets.mjs --count=8
 *   node scripts/launch/verify_live_assets.mjs --asset-base=https://... --site=https://...
 *   node scripts/launch/verify_live_assets.mjs --sha=<sha256>   # check exactly this asset
 *                                                               # (no receipt probes)
 *   node scripts/launch/verify_live_assets.mjs --skip-site      # asset host only
 *   node scripts/launch/verify_live_assets.mjs --expect-head=<40-hex sha>
 *                                   # the commit the live site must report, in
 *                                   # place of this checkout's HEAD (an audit of
 *                                   # a build made elsewhere)
 *
 * --count applies to assertion 1 only; the receipt probes (assertion 2) and
 * the fixed-name objects (assertion 5) are never sampled.
 *
 * The asset host defaults to site/public/config.json's `assetBaseUrl`, so the
 * check follows the same host the built pages were told to use.
 *
 * EXIT CODES
 *   0  every assertion passed
 *   1  an assertion failed (missing asset, bad status, empty or non-PDF body,
 *      a fixed-name object whose content differs from the local file, a live
 *      /.build-meta.json that is unreadable or names another build)
 *   2  could not even set up (no citations.json, no PDFs, no receipt shards,
 *      a receipt part whose hosted_pdf_url is not /pdfs/<sha256>.pdf, no
 *      files under data/site/data/, no readable HEAD to compare with, a
 *      site/out/.build-meta.json that is not a build of that HEAD, bad
 *      arguments). Nothing is requested before these are settled.
 */

import { execFileSync } from "child_process";
import crypto from "crypto";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..", "..");
const pdfDir = path.join(repoRoot, "data", "site", "pdfs");
const citationsPath = path.join(repoRoot, "data", "site", "json", "citations.json");
const configPath = path.join(repoRoot, "site", "public", "config.json");
const siteOutMetaPath = path.join(repoRoot, "site", "out", ".build-meta.json");
/**
 * The fixed-name prefixes upload_r2.sh copies (assertion 5). pdfs/ and
 * workbooks/ are content-addressed (<sha256>.<ext>), so a key never changes
 * content; these two are not, and a sync overwrites them in place. data/ is
 * required: without it there is nothing to compare the live objects with.
 */
const fixedNameDirs = [
  { dir: path.join(repoRoot, "data", "site", "data"), prefix: "data", required: true },
  { dir: path.join(repoRoot, "data", "site", "citations"), prefix: "citations", required: false },
];
/**
 * Receipt shard directories, export first. prepare-assets.mjs copies the
 * export into site/out/ at build time; both are read so a book cited by
 * either the export or the deployed copy is probed.
 */
const receiptShardDirs = [
  path.join(repoRoot, "data", "site", "json", "budget-pdf-receipts", "v2"),
  path.join(repoRoot, "site", "out", "json", "budget-pdf-receipts", "v2"),
];

const DEFAULT_COUNT = 5;
const DEFAULT_SITE = "https://fiscalreceipts.com";
/** A known-good /fact/ id for the rewrite check (LAUNCH.md §7d). */
const FACT_PROBE = process.env.FACT_PROBE ?? "3134a6e0";
const TIMEOUT_MS = 30_000;

// ── Arguments ────────────────────────────────────────────────────────────────

function parseArgs(argv) {
  const opts = { count: DEFAULT_COUNT, shas: [], skipSite: false };
  for (const arg of argv) {
    const [k, v] = arg.includes("=") ? arg.split(/=(.*)/s) : [arg, ""];
    switch (k) {
      case "--count":
        opts.count = Number(v);
        break;
      case "--sha":
        opts.shas.push(v.trim().toLowerCase());
        break;
      case "--asset-base":
        opts.assetBase = v;
        break;
      case "--site":
        opts.site = v;
        break;
      case "--skip-site":
        opts.skipSite = true;
        break;
      case "--expect-head":
        opts.expectHead = v.trim();
        break;
      case "--help":
      case "-h":
        opts.help = true;
        break;
      default:
        opts.bad = arg;
    }
  }
  return opts;
}

const opts = parseArgs(process.argv.slice(2));

if (opts.help) {
  const src = fs.readFileSync(fileURLToPath(import.meta.url), "utf8");
  console.log(src.slice(0, src.indexOf(" */") + 3));
  process.exit(0);
}
if (opts.bad) {
  console.error(`ERROR: unknown argument: ${opts.bad}`);
  process.exit(2);
}
if (!Number.isInteger(opts.count) || opts.count < 1) {
  console.error(`ERROR: --count must be a positive integer`);
  process.exit(2);
}
if (opts.expectHead !== undefined && !/^[0-9a-f]{40}$/.test(opts.expectHead)) {
  console.error(
    `ERROR: --expect-head must be a full 40-hex commit sha (lowercase), as ` +
      `/.build-meta.json records it; got ${JSON.stringify(opts.expectHead)}`,
  );
  process.exit(2);
}

/** Asset host: explicit flag > env > the host the built pages were given. */
function resolveAssetBase() {
  if (opts.assetBase) return opts.assetBase;
  if (process.env.ASSET_BASE_URL) return process.env.ASSET_BASE_URL;
  try {
    const cfg = JSON.parse(fs.readFileSync(configPath, "utf8"));
    if (cfg.assetBaseUrl) return cfg.assetBaseUrl;
  } catch {
    /* fall through */
  }
  return null;
}

const assetBase = (resolveAssetBase() ?? "").replace(/\/+$/, "");
const siteBase = (opts.site ?? process.env.SITE_URL ?? DEFAULT_SITE).replace(/\/+$/, "");

if (!assetBase) {
  console.error(
    `ERROR: no asset base URL. Pass --asset-base=<url>, set ASSET_BASE_URL, ` +
      `or write assetBaseUrl into ${path.relative(repoRoot, configPath)}.`,
  );
  process.exit(2);
}

// ── Target selection ─────────────────────────────────────────────────────────

/**
 * The set of sha256s that a `jbook_pdf` citation points at.
 *
 * citations.json is ~90 MB, so it is STREAMED and scanned for the
 * `hosted_pdf_url` field rather than parsed: hosted_pdf_url is populated only
 * for jbook_pdf citations, and its value is exactly the asset path the
 * citation panel requests. Chunks overlap so a value split across a read
 * boundary is not missed.
 */
async function citedPdfShas() {
  const shas = new Set();
  const re = /"hosted_pdf_url"\s*:\s*"\/pdfs\/([0-9a-f]{64})\.pdf/g;
  const stream = fs.createReadStream(citationsPath, {
    encoding: "utf8",
    highWaterMark: 1 << 20,
  });
  let tail = "";
  for await (const chunk of stream) {
    const buf = tail + chunk;
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(buf))) shas.add(m[1]);
    tail = buf.slice(-128); // longer than the longest match
  }
  return shas;
}

/** The `count` most recently added PDF binaries that a citation points at. */
async function selectTargets(count) {
  if (opts.shas.length > 0) {
    return opts.shas.map((sha) => ({ sha, mtime: null, source: "--sha" }));
  }
  if (!fs.existsSync(pdfDir)) {
    console.error(`ERROR: ${path.relative(repoRoot, pdfDir)} not found — run export-site first.`);
    process.exit(2);
  }
  const pdfs = fs
    .readdirSync(pdfDir)
    .filter((n) => /^[0-9a-f]{64}\.pdf$/.test(n))
    .map((n) => ({
      sha: n.slice(0, 64),
      mtime: fs.statSync(path.join(pdfDir, n)).mtimeMs,
    }))
    .sort((a, b) => b.mtime - a.mtime);

  if (pdfs.length === 0) {
    console.error(`ERROR: no PDF assets under ${path.relative(repoRoot, pdfDir)}.`);
    process.exit(2);
  }

  let cited = null;
  if (fs.existsSync(citationsPath)) {
    cited = await citedPdfShas();
  } else {
    console.warn(
      `WARN: ${path.relative(repoRoot, citationsPath)} not found — checking the ` +
        `newest PDF binaries without confirming a citation points at them.`,
    );
  }

  const eligible = cited ? pdfs.filter((p) => cited.has(p.sha)) : pdfs;
  if (eligible.length === 0) {
    console.error(
      `ERROR: none of the ${pdfs.length} local PDF assets is referenced by a ` +
        `jbook_pdf citation — the corpus and the binaries have diverged.`,
    );
    process.exit(2);
  }
  return eligible.slice(0, count).map((p) => ({ ...p, source: "newest cited" }));
}

/**
 * Every asset-host binary the verified PDF receipts depend on (assertion 2):
 *   books      — each part's hosted_pdf_url (/pdfs/<sha>.pdf), the page the
 *                receipt highlights;
 *   workbooks  — each part's workbook_sha256, which the receipt's download
 *                button fetches as /workbooks/<sha>.xlsx
 *                (components/workbook-download.tsx). A workbook_sha256 that
 *                is not 64 hex gets no button (lib/source-document.ts), so it
 *                is no dependency and is not probed.
 * A part whose hosted_pdf_url is not exactly /pdfs/<64 hex>.pdf is a setup
 * error, not a skip: the probe could not cover it, and a silent skip is the
 * blind spot this assertion exists to close.
 */
function receiptTargets() {
  const books = new Map();
  const workbooks = new Map();
  const scanned = [];
  // Part counts are kept per shard directory: the export and the site/out
  // copy normally hold the same receipts, and summing them would double-count.
  const note = (map, key, part, dirIdx) => {
    const entry = map.get(key) ?? { edition: part.edition, exhibit: part.exhibit, partsByDir: [] };
    entry.partsByDir[dirIdx] = (entry.partsByDir[dirIdx] ?? 0) + 1;
    map.set(key, entry);
  };
  for (const [dirIdx, dir] of receiptShardDirs.entries()) {
    if (!fs.existsSync(dir)) continue;
    const rel = path.relative(repoRoot, dir);
    const shards = fs.readdirSync(dir).filter((n) => /^[0-9a-f]{3}\.json$/.test(n));
    let parts = 0;
    for (const name of shards) {
      let shard;
      try {
        shard = JSON.parse(fs.readFileSync(path.join(dir, name), "utf8"));
      } catch (e) {
        console.error(`ERROR: receipt shard ${rel}/${name} is not readable JSON: ${e.message}`);
        process.exit(2);
      }
      for (const [factId, receipt] of Object.entries(shard)) {
        for (const part of receipt?.parts ?? []) {
          parts += 1;
          const m = /^\/pdfs\/([0-9a-f]{64})\.pdf$/.exec(part?.hosted_pdf_url ?? "");
          if (!m) {
            console.error(
              `ERROR: receipt ${factId} in ${rel}/${name} has a part whose hosted_pdf_url ` +
                `is ${JSON.stringify(part?.hosted_pdf_url)}, not /pdfs/<sha256>.pdf — ` +
                `this check cannot probe it.`,
            );
            process.exit(2);
          }
          note(books, m[1], part, dirIdx);
          const wb = part.workbook_sha256;
          if (typeof wb === "string" && /^[a-f0-9]{64}$/i.test(wb)) note(workbooks, wb, part, dirIdx);
        }
      }
    }
    scanned.push({ rel, shards: shards.length, parts });
  }
  if (scanned.length === 0) {
    console.error(
      `ERROR: no receipt shards at ${receiptShardDirs.map((d) => path.relative(repoRoot, d)).join(" or ")} — ` +
        `run \`govbudget export-budget-pdf-receipts\` (the site build refuses to run without them).`,
    );
    process.exit(2);
  }
  if (books.size === 0) {
    console.error(
      `ERROR: the receipt shards (${scanned.map((s) => s.rel).join(", ")}) name no budget ` +
        `book — the receipts and the build have diverged.`,
    );
    process.exit(2);
  }
  const flatten = (sha, { edition, exhibit, partsByDir }) => ({
    sha,
    edition,
    exhibit,
    parts: Math.max(0, ...partsByDir.filter((n) => n !== undefined)),
  });
  const newestFirst = (a, b) =>
    (b[1].edition ?? 0) - (a[1].edition ?? 0) || String(a[1].exhibit).localeCompare(String(b[1].exhibit));
  return {
    scanned,
    books: [...books].sort(newestFirst).map(([sha, meta]) => flatten(sha, meta)),
    workbooks: [...workbooks].sort(newestFirst).map(([sha, meta]) => flatten(sha, meta)),
  };
}

const sha256 = (buf) => crypto.createHash("sha256").update(buf).digest("hex");

/**
 * Every fixed-name object upload_r2.sh copies (assertion 5), with the local
 * file's sha256 and size. The walk mirrors `rclone copy` without -L: regular
 * files at any depth, symlinked entries skipped (rclone skips them too).
 */
function fixedNameTargets() {
  const out = [];
  for (const { dir, prefix, required } of fixedNameDirs) {
    const rel = path.relative(repoRoot, dir);
    if (!fs.existsSync(dir)) {
      if (!required) continue;
      console.error(
        `ERROR: ${rel}/ not found — nothing to compare the live ${prefix}/ objects with. ` +
          `Run \`govbudget export-site\` first.`,
      );
      process.exit(2);
    }
    const files = [];
    const walk = (d) => {
      for (const ent of fs.readdirSync(d, { withFileTypes: true })) {
        const p = path.join(d, ent.name);
        if (ent.isDirectory()) walk(p);
        else if (ent.isFile()) files.push(p);
      }
    };
    walk(dir);
    if (files.length === 0) {
      if (!required) continue;
      console.error(
        `ERROR: ${rel}/ holds no files — nothing to compare the live ${prefix}/ objects with. ` +
          `Run \`govbudget export-site\` first.`,
      );
      process.exit(2);
    }
    for (const f of files.sort()) {
      const buf = fs.readFileSync(f);
      out.push({
        key: `${prefix}/${path.relative(dir, f).split(path.sep).join("/")}`,
        size: buf.length,
        sha256: sha256(buf),
      });
    }
  }
  return out;
}

/**
 * The commit the live site must report (assertion 6): --expect-head, else
 * `git rev-parse HEAD` in the checkout this script lives in — the same
 * command deploy.sh's preflight compares site/out/ against.
 */
function expectedHead() {
  if (opts.expectHead) return { sha: opts.expectHead, source: "--expect-head" };
  try {
    const sha = execFileSync("git", ["-C", repoRoot, "rev-parse", "HEAD"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
    if (/^[0-9a-f]{40}$/.test(sha)) return { sha, source: "git rev-parse HEAD" };
  } catch {
    /* fall through */
  }
  console.error(
    `ERROR: cannot read the checkout's HEAD (git -C ${repoRoot} rev-parse HEAD), so the ` +
      `live /.build-meta.json has nothing to be compared with. Pass --expect-head=<sha>, ` +
      `or --skip-site to check the asset host only.`,
  );
  process.exit(2);
}

/**
 * The local build the live stamp is compared with (assertion 6). When HEAD
 * comes from git (the deploy.sh path), site/out/.build-meta.json must exist
 * and be a build of that HEAD — deploy.sh refuses anything else, and a stamp
 * of another commit's build proves nothing. Under --expect-head (an audit of
 * a build made elsewhere) a local build of another commit, or none, is
 * reported as not compared; git_head is still enforced.
 */
function localBuild(head) {
  const rel = path.relative(repoRoot, siteOutMetaPath);
  const strict = head.source !== "--expect-head";
  const refuse = (why) => {
    console.error(`ERROR: ${rel} ${why}`);
    process.exit(2);
  };
  if (!fs.existsSync(siteOutMetaPath)) {
    if (strict) refuse(`not found — no local build to compare the live build stamp with. Build site/out/ at HEAD first.`);
    return { meta: null, note: `${rel} not found` };
  }
  let meta;
  try {
    meta = JSON.parse(fs.readFileSync(siteOutMetaPath, "utf8"));
  } catch (e) {
    refuse(`is not readable JSON (${e.message}) — rebuild site/out/.`);
  }
  if (meta?.git_head !== head.sha) {
    if (strict) {
      refuse(
        `is a build of ${JSON.stringify(meta?.git_head)}, not of HEAD ${head.sha} — the live build ` +
          `stamp cannot be compared with it. Rebuild site/out/ at HEAD (deploy.sh refuses this too).`,
      );
    }
    return { meta: null, note: `${rel} is a build of ${JSON.stringify(meta?.git_head)}, not of ${head.sha}` };
  }
  if (typeof meta.built_at !== "string" || meta.built_at === "") {
    refuse(`has no built_at stamp — rebuild site/out/.`);
  }
  return { meta, note: null };
}

// ── Assertions ───────────────────────────────────────────────────────────────

const results = [];
function record(ok, label, detail) {
  results.push({ ok, label, detail });
  console.log(`  ${ok ? "PASS" : "FAIL"}: ${label}${detail ? ` — ${detail}` : ""}`);
}

async function fetchWithTimeout(url, init = {}) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), TIMEOUT_MS);
  try {
    return await fetch(url, { ...init, signal: ac.signal, redirect: "follow" });
  } finally {
    clearTimeout(t);
  }
}

const PDF_MAGIC = { bytes: [0x25, 0x50, 0x44, 0x46, 0x2d], name: "%PDF-", kind: "a PDF" };
const XLSX_MAGIC = { bytes: [0x50, 0x4b, 0x03, 0x04], name: "PK\\x03\\x04 (zip)", kind: "an .xlsx" };

/** 200/206 + non-zero body + the file type's magic bytes. */
async function checkBinary(url, label, magicSpec) {
  let res;
  try {
    // Ranged GET: enough bytes to see the magic without pulling 20 MB.
    res = await fetchWithTimeout(url, { headers: { Range: "bytes=0-1023" } });
  } catch (e) {
    record(false, label, `request failed: ${e.message} (${url})`);
    return;
  }
  if (res.status !== 200 && res.status !== 206) {
    record(
      false,
      label,
      `HTTP ${res.status} from ${url} — the binary is not on the CDN. ` +
        `Run scripts/launch/upload_r2.sh --live.`,
    );
    return;
  }
  const body = new Uint8Array(await res.arrayBuffer());
  if (body.length === 0) {
    record(false, label, `HTTP ${res.status} but a ZERO-length body (${url})`);
    return;
  }
  const head = body.slice(0, magicSpec.bytes.length);
  if (head.length !== magicSpec.bytes.length || magicSpec.bytes.some((b, i) => head[i] !== b)) {
    record(
      false,
      label,
      `HTTP ${res.status}, ${body.length} bytes, but the body does not start ` +
        `with ${magicSpec.name} (got ${JSON.stringify(new TextDecoder().decode(head))}) — ` +
        `an error page, not ${magicSpec.kind}`,
    );
    return;
  }
  const total = res.headers.get("content-range")?.split("/")[1];
  record(
    true,
    label,
    `HTTP ${res.status}, ${magicSpec.name} magic, ${total ? `${total} bytes total` : `${body.length} bytes`}`,
  );
}

/** Assertion 1 probe: 200/206 + non-zero body + `%PDF-` magic. */
async function checkPdf(target) {
  await checkBinary(`${assetBase}/pdfs/${target.sha}.pdf`, `PDF ${target.sha.slice(0, 12)}…`, PDF_MAGIC);
}

/** Assertion 2 probes: every receipt book and receipt workbook. */
async function checkReceiptAssets(receipts, alreadyChecked) {
  const localNote = (dir, file) =>
    fs.existsSync(path.join(repoRoot, "data", "site", dir, file))
      ? ""
      : ` [NOT in data/site/${dir}/ — upload_r2.sh cannot ship it]`;
  const books = receipts.books.filter((b) => !alreadyChecked.has(b.sha));
  const skipped = receipts.books.length - books.length;
  console.log(
    `── ${receipts.books.length} receipt budget book(s) [every book a receipt part cites` +
      `${skipped ? `; ${skipped} already probed above` : ""}] ──`,
  );
  for (const b of books) {
    await checkBinary(
      `${assetBase}/pdfs/${b.sha}.pdf`,
      `PDF ${b.sha.slice(0, 12)}… PB${b.edition} ${b.exhibit} (${b.parts.toLocaleString("en-US")} receipt part${b.parts === 1 ? "" : "s"})` +
        localNote("pdfs", `${b.sha}.pdf`),
      PDF_MAGIC,
    );
  }
  console.log("");
  console.log(
    `── ${receipts.workbooks.length} receipt workbook(s) [every workbook a receipt offers for download] ──`,
  );
  for (const w of receipts.workbooks) {
    await checkBinary(
      `${assetBase}/workbooks/${w.sha}.xlsx`,
      `XLSX ${w.sha.slice(0, 12)}… PB${w.edition} ${w.exhibit}` + localNote("workbooks", `${w.sha}.xlsx`),
      XLSX_MAGIC,
    );
  }
}

async function checkUrl(label, url, { expectBody = true } = {}) {
  let res;
  try {
    res = await fetchWithTimeout(url);
  } catch (e) {
    record(false, label, `request failed: ${e.message} (${url})`);
    return;
  }
  if (res.status !== 200) {
    record(false, label, `HTTP ${res.status} from ${url}`);
    return;
  }
  const len = (await res.arrayBuffer()).byteLength;
  if (expectBody && len === 0) {
    record(false, label, `HTTP 200 but a ZERO-length body (${url})`);
    return;
  }
  record(true, label, `HTTP 200, ${len} bytes`);
}

/** Assertion 5 probe: the live object's sha256 and size equal the local file's. */
async function checkFixedName(t) {
  const url = `${assetBase}/${t.key.split("/").map(encodeURIComponent).join("/")}`;
  let res;
  try {
    res = await fetchWithTimeout(url, { headers: { "Cache-Control": "no-cache" } });
  } catch (e) {
    record(false, t.key, `request failed: ${e.message} (${url})`);
    return;
  }
  if (res.status !== 200) {
    record(
      false,
      t.key,
      `HTTP ${res.status} from ${url} — the object is not on the asset host. ` +
        `Run scripts/launch/upload_r2.sh --live.`,
    );
    return;
  }
  const body = Buffer.from(await res.arrayBuffer());
  const got = sha256(body);
  const etag = res.headers.get("etag");
  if (got !== t.sha256 || body.length !== t.size) {
    record(
      false,
      t.key,
      `live sha256 ${got.slice(0, 12)}… (${body.length} bytes) != local sha256 ` +
        `${t.sha256.slice(0, 12)}… (${t.size} bytes) — the R2 sync did not replace it here ` +
        `(did upload_r2.sh --live run, into this bucket?), or a cache in front of the ` +
        `bucket still serves the old copy (${url})`,
    );
    return;
  }
  record(
    true,
    t.key,
    `sha256 ${got.slice(0, 12)}… matches the local file (${body.length} bytes${etag ? `, ETag ${etag}` : ""})`,
  );
}

/** Assertion 6 probe: the live /.build-meta.json names this HEAD and this build. */
async function checkBuildMeta(head, local) {
  const label = "/.build-meta.json git_head";
  // A throwaway query string: static hosts ignore it, and no cache between
  // here and the deployment can answer with a copy from before the deploy.
  const url = `${siteBase}/.build-meta.json?verify=${Date.now()}`;
  let res;
  try {
    res = await fetchWithTimeout(url, { headers: { "Cache-Control": "no-cache" } });
  } catch (e) {
    record(false, label, `request failed: ${e.message} (${url}) — cannot tell which build is live`);
    return;
  }
  if (res.status !== 200) {
    record(false, label, `HTTP ${res.status} from ${url} — cannot tell which build is live`);
    return;
  }
  let live;
  try {
    live = JSON.parse(await res.text());
  } catch {
    record(false, label, `the body of ${url} is not JSON — cannot tell which build is live`);
    return;
  }
  if (typeof live?.git_head !== "string" || live.git_head === "") {
    record(false, label, `${url} carries no git_head — cannot tell which build is live`);
    return;
  }
  if (live.git_head !== head.sha) {
    record(
      false,
      label,
      `live ${live.git_head} != HEAD ${head.sha} (${head.source}) — the site host serves ` +
        `another build: the Vercel step did not land`,
    );
    return;
  }
  record(true, label, `${live.git_head} == HEAD (${head.source})`);

  const buildLabel = "/.build-meta.json build";
  if (!local.meta) {
    console.log(`  NOTE: ${buildLabel} not compared — ${local.note}`);
    return;
  }
  const sameMs = local.meta.built_at_ms === undefined || live.built_at_ms === local.meta.built_at_ms;
  if (live.built_at !== local.meta.built_at || !sameMs) {
    record(
      false,
      buildLabel,
      `live built_at ${live.built_at} != site/out/.build-meta.json built_at ${local.meta.built_at} — ` +
        `the same commit, but not this build: the rebuild was not deployed`,
    );
    return;
  }
  record(true, buildLabel, `built_at ${live.built_at} == site/out/.build-meta.json`);
}

// ── Run ──────────────────────────────────────────────────────────────────────

async function main() {
  console.log("═══════════════════════════════════════════════════════════════════");
  console.log("  post-deploy live-asset verification");
  console.log("═══════════════════════════════════════════════════════════════════");
  console.log(`  asset host: ${assetBase}`);
  if (!opts.skipSite) console.log(`  site host:  ${siteBase}`);
  console.log("");

  const targets = await selectTargets(opts.count);
  // Read the receipt set BEFORE any request, so a setup error (exit 2) never
  // follows a half-finished run.  --sha means "exactly this asset".
  const receipts = opts.shas.length > 0 ? null : receiptTargets();
  // Likewise the fixed-name set, the HEAD and the local build (assertions
  // 5 and 6): every setup error exits 2 before the first request.
  const fixedNames = fixedNameTargets();
  const head = opts.skipSite ? null : expectedHead();
  const local = head ? localBuild(head) : null;
  if (receipts) {
    for (const s of receipts.scanned) {
      console.log(`  receipts:   ${s.rel} — ${s.shards} shards, ${s.parts.toLocaleString("en-US")} parts`);
    }
  }
  console.log(
    `  fixed-name: ${fixedNames.length} object(s) under ${fixedNameDirs
      .map((d) => `${path.relative(repoRoot, d.dir)}/`)
      .join(", ")}`,
  );
  if (head) console.log(`  expect:     git_head ${head.sha} (${head.source})`);
  console.log("");
  console.log(
    `── ${targets.length} recently-added jbook_pdf asset(s) [${targets[0].source}] ──`,
  );
  for (const t of targets) await checkPdf(t);

  if (receipts) {
    console.log("");
    await checkReceiptAssets(receipts, new Set(targets.map((t) => t.sha)));
  }

  console.log("");
  console.log("── R2 data assets (reachable) ──");
  await checkUrl("citations/citations.parquet", `${assetBase}/citations/citations.parquet`);

  console.log("");
  console.log(
    `── ${fixedNames.length} fixed-name R2 object(s) [the sync landed: live sha256 == local file] ──`,
  );
  for (const t of fixedNames) await checkFixedName(t);

  if (!opts.skipSite) {
    console.log("");
    console.log("── site host (which build is live; the /fact/ rewrite) ──");
    await checkBuildMeta(head, local);
    await checkUrl(`/fact/${FACT_PROBE}`, `${siteBase}/fact/${FACT_PROBE}`);
    await checkUrl("/json/years_matrix.json", `${siteBase}/json/years_matrix.json`);
  }

  const failed = results.filter((r) => !r.ok);
  console.log("");
  if (failed.length > 0) {
    console.log(
      `FAIL: ${failed.length} of ${results.length} live-asset assertion(s) failed.`,
    );
    console.log(
      `Assets missing from the CDN mean citation panels fall back to "open ` +
        `official source" for every reader. Re-run: scripts/launch/upload_r2.sh --live`,
    );
    console.log(
      `A fixed-name object that differs from data/site/ means the R2 sync did not ` +
        `land (or landed in another bucket); a /.build-meta.json that names another ` +
        `build means the site host is not serving this one (re-run the Vercel step).`,
    );
    process.exit(1);
  }
  console.log(`All ${results.length} live-asset assertions passed.`);
}

main().catch((e) => {
  console.error(`verify_live_assets: unhandled error: ${e?.stack ?? e}`);
  process.exit(1);
});
