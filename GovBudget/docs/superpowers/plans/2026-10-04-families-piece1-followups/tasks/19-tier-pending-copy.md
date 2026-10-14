<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the approved design is ../../../specs/2026-10-04-families-piece1-followups-design.md. -->

### Task 19: one definition of "citation tier pending"; claims narrowed to dollar figures (#206 T7, Q16)

**Spec:** design §5.3 (T7: the six /methodology/ strings and the two /about/ strings; delete `copy-allowlist.json:38-43`
in the same commit, because the copy gate fails on a stale entry; the FAQ string is 98 B against the 102 B pin; gate 2,
`render-static.mjs:5-14`, enforces dollar figures, which is what the narrowed claims say; extend
`methodology-pending-ledger.test.ts`; measured by substitution /methodology/ −13 gzip / +16 raw and /about/ −13 gzip,
re-measured on the release build); §2.2 Q16 (owner, 2026-10-04: approved — "the design's other recommendations stand",
ROADMAP "Follow-ups first" paragraph, commit 532205c9); §3.7 (the /methodology/ byte budget and Q13, which Task 15
edits in another sentence); §7 W4 (copy gate, page weights).

**Files:**
- Modify: `site/src/app/methodology/page.tsx` (FAQ answers :56 and :71; §4 "Citation tiers" body :1015 and :1023-1028)
- Modify: `site/src/app/about/page.tsx` ("Data provenance", :169-174)
- Modify: `site/scripts/gates/copy-allowlist.json` (delete the entry at :38-43)
- Modify: `site/src/__tests__/methodology-pending-ledger.test.ts` (the FAQ describe :42-53; a new describe appended)

Line numbers are hints measured at `532205c9` (anchor on the quoted text).

**Interfaces:**
Consumes: the existing `rendered()` helper in `methodology-pending-ledger.test.ts` (the citation-tier paragraph from
`<strong>Citation tier pending</strong>` to `</p>`, tags dropped, whitespace collapsed); the copy gate (`copy.mjs`):
leg 13 `/—[^.!?]*—/` is what the allowlist entry exempted, and reference pages (/methodology/, /about/) skip the style
legs 10, 12, 23 and 31; unmatched allowlist entries fail as stale.
Produces: the shared phrase "a dataset without row-level citations" in the /methodology/ body, its FAQ JSON-LD and
/about/; "dollar figure" in the four claims; one fewer `copy-allowlist.json` entry (11 → 10). Task 21 re-stamps the
/methodology/ page weight (`build.mjs` `PAGE_WEIGHT_BUDGET`, stamp `161,353 / 45,336` against `162,000 / 45,400`);
/about/ has no budget entry. Task 22's ROADMAP stamp quotes the strings (Q16).

The strings, as rendered (each appears twice in the built HTML, SSR and RSC):

| Where | Before | After |
|---|---|---|
| /methodology/ FAQ "What is Fiscal Receipts…" | Every rendered number carries a citation to the exact source document, page, or API endpoint. | Every rendered dollar figure carries a citation state; a cited one links to the exact source document, page, or API endpoint. |
| /methodology/ FAQ "How confident…" (opening) | Figures in one of three states: | Dollar figures in one of three states: |
| /methodology/ FAQ "How confident…" (pending) | Citation tier pending (⁂) — reserved for datasets without citations (currently p1_era_line_map). | Citation tier pending (⁂) — a dataset without row-level citations (currently p1_era_line_map). |
| /methodology/ §4 body (opening) | Every rendered figure is in one of three states. | Every rendered dollar figure is in one of three states. |
| /methodology/ §4 body (pending) | (⁂): figure is from a dataset for which row-level citation linkage is not yet complete. | (⁂): a figure from a dataset without row-level citations. |
| /methodology/ §4 body (clause) | the state remains defined — and gate-enforced — for future datasets | the state remains defined, and gate-enforced, for future datasets |
| /about/ (opening) | Every rendered number is in one of three citation states: | Every rendered dollar figure is in one of three citation states: |
| /about/ (pending + claim) | (dataset where row-level linkage is a work in progress). No number is displayed | (a dataset without row-level citations). No dollar figure is displayed |

