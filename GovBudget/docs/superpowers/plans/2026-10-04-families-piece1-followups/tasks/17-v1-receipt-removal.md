<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the approved design is ../../../specs/2026-10-04-families-piece1-followups-design.md. -->

### Task 17: remove the v1 PDF receipt writer, its unread seed and its 256 shards; ship only v2/ (#196)

**Spec:** design §5.7 (#196, owner sign-off 2026-10-04: delete `export_budget_pdf_receipts` and the two helpers only
it uses, `load_sources` and `tight_glyph_geometry`, the nine imports that become unused — AST-checked, the project
installs no ruff — and `data-seeds/f15_budget_pdf_sources.json`; `export_program_pdf_receipts` removes the top-level
`json/budget-pdf-receipts/[0-9a-f]{2}.json` and leaves `v2/`, with a pytest; `prepare-assets.mjs` removes the
destination parent, then copies only `v2/`; a new `build.mjs` leg checks `out/json/budget-pdf-receipts` holds exactly
`v2/` with 4,096 `[0-9a-f]{3}.json` files; no R2 step); §7 W1 (pyflakes via `uvx --offline ruff check --isolated
--select F,E9`, no finding beyond the HEAD baseline), W4 (gate 1).

**Files:**
- Modify: `src/govbudget/budget_pdf_receipts.py` (delete `tight_glyph_geometry` :91-115, `load_sources` :349-382,
  `export_budget_pdf_receipts` :393-472 by script; then the docstring and imports, :1-22)
- Modify: `src/govbudget/program_pdf_receipts.py` (`remove_v1_receipt_shards` before `export_program_pdf_receipts`
  :308; its call after `attach_additive_receipts(citations, receipts)` :417)
- Delete: `data-seeds/f15_budget_pdf_sources.json`
- Create: `tests/test_budget_pdf_v1_removal.py`
- Modify: `site/scripts/gates/build.mjs` (`checkShippedPdfReceipts` before "/** The leg. Returns" :995; its call before
  the "/json/feed.json is SHIPPED" section :1618)
- Modify: `site/scripts/prepare-assets.mjs` (step 5d2, :223-227)
- Create: `site/scripts/gates/__tests__/build-pdf-receipts.test.mjs`

Line numbers are hints measured at `532205c9` (anchor on the quoted text). The design's ":91-116" for
`tight_glyph_geometry` counts a blank line; the function's AST span is 91–115, which the deletion script pins.

**Interfaces:**
Consumes: `program_pdf_receipts` imports `amount, close_line, combine_receipts, match_cell, page_columns,
pdf_header_key, program_lines, select_glyph_geometry, title_identity, wrapped_title, inherited_activity` from
`budget_pdf_receipts` (all kept); `dossiers/claim_drift.py` imports `amount` (kept); `scripts/export_budget_pdf_receipts.py`
delegates to `govbudget export-budget-pdf-receipts`, which already runs `export_program_pdf_receipts` (kept);
`prepare-assets.mjs`' 5d2 guard (`pdfV2`, the schema-2 audit check) and `copyDir` (mirror: removes the destination
first); `build.mjs`' `outDir`, `dirExists`.
Produces: `program_pdf_receipts.remove_v1_receipt_shards(receipts_dir: Path) -> int`, called on every receipts
export (the release export, Task 22, removes the 256 live shards: Task 21's P2 rule "`json/budget-pdf-receipts/??.json`
only in A, 256 files"; `manifest.json` `json_sidecars` 36,271 → 36,015 before Task 13's two /years/ shards, recounted by
`cli._refresh_json_sidecars` after the receipts step); gate 1 export `checkShippedPdfReceipts(root = outDir) ->
{errors, notes}`, note `budget-pdf-receipts: exactly v2/ with 4,096 shards ✓`. Release live check (Task 22):
`/json/budget-pdf-receipts/00.json` → 404, a `v2/` shard → 200.

