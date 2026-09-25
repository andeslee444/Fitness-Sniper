/**
 * gate — type_gate (the type system, RENDERED)
 *
 * tokens.mjs proves the source only names faces and sizes through tokens.
 * This gate proves what actually painted: that the vendored faces loaded,
 * that every label, figure, identifier and heading resolved to its role, and
 * that nothing on a page is set outside the ladder. It is the rendered half
 * of the 2026-09-12 type system, written against the nine critics' words:
 * "mono eyebrows at two sizes and two trackings between pages", "$10.7B
 * reads as a terminal", "a technical costume rather than a type system".
 *
 * Routes: /, /programs/, one full-tier program page, /company/lockheed-martin/,
 * /data/, /flow/, one /fact/ permalink, /families/f-15/ and its #funding
 * workspace — at 1440×900 and 390×844.
 *
 * Legs (all FAIL):
 *  (0) faces — the three vendored faces load from the origin (document.fonts.load;
 *      the mono is CSS-discovered, so it is asked for rather than required painted)
 *      and no request went to fonts.googleapis.com / fonts.gstatic.com; the two
 *      preload <link>s (serif, sans) are present on every route.
 *  (a) labels — every `.t-label` computes the sans at 12px / 500 / uppercase /
 *      0.96px tracking; and every element whose text is rendered uppercase
 *      below 14px is a `.t-label`, a `[data-plate-mark]`, or inside an <svg>
 *      — the "exactly one eyebrow spec" invariant.
 *  (b) figures — every `.t-figure` computes the --font-figure family, weight
 *      500, a ladder size, and tabular-nums.
 *  (c) floor — no rendered text computes below 12px, except inside <svg> or
 *      `[data-plate-mark]`, where the floor is 10px.
 *  (d) weights — computed font-weight ∈ {400, 500, 600} on every text
 *      element; computed italic ⇒ the serif at 400 (the only italic vendored).
 *  (e) faces everywhere — the first family of every text element's computed
 *      font-family is one of the three vendored faces (a raw `monospace` or
 *      `Georgia` leak the static scan could not see fails here).
 *  (f) money never in the mono — no text node starting with a currency figure
 *      computes to the identifier face.
 *  (g) headings — every h1/h2/h3 computes the serif at 500 and a ladder size
 *      (h1 32–48, or 48–72 with data-display; h2 28; h3 22).
 *  (h) ratchet — the `font-mono` utility count across the sampled built pages
 *      may not exceed the number frozen in type-allowlist-ratchet.json; new
 *      code writes t-id / t-figure, never font-mono.
 *
 * Elements are sampled as every element that owns a non-whitespace text node
 * and paints (non-zero box, not visibility:hidden). Violations are reported
 * per (route, viewport, leg) with the first few selectors and a count.
 *
 * Export: runTypeGate({ baseUrl, browser? }) → { pass, errors, notes }
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { chromium } from "playwright";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, "..", "..");
const outDir = path.resolve(siteRoot, "out");
const RATCHET_PATH = path.join(__dirname, "type-allowlist-ratchet.json");

const FACES = ["Source Serif 4", "Source Sans 3", "Source Code Pro"];
const VIEWPORTS = [
  { width: 1440, height: 900 },
  { width: 390, height: 844 },
];
const LADDER_PX = new Set([12, 14, 16, 17, 22, 28, 32, 48, 72]);
const FIG_PX = new Set([12, 14, 17, 22, 32, 48, 72]);

function sampleRoutes() {
  const routes = ["/", "/programs/", "/company/lockheed-martin/", "/data/", "/flow/", "/families/f-15/", "/families/f-15/#funding"];
  const programDir = path.join(outDir, "program");
  if (fs.existsSync(programDir)) {
    const slugs = fs.readdirSync(programDir).filter((d) => fs.existsSync(path.join(programDir, d, "index.html"))).sort();
    const pick = slugs.find((s) => /^0606301D8Z$/.test(s)) ?? slugs[0];
    if (pick) routes.push(`/program/${pick}/`);
  }
  const factDir = path.join(outDir, "fact");
  if (fs.existsSync(path.join(factDir, "index.html"))) routes.push("/fact/");
  return routes;
}

/** In-page audit. Returns aggregates only (the pages are large). */
function auditScript() {
  return () => {
    const first = (ff) => (ff || "").split(",")[0].trim().replace(/^["']|["']$/g, "");
    const rootStyle = getComputedStyle(document.documentElement);
    const figureFace = first(rootStyle.getPropertyValue("--font-figure") || rootStyle.getPropertyValue("--font-serif"));
    const sel = (el) => {
      const id = el.id ? `#${el.id}` : "";
      const cls = typeof el.className === "string" && el.className ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".") : "";
      const testid = el.getAttribute("data-testid") ? `[data-testid=${el.getAttribute("data-testid")}]` : "";
      return `${el.tagName.toLowerCase()}${id}${cls}${testid}`;
    };
    const ownsText = (el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 0);
    const painted = (el) => {
      const cs = getComputedStyle(el);
      if (cs.visibility === "hidden" || cs.display === "none") return false;
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    };
    const inSvg = (el) => !!el.closest("svg");
    const isPlateMark = (el) => !!el.closest("[data-plate-mark]");
    const push = (bucket, el, extra = "") => {
      const b = out[bucket];
      b.count += 1;
      if (b.examples.length < 4) b.examples.push(`${sel(el)}${extra ? ` (${extra})` : ""}`);
    };
    const out = {};
    for (const k of ["label_spec", "label_only", "figure_spec", "floor", "weight", "italic", "face", "money_mono", "heading"]) out[k] = { count: 0, examples: [] };

    const all = [...document.querySelectorAll("body *")].filter((el) => ownsText(el) && painted(el));
    for (const el of all) {
      const cs = getComputedStyle(el);
      const px = parseFloat(cs.fontSize);
      const face = first(cs.fontFamily);
      const weight = Math.round(parseFloat(cs.fontWeight));
      const text = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join("").trim();
      const svg = inSvg(el), plate = isPlateMark(el);

      // (c) floor
      const floor = svg || plate ? 10 : 12;
      if (px < floor - 0.01) push("floor", el, `${px.toFixed(2)}px`);

      // (d) weights, italic
      if (![400, 500, 600].includes(weight)) push("weight", el, `weight ${weight}`);
      if (cs.fontStyle === "italic" && !(face === "Source Serif 4" && weight === 400)) push("italic", el, `${face} ${weight}`);

      // (e) faces everywhere
      if (!FACES_IN_PAGE.includes(face)) push("face", el, face);

      // (f) money never in the mono
      if (/^\s*[-−+]?\$\d/.test(text) && face === "Source Code Pro") push("money_mono", el, text.slice(0, 12));

      // (a) uppercase small text must be a label, a plate mark, or svg
      if (cs.textTransform === "uppercase" && px < 14 && !el.closest(".t-label") && !plate && !svg) push("label_only", el, `${px.toFixed(1)}px uppercase`);
    }

    // (a) every .t-label
    for (const el of document.querySelectorAll(".t-label")) {
      if (!painted(el)) continue;
      const cs = getComputedStyle(el);
      const ok = first(cs.fontFamily) === "Source Sans 3" && Math.round(parseFloat(cs.fontSize)) === 12 && Math.round(parseFloat(cs.fontWeight)) === 500 && cs.textTransform === "uppercase" && Math.abs(parseFloat(cs.letterSpacing) - 0.96) < 0.05;
      if (!ok) push("label_spec", el, `${first(cs.fontFamily)} ${cs.fontSize} ${cs.fontWeight} ${cs.textTransform} ${cs.letterSpacing}`);
    }
    // (b) every .t-figure
    for (const el of document.querySelectorAll(".t-figure")) {
      if (!painted(el)) continue;
      const cs = getComputedStyle(el);
      const px = Math.round(parseFloat(cs.fontSize));
      const ok = first(cs.fontFamily) === figureFace && Math.round(parseFloat(cs.fontWeight)) === 500 && FIG_PX_IN_PAGE.includes(px) && /tabular-nums/.test(cs.fontVariantNumeric);
      if (!ok) push("figure_spec", el, `${first(cs.fontFamily)} ${cs.fontSize} ${cs.fontWeight} ${cs.fontVariantNumeric}`);
    }
    // (g) headings
    for (const el of document.querySelectorAll("h1, h2, h3")) {
      if (!painted(el)) continue;
      const cs = getComputedStyle(el);
      const px = parseFloat(cs.fontSize);
      const tag = el.tagName.toLowerCase();
      const display = tag === "h1" && (el.hasAttribute("data-display") || el.parentElement?.hasAttribute("data-display"));
      const sizeOk = tag === "h1" ? (display ? px >= 47.5 && px <= 72.5 : px >= 31.5 && px <= 48.5) : tag === "h2" ? Math.round(px) === 28 : Math.round(px) === 22;
      const ok = first(cs.fontFamily) === "Source Serif 4" && Math.round(parseFloat(cs.fontWeight)) === 500 && sizeOk;
      if (!ok) push("heading", el, `${first(cs.fontFamily)} ${cs.fontSize} ${cs.fontWeight}`);
    }

    // Loaded, or loadable from the origin: the mono is CSS-discovered and a
    // page with no identifier painted has not fetched it yet — ask for it
    // (a failed fetch, e.g. a wrong path, rejects and reads as not loaded).
    const fonts = { serif: false, sans: false, mono: false };
    return Promise.all([
      document.fonts.load('500 16px "Source Serif 4"').then((f) => (fonts.serif = f.length > 0), () => {}),
      document.fonts.load('400 16px "Source Sans 3"').then((f) => (fonts.sans = f.length > 0), () => {}),
      document.fonts.load('400 12px "Source Code Pro"').then((f) => (fonts.mono = f.length > 0), () => {}),
    ]).then(() => ({ out, fonts, preloads: [...document.querySelectorAll('link[rel="preload"][as="font"]')].map((l) => l.getAttribute("href")), sampled: all.length, figureFace }));
  };
}
export async function runTypeGate({ baseUrl, browser: given } = {}) {
  const errors = [];
  const notes = [];
  if (!fs.existsSync(outDir)) {
    errors.push("type_gate: out/ not found — build first");
    return { pass: false, errors, notes };
  }
  const routes = sampleRoutes();
  const browser = given ?? (await chromium.launch());
  const externalFontRequests = [];
  let sampledTotal = 0;
  try {
    for (const vp of VIEWPORTS) {
      const context = await browser.newContext({ viewport: vp });
      const page = await context.newPage();
      page.on("request", (req) => {
        const u = req.url();
        if (/fonts\.(googleapis|gstatic)\.com/.test(u)) externalFontRequests.push(u);
      });
      for (const route of routes) {
        try {
          await page.goto(`${baseUrl}${route}`, { waitUntil: "networkidle", timeout: 60000 });
        } catch (e) {
          errors.push(`type_gate: ${route} @${vp.width}: navigation failed — ${e.message.split("\n")[0]}`);
          continue;
        }
        if (route.endsWith("#funding")) await page.waitForTimeout(500);
        await page.evaluate(() => document.fonts.ready.then(() => true));
        // reveal below-fold content so IntersectionObserver-gated sections paint
        const total = await page.evaluate(() => document.documentElement.scrollHeight);
        for (let y = 0; y < Math.min(total, 12000); y += 700) {
          await page.evaluate((v) => window.scrollTo(0, v), y);
          await page.waitForTimeout(40);
        }
        await page.evaluate(() => window.scrollTo(0, 0));
        const r = await page.evaluate(
          ({ faces, fig }) => {
            globalThis.FACES_IN_PAGE = faces;
            globalThis.FIG_PX_IN_PAGE = fig;
            return null;
          },
          { faces: FACES, fig: [...FIG_PX] },
        ).then(() => page.evaluate(auditScript()));
        sampledTotal += r.sampled;
        const tag = `${route} @${vp.width}`;
        if (!r.fonts.serif || !r.fonts.sans || !r.fonts.mono) errors.push(`type_gate (0): ${tag}: vendored faces not loaded — serif=${r.fonts.serif} sans=${r.fonts.sans} mono=${r.fonts.mono}`);
        const wantPre = ["/fonts/source-serif-4/v14/SourceSerif4Variable-Roman.woff2", "/fonts/source-sans-3/v19/SourceSans3Variable-Roman.woff2"];
        for (const p of wantPre) if (!r.preloads.includes(p)) errors.push(`type_gate (0): ${tag}: missing <link rel="preload" as="font"> for ${p}`);
        const legs = {
          label_spec: "(a) .t-label off spec",
          label_only: "(a) uppercase text under 14px that is not a .t-label / plate mark / svg",
          figure_spec: "(b) .t-figure off spec",
          floor: "(c) text below the 12px floor (10px in svg / plate marks)",
          weight: "(d) font-weight outside {400,500,600}",
          italic: "(d) italic that is not the serif at 400",
          face: "(e) computed family is not a vendored face",
          money_mono: "(f) a currency figure set in the identifier face",
          heading: "(g) h1/h2/h3 off the ladder or not the serif at 500",
        };
        for (const [k, label] of Object.entries(legs)) {
          const b = r.out[k];
          if (b.count > 0) errors.push(`type_gate ${label}: ${tag}: ${b.count} element(s) — e.g. ${b.examples.join("; ")}`);
        }
      }
      await context.close();
    }
  } finally {
    if (!given) await browser.close();
  }
  if (externalFontRequests.length) errors.push(`type_gate (0): ${externalFontRequests.length} request(s) to Google Fonts — every face is self-hosted: ${externalFontRequests[0]}`);
  notes.push(`sampled ${routes.length} routes × ${VIEWPORTS.length} viewports, ${sampledTotal} text elements`);

  // (h) ratchet on the font-mono utility across the sampled built pages
  let monoCount = 0;
  for (const route of routes) {
    const file = path.join(outDir, route.replace(/#.*$/, "").replace(/^\//, ""), "index.html");
    if (!fs.existsSync(file)) continue;
    monoCount += (fs.readFileSync(file, "utf8").match(/(?<![\w-])font-mono(?![\w-])/g) || []).length;
  }
  if (process.env.TYPE_RATCHET_EMIT === "1") {
    fs.writeFileSync(RATCHET_PATH, JSON.stringify({ fontMonoClassCount: monoCount, frozen: "2026-09-12 (iteration 8) — new code writes t-id / t-figure, never font-mono; this number may only fall" }, null, 2) + "\n");
    notes.push(`ratchet: TYPE_RATCHET_EMIT froze font-mono count at ${monoCount}`);
  } else if (fs.existsSync(RATCHET_PATH)) {
    const frozen = JSON.parse(fs.readFileSync(RATCHET_PATH, "utf8")).fontMonoClassCount;
    if (monoCount > frozen) errors.push(`type_gate (h): font-mono utility count rose to ${monoCount} across the sampled pages (frozen at ${frozen}) — new code writes t-id / t-figure, never font-mono`);
    else notes.push(`ratchet: font-mono ${monoCount} ≤ frozen ${frozen} ✓${monoCount < frozen ? " (re-freeze with TYPE_RATCHET_EMIT=1 to lock the gain)" : ""}`);
  } else {
    notes.push(`ratchet: no type-allowlist-ratchet.json yet — run with TYPE_RATCHET_EMIT=1 to freeze font-mono at ${monoCount}`);
  }
  if (errors.length === 0) notes.push("type: every label, figure, identifier and heading resolved to its role; faces self-hosted and loaded ✓");
  return { pass: errors.length === 0, errors, notes };
}
