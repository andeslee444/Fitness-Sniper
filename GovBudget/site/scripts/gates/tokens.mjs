/**
 * gate — tokens_gate (design system: "tokens are the palette")
 *
 * Pure static scan enforcing the single colour/type system. The rule this gate
 * enforces:
 *
 *   src/app/globals.css is the DECLARATION SITE. Colours live there as oklch
 *   custom properties (--background, --foreground, --cite-decoration, …) and
 *   the typefaces live there as --font-* variables. Everything else in
 *   site/src consumes those tokens through var(). No other file may introduce
 *   a colour value of its own — not as a hex literal, not as rgb()/rgba(), not
 *   as its own oklch() — and no other file may name a typeface.
 *
 *   The failure this prevents is drift, and drift here is invisible: a raw
 *   #6b7280 looks right in light mode and is unreadable in dark, and nothing
 *   downstream reports it. Tokens are the only thing that flips.
 *
 *   Existing raw values are enumerated in token-allowlist.json, one entry per
 *   (file, value) pair, each carrying a written reason — the same convention
 *   as prose-allowlist.json. The allowlist freezes the debt at its current
 *   size: adding a NEW raw value anywhere in src fails immediately, and an
 *   entry that stops matching is a stale exemption and also fails, so the list
 *   can only shrink by being edited on purpose.
 *
 * Checks:
 * 1. NO raw hex colours (#rgb, #rgba, #rrggbb, #rrggbbaa) in site/src outside
 *    globals.css and the allowlist. In .css the scan is restricted to
 *    DECLARATION VALUES (text after a `prop:` up to the next `;`/`}`), so an
 *    `#id` selector — which is not a colour — is structurally out of scope. In
 *    .ts/.tsx a hex counts only in a colour-shaped position: a string literal
 *    that is exactly a hex (`stroke="#e5e7eb"`), a Tailwind arbitrary value
 *    (`bg-[#0a161f]`), or a hex after a CSS colon inside a style string. That
 *    keeps URL fragments (`/methodology/#feed`, `#fact-bb54b165`) and HTML
 *    entities (`&#8220;`) out — they merely look like hex. One collision is
 *    irreducible: a BARE 8-hex fact id in a test assertion (`"#abc123de"`) is
 *    character-for-character a valid #rrggbbaa. The three that exist are
 *    enumerated in the allowlist and say so in their reason.
 * 2. NO raw rgb()/rgba() colour literals outside globals.css. `oklchToSrgb(`
 *    and an escaped `rgb\(` inside a RegExp source are not matches.
 * 3. NO raw oklch() literals outside globals.css. `oklch()` written in prose
 *    inside an error message, and `oklch\\(` inside a RegExp that PARSES
 *    globals.css, are not colour literals and are not matches.
 * 4. NO type declaration outside globals.css that fails to resolve ENTIRELY
 *    through var() custom properties. `font-family: var(--font-mono)` passes,
 *    and so does `var(--font-editorial, Georgia, serif)` — the fallback chain
 *    lives inside the token. `font-family: "IBM Plex Sans", sans-serif` and
 *    `font-family: monospace` fail. So does a custom property that builds its
 *    own stack on top of a token (`--register-sans: "IBM Plex Sans",
 *    var(--font-sans, sans-serif)`) — renaming the property does not stop it
 *    being a font-family declaration. Covered props: `font-family`, `fontFamily`
 *    in .tsx, and any custom property named `--*font*` or `--*-serif/sans/mono`.
 *    @font-face blocks are structurally exempt: the `font-family` descriptor
 *    inside one NAMES the face being defined and cannot be a var().
 * 5. Allowlist hygiene (all FAIL, not warn), mirroring prose-allowlist.mjs:
 *    every entry needs file + value + reason; the file must exist; and every
 *    entry must actually match something. An exemption nobody explained is an
 *    exemption nobody can review, and an exemption that matches nothing is how
 *    an escape hatch grows without anyone noticing.
 * 6. THE SIZE LADDER (2026-09-12, the type system). Outside globals.css a
 *    font size is a token, not a number: every `font-size:` value and the
 *    size token of every `font:` shorthand must be `var(--text-*)` /
 *    `var(--fig-*)` (or the whole shorthand a single `var(--type-*)`), and a
 *    `letter-spacing:` must be `var(--tracking-*)`, `0`, or `normal`. In .tsx
 *    the same rule reads Tailwind: `text-[…]` arbitrary sizes and
 *    `text-lg|xl|2xl|…` (anything above text-base) and `tracking-*`
 *    utilities are off the ladder. Nine critics read "mono eyebrows at two
 *    sizes and two trackings between pages" as the absence of a type
 *    system; a size that is not a token is exactly that. The debt that
 *    existed when the ladder landed is enumerated in type-allowlist.json
 *    (`{file, value, reason}`; seed/merge it with `TYPE_ALLOWLIST_EMIT=1`)
 *    under the same hygiene as check 5 — it can only shrink.
 *    The `font:` shorthand is also parsed for check 4: its family part must
 *    resolve through var() like a `font-family` would (`font: 10px monospace`
 *    names a face; it used to slip past a scan that only read `font-family`).
 * 7. THE DECLARATION SITE IS COMPLETE AND ALONE. globals.css declares exactly
 *    the three faces (--font-sans, --font-serif, --font-mono) and the three
 *    roles (--font-figure, --font-label, --font-id); no file declares a
 *    `--register-*` or `--font-editorial` token, and nothing consumes
 *    `var(--font-editorial)` — the transitional alias is deleted with its
 *    last consumer, and a private register on one page is "two products".
 *
 * Cost: pure source scan — no build, no server, no network. ~270 files.
 *
 * Export: runTokensGate() → { pass, errors, notes }
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, "..", "..");
const srcDir = path.resolve(siteRoot, "src");
const ALLOWLIST_PATH = path.join(__dirname, "token-allowlist.json");
const TYPE_ALLOWLIST_PATH = path.join(__dirname, "type-allowlist.json");

/** The one file allowed to declare colour and type values (relative to site/). */
const DECLARATION_SITE = "src/app/globals.css";