Verified now (read-only, 2026-10-13): `data/site/json/budget-pdf-receipts/` holds `v2/` (4,096 files) and 256
`??.json` files, 419,075 bytes, 169 of them non-empty; the worktree's `site/out` (built 2026-10-04) ships the same 256;
`data-seeds/f15_budget_pdf_sources.json` has 20 shas, all in `budget_pdf_sources.json`, and nothing reads it (only the
ROADMAP and the piece-1 Task 2 text name it). ruff at HEAD on `budget_pdf_receipts.py`: one finding, F841
`line_text` in `match_cell` (the baseline; kept).

- [ ] **Step 1: Write the failing Python tests**

Create `tests/test_budget_pdf_v1_removal.py`:

```python
"""ROADMAP #196 (families piece-1 follow-ups, design §5.7; owner sign-off
2026-10-04): the v1 F-15-only receipt writer, its unread PDF seed and the 256
two-hex shards it left are gone. program_pdf_receipts writes
json/budget-pdf-receipts/v2/, which is all the site reads
(site/src/lib/budget-pdf-receipts.ts), and now also clears the v1 shards an
older export left beside it, so the site build cannot ship them.
"""
from __future__ import annotations

import ast
from pathlib import Path

import govbudget.budget_pdf_receipts as receipts_v1
from govbudget.program_pdf_receipts import export_program_pdf_receipts, remove_v1_receipt_shards

ROOT = Path(__file__).resolve().parents[1]


def test_the_v1_writer_and_the_helpers_only_it_used_are_gone():
    for name in ("export_budget_pdf_receipts", "load_sources", "tight_glyph_geometry"):
        assert not hasattr(receipts_v1, name), name


def test_the_matcher_module_imports_nothing_it_does_not_use():
    tree = ast.parse(Path(receipts_v1.__file__).read_text(encoding="utf-8"))
    imported = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.update({(a.asname or a.name).split(".")[0]: node.lineno for a in node.names})
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            imported.update({a.asname or a.name: node.lineno for a in node.names})
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert sorted(set(imported) - used) == []


def test_the_unread_f15_pdf_seed_is_gone():
    assert not (ROOT / "data-seeds" / "f15_budget_pdf_sources.json").exists()
    assert (ROOT / "data-seeds" / "budget_pdf_sources.json").exists()


def test_the_export_removes_v1_shards_and_keeps_v2(tmp_path):
    site = tmp_path / "site"
    receipts = site / "json" / "budget-pdf-receipts"
    (receipts / "v2").mkdir(parents=True)
    for name in ("00.json", "a7.json", "ff.json"):
        (receipts / name).write_text("{}\n")
    (receipts / "README.txt").write_text("kept\n")
    (receipts / "v2" / "000.json").write_text('{"stale": {}}\n')
    (site / "json" / "citations.json").write_text("{}")
    manifest = tmp_path / "sources.json"
    manifest.write_text("[]")
    report = export_program_pdf_receipts(site_dir=site, manifest=manifest, cache_dir=tmp_path / "cache")
    assert sorted(p.name for p in receipts.iterdir()) == ["README.txt", "v2"]
    assert len(list((receipts / "v2").glob("*.json"))) == 4096
    assert (receipts / "v2" / "000.json").read_text() == "{}\n"
    assert report["receipt_count"] == 0


def test_remove_v1_receipt_shards_takes_only_two_hex_digit_files(tmp_path):
    assert remove_v1_receipt_shards(tmp_path / "absent") == 0
    (tmp_path / "v2").mkdir()
    (tmp_path / "v2" / "0f.json").write_text("{}")
    for name in ("0f.json", "10.json", "abc.json", "1g.json"):
        (tmp_path / name).write_text("{}")
    assert remove_v1_receipt_shards(tmp_path) == 2
    assert sorted(p.name for p in tmp_path.iterdir()) == ["1g.json", "abc.json", "v2"]
    assert (tmp_path / "v2" / "0f.json").exists()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_budget_pdf_v1_removal.py -q`
Expected: a collection error, `ImportError: cannot import name 'remove_v1_receipt_shards' from
'govbudget.program_pdf_receipts'`.

