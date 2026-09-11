/**
 * jsx-glue.mjs — find the text JSX silently eats (gate 2 leg (sp)).
 *
 * THE DEFECT. `/about/` rendered "Fiscal Receiptsshows" and "award.The". The
 * source looked correct:
 *
 *     <p>
 *       {SITE_NAME}
 *       makes federal defense spending legible…
 *     </p>
 *
 * JSX trims a text child's leading whitespace when that whitespace contains a
 * newline, and DROPS a whitespace-only text child entirely. So the space the
 * author typed does not exist in the output. The class is invisible in source
 * review (the code reads as prose) and effectively unfindable in the built
 * HTML (the glued result is ordinary letters — "Receiptsshows" is not
 * distinguishable from a word by any lexical rule). It has to be caught at
 * the shape.
 *
 * THE DETECTOR. Parse every .tsx with the TypeScript compiler, walk each JSX
 * element's children, apply React's own JSXText cleaner (the exact algorithm
 * babel's cleanJSXElementLiteralChild uses), and report any expression/text
 * pair the renderer joins with NO separator where the author wrote a line
 * break between them.
 *
 * WHAT IS NOT GLUE — the four shapes that are deliberate, and how each is
 * recognised structurally rather than by allowlist:
 *   - an explicit {" "} between the two children;
 *   - an AFFIX expression: every non-empty branch is a short lowercase
 *     inflection ({n !== 1 ? "s" : ""}, {"ies"} / {"y"}) — pluralisation is
 *     supposed to touch the word;
 *   - a non-word edge: the join lands on "(", ")", "%", ".", " " or similar,
 *     on whichever side is a determinable string literal / template head /
 *     ternary of literals;
 *   - an all-caps ≤3-letter prefix ending the text ("FY" in FY{year},
 *     "BA" in BA{n}) — the site's own code-formatting idiom.
 * Expressions that render JSX are treated as elements, not text, and element
 * neighbours are out of scope: block-level siblings gluing is layout, not
 * prose.
 *
 * THE SECOND TRIM (ROADMAP #106, 2026-09-05). Babel's cleaner keeps a FIRST
 * line's leading space, so `{n} whose cited record stops in an\n  earlier
 * President&apos;s…` is fine by the rule above — and Next 16's Turbopack
 * transform still rendered "553whose". When the run also carries an HTML
 * character reference, Turbopack trims that space. ba6c7d66 (2026-07-03)
 * already fixed one such site by hand (methodology/page.tsx: "Turbopack
 * drops the leading space of an entity-bearing text chunk after an
 * expression") and a2637af2 fixed the species in one component without
 * sweeping it. turbopackTrimsLeadingSpace() models exactly that shape and
 * nothing wider — measured 5/5 on the sites site/src had that day, with no
 * false positive across all 136 .tsx files. Delete when a Next upgrade stops
 * trimming; every site it flagged stays correct regardless.
 *
 * Export: findGlueSites(rootDir) → { hits: [{ file, line, why, left, right }], filesScanned }
 *         findGlueSitesInSource(file, src, rootDir) → the hits for one source
 *         turbopackTrimsLeadingSpace(rawJsxText) → boolean
 */

import fs from "fs";
import path from "path";
import { createRequire } from "module";

const require_ = createRequire(import.meta.url);
const ts = require_("typescript");

function* walkTsx(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "node_modules") continue;
      yield* walkTsx(p);
    } else if (p.endsWith(".tsx")) {
      yield p;
    }
  }
}

/**
 * React's JSXText cleaner. Lines are trimmed of the whitespace that touches a
 * newline; a whitespace-only child cleans to "" and is dropped outright.
 * Kept byte-for-byte faithful to babel — the whole point is to model what the
 * renderer really does, not what it plausibly does.
 */
export function cleanJsxText(raw) {
  const lines = raw.split(/\r\n|\n|\r/);
  let lastNonEmpty = 0;
  for (let i = 0; i < lines.length; i += 1) {
    if (/[^ \t]/.test(lines[i])) lastNonEmpty = i;
  }
  let out = "";
  for (let i = 0; i < lines.length; i += 1) {
    let line = lines[i].replace(/\t/g, " ");
    if (i !== 0) line = line.replace(/^ +/, "");
    if (i !== lines.length - 1) line = line.replace(/ +$/, "");
    if (line) {
      if (i !== lastNonEmpty) line += " ";
      out += line;
    }
  }
  return out;
}

const WORD = /[0-9A-Za-z]/;

/**
 * An HTML character reference as JSX text carries it: &apos; &rsquo; &amp;
 * &#8217; &#x2019;. A bare "&" (RDT & E) is not one.
 */
const HTML_ENTITY_RE = /&(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);/;

/**
 * The Turbopack entity trim (#106). True when a JSX text run starts with
 * horizontal whitespace followed by content on that SAME line (the space
 * that disappears), spans a line break, and contains a character reference.
 * A run whose first line is blank is the ordinary case cleanJsxText models.
 */
export function turbopackTrimsLeadingSpace(raw) {
  return (
    /^[ \t]+[^\s]/.test(raw) && /[\r\n]/.test(raw) && HTML_ENTITY_RE.test(raw)
  );
}