/** Hex colour lengths CSS actually accepts. 5 and 7 digits are not colours. */
const HEX_LENGTHS = new Set([3, 4, 6, 8]);

/**
 * Declarations check 4 treats as type declarations: `font-family` itself, plus
 * any custom property whose NAME is about type. Renaming `font-family` to
 * `--register-sans` does not stop the value being a font stack.
 */
const TYPE_PROP_RE = /^(font-family|--[\w-]*font[\w-]*|--[\w-]*-(serif|sans|mono))$/;

/** Face tokens the declaration site must define (check 7). */
const FACE_TOKENS = ["--font-sans", "--font-serif", "--font-mono"];
const ROLE_TOKENS = ["--font-figure", "--font-label", "--font-id"];
/** A font size / letter-spacing that IS on the ladder (check 6). */
const LADDER_SIZE_RE = /^var\(--(text|fig)-[\w-]+\)$/;
const LADDER_TRACK_RE = /^(var\(--tracking-[\w-]+\)|0|normal)$/;
/** Tailwind utilities off the ladder: arbitrary sizes, sizes above base, trackings. */
const TW_OFF_LADDER_RE = /(?<![\w-])(?:text-\[[^\]]*(?:px|rem|em)\]|text-(?:lg|xl|[2-9]xl)|tracking-(?:tighter|tight|normal|wide|wider|widest|\[[^\]]+\]))(?![\w-])/g;

/**
 * Split a `font:` shorthand into { size, lineHeight, family }. The value is
 * `[style] [variant] [weight] [stretch] size[/line-height] family` — the size
 * is the first token that looks like a length, a clamp(), or a var(); what
 * follows is the family. A bare `var(--type-*)` is a composite role token.
 */