- [ ] **Step 3: Delete the v1 writer and the two helpers only it used**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - <<'EOF'
"""Delete the v1 writer and the two helpers only it used from
src/govbudget/budget_pdf_receipts.py by AST span (each def plus the blank
lines above it), refusing any span that is not the one measured 2026-10-13."""
import ast
import sys
from pathlib import Path

path = Path("src/govbudget/budget_pdf_receipts.py")
text = path.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)
spans = {n.name: (n.lineno, n.end_lineno) for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)}
expected = {"tight_glyph_geometry": (91, 115), "load_sources": (349, 382),
            "export_budget_pdf_receipts": (393, 472)}
for name, span in expected.items():
    if spans.get(name) != span:
        sys.exit(f"{name} spans lines {spans.get(name)}, expected {span}: re-measure before deleting")
drop = set()
for start, end in expected.values():
    drop.update(range(start - 1, end))
    k = start - 2
    while k >= 0 and not lines[k].strip():
        drop.add(k)
        k -= 1
path.write_text("".join(line for i, line in enumerate(lines) if i not in drop), encoding="utf-8")
print(f"{path}: removed {len(drop)} lines; {len(lines) - len(drop)} remain")
EOF
```
Expected: `src/govbudget/budget_pdf_receipts.py: removed 145 lines; 327 remain`.

Then trim the docstring and the imports:

In `src/govbudget/budget_pdf_receipts.py` (:1-22), replace:

```python
"""Reconcile F-15 workbook cells to the same-edition DoD P-1/R-1 PDF.

Only exact matches of account, line, program, fiscal column, and amount become
highlights. Parentheses around gross procurement amounts are not negatives;
the explicit minus sign on Less: Advance Procurement is retained. Printed
blanks are recorded separately for workbook zeros and never get a made-up box.
Canonical workbook citations and facts are not modified by this sidecar export.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from ctypes import c_double
from statistics import median
from pathlib import Path

import openpyxl
import pdfplumber
import pypdfium2 as pdfium
```

with:

```python
"""Exact-match primitives that bind a workbook cell to the same-edition DoD
P-1/R-1 PDF amount (program_pdf_receipts writes the receipts with them).

Only exact matches of account, line, program, fiscal column, and amount become
highlights. Parentheses around gross procurement amounts are not negatives;
the explicit minus sign on Less: Advance Procurement is retained. Printed
blanks are recorded separately for workbook zeros and never get a made-up box.
Canonical workbook citations and facts are not modified by the receipts.