- [ ] **Step 1: Write the failing tests**

In `site/src/__tests__/methodology-pending-ledger.test.ts` (:42-53), replace:

```ts
/**
 * Task 19 fix round 1: the FAQ answer in /methodology/'s JSON-LD said the
 * pending tier is "reserved for datasets shipped before their citations
 * (currently none)", false beside the clause above once p1_era_line_map
 * ships. It names the dataset now, two bytes shorter (the page sits near its
 * gate-1 ceiling).
 */
describe("/methodology/ FAQ JSON-LD: the pending tier", () => {
  const src = fs.readFileSync(PAGE, "utf8");
  const OLD_FAQ = "Citation tier pending (⁂) — reserved for datasets shipped before their citations (currently none).";
  const NEW_FAQ = "Citation tier pending (⁂) — reserved for datasets without citations (currently p1_era_line_map).";
```

with:

```ts
/**
 * Task 19 fix round 1: the FAQ answer in /methodology/'s JSON-LD said the
 * pending tier is "reserved for datasets shipped before their citations
 * (currently none)", false beside the clause above once p1_era_line_map
 * ships. It names the dataset now, shorter than the answer it replaced (the
 * page sits near its gate-1 ceiling). Follow-ups T7 (ROADMAP #206, owner
 * Q16) gave it the shared definition below: 98 bytes against 102.
 */
describe("/methodology/ FAQ JSON-LD: the pending tier", () => {
  const src = fs.readFileSync(PAGE, "utf8");
  const OLD_FAQ = "Citation tier pending (⁂) — reserved for datasets shipped before their citations (currently none).";
  const NEW_FAQ = "Citation tier pending (⁂) — a dataset without row-level citations (currently p1_era_line_map).";
```

Append to the end of `site/src/__tests__/methodology-pending-ledger.test.ts`:

```ts

/**
 * ROADMAP #206 T7 (families piece-1 follow-ups, design §5.3; owner sign-off
 * Q16, 2026-10-04). "Citation tier pending" had three definitions: the
 * /methodology/ body ("row-level citation linkage is not yet complete"), its
 * FAQ JSON-LD ("reserved for datasets without citations") and /about/ ("row-
 * level linkage is a work in progress"). None fits p1_era_line_map, whose
 * rows are decisions and will never carry amounts. There is one definition
 * now, and the claims around it say "dollar figure", which is what gate 2
 * (render-static.mjs) enforces, instead of "number".
 */
describe("one definition of citation tier pending (T7)", () => {
  const ABOUT = path.resolve(__dirname, "..", "app", "about", "page.tsx");
  const flat = (file: string) => fs.readFileSync(file, "utf8").replace(/\s+/g, " ");
  const SHARED = "a dataset without row-level citations";

  it("the /methodology/ body, its FAQ and /about/ share one phrase", () => {
    expect(rendered()).toContain(`(⁂): a figure from ${SHARED}.`);
    expect(flat(PAGE)).toContain(`Citation tier pending (⁂) — ${SHARED} (currently p1_era_line_map).`);
    expect(flat(ABOUT)).toContain(`citation tier pending (${SHARED}).`);
  });

  it("no older definition or unnarrowed claim is left", () => {
    for (const file of [PAGE, ABOUT]) {
      const text = flat(file);
      for (const stale of ["work in progress", "not yet complete", "reserved for datasets",
        "Every rendered number", "No number is displayed", "Every rendered figure"]) {
        expect(text.includes(stale), `${path.basename(path.dirname(file))} still says "${stale}"`).toBe(false);
      }
    }
  });

  it("narrows each claim to dollar figures", () => {
    const page = flat(PAGE);
    expect(page).toContain("Every rendered dollar figure is in one of three states.");
    expect(page).toContain("Every rendered dollar figure carries a citation state; a cited one links to the exact source document, page, or API endpoint.");
    expect(page).toContain("Dollar figures in one of three states:");
    const about = flat(ABOUT);
    expect(about).toContain("Every rendered dollar figure is in one of three citation states:");
    expect(about).toContain("No dollar figure is displayed without disclosing which state it is in.");
  });

  it("keeps the em-dash-free clause the copy gate's allowlist entry no longer covers", () => {
    expect(rendered()).toContain("the state remains defined, and gate-enforced, for future datasets");
  });
});
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run src/__tests__/methodology-pending-ledger.test.ts`
Expected: `5 failed | 4 passed (9)` — "names p1_era_line_map and no longer says none" and the four tests of "one
definition of citation tier pending (T7)" (scratch overlay of `532205c9`, 2026-10-13).