export function splitFontShorthand(value) {
  const v = value.trim().replace(/\s+/g, " ");
  if (/^var\(--type-[\w-]+\)$/.test(v)) return { composite: v };
  const tokens = [];
  let depth = 0, cur = "";
  for (const ch of v) {
    if (ch === "(") depth++;
    if (ch === ")") depth--;
    if (ch === " " && depth === 0) { if (cur) tokens.push(cur); cur = ""; continue; }
    cur += ch;
  }
  if (cur) tokens.push(cur);
  const isSize = (t) => /^(?:[\d.]+(?:px|rem|em|%)|clamp\(.*\)|var\(--[\w-]+\))(?:\/.+)?$/.test(t);
  const i = tokens.findIndex(isSize);
  if (i === -1) return { size: null, family: v };
  const [size, lineHeight] = tokens[i].split("/");
  return { size, lineHeight: lineHeight ?? null, family: tokens.slice(i + 1).join(" ") };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Recursively collect files under dir matching extensions. (as motion.mjs) */
function collectFiles(dir, exts, acc = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      collectFiles(full, exts, acc);
    } else if (exts.some((e) => entry.name.endsWith(e))) {
      acc.push(full);
    }
  }
  return acc;
}

/** Replace every character of `text` except newlines with a space. */
function blank(text) {
  return text.replace(/[^\n]/g, " ");
}

/**
 * Strip comments so documentation prose ("the old #6b7280 grey") doesn't trip
 * the scan. Same approach as motion.mjs's stripComments — block comments in
 * all files, line comments in ts/tsx — with one addition: comments are
 * replaced by blanks rather than deleted, so line numbers survive and the gate
 * can name file:line. The `//` heuristic may also truncate URL strings, which
 * is harmless here (a URL is not a colour).
 */