The v1 F-15-only writer that lived here (export_budget_pdf_receipts, with
load_sources and tight_glyph_geometry, which only it used) and its unread
data-seeds/f15_budget_pdf_sources.json were removed with the owner's sign-off
(ROADMAP #196, 2026-10-04); program_pdf_receipts writes
json/budget-pdf-receipts/v2/, the only shards the site reads.
"""
from __future__ import annotations

import re
from collections import Counter
from statistics import median
```

- [ ] **Step 4: Clear v1 shards in the receipts export, and remove the unread seed**

In `src/govbudget/program_pdf_receipts.py` (:308), replace:

```python
def export_program_pdf_receipts(*, site_dir: Path, manifest: Path, cache_dir: Path, editions: set[int] | None = None) -> dict:
```

with:

```python
_V1_SHARD = re.compile(r"[0-9a-f]{2}\.json")


def remove_v1_receipt_shards(receipts_dir: Path) -> int:
    """Delete the 256 v1 shards (json/budget-pdf-receipts/??.json) the removed
    F-15-only writer left beside v2/ (ROADMAP #196: the site reads only v2/,
    and prepare-assets used to copy the whole directory, so they deployed).
    Only top-level two-hex-digit .json files go; v2/ and anything else stay.
    Returns the number removed."""
    if not receipts_dir.is_dir():
        return 0
    removed = 0
    for path in sorted(receipts_dir.iterdir()):
        if path.is_file() and _V1_SHARD.fullmatch(path.name):
            path.unlink()
            removed += 1
    return removed


def export_program_pdf_receipts(*, site_dir: Path, manifest: Path, cache_dir: Path, editions: set[int] | None = None) -> dict:
```

In `src/govbudget/program_pdf_receipts.py` (:417-418), replace:

```python
    attach_additive_receipts(citations, receipts)
    out = site_dir / "json/budget-pdf-receipts/v2"
```

with:

```python
    attach_additive_receipts(citations, receipts)
    remove_v1_receipt_shards(site_dir / "json/budget-pdf-receipts")
    out = site_dir / "json/budget-pdf-receipts/v2"
```

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git rm GovBudget/data-seeds/f15_budget_pdf_sources.json`
Expected: `rm 'GovBudget/data-seeds/f15_budget_pdf_sources.json'`.

- [ ] **Step 5: Run the Python tests and the import check**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_budget_pdf_v1_removal.py tests/test_budget_pdf_receipts.py tests/test_program_pdf_layouts.py tests/test_budget_pdf_export_workflow.py tests/test_dossier_claim_drift.py -q`
Expected: no failures (scratch overlay: `143 passed, 1 skipped`; in the worktree `test_shipped_f15_evidence_preserves_all_default_and_historical_cells`
reads `data/site` and runs instead of skipping).

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uvx --offline ruff check --isolated --select F,E9 src/govbudget/budget_pdf_receipts.py src/govbudget/program_pdf_receipts.py`
Expected: exactly the HEAD baseline — one finding, `F841` on `line_text` in `match_cell` — ending `Found 1 error.`

- [ ] **Step 6: Commit the Python side**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/budget_pdf_receipts.py GovBudget/src/govbudget/program_pdf_receipts.py GovBudget/tests/test_budget_pdf_v1_removal.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "chore(receipts): remove the v1 F-15 receipt writer and its unread seed; the export clears v1 shards (#196)" -m "Owner sign-off 2026-10-04. export_budget_pdf_receipts, load_sources, tight_glyph_geometry and nine unused imports go; data-seeds/f15_budget_pdf_sources.json (20 shas, all in budget_pdf_sources.json, no reader) goes; export_program_pdf_receipts removes json/budget-pdf-receipts/??.json and keeps v2/." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

(The `git rm` of Step 4 is already staged; this commit records it too.)

- [ ] **Step 7: Write the failing gate test**

Create `site/scripts/gates/__tests__/build-pdf-receipts.test.mjs`:

```js
/**
 * Gate 1's shipped-receipts leg (ROADMAP #196; follow-ups design §5.7).
 * out/json/budget-pdf-receipts must hold exactly v2/ with its 4,096
 * three-hex-digit shards: the 256 two-hex v1 shards an older export left
 * beside v2/ (419,075 bytes) are read by nothing and used to deploy.
 */
import fs from "fs";
import os from "os";
import path from "path";
import { afterEach, describe, expect, it } from "vitest";
import { checkShippedPdfReceipts } from "../build.mjs";

const roots = [];
function outRoot({ shards = 4096, beside = [], inV2 = [] } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "receipts-out-"));
  roots.push(root);
  const dir = path.join(root, "json", "budget-pdf-receipts");
  fs.mkdirSync(path.join(dir, "v2"), { recursive: true });
  for (let i = 0; i < shards; i++) fs.writeFileSync(path.join(dir, "v2", `${i.toString(16).padStart(3, "0")}.json`), "{}\n");
  for (const name of beside) fs.writeFileSync(path.join(dir, name), "{}\n");
  for (const name of inV2) fs.writeFileSync(path.join(dir, "v2", name), "{}\n");
  return root;
}
afterEach(() => { for (const root of roots.splice(0)) fs.rmSync(root, { recursive: true, force: true }); });

describe("checkShippedPdfReceipts", () => {
  it("passes on exactly v2/ with 4,096 shards", () => {
    expect(checkShippedPdfReceipts(outRoot())).toEqual({
      errors: [], notes: ["budget-pdf-receipts: exactly v2/ with 4,096 shards ✓"] });
  });

  it("fails when a v1 shard ships beside v2/", () => {
    expect(checkShippedPdfReceipts(outRoot({ beside: ["00.json"] })).errors).toEqual([
      'out/json/budget-pdf-receipts/ holds ["00.json","v2"]; it must hold exactly v2/ (ROADMAP #196)']);
  });

  it("fails on a missing shard or a stray file in v2/", () => {
    expect(checkShippedPdfReceipts(outRoot({ shards: 4095 })).errors).toEqual([
      "out/json/budget-pdf-receipts/v2/ holds 4095 entries, 4095 of them [0-9a-f]{3}.json shards; it must hold exactly the 4,096 shards"]);
    expect(checkShippedPdfReceipts(outRoot({ inV2: ["notes.txt"] })).errors).toEqual([
      "out/json/budget-pdf-receipts/v2/ holds 4097 entries, 4096 of them [0-9a-f]{3}.json shards; it must hold exactly the 4,096 shards"]);
  });

  it("fails when the directory was never copied", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "receipts-out-"));
    roots.push(root);
    expect(checkShippedPdfReceipts(root).errors).toEqual([
      "out/json/budget-pdf-receipts/ not found — prepare-assets 5d2 copies v2/ there"]);
  });
});
```

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run scripts/gates/__tests__/build-pdf-receipts.test.mjs`
Expected: `4 failed`, each with `TypeError: (0 , checkShippedPdfReceipts) is not a function` (`build.mjs` does not
export it yet).

- [ ] **Step 8: Add the gate leg and copy only v2/**

In `site/scripts/gates/build.mjs` (:995), replace:

```js
/** The leg. Returns {errors, notes} so runBuildGate can fold them in. */
```

with:

```js
/**
 * Shipped PDF receipts (ROADMAP #196; follow-ups design §5.7, owner sign-off
 * 2026-10-04): out/json/budget-pdf-receipts holds exactly v2/ — its 4,096
 * three-hex-digit shards and nothing else. The 256 two-hex v1 shards the
 * removed F-15-only writer left (419,075 bytes) are read by nothing
 * (src/lib/budget-pdf-receipts.ts fetches only v2/), and anything else here
 * ships to every reader. Returns {errors, notes}.
 */
export function checkShippedPdfReceipts(root = outDir) {
  const errors = [];
  const notes = [];
  const dir = path.join(root, "json", "budget-pdf-receipts");
  if (!dirExists(dir)) {
    errors.push("out/json/budget-pdf-receipts/ not found — prepare-assets 5d2 copies v2/ there");
    return { errors, notes };
  }
  const top = fs.readdirSync(dir).sort();
  if (top.length !== 1 || top[0] !== "v2" || !dirExists(path.join(dir, "v2"))) {
    const shown = JSON.stringify(top.slice(0, 5)) + (top.length > 5 ? ` and ${top.length - 5} more` : "");
    errors.push(`out/json/budget-pdf-receipts/ holds ${shown}; it must hold exactly v2/ (ROADMAP #196)`);
  }
  const v2 = dirExists(path.join(dir, "v2")) ? fs.readdirSync(path.join(dir, "v2")) : [];
  const shards = v2.filter((name) => /^[0-9a-f]{3}\.json$/.test(name));
  if (v2.length !== 4096 || shards.length !== 4096) {
    errors.push(`out/json/budget-pdf-receipts/v2/ holds ${v2.length} entries, ${shards.length} of them [0-9a-f]{3}.json shards; it must hold exactly the 4,096 shards`);
  }
  if (errors.length === 0) notes.push("budget-pdf-receipts: exactly v2/ with 4,096 shards ✓");
  return { errors, notes };
}

/** The leg. Returns {errors, notes} so runBuildGate can fold them in. */
```

In `site/scripts/gates/build.mjs` (:1618), replace:

```js
  // ── /json/feed.json is SHIPPED, parses, and carries cards ─────────────────
```

with:

```js
  // ── Shipped PDF receipts: exactly v2/ (ROADMAP #196) ──────────────────────
  {
    const r = checkShippedPdfReceipts();
    errors.push(...r.errors);
    notes.push(...r.notes);
  }

  // ── /json/feed.json is SHIPPED, parses, and carries cards ─────────────────
```

In `site/scripts/prepare-assets.mjs` (step 5d2, :223-227), replace:

```js
if (fs.existsSync(budgetPdfSrc)) {
  copyDir(budgetPdfSrc, path.join(jsonDestDir, "budget-pdf-receipts"));
} else {
  fs.rmSync(path.join(jsonDestDir, "budget-pdf-receipts"), { recursive: true, force: true });
}
```

with:

```js
// ROADMAP #196 (owner sign-off 2026-10-04): ship ONLY v2/. Mirroring the whole
// directory also deployed the 256 two-hex v1 shards an older export left
// beside it, which nothing reads. The destination parent is removed first, so
// a file an earlier build copied there cannot survive; gate 1 checks that
// out/json/budget-pdf-receipts holds exactly v2/ (checkShippedPdfReceipts).
const budgetPdfDest = path.join(jsonDestDir, "budget-pdf-receipts");
fs.rmSync(budgetPdfDest, { recursive: true, force: true });
copyDir(pdfV2, path.join(budgetPdfDest, "v2"));
console.log("✓  budget-pdf-receipts/v2/ (4,096 shards) → public/json/");
```

- [ ] **Step 9: Run the gate test, then prove the leg and the copy on real files**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && npx vitest run scripts/gates/__tests__/build-pdf-receipts.test.mjs`
Expected: `4 passed`.

The leg fires on today's build, which shipped the v1 shards (measured 2026-10-13):

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && node -e 'import("./scripts/gates/build.mjs").then(m => console.log(JSON.stringify(m.checkShippedPdfReceipts("out").errors)))'`
Expected: `["out/json/budget-pdf-receipts/ holds [\"00.json\",\"01.json\",\"02.json\",\"03.json\",\"04.json\"] and 252 more; it must hold exactly v2/ (ROADMAP #196)"]`
(if Task 1 or another task rebuilt `site/out` with this step's prepare-assets, the list is `[]` instead).

prepare-assets copies only `v2/` from the live `data/site`, which still holds the v1 shards (it reads `data/site`
and writes only `site/public`, which is gitignored except `public/llms.txt`):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site || exit 1
NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com node scripts/prepare-assets.mjs | grep "budget-pdf-receipts"
ls public/json/budget-pdf-receipts; ls public/json/budget-pdf-receipts/v2 | wc -l
node -e 'import("./scripts/gates/build.mjs").then(m => console.log(JSON.stringify(m.checkShippedPdfReceipts("public"))))'
git diff --stat -- public/llms.txt
```
Expected: `✓  budget-pdf-receipts/v2/ (4,096 shards) → public/json/`, then `v2`, then `4096`, then
`{"errors":[],"notes":["budget-pdf-receipts: exactly v2/ with 4,096 shards ✓"]}`, and no `llms.txt` diff (the
export it reads is the one 916ae88e's `llms.txt` was built from). If `llms.txt` differs, restore it with
`git checkout -- public/llms.txt`; Task 22 commits the release build's copy.

- [ ] **Step 10: Commit the site side**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/site/scripts/gates/build.mjs GovBudget/site/scripts/prepare-assets.mjs GovBudget/site/scripts/gates/__tests__/build-pdf-receipts.test.mjs && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "chore(site): ship only json/budget-pdf-receipts/v2/; gate 1 checks it holds exactly v2/ (#196)" -m "prepare-assets 5d2 removes the destination parent and copies v2/ alone; the 256 v1 shards (419,075 bytes) leave the deploy at the release. checkShippedPdfReceipts fails on anything beside v2/ or a v2/ that is not exactly 4,096 shards." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