/** The glue sites in ONE source text — exported for the unit tests. */
export function findGlueSitesInSource(file, src, rootDir = path.dirname(file)) {
  const hits = [];
  {
    const sf = ts.createSourceFile(
      file,
      src,
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );

    /** The string values an expression can render, or null when unknowable. */
    const branchValues = (e) => {
      if (ts.isStringLiteral(e) || ts.isNoSubstitutionTemplateLiteral(e)) {
        return [e.text];
      }
      // A template's HEAD is known; the rest is not, and only the head touches
      // the join on the left side.
      if (ts.isTemplateExpression(e)) return [e.head.text];
      if (ts.isParenthesizedExpression(e)) return branchValues(e.expression);
      if (ts.isConditionalExpression(e)) {
        const a = branchValues(e.whenTrue);
        const b = branchValues(e.whenFalse);
        return a && b ? [...a, ...b] : null;
      }
      if (
        ts.isBinaryExpression(e) &&
        e.operatorToken.kind === ts.SyntaxKind.AmpersandAmpersandToken
      ) {
        const b = branchValues(e.right);
        return b ? ["", ...b] : null;
      }
      return null;
    };

    const rendersJsx = (e) => {
      let found = false;
      const visit = (n) => {
        if (
          ts.isJsxElement(n) ||
          ts.isJsxSelfClosingElement(n) ||
          ts.isJsxFragment(n)
        ) {
          found = true;
        } else {
          ts.forEachChild(n, visit);
        }
      };
      visit(e);
      return found;
    };

    const isWhitespaceExpr = (k) =>
      ts.isJsxExpression(k) &&
      k.expression &&
      ts.isStringLiteral(k.expression) &&
      /^\s+$/.test(k.expression.text);

    /** All non-empty branch values start with a non-word character. */
    const edgeIsNonWord = (vals, side) => {
      const nonEmpty = (vals ?? []).filter((v) => v !== "");
      if (nonEmpty.length === 0) return null;
      return nonEmpty.every((v) => {
        const ch = side === "start" ? v[0] : v[v.length - 1];
        return !WORD.test(ch);
      });
    };

    const isAffix = (vals) => {
      const nonEmpty = (vals ?? []).filter((v) => v !== "");
      return nonEmpty.length > 0 && nonEmpty.every((v) => /^[a-z]{1,4}$/.test(v));
    };

    const check = (node) => {
      const seq = [];
      for (const k of node.children) {
        if (ts.isJsxText(k)) {
          const cleaned = cleanJsxText(k.text);
          seq.push(
            cleaned === ""
              ? { kind: "gap", raw: k.text }
              : { kind: "text", cleaned, raw: k.text, node: k },
          );
        } else if (ts.isJsxExpression(k)) {
          if (!k.expression) continue; // {/* comment */}
          if (isWhitespaceExpr(k)) seq.push({ kind: "space" });
          else if (rendersJsx(k.expression)) seq.push({ kind: "el" });
          else seq.push({ kind: "expr", node: k, vals: branchValues(k.expression) });
        } else {
          seq.push({ kind: "el" });
        }
      }

      for (let i = 0; i < seq.length - 1; i += 1) {
        const a = seq[i];
        if (a.kind === "gap" || a.kind === "space") continue;
        let j = i + 1;
        let gapRaw = "";
        while (j < seq.length && seq[j].kind === "gap") {
          gapRaw += seq[j].raw;
          j += 1;
        }
        if (j >= seq.length) break;
        const b = seq[j];
        if (b.kind === "space") continue;
        const pair = `${a.kind}+${b.kind}`;
        if (pair !== "expr+text" && pair !== "text+expr") continue;

        // Did the renderer eat a line break the author wrote?
        let glued;
        let why = "newline";
        if (gapRaw) {
          glued = /[\n\r]/.test(gapRaw);
        } else if (pair === "expr+text") {
          glued = /^[ \t]*[\r\n]/.test(b.raw) && !/^\s/.test(b.cleaned);
          // …or the space babel keeps and Turbopack does not (#106).
          if (!glued && turbopackTrimsLeadingSpace(b.raw)) {
            glued = true;
            why = "entity-trim";
          }
        } else {
          glued = /[\r\n][ \t]*$/.test(a.raw) && !/\s$/.test(a.cleaned);
        }
        if (!glued) continue;

        // Deliberate joins.
        if (isAffix(a.vals) || isAffix(b.vals)) continue;
        const leftEdge =
          a.kind === "text"
            ? !WORD.test(a.cleaned.slice(-1))
            : edgeIsNonWord(a.vals, "end");
        // Under the entity trim the cleaned text still starts with the
        // space babel would keep; what actually meets the value is the
        // first non-blank character.
        const bText =
          b.kind === "text" && why === "entity-trim"
            ? b.cleaned.replace(/^\s+/, "")
            : b.cleaned;
        const rightEdge =
          b.kind === "text"
            ? !WORD.test(bText[0])
            : edgeIsNonWord(b.vals, "start");
        if (leftEdge === true || rightEdge === true) continue;
        // "…FY" / "…BA" immediately before a value is the site's code idiom.
        if (a.kind === "text" && /(^|[^A-Za-z])[A-Z]{1,3}$/.test(a.cleaned)) continue;

        const start = (a.node ?? b.node).getStart(sf);
        const pos = sf.getLineAndCharacterOfPosition(start);
        hits.push({
          file: path.relative(rootDir, file),
          line: pos.line + 1,
          why,
          left: (a.kind === "text" ? a.cleaned : a.node.getText(sf))
            .replace(/\s+/g, " ")
            .slice(-60),
          right: (b.kind === "text" ? bText : b.node.getText(sf))
            .replace(/\s+/g, " ")
            .slice(0, 60),
        });
        i = j - 1;
      }
    };

    const visit = (n) => {
      if (ts.isJsxElement(n) || ts.isJsxFragment(n)) check(n);
      ts.forEachChild(n, visit);
    };
    visit(sf);
  }

  return hits;
}

export function findGlueSites(rootDir) {
  const hits = [];
  let filesScanned = 0;
  for (const file of walkTsx(rootDir)) {
    filesScanned += 1;
    hits.push(
      ...findGlueSitesInSource(file, fs.readFileSync(file, "utf8"), rootDir),
    );
  }
  return { hits, filesScanned };
}