function stripComments(text, ext) {
  let out = text.replace(/\/\*[\s\S]*?\*\//g, blank);
  if (ext !== ".css") {
    out = out.replace(/(^|[^:])\/\/.*$/gm, (m, p1) => p1 + blank(m.slice(p1.length)));
  }
  return out;
}

/**
 * Blank out @font-face blocks (check 4): the `font-family` descriptor inside
 * one is the NAME of the face being defined, not a use of a typeface, and it
 * cannot be a var(). Blanking rather than deleting keeps line numbers.
 * @font-face carries no colour values, so this is safe for checks 1-3 too.
 */
function blankFontFaceBlocks(css) {
  let out = css;
  const re = /@font-face\s*\{/g;
  let m;
  while ((m = re.exec(out)) !== null) {
    let depth = 1;
    let i = re.lastIndex;
    while (i < out.length && depth > 0) {
      if (out[i] === "{") depth++;
      else if (out[i] === "}") depth--;
      i++;
    }
    out = out.slice(0, m.index) + blank(out.slice(m.index, i)) + out.slice(i);
    re.lastIndex = i;
  }
  return out;
}

/** 1-based line number of a character offset. */
function lineAt(text, index) {
  let n = 1;
  for (let i = 0; i < index && i < text.length; i++) if (text[i] === "\n") n++;
  return n;
}

/**
 * CSS declarations as { prop, value, offset } where offset points at the start
 * of the value. Anchoring on `^`, `;`, `{` or `}` means a selector (`#fff { }`,
 * `.a:hover`) is never mistaken for a declaration — that is what keeps `#id`
 * selectors out of the hex scan.
 */
export function cssDeclarations(css) {
  const out = [];
  const re = /(^|[;{}])[^\S\n]*(--[\w-]+|[a-zA-Z-]+)[^\S\n]*:[^\S\n]*([^;{}]*)/gm;
  let m;
  while ((m = re.exec(css)) !== null) {
    out.push({
      prop: m[2].toLowerCase(),
      value: m[3],
      offset: m.index + m[0].length - m[3].length,
    });
  }
  return out;
}

/**
 * Hex-colour matches in a chunk of text, as { value, offset } relative to the
 * chunk. The trailing boundary rejects `#fact-…` and `#feed-…`; the leading
 * boundary rejects `&#8220;` and any word-glued run.
 */
function hexMatches(text, baseOffset = 0) {
  const re = /(?<![&\w])#([0-9a-fA-F]{3,8})(?![0-9a-zA-Z_-])/g;
  const out = [];
  let m;
  while ((m = re.exec(text)) !== null) {
    if (!HEX_LENGTHS.has(m[1].length)) continue;
    out.push({ value: `#${m[1].toLowerCase()}`, offset: baseOffset + m.index });
  }
  return out;
}

/**
 * Colour-shaped hex positions in .ts/.tsx. Three forms, which is every form
 * the codebase actually uses for a colour:
 *   A  a string literal that is EXACTLY a hex   — stroke="#e5e7eb", ? "#16a34a"
 *   B  a Tailwind arbitrary value               — bg-[#0a161f]
 *   C  a hex after a CSS colon in a style string — "background:#0a161f"
 * Anything else that starts with `#` in TS — a URL fragment, an 8-hex fact id
 * in a test assertion, an HTML entity, "(ROADMAP #32a)" — is not a colour and
 * is not scanned.
 */
function tsHexMatches(code) {
  const out = [];
  const patterns = [
    /(["'`])#([0-9a-fA-F]{3,8})\1/g,
    /\[#([0-9a-fA-F]{3,8})\]/g,
    /:\s*#([0-9a-fA-F]{3,8})(?![0-9a-zA-Z_-])/g,
  ];
  for (const re of patterns) {
    let m;
    while ((m = re.exec(code)) !== null) {
      const digits = m[2] ?? m[1];
      if (!HEX_LENGTHS.has(digits.length)) continue;
      out.push({
        value: `#${digits.toLowerCase()}`,
        offset: m.index + m[0].indexOf("#"),
      });
    }
  }
  return out;
}

/**
 * Remove every `var(--…)` call (innermost first, so nested fallbacks go too).
 * What is left of a type declaration is the part that did NOT come from a
 * token: empty means the declaration resolves entirely through globals.css.
 */
export function stripVarCalls(value) {
  let prev;
  let out = value;
  do {
    prev = out;
    out = out.replace(/var\(\s*--[^()]*\)/g, "");
  } while (out !== prev);
  return out;
}

/**
 * rgb()/rgba()/oklch() colour literals, returned with the full call text so an
 * allowlist entry names the actual value. The `(?![)\\])` guard means `oklch()`
 * written in prose and `oklch\(` inside a RegExp source are not matches, and
 * the `\b` means `oklchToSrgb(` is not one either.
 */
function colorFunctionMatches(text, name) {
  const re = new RegExp(`\\b${name}\\(\\s*(?![)\\\\])([^)\\n]{0,120})\\)`, "g");
  const out = [];
  let m;
  while ((m = re.exec(text)) !== null) {
    out.push({ value: `${m[0]}`.replace(/\s+/g, " "), offset: m.index });
  }
  return out;
}

// ── Gate ─────────────────────────────────────────────────────────────────────

export async function runTokensGate() {
  const errors = [];
  const notes = [];

  if (!fs.existsSync(srcDir)) {
    errors.push("tokens_gate: site/src not found");
    return { pass: false, errors, notes };
  }

  // ── Allowlist load + shape hygiene (check 5) ───────────────────────────────
  let entries = [];
  try {
    entries = JSON.parse(fs.readFileSync(ALLOWLIST_PATH, "utf8"));
  } catch (e) {
    errors.push(`tokens_gate: token-allowlist.json unreadable — ${e.message}`);
    return { pass: false, errors, notes };
  }
  if (!Array.isArray(entries)) {
    errors.push("tokens_gate: token-allowlist.json is not an array");
    return { pass: false, errors, notes };
  }

  /** key `${file} ${value}` → { used, index } */
  const allow = new Map();
  entries.forEach((entry, i) => {
    const where = `token-allowlist.json[${i}]`;
    const file = typeof entry?.file === "string" ? entry.file.trim() : "";
    const value = typeof entry?.value === "string" ? entry.value.trim() : "";
    if (!file) return errors.push(`${where}: missing "file"`);
    if (!value) return errors.push(`${where} (${file}): missing "value"`);
    if (typeof entry?.reason !== "string" || entry.reason.trim() === "") {
      return errors.push(
        `${where} (${file} ${value}): "reason" is required — an exemption ` +
          `nobody explained is an exemption nobody can review`,
      );
    }
    if (!fs.existsSync(path.join(siteRoot, file))) {
      return errors.push(
        `${where}: "file" ${file} does not exist — a dead path is a dead rule`,
      );
    }
    const key = `${file} ${value.toLowerCase()}`;
    if (allow.has(key)) {
      return errors.push(`${where}: duplicate entry for ${file} ${value}`);
    }
    allow.set(key, { used: 0, index: i, file, value });
  });

  const isAllowed = (rel, value) => {
    const hit = allow.get(`${rel} ${String(value).toLowerCase()}`);
    if (!hit) return false;
    hit.used += 1;
    return true;
  };

  // ── Source scan (checks 1-4) ───────────────────────────────────────────────
  const files = collectFiles(srcDir, [".ts", ".tsx", ".css"]);
  notes.push(`scanned ${files.length} source files`);

  const counts = { hex: 0, rgb: 0, oklch: 0, font: 0 };
  /** `${rel} ${value}` → { rel, value, check, lines[] } */
  const violations = new Map();

  const record = (rel, value, check, line) => {
    if (isAllowed(rel, value)) return;
    const key = `${rel} ${value.toLowerCase()}`;
    const v = violations.get(key) ?? { rel, value, check, lines: [] };
    v.lines.push(line);
    violations.set(key, v);
    counts[check] += 1;
  };

  // ── Ladder allowlist (check 6) — same shape and hygiene as the colour one ──
  const typeAllow = new Map();
  let typeAllowRaw = [];
  if (fs.existsSync(TYPE_ALLOWLIST_PATH)) {
    try {
      typeAllowRaw = JSON.parse(fs.readFileSync(TYPE_ALLOWLIST_PATH, "utf8"));
      if (!Array.isArray(typeAllowRaw)) throw new Error("not an array");
    } catch (e) {
      errors.push(`tokens_gate: type-allowlist.json unreadable — ${e.message}`);
      typeAllowRaw = [];
    }
    typeAllowRaw.forEach((entry, index) => {
      const { file, value, reason } = entry ?? {};
      if (!file || !value) return errors.push(`tokens_gate: type-allowlist.json[${index}]: missing file/value`);
      if (!reason || String(reason).trim().length < 12) return errors.push(`tokens_gate: type-allowlist.json[${index}] (${file}): needs a reason`);
      if (!fs.existsSync(path.join(siteRoot, file))) return errors.push(`tokens_gate: type-allowlist.json[${index}]: ${file} does not exist`);
      typeAllow.set(`${file} ${String(value).toLowerCase()}`, { index, file, value, used: 0 });
    });
  }
  /** `${rel} ${value}` → { rel, value, lines[] } — ladder violations not allowlisted */
  const ladder = new Map();
  const recordLadder = (rel, value, line) => {
    const key = `${rel} ${value.toLowerCase()}`;
    const hit = typeAllow.get(key);
    if (hit) { hit.used += 1; return; }
    const v = ladder.get(key) ?? { rel, value, lines: [] };
    v.lines.push(line);
    ladder.set(key, v);
  };

  for (const file of files) {
    const rel = path.relative(siteRoot, file).split(path.sep).join("/");
    if (rel === DECLARATION_SITE) continue;

    const ext = path.extname(file);
    let code = stripComments(fs.readFileSync(file, "utf8"), ext);
    if (ext === ".css") code = blankFontFaceBlocks(code);

    // ── (1) raw hex colours ────────────────────────────────────────────────
    if (ext === ".css") {
      for (const decl of cssDeclarations(code)) {
        for (const hit of hexMatches(decl.value, decl.offset)) {
          record(rel, hit.value, "hex", lineAt(code, hit.offset));
        }
      }
    } else {
      for (const hit of tsHexMatches(code)) {
        record(rel, hit.value, "hex", lineAt(code, hit.offset));
      }
    }

    // ── (2) rgb()/rgba() literals ──────────────────────────────────────────
    for (const hit of colorFunctionMatches(code, "rgba?")) {
      record(rel, hit.value, "rgb", lineAt(code, hit.offset));
    }

    // ── (3) oklch() literals ───────────────────────────────────────────────
    for (const hit of colorFunctionMatches(code, "oklch")) {
      record(rel, hit.value, "oklch", lineAt(code, hit.offset));
    }

    // ── (4) type declarations that don't resolve through tokens ────────────
    // ── (6) sizes and trackings off the ladder ─────────────────────────────
    if (ext === ".css") {
      for (const decl of cssDeclarations(code)) {
        const line = lineAt(code, decl.offset);
        const value = decl.value.trim().replace(/\s+/g, " ");
        if (decl.prop === "font") {
          const f = splitFontShorthand(value);
          if (f.composite) continue;
          if (f.family && stripVarCalls(f.family).replace(/[\s,]/g, "") !== "") {
            record(rel, `font: … ${f.family}`, "font", line);
          }
          if (f.size && !LADDER_SIZE_RE.test(f.size)) recordLadder(rel, `font: ${f.size}`, line);
          continue;
        }
        if (decl.prop === "font-size") {
          if (!LADDER_SIZE_RE.test(value)) recordLadder(rel, `font-size: ${value}`, line);
          continue;
        }
        if (decl.prop === "letter-spacing") {
          if (!LADDER_TRACK_RE.test(value)) recordLadder(rel, `letter-spacing: ${value}`, line);
          continue;
        }
        if (!TYPE_PROP_RE.test(decl.prop)) continue;
        if (stripVarCalls(decl.value).replace(/[\s,]/g, "") === "") continue;
        record(rel, value, "font", line);
      }
    } else {
      const re = /fontFamily\s*:\s*(["'`])([^"'`\n]*)\1/g;
      let m;
      while ((m = re.exec(code)) !== null) {
        if (stripVarCalls(m[2]).replace(/[\s,]/g, "") === "") continue;
        record(rel, m[2].trim().replace(/\s+/g, " "), "font", lineAt(code, m.index));
      }
      // Inline style sizes and Tailwind utilities off the ladder. Test files
      // assert on class names and are not rendered type; skip them.
      if (!/(^|\/)__tests__\//.test(rel) && !/\.test\.tsx?$/.test(rel)) {
        const fs1 = /fontSize\s*:\s*(["'`]?)([^,}\n]*)\1/g;
        while ((m = fs1.exec(code)) !== null) {
          const val = m[2].trim();
          if (!LADDER_SIZE_RE.test(val.replace(/^["'`]|["'`]$/g, ""))) recordLadder(rel, `fontSize: ${val}`, lineAt(code, m.index));
        }
        while ((m = TW_OFF_LADDER_RE.exec(code)) !== null) {
          recordLadder(rel, m[0], lineAt(code, m.index));
        }
      }
    }
  }

  for (const v of [...violations.values()].sort((a, b) =>
    a.rel === b.rel ? a.value.localeCompare(b.value) : a.rel.localeCompare(b.rel),
  )) {
    const where = `${v.rel}:${[...new Set(v.lines)].slice(0, 6).join(",")}`;
    const more = v.lines.length > 6 ? ` (+${v.lines.length - 6} more)` : "";
    const fix =
      v.check === "font"
        ? `font-family ${JSON.stringify(v.value)} names a typeface — use var(--font-*) declared in ${DECLARATION_SITE}`
        : `raw colour ${v.value} — colours are declared as oklch custom properties in ${DECLARATION_SITE}; use var(--token)`;
    errors.push(
      `tokens_gate: ${where}${more} ${fix}, or add a {file, value, reason} entry to token-allowlist.json`,
    );
  }

  // "clean" here means nothing OUTSIDE the allowlist — the allowlist line below
  // is the standing count of the debt, and it is the number that has to shrink.
  if (counts.hex === 0) notes.push("raw-hex scan: no unlisted values ✓");
  if (counts.rgb === 0) notes.push("rgb()/rgba() scan: no unlisted values ✓");
  if (counts.oklch === 0) notes.push("oklch() scan: no unlisted values ✓ (declared only in globals.css)");
  if (counts.font === 0) notes.push("type scan: no unlisted values ✓ (the rest resolve through var())");

  // ── (5) stale allowlist entries ────────────────────────────────────────────
  const stale = [...allow.values()].filter((e) => e.used === 0);
  for (const e of stale) {
    errors.push(
      `tokens_gate: token-allowlist.json[${e.index}] (${e.file} ${e.value}) matched ` +
        `nothing — the raw value is gone, so delete the entry; a stale exemption ` +
        `is how an escape hatch grows without anyone noticing`,
    );
  }

  const used = allow.size - stale.length;
  notes.push(
    `allowlist: ${allow.size} entr${allow.size === 1 ? "y" : "ies"}, ${used} matched` +
      (stale.length > 0 ? `, ${stale.length} STALE` : ""),
  );

  // ── (6) the ladder: report, or seed/merge the allowlist on request ──────────
  const sortedLadder = [...ladder.values()].sort((a, b) =>
    a.rel === b.rel ? a.value.localeCompare(b.value) : a.rel.localeCompare(b.rel),
  );
  if (process.env.TYPE_ALLOWLIST_EMIT === "1") {
    const kept = typeAllowRaw.filter((e) => typeAllow.get(`${e.file}\x00${String(e.value).toLowerCase()}`)?.used > 0);
    const merged = [
      ...kept,
      ...sortedLadder.map((v) => ({
        file: v.rel,
        value: v.value,
        reason:
          "Ladder debt frozen 2026-09-12 (iteration 8, the type system landed): a size or tracking that predates the ladder. Shrink only — re-author onto var(--text-*)/var(--fig-*)/var(--tracking-*) or a ladder utility, then delete this entry.",
      })),
    ];
    fs.writeFileSync(TYPE_ALLOWLIST_PATH, JSON.stringify(merged, null, 2) + "\n");
    notes.push(`ladder: TYPE_ALLOWLIST_EMIT wrote ${merged.length} entries to type-allowlist.json (${kept.length} kept, ${sortedLadder.length} new)`);
  } else {
    for (const v of sortedLadder) {
      const where = `${v.rel}:${[...new Set(v.lines)].slice(0, 6).join(",")}`;
      const more = v.lines.length > 6 ? ` (+${v.lines.length - 6} more)` : "";
      errors.push(
        `tokens_gate: ${where}${more} ${JSON.stringify(v.value)} is not on the size ladder — use var(--text-*)/var(--fig-*)/var(--tracking-*) (or a ladder utility: t-label, t-figure--N, t-id, text-xs/sm/base), or add a {file, value, reason} entry to type-allowlist.json`,
      );
    }
    const staleLadder = [...typeAllow.values()].filter((e) => e.used === 0);
    for (const e of staleLadder) {
      errors.push(`tokens_gate: type-allowlist.json[${e.index}] (${e.file} ${e.value}) matched nothing — delete the entry (shrink-only ladder debt)`);
    }
    if (sortedLadder.length === 0) {
      notes.push(
        `ladder: no unlisted sizes/trackings ✓ (type-allowlist: ${typeAllow.size} entr${typeAllow.size === 1 ? "y" : "ies"}, ${typeAllow.size - staleLadder.length} matched${staleLadder.length ? `, ${staleLadder.length} STALE` : ""})`,
      );
    }
  }

  // ── (7) the declaration site is complete and alone ──────────────────────────
  const globalsCss = stripComments(fs.readFileSync(path.join(siteRoot, DECLARATION_SITE), "utf8"), ".css");
  for (const t of [...FACE_TOKENS, ...ROLE_TOKENS]) {
    if (!new RegExp(`(^|[\\s;{])${t}\\s*:`, "m").test(globalsCss)) {
      errors.push(`tokens_gate: ${DECLARATION_SITE} does not declare ${t} — the declaration site must define the three faces and the three roles`);
    }
  }
  if (/(^|[\s;{])--font-editorial\s*:/m.test(globalsCss)) {
    errors.push(`tokens_gate: ${DECLARATION_SITE} still declares --font-editorial — the transitional alias is deleted with its last consumer (headings take the base rules; prose takes [data-prose])`);
  }
  let registerDecl = 0, editorialUse = 0;
  for (const file of files) {
    const rel = path.relative(siteRoot, file).split(path.sep).join("/");
    const code = stripComments(fs.readFileSync(file, "utf8"), path.extname(file));
    const reg = code.match(/--register-(serif|sans|mono)\s*:/g);
    if (reg) { registerDecl += reg.length; errors.push(`tokens_gate: ${rel} declares ${[...new Set(reg)].join(", ")} — a page-private type register is "two products"; consume var(--font-serif|sans|id) and the ladder instead`); }
    const ed = code.match(/var\(--font-editorial[^)]*\)/g);
    if (ed) { editorialUse += ed.length; errors.push(`tokens_gate: ${rel} consumes var(--font-editorial) ×${ed.length} — migrate to the base heading rules / var(--font-serif)`); }
  }
  if (registerDecl === 0 && editorialUse === 0) notes.push("declaration site: three faces + three roles, no private register, no --font-editorial consumer ✓");

  return { pass: errors.length === 0, errors, notes };
}