- [ ] **Step 3: Change the strings and drop the stale allowlist entry**

In `site/src/app/methodology/page.tsx` (FAQ_ITEMS, :56), replace:

```tsx
      "Fiscal Receipts connects four government data silos: DoD budget justification books (J-books), USAspending federal award records, corporate entity registries, and Senate LDA lobbying disclosures. Every rendered number carries a citation to the exact source document, page, or API endpoint.",
```

with:

```tsx
      "Fiscal Receipts connects four government data silos: DoD budget justification books (J-books), USAspending federal award records, corporate entity registries, and Senate LDA lobbying disclosures. Every rendered dollar figure carries a citation state; a cited one links to the exact source document, page, or API endpoint.",
```

In `site/src/app/methodology/page.tsx` (FAQ_ITEMS, :71), replace:

```tsx
      "Figures in one of three states: Cited (underlined, clickable) — a fact_id resolves to a source document, query, or derived formula; XML-path chip — a zero-dollar budget line in XML with no citation row; Citation tier pending (⁂) — reserved for datasets without citations (currently p1_era_line_map).",
```

with:

```tsx
      "Dollar figures in one of three states: Cited (underlined, clickable) — a fact_id resolves to a source document, query, or derived formula; XML-path chip — a zero-dollar budget line in XML with no citation row; Citation tier pending (⁂) — a dataset without row-level citations (currently p1_era_line_map).",
```

In `site/src/app/methodology/page.tsx` (§4, :1015), replace:

```tsx
                  Every rendered figure is in one of three states. <strong>Cited</strong>{" "}
```

with:

```tsx
                  Every rendered dollar figure is in one of three states. <strong>Cited</strong>{" "}
```

In `site/src/app/methodology/page.tsx` (§4, :1023-1028), replace:

```tsx
                  <strong>Citation tier pending</strong> (⁂): figure is from a
                  dataset for which row-level citation linkage is not yet
                  complete. As of this build only p1_era_line_map is on the
                  pending ledger, as it holds no amounts to cite; the state
                  remains defined — and gate-enforced — for future datasets that
                  ship before their citations do.
```

with:

```tsx
                  <strong>Citation tier pending</strong> (⁂): a figure from a
                  dataset without row-level citations. As of this build only
                  p1_era_line_map is on the pending ledger, as it holds no
                  amounts to cite; the state remains defined, and
                  gate-enforced, for future datasets that ship before their
                  citations do.
```

In `site/src/app/about/page.tsx` (:169-174), replace:

```tsx
              Every rendered number is in one of three citation states: directly
              cited (linked to a PDF page, workbook cell, or API endpoint),
              XML-path traced (zero-dollar line from structured budget XML), or
              citation tier pending (dataset where row-level linkage is a work in
              progress). No number is displayed without disclosing which state it
              is in. See{" "}
```

with:

```tsx
              Every rendered dollar figure is in one of three citation states:
              directly cited (linked to a PDF page, workbook cell, or API
              endpoint), XML-path traced (zero-dollar line from structured budget
              XML), or citation tier pending (a dataset without row-level
              citations). No dollar figure is displayed without disclosing which
              state it is in. See{" "}
```

In `site/scripts/gates/copy-allowlist.json` (:38-43; the copy gate would fail this entry as stale once leg 13 stops firing on the paragraph), delete this block:

```json
  {
    "page": "/methodology/",
    "leg": 13,
    "text": "(⁂): figure is from a dataset for which row-level citation linkage is not yet complete. As of this build only p1_era_line_map is on the pend",
    "reason": "Pre-existing in production 81929a6b (gate run on the deployed build 2026-09-25); exempted under integration ruling R-INT-7; burn-down tracked in ROADMAP #175; re-keyed 2026-10-04 after families piece 1 Task 19 replaced the sentence; burn-down still ROADMAP #175"
  },
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run src/__tests__/methodology-pending-ledger.test.ts && node -e 'console.log(JSON.parse(require("fs").readFileSync("scripts/gates/copy-allowlist.json","utf8")).length)'`
Expected: `9 passed (9)`, then `10`.

- [ ] **Step 5: Weigh the change by substitution on the current build**

The site is not rebuilt here (Task 21 builds and re-stamps); this applies the same strings to the worktree's built
pages in memory and gzips at level 9 as gate 1 does. It refuses if a string is not found exactly twice.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site || exit 1
node --input-type=module - out <<'EOF'
// T7 weight by substitution on the built HTML (each string appears twice: SSR + RSC).
import fs from "fs"; import zlib from "zlib"; import path from "path";
const out = process.argv[2];
const M = [
  ["figure is from a dataset for which row-level citation linkage is not yet complete.", "a figure from a dataset without row-level citations."],
  ["defined — and gate-enforced — for", "defined, and gate-enforced, for"],
  ["reserved for datasets without citations (currently p1_era_line_map).", "a dataset without row-level citations (currently p1_era_line_map)."],
  ["Every rendered number carries a citation to the exact source document, page, or API endpoint.", "Every rendered dollar figure carries a citation state; a cited one links to the exact source document, page, or API endpoint."],
  ["Every rendered figure is in one of three states.", "Every rendered dollar figure is in one of three states."],
  ["Figures in one of three states:", "Dollar figures in one of three states:"],
];
const A = [
  ["Every rendered number is in one of three citation states", "Every rendered dollar figure is in one of three citation states"],
  ["(dataset where row-level linkage is a work in progress). No number is displayed", "(a dataset without row-level citations). No dollar figure is displayed"],
];
const w = (s) => ({ raw: Buffer.byteLength(s), gzip: zlib.gzipSync(Buffer.from(s), { level: 9 }).length });
for (const [page, pairs] of [["methodology", M], ["about", A]]) {
  const before = fs.readFileSync(path.join(out, page, "index.html"), "utf8");
  let after = before;
  for (const [o, n] of pairs) {
    const k = after.split(o).length - 1;
    if (k !== 2) { console.log(`${page}: ${JSON.stringify(o.slice(0, 40))} occurs ${k}x (expected 2)`); process.exitCode = 1; }
    after = after.split(o).join(n);
  }
  const b = w(before), a = w(after);
  console.log(`/${page}/: ${b.raw} / ${b.gzip} -> ${a.raw} / ${a.gzip} (raw ${a.raw - b.raw >= 0 ? "+" : ""}${a.raw - b.raw}, gzip ${a.gzip - b.gzip >= 0 ? "+" : ""}${a.gzip - b.gzip})`);
}
EOF
```
Expected (measured 2026-10-13 on the `site/out` built 2026-10-04):

```
/methodology/: 161353 / 45338 -> 161369 / 45325 (raw +16, gzip -13)
/about/: 41071 / 8278 -> 41067 / 8265 (raw -4, gzip -13)
```
(node's zlib reads 45,338 where the stamp says 45,336.) /methodology/ stays under `162,000 / 45,400`. If an earlier task
rebuilt `site/out`, the absolute bytes differ but the deltas must match.

- [ ] **Step 6: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/site/src/app/methodology/page.tsx GovBudget/site/src/app/about/page.tsx GovBudget/site/scripts/gates/copy-allowlist.json GovBudget/site/src/__tests__/methodology-pending-ledger.test.ts && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "copy(methodology, about): one definition of citation tier pending; claims narrowed to dollar figures (#206 T7)" -m "Owner Q16, 2026-10-04. Shared phrase: a dataset without row-level citations (body, FAQ JSON-LD, /about/). Every rendered number -> every rendered dollar figure, which gate 2 enforces. The em-dash pair goes, so its copy-allowlist entry goes. By substitution: /methodology/ +16 raw / -13 gzip, /about/ -13 gzip." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
