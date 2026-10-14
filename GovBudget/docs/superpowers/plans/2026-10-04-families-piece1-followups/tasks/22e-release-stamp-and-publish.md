<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13). -->

### Task 22e: Release 1 — ROADMAP stamp, publish, report and cleanup offer

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §8 step 8 (a ledger row and findings entry; Status lines on #193–#206, CLOSED or PARTIAL with the §6.9 reasons, never rewording an entry; the new entries closed; Q7's notes; the dated spec amendments; #10's SAM count), step 9 (fast-forward monorepo `main` and the main checkout; `git subtree split --prefix=GovBudget` from the toplevel, merge `govbudget/main` into the split, push to `govbudget` main; never push a worktree branch to `origin`), step 10 (report and cleanup offer), §2.2 Q15 (recorded in this stamp; the owner was told on 2026-10-04 and did not object), Q22 (the §6.9 items closed with a dated reason), Q23 ("filed for piece 2 in release 1's stamp": `site/src/lib/aliases.ts`). Piece-1 Task 23 Steps 13–21 are the model.

**Files:**
- Modify: `docs/superpowers/ROADMAP.md` — the `**Updated:**` line (line 3 today); a sentence after the "Follow-ups first (owner, 2026-10-04)" paragraph (anchor on its last sentence, "… and the Chem Demil write gets a `--revert` mode (Q24 (b)).", line 69 today); a phase-ledger row directly above `| Post-launch |` (line 234 today); a first entry under `## Findings log (what we learned; feeds future phases)` (line 270 today); new Status markers on backlog #193, #194, #196–#208 (each entry's one plain `**Status:**` line, today `**Status:** open (2026-10-02).` on #193–#197 and `**Status:** open (2026-10-04).` on #198–#206; Task 1 files #207 and #208 the same way); a new marker on numbered item 10 (anchor on `    **Status:** PARTIAL 2026-10-04 — 149 registrations are live (87 more`, line 5325 today); one new backlog entry, Q23's, directly above the line `*Status markers (one ledger sweep, 2026-08-24).* Every numbered entry below now` (line 5045 today; after Task 1 it follows #208)
- Modify: `tests/test_roadmap_backlog.py` — the `test_the_families_piece_1_follow_ups_are_filed_once_and_open` function (lines 247–256 today), which pins #193–#197 open, and a new test at the end of the file pinning Q23's entry
- Git (no file): monorepo `main` on `origin`; the main checkout `/Users/andeslee/Documents/Cursor-Projects`; fiscalreceipts `main` on the `govbudget` remote

**Interfaces:**
Consumes: Task 22d's deploy (HEAD short sha, the rollback tag in `$L/release-deploy.log`), `tmp/fu-release-counts.json` (Task 22c), `$L/p2b-report.json`, `$L/p1-content.txt`, `$L/p1-fact-delta.json` (Task 21f), `$L/release-verify-phase5.log`, the proof note `docs/superpowers/reviews/fu-release1-proof.md` (Task 21i); Task 1's backlog entries #207/#208 (`**Status:** open (2026-10-04).`) and its Q7/Q4 notes on #194 and piece-1 spec §5.2; Task 9's piece-1 spec §4.4 amendment (`decided_on`); Task 15's piece-1 spec §6.2 amendment (/years/ fence lifted).
Produces: the stamped ROADMAP, with Q23's entry filed as the next backlog number (#209 unless another entry lands first) and open for piece 2; the updated backlog test (`FAMILIES_FOLLOW_UPS_STILL_OPEN = {"JLTV continuation sentence"}`, which Task 26 empties when release 2 closes #195, and `test_the_aliases_ts_follow_up_is_filed_once_for_piece_2`); `origin/main`, the main checkout and `govbudget/main` at the release.

Measured for this task (2026-10-13): `govbudget/main` is `40b1cb4a` ("Merge families piece 1 …"), a merge commit not in the monorepo whose tree equals `7dccd983:GovBudget` (`759a84d3…`), so the split needs piece 1's merge recipe again (`git merge-base --is-ancestor govbudget/main 7dccd983` fails); the main checkout is on `main` at `7dccd983` with ` M CLAUDE.md` (the workspace file, not this project's) and many untracked paths; `tests/test_roadmap_backlog.py` passes 30 tests; the stamp script and the new test below were run on a copy of today's ROADMAP (stamping #193–#206 with sample values): every stamped entry keeps exactly one plain Status line and the five follow-up subject tests pass.

- [ ] **Step 1: The spec amendments and Q7 notes are in place (read-only)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && S=docs/superpowers/specs/2026-10-02-era-procurement-history-design.md && for t in decided_on 0390DOM "R-1 restatement\|restates R-1" "/years/"; do printf '%s: ' "$t"; grep -c "$t" "$S"; done; grep -n "^\*Amendment\|^\*Correction (2026-10-0[4-9]\|^\*Correction (2026-10-1" "$S" | tail -8; grep -c "^- \*\*#20[78] " docs/superpowers/ROADMAP.md
```
Expected: each count above 0, and the dated notes Task 1 (Q7 and Q4 on §5.2), Task 9 (§4.4, `decided_on`) and Task 15 (§6.2, the /years/ fence lifted) added, listed by line; then `2` (#207 and #208 filed). A missing one: the owning task is incomplete — stop and finish it there, not here.

- [ ] **Step 2: Stamp the backlog Status lines**

Each entry keeps its words; its plain `**Status:**` line is relabelled with its own date (`**Status (2026-10-02):** open (2026-10-02).`), and a new plain marker plus `*(Earlier marker below.)*` goes directly above it (the #191 convention, ROADMAP line 4776). Before running, read each text below against the commits of the task it names (`git -C .. log --oneline <merge-base>..HEAD`): if a task left one of the entry's own bullets undone and §6.9 does not list it, edit that entry's text to `PARTIAL <date> — … Still open: <the bullet>.` before you run the script. The script reads the dates and numbers it prints from the release's own records:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fu-logs"
DATE=$(date +%Y-%m-%d) && SHA=$(git rev-parse --short=8 HEAD) && TAG=$(sed -n 's/.*rollback tag: *\([0-9TZ-]*\).*/\1/p' "$L/release-deploy.log" | head -1) && F15_LEFT=$(cd site && node -e 'const fs=require("fs"),z=require("zlib");console.log((70000-z.gzipSync(fs.readFileSync("out/families/f-15/index.html"),{level:9}).length).toLocaleString("en-US"))') && echo "date $DATE | deployed $SHA | tag ${TAG:?no rollback tag in the deploy log} | f-15 gzip left $F15_LEFT"
uv run --project . python - "$L/p2b-report.json" "$DATE" "$SHA" "$TAG" "$F15_LEFT" <<'PY'
import json, re, sys, textwrap  # follow-ups Task 22e: stamp the Status lines of #193, #194, #196-#208
from pathlib import Path

roadmap = Path("docs/superpowers/ROADMAP.md")
p2b = json.loads(Path(sys.argv[1]).read_text())
# Q13's clause swap ships only if /methodology/ fit its weight ceiling (spec §3.7; Task 21h).
Q13 = "the edition workbook simply holds no line for that program and column" in Path(
    "site/out/methodology/index.html").read_text(encoding="utf-8")
Q13_TEXT = "the Q13 clause on /methodology/" if Q13 else "Q13's clause swap dropped for weight, spec §3.7"
DATE, SHA, TAG, F15_LEFT = sys.argv[2:6]
REL = f"follow-ups release 1 (deployed {SHA}, rollback tag {TAG}; proof docs/superpowers/reviews/fu-release1-proof.md)"
added = p2b["decade_cells_added"]
org_extra = sorted({c for cells in p2b["org_split_nondecade_added"].values() for c in cells})
NEW = {
    193: f"CLOSED {DATE} — {REL}: /years/ ships as a schema-2 core `json/years_matrix.json` ({p2b['sizes']['years_matrix.json']['bytes']:,} bytes, {p2b['sizes']['years_matrix.json']['gzip']:,} gzip, under the 780,074 budget) plus the lazy `json/years_matrix/decade.json` and `json/years_matrix/detail.json`, each under the unchanged 4 MiB cap measured on the bytes written; the era fence is lifted, adding the {added['era']:,} PB2017–PB2023 cells the program pages carry (yearsmatrix leg j: 0 mismatches against the sidecars). #206 T4 closes with it.",
    194: f"CLOSED {DATE} — {REL}: the O&M line loads under the route-safe key 0390DOM (the printed code O&M stays in `line_item_code`; `dbt/seeds/p1_route_safe_codes.csv`) with the rollup-tier page /program/0390DOM/; the RDT&E line is recorded as an R-1 restatement of 0708081D + 0708083D and gets no page (owner, Q1 (a)); the era O&M chain joins 0390DOM as owner batch R-DEC-ERA-B7 and the era RDT&E chain keeps `exclude_route_unsafe` (Q4); the 0390D account's PB2026 FY24A / FY25E / FY26R are now the P-1's own 1,089,964 / 775,507 / 213,282; `scripts/clean_junk_pe_bli.py` is retired; `assert_budget_lines_route_safe_pe_bli` guards `budget_lines`.",
    196: f"CLOSED {DATE} — {REL}: `export_budget_pdf_receipts`, its two helpers, nine unused imports and `data-seeds/f15_budget_pdf_sources.json` are removed; the export deletes the 256 v1 shards and `prepare-assets.mjs` copies only `v2/`; live /json/budget-pdf-receipts/00.json answers 404 while `v2/` answers 200.",
    197: f"CLOSED {DATE} — {REL}: `search_aliases.csv` routes JASSM to /program/0207325F/ and C-130J to /program/0401132F/, as #55 did; a test requires every search term that matches a `program_aliases` alias to target a member of that alias's target set.",
    198: f"PARTIAL {DATE} — follow-ups Task 4, shipped in {REL}: rule 4(b) runs in `propose`; a class result that differs from a seeded decision goes to review (how B7 reached the owner); `propose` writes its five outputs atomically; `--decided-on` defaults to `CLASS_RULINGS_DECIDED_ON`; literal successors first; evidence quotes escaped; `EraKeyConflict` lives in `era_keys`; `ratify` reads chains.csv only for successors and reports every error per row; the review page records review.csv's sha256 and refuses a changed file; ratify's success message names the one build invocation; tests pin that a mere mention is not a successor and that `propose` opens the lake read-only; and (Task 8) UNSAFE narrows to the unaliased (0390D, RDT&E) pair, any other unsafe code raising. Not done (owner, Q22, 2026-10-04): the successor search for the 133 digits-only chains ($20,293,971K, all history_only, so no page changes) and the dict field in the frozen `Chain` (never hashed). Still open (neither scheduled nor closed by the follow-ups design): titles containing ' | ' read as drift (fails safe), and the test gaps None in a present key, a multi-page collision chain and per-edition R3.",
    199: f"CLOSED {DATE} — follow-ups Task 2, used by {REL}: snapshot hermeticity checked by resolved path, the SAM window over the whole copy, the symlink scan and digests before `create database` (a failure drops only the tool's own database), a quoted env.sh default, a DSN with a password refused, the untested refusals tested, non-finite JSON-in-string values kept as text, noise file schema 2 with tree digests (a DIFFERENT control deletes a stale file), `fact_stability.py` on a public proof API, the `s4_report` docstring, and dated notes on families-s1-proof.md and families-s1b-proof.md. Not done (owner, Q22, 2026-10-04): `measured_on` masked at any depth, dotted numeric text, two noisy lenient columns (fails safe), the 16-hex `{{fid}}` rule (no live segments), a repeatable `--noise-from`, and expected-diff rules 5–8, 17, 33 and 35 (built when piece 2's proof needs them).",
    200: f"CLOSED {DATE} — follow-ups Task 5, run in {REL}: link-coverage fails when the baseline recorded `receipts_match_citations` and the report has none, compares before it writes and refuses one path for both, counts a summary card with a value and no citation as (d), and reports the detail cards cited by XML path with no fact ID as their own count (Q20); tool errors exit 2.",
    201: f"CLOSED {DATE} — follow-ups Tasks 20 and 21h, shipped in {REL}: realpath direct-run guards in the five scripts; the page snapshot captures the coverage paragraph, total-row header, Partial badges, matrix note and notes list (re-pinned in Task 21h); the capture rebuilds from the round-tripped fixture and writes atomically; the family-history gate checks the note href and the receipt's page, sha and `#page=`; the F015E0 row header carries the `aria-label` \"BLI F015E0 F-15e (FY2020 F-15EX Lot 1 aircraft) Procurement · Historical code\" (Q21); verify.mjs prints \"+N more notes\". Not done (owner, Q22, 2026-10-04): trimming /families/f-15/ now ({F15_LEFT} gzip bytes are left after T9, measured in Task 21h); the lazy narratives wait for piece 2.",
    202: f"CLOSED {DATE} — follow-ups Task 3, ahead of {REL}: `P1KeyConflict` when two groups share the full upsert key (amount_type included; 0 across the 20 workbooks), a modern P-1 test for `line_item_code`, the classified-title tripwire test, and the p1_loader comment and the crosswalk S1b date fixed.",
    203: f"CLOSED {DATE} — follow-ups Task 9, shipped in {REL}: `assert_p1_era_map_collision_pinned` requires both pins; the full era-key regex at all ten sites; `_ERA_KEY_RE` anchored with `\\Z`; the four unplanted legs planted; leg a's classified filter and failure branches tested; a bad `--legs` exits 2; `ensure_lake_columns` unlinks its temporary file. Not done (owner, Q22, 2026-10-04): a sheet name in `source_cells` (every era row comes from \"Exhibit P-1\", and the change would alter a published dataset).",
    204: f"CLOSED {DATE} — follow-ups Task 16, shipped in {REL}: `era_grain_fids` is a required keyword-only argument of `_emit_lineage`, `_emit_json_sidecars` and `_write_all_sidecars` (an `inspect.signature` test pins it); `_emit_years_matrix` no longer takes it (#193 lifted that fence); an invariant at the `build_lineage_flow` call asserts that no chosen amount fid is an era grain.",
    205: f"CLOSED {DATE} — follow-ups Task 1, used by {REL}: `site/package-lock.json` locks @emnapi/wasi-threads 1.2.3 and `npm ci` passes; the two build.mjs comments say the era table was decided on 2026-10-02 at plan review: /downloads/. Not done (owner, Q22, 2026-10-04): a `package.json` overrides pin, unless the one-entry fix breaks again.",
    206: f"CLOSED {DATE} — {REL}: T4 by #193 (yearsmatrix leg j proves \"absent means absent\"; {Q13_TEXT}); T6 `p1_era_line_map` publishes `decided_on` (column 14 of 18; verify-era-map leg b compares it with the seed); T7 one definition of \"tier pending\" on /methodology/ and /about/ (the Q16 strings); T9 the F015E0 note reads \"This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include …\" (the owner's string, Q17); T11 verify-era-map legs g (era minters) and h (era book diffs).",
    207: f"CLOSED {DATE} — follow-ups Task 13, shipped in {REL}: `_acct_key` gates the account on `is_account_split`, so the seven org-split rows carry their {added['modern_org_split']} modern and {added['era_org_split']} era decade cells on /years/ (P2b) and their non-decade cells {', '.join(org_extra) or 'unchanged'}; /programs/ shows their FY24 and FY26.",
    208: f"CLOSED {DATE} — follow-ups Task 14, shipped in {REL}: /agency/[org]/ looks decade cells up by `slug ?? pe_bli`, so the 27 split-key rows render their cells.",
}
text = roadmap.read_text(encoding="utf-8")
lines = text.split("\n")
starts = {int(m.group(1)): i for i, l in enumerate(lines) if (m := re.match(r"^- \*\*#(\d+)\b", l))}
for n, body in sorted(NEW.items(), reverse=True):
    i = starts[n]
    nxt, after_blank = i + 1, False          # the entry's end, as tests/test_roadmap_backlog.py reads it
    while nxt < len(lines) and not (re.match(r"^- \*\*#\d+\b", lines[nxt]) or (
            after_blank and lines[nxt].strip() and not lines[nxt][0].isspace() and not lines[nxt].startswith("- "))):
        after_blank = not lines[nxt].strip()
        nxt += 1
    plain = [j for j in range(i, nxt) if re.match(r"^\s*\*\*Status:\*\* ", lines[j])]
    assert len(plain) == 1, (n, plain)
    j = plain[0]
    indent = re.match(r"^(\s*)", lines[j]).group(1)
    old_date = re.search(r"\d{4}-\d{2}-\d{2}", lines[j]).group(0)
    lines[j] = lines[j].replace("**Status:** ", f"**Status ({old_date}):** ", 1)
    new = textwrap.wrap("**Status:** " + body, width=78, initial_indent=indent, subsequent_indent=indent,
                        break_on_hyphens=False, break_long_words=False)
    lines[j:j] = new + [f"{indent}*(Earlier marker below.)*"]
roadmap.write_text("\n".join(lines), encoding="utf-8")
print("stamped:", ", ".join(f"#{n}" for n in sorted(NEW)))
PY
git -C .. diff --stat -- GovBudget/docs/superpowers/ROADMAP.md
```
Expected: `date … | deployed <the deployed short sha> | tag <the rollback tag> | f-15 gzip left <n>`, `stamped: #193, #194, #196, #197, #198, #199, #200, #201, #202, #203, #204, #205, #206, #207, #208`, and the diff stat. HEAD here is still the deployed commit (Task 22d's last commit), so `SHA` is the one production serves. An `AssertionError` names an entry with no single plain Status line: read it and fix it by hand, never by rewording the entry.

- [ ] **Step 3: The rest of the ROADMAP stamp**

Values that move with SAM fetches come from `tmp/fu-release-counts.json` (Task 22c), never from a later read of the lake: they describe the export that shipped. Fill every `<…>` from the file named beside it; `<panel.a.programs>`, `<panel.b.programs>`, `<panel.a.fy2024a_to_fy2026r_pct>`, `<panel.b.fy2024a_to_fy2026r_pct>`, `<panel.a.first_to_last_pct>` and `<panel.b.first_to_last_pct>` are the keys of `$L/p2b-report.json` that Task 22d Step 5 printed (signed, as printed: `9.34` reads `+9.34`, `-2.61` reads `−2.61`).

(a) Phase ledger: insert directly above the `| Post-launch |` row:

```markdown
| Families-1 FU-1 | Piece-1 follow-ups, release 1: `/years/` sharded (schema-2 core + lazy decade and detail shards) with its era fence lifted (#193, #206 T4, #207, #208); the 0390D Chem Demil O&M line under the route-safe key 0390DOM with a rollup-tier page and the era O&M chain as owner batch R-DEC-ERA-B7, the RDT&E line recorded as an R-1 restatement of 0708081D + 0708083D (#194); `p1_era_line_map.decided_on` (#206 T6); the v1 receipt files removed (#196); JASSM/C-130J search aliases (#197); one "tier pending" definition (T7); the F015E0 gloss (T9); verify-era-map legs g and h (T11); hardening #198–#205 | P1/P2/P2b/P3 proofs on snapshots fu-pre/fu-post, the write rehearsed on fu-post and fu-pre and its `--revert` on fu-pre ([proof](reviews/fu-release1-proof.md)) + yearsmatrix leg j + verify-era-map a–h + link-coverage V9 | ✅ DEPLOYED <YYYY-MM-DD> at <short sha> (rollback tag <tag>) | /years/ +14,985 era cells and the org-split rows' 63 modern cells, leg j 0 mismatches, core <bytes> / <gzip> gzip (budget 780,074), decade <bytes> / <gzip>, detail <bytes> / <gzip> [p2b-report.json]; /program/0390DOM/ with <e> points before PB2024 [p1-content.txt]; totals chart panel <panel.a.programs> → <panel.b.programs> programs, FY2024A→FY2026R <panel.a.fy2024a_to_fy2026r_pct>% → <panel.b.fy2024a_to_fy2026r_pct>% (Q15; told 2026-10-04: 524 → 1,056 and +9.3% → about −2.5%) [p2b-report.json]; citations 143,841 → <N> (+<WAVE_D> 0390DOM, +<SAM_D> SAM #10) [fu-release-counts.json]; 256 v1 receipt files gone; universe 385,268,393 → 385,271,636 ($385.3B); gates: npm verify overall PASS, verify-phase5 PASS (eval <x>/48), 5b1/5e/lineage/era-map a–h PASS, link-coverage PASS, evals check PASS |
```

(b) After the "Follow-ups first (owner, 2026-10-04)" paragraph's last sentence ("… and the Chem Demil write gets a `--revert` mode (Q24 (b)).") append, on new lines in the same paragraph:

```markdown
**Follow-ups release 1 deployed (<YYYY-MM-DD>, <short sha>):** #193, #194 and
#196–#208 are closed or partial with their dated reasons; #195 ships as release 2.
The `/years/` totals chart's balanced panel grew from <panel.a.programs> to
<panel.b.programs> programs and its FY2024A→FY2026R change turned from
<panel.a.fy2024a_to_fy2026r_pct>% to <panel.b.fy2024a_to_fy2026r_pct>% (Q15: the owner
was told on 2026-10-04 that the panel would grow from 524 to 1,056 programs and the
change move from +9.3% to about −2.5%, and did not object; the deploy go-ahead named
the measured figures, which differ because the seven org-split rows #207 fixed
joined the panel).
```

(c) Findings log: insert as the first item under `## Findings log (what we learned; feeds future phases)`:

```markdown
- **<YYYY-MM-DD>: Families piece-1 follow-ups, release 1.** Proven on two snapshots
  of one live state, `.proofs/fu-pre` and `.proofs/fu-post` (equal pins: DuckDB at
  copy, every parquet file but `sam/`, the site and raw_docs digests, each Postgres
  table's row count and row md5 — two `pg_dump` archives of one database differ in
  their header, so the dump sha is not a pin). On fu-post the Chem Demil write
  committed once after a dry run (its revert file kept); on fu-pre, after its
  exports, the same write equalled fu-post's, ids included, the two revert files'
  pre-write rows were equal, `--revert` returned every Postgres pin to fu-pre's
  pre-write pins, and a second `--revert` found nothing to revert; the abort
  path's lake rebuild by the deployed code, rehearsed on a clone of fu-post,
  equalled fu-pre's lake. The live write's pre-image rows equalled the
  rehearsals'. One `dbt build` of the seeds and
  `stg_budget_lines+` built the map before the program table and ran the
  conservation test after both. The re-paired proofs held: P2 (A@fu-pre vs B@fu-pre,
  code only) moved no fact; P2b put 14,985 era and 63 modern cells on /years/ with
  0 mismatches against the program pages; P1 (B@fu-pre vs B@fu-post, lake only)
  added <WAVE_D> facts, every one traced to 0390DOM, and moved exactly eleven
  derived aggregates by +3,243 — the design's §4.7 named five; the other six are
  the flow chart's "Other" nodes and edges on the same path; P3 moved the F-15
  history only in F015E0's note ([proof](reviews/fu-release1-proof.md)). A fresh
  snapshot before the write carried fu-pre's pins; after it, the live lake equalled
  fu-post (`scripts/fu/lake_parity.py`), and the release export equalled B@fu-post
  but for the SAM registrations (`proof diff` with the control's noise classes).
  The export also shipped <SAM_D> SAM.gov registrations stored since 916ae88e
  (`companies_with_sam` 149 → <b>, one derived citation each; citations 143,841 →
  <N> = +<WAVE_D> 0390DOM +<SAM_D> SAM). Deployed by `deploy.sh` from the families
  worktree (rollback tag <tag>); live: `/.build-meta.json` <short sha>, the three
  /years/ files share one `build_id`, a /years/ load fetches only the core,
  `/program/0390DOM/` 200, `/json/budget-pdf-receipts/00.json` 404, sitemap 4,350,
  the JASSM and C-130J aliases on their #55 pages, F01500's FY2015 actuals
  (`3bd9c921b2397209`) on /years/. The totals chart's panel is
  <panel.b.programs>, not the design's 1,056: the design's simulation left the
  seven org-split rows without cells, and #207's fix gives them all twelve
  default columns.
```

(d) Item 10 (SAM entity extract / Splink): relabel its newest marker and put the new one above it, at the same 4-space indentation. Replace the line `    **Status:** PARTIAL 2026-10-04 — 149 registrations are live (87 more` with `    **Status (2026-10-04):** PARTIAL 2026-10-04 — 149 registrations are live (87 more` (the label alone restyled, the closing `**` where it was; its body untouched), and insert directly above it:

```markdown
    **Status:** PARTIAL <YYYY-MM-DD> — <b> registrations are live (<SAM_D> more
    than the 149 of 916ae88e), shipped with the piece-1 follow-ups release 1 at
    <short sha> (rollback tag <tag>): the daily job stored them after the
    2026-10-04 export and the release export carried them (`json/sam` 149 → <b>
    receipts, `site_meta.counts.companies_with_sam` 149 → <b>, one derived
    citation each). All 200 published families have a stored SAM answer
    (`data/parquet/sam/daily/state.json`, read <YYYY-MM-DD>); the Splink
    entity-resolution upgrade is still open.
    *(Earlier markers below.)*

```
(Read `state.json`'s `last_message` first, outside :12–:22; if it no longer says all 200 have an answer, write what it says.) If `SAM_D` is 0, skip (d).

(e) Line 3: replace the opening `**Updated:** ` with `**Updated:** <YYYY-MM-DD> (families piece-1 follow-ups release 1 deployed at <short sha>; SAM #10 status; Q23 filed for piece 2); ` and leave the rest of the line unchanged.

(f) Q23, filed for piece 2 (spec §2.2 Q23, §8 step 8): one new backlog entry, numbered from the highest in the backlog section, directly above the sweep note that follows the last entry. The subject phrase `the search seeds disagree on B-21` sits on one line, which Step 4's test reads:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
DATE=$(date +%Y-%m-%d) && uv run --project . python - "$DATE" <<'PY'
import re, sys
from pathlib import Path

roadmap = Path("docs/superpowers/ROADMAP.md")
DATE = sys.argv[1]
text = roadmap.read_text(encoding="utf-8")
start = text.index("\n## Improvement backlog")
end = text.index("\n## ", start + 1)
n = max(int(x) for x in re.findall(r"^- \*\*#(\d+)\b", text[start:end], re.M)) + 1
anchor = "*Status markers (one ledger sweep, 2026-08-24).* Every numbered entry below now"
assert text.count(anchor) == 1 and start < text.index(anchor) < end
entry = f"""- **#{n} `site/src/lib/aliases.ts` and the search seeds disagree on B-21.**
  The chip table `PROGRAM_ALIASES` in `site/src/lib/aliases.ts` maps B-21 to
  0604015F (the Long Range Strike - Bomber RDT&E line) as well as B02100, under
  different chip semantics, while `dbt/seeds/program_aliases.csv` sends B-21 to
  B02100 alone. #197's cross-seed test (`tests/test_dossiers_research.py`)
  checks only `data-seeds/search_aliases.csv` against
  `dbt/seeds/program_aliases.csv`; the owner chose not to extend it to
  `aliases.ts` and to leave this for the families registry (piece 2), which
  becomes the single source of program aliases (follow-ups design Q23,
  2026-10-04; re-read {DATE}). Source: `site/src/lib/aliases.ts`. Effort: hours.
  **Status:** open ({DATE}) — for piece 2.

"""
roadmap.write_text(text.replace(anchor, entry + anchor, 1), encoding="utf-8")
print(f"filed #{n}")
PY
```
Expected: `filed #209` (or the next number, if another entry was filed since Task 1's #208).

- [ ] **Step 4: The backlog test follows the closures**

In `tests/test_roadmap_backlog.py`, replace:

```python
@pytest.mark.parametrize("subject", FAMILIES_FOLLOW_UPS)
def test_the_families_piece_1_follow_ups_are_filed_once_and_open(subject):
    hits = [(num, body) for num, body in entries() if subject in body]
    assert len(hits) == 1, f"{subject!r} filed {len(hits)} times, want 1"
    num, body = hits[0]
    assert EFFORT_RE.search(body), f"#{num} has no `Effort: hours|days|weeks`"
    assert POINTER_RE.search(body), f"#{num} names no source path"
    assert body.rstrip().endswith("**Status:** open (2026-10-02)."), (
        f"#{num} does not end with its open-status line"
    )
```
with:

```python
# The piece-1 follow-ups release 1 (docs/superpowers/plans/2026-10-04-families-
# piece1-followups/tasks/22e-*) closed four of the five; #195 stays open until
# release 2. A closed entry keeps its old marker relabelled "Status (<date>):"
# below the new plain one, so each entry still has exactly one grep-able line.
FAMILIES_FOLLOW_UPS_STILL_OPEN = {"JLTV continuation sentence"}


@pytest.mark.parametrize("subject", FAMILIES_FOLLOW_UPS)
def test_the_families_piece_1_follow_ups_are_filed_once_and_stamped(subject):
    hits = [(num, body) for num, body in entries() if subject in body]
    assert len(hits) == 1, f"{subject!r} filed {len(hits)} times, want 1"
    num, body = hits[0]
    assert EFFORT_RE.search(body), f"#{num} has no `Effort: hours|days|weeks`"
    assert POINTER_RE.search(body), f"#{num} names no source path"
    plain = [line.strip() for line in body.splitlines() if "**Status:**" in line]
    assert len(plain) == 1, f"#{num} has {len(plain)} plain Status lines"
    if subject in FAMILIES_FOLLOW_UPS_STILL_OPEN:
        assert body.rstrip().endswith("**Status:** open (2026-10-02)."), (
            f"#{num} does not end with its open-status line"
        )
    else:
        assert plain[0].startswith("**Status:** CLOSED "), f"#{num} is not stamped CLOSED"
        assert "**Status (2026-10-02):** open (2026-10-02)." in body, (
            f"#{num} lost its earlier marker"
        )
```

and append at the end of the file:

```python


# Filed by the piece-1 follow-ups release 1 stamp (tasks/22e-*; design Q23): the
# alias table the search seeds do not check, left for the families registry
# (piece 2). Only the filing is pinned, so the test survives its closure.
Q23_SUBJECT = "the search seeds disagree on B-21"


def test_the_aliases_ts_follow_up_is_filed_once_for_piece_2():
    hits = [(num, body) for num, body in entries() if Q23_SUBJECT in body]
    assert len(hits) == 1, f"{Q23_SUBJECT!r} filed {len(hits)} times, want 1"
    num, body = hits[0]
    assert EFFORT_RE.search(body), f"#{num} has no `Effort: hours|days|weeks`"
    assert POINTER_RE.search(body), f"#{num} names no source path"
```

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_roadmap_backlog.py -q`
Expected: `33 passed` (30 today, Task 1's two #207/#208 cases, and the Q23 test). A failure names the entry: fix the stamp, not the test.

- [ ] **Step 5: Commit the stamp**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/docs/superpowers/ROADMAP.md GovBudget/tests/test_roadmap_backlog.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(roadmap): stamp the piece-1 follow-ups release 1 deploy (<short sha>, rollback tag <tag>); close #193, #194, #196-#208; file Q23 for piece 2" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: `2 files changed`.

- [ ] **Step 6: ★ Owner go-ahead to publish the code**

Ask the owner: "Release 1 is live and stamped. #198 is stamped PARTIAL: four items neither the design scheduled nor closed stay open (titles containing ' | ' read as drift, which fails safe, and the test gaps 'None in a present key', 'a multi-page collision chain' and 'per-edition R3'); say if you want them closed with a dated reason instead. Q23 (`aliases.ts`) is filed as #<n> for piece 2. Push the branch to monorepo `main` (fast-forward only), fast-forward the main checkout, and publish GovBudget to fiscalreceipts `main`?" Wait for an explicit yes to the publish; an answer on #198 is applied as a further dated Status marker in a separate commit before Step 7.

- [ ] **Step 7: Fast-forward monorepo `main`**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git fetch origin && git merge-base --is-ancestor origin/main HEAD && echo "fast-forward from origin/main" && git push origin "HEAD:refs/heads/main"
```
Expected: `fast-forward from origin/main`, then `7dccd983..<sha>  HEAD -> main` (or from whatever `origin/main` was, if it is an ancestor). If the ancestor check prints nothing (the `&&` chain stops before the push), someone advanced `origin/main`: stop and report; never force.

- [ ] **Step 8: Fast-forward the main checkout (the SAM job runs from it) and refresh its dbt manifest**

Only between :25 and :10 past the hour (the SAM tick starts at :17):

```bash
MIN=$(date +%M) && if [ "$MIN" -ge 10 ] && [ "$MIN" -lt 25 ]; then echo "WAIT: minute $MIN is near the SAM tick"; else cd /Users/andeslee/Documents/Cursor-Projects && git rev-parse --abbrev-ref HEAD && git merge --ff-only origin/main && git log --oneline -1 && git status --porcelain --untracked-files=no && cd GovBudget && uv run --no-sync dbt parse --project-dir dbt --profiles-dir dbt > /dev/null && python3 -c "import json; m=json.load(open('dbt/target/manifest.json')); print('dbt test nodes:', sum(1 for n in m['nodes'].values() if n['resource_type'] == 'test'))"; fi
```
Expected: `main`, a fast-forward to the pushed sha, only ` M CLAUDE.md`, then `dbt test nodes: <n>` equal to B's count (Task 21d Step 5). Without the parse, the main checkout's manifest stays at 196 and its next export would put "196" back on /methodology/ (piece-1 INT-3). `--no-sync` leaves the venv the SAM job uses untouched; if the new code needs a package the venv lacks, the next tick fails loudly — tell the owner to run `uv sync` there. If `--ff-only` refuses, stop and report. From here the main checkout runs the release's code, so Task 22b's hazard ends.

- [ ] **Step 9: Split the subtree**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git fetch govbudget && git subtree split --prefix=GovBudget -b publish-fu1 && SPLIT=$(git rev-parse publish-fu1) && echo "SPLIT=${SPLIT}" && (git merge-base --is-ancestor govbudget/main "${SPLIT}" && echo "fast-forward" || echo "needs merge")
```
Expected: the split sha and `needs merge` (`govbudget/main` `40b1cb4a` is a merge commit the monorepo lacks). On `fast-forward`, skip Step 10 and park the split itself: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git branch publish-fu1-merge publish-fu1`. If the split stops with `fatal: branch 'publish-fu1' is not an ancestor of commit …`, a previous attempt left a stale `publish-fu1`: inspect it (`git log -1 publish-fu1`), `git branch -D publish-fu1`, and re-run this block. (A leftover that is an ancestor of the new split is moved forward in place: `Updated branch 'publish-fu1'`, which is fine.)

- [ ] **Step 10: Confirm fiscalreceipts holds nothing the monorepo lacks, then merge**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && GT=$(git rev-parse 'govbudget/main^{tree}') && MATCH=$(git log --format=%H HEAD | while read c; do [ "$(git rev-parse "${c}:GovBudget")" = "${GT}" ] && echo "${c}" && break; done) && echo "govbudget/main tree = ${MATCH}:GovBudget" && git log -1 --format='%h %s' "${MATCH}"
```
Expected: one monorepo commit, `7dccd983` (unless another publish happened since; any commit of this branch's history is fine). If nothing matches, stop: fiscalreceipts holds content the monorepo lacks — reconcile, never force. Then:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && SPLIT=$(git rev-parse publish-fu1) && MERGE=$(GIT_AUTHOR_NAME="Andes Lee" GIT_AUTHOR_EMAIL="andes.lee444@gmail.com" GIT_COMMITTER_NAME="Andes Lee" GIT_COMMITTER_EMAIL="andes.lee444@gmail.com" git commit-tree "${SPLIT}^{tree}" -p "${SPLIT}" -p govbudget/main -m "Merge families piece-1 follow-ups release 1 into fiscalreceipts" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>") && git merge-base --is-ancestor govbudget/main "${MERGE}" && [ "$(git rev-parse "${MERGE}^{tree}")" = "$(git rev-parse HEAD:GovBudget)" ] && git branch publish-fu1-merge "${MERGE}" && echo "MERGE=${MERGE} ok, parked in refs/heads/publish-fu1-merge"
```
Expected: `MERGE=<sha> ok, parked in refs/heads/publish-fu1-merge`. Step 11 pushes the parked ref by name, never a shell variable that could be empty (an empty source would make `:refs/heads/main` a delete refspec). If `git branch` refuses because the ref exists, a previous attempt left it: check it (`git log -1 publish-fu1-merge`), `git branch -D publish-fu1-merge`, and re-run this block.

- [ ] **Step 11: Publish to fiscalreceipts and delete the temporary branches**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families || exit 1
git rev-parse --verify -q refs/heads/publish-fu1-merge > /dev/null || { echo "STOP: refs/heads/publish-fu1-merge is missing: run Step 10 (or Step 9's fast-forward line) first"; exit 1; }
git push govbudget publish-fu1-merge:refs/heads/main && git branch -D publish-fu1 publish-fu1-merge && git fetch govbudget && [ "$(git rev-parse 'govbudget/main^{tree}')" = "$(git rev-parse HEAD:GovBudget)" ] && echo "fiscalreceipts main == monorepo GovBudget"
```
Expected: `40b1cb4a..<sha>  publish-fu1-merge -> main`, the two `Deleted branch …` lines, `fiscalreceipts main == monorepo GovBudget`. The push cannot deploy (`GovBudget/vercel.json` `git.deploymentEnabled: false`).

- [ ] **Step 12: Report, and offer the cleanup**

Report to the owner: the deployed sha and rollback tag; the /years/ numbers (cells added, file sizes); the 0390DOM page; the totals that moved and the panel change (Q15); `<SAM_D>` SAM registrations shipped alongside; the publish shas; that release 2 (#195, Tasks 23–26) takes its own fresh snapshot and does not need this release's proof state. First copy the proof and release logs into the worktree ledger, so the proof note's bracketed log names stay readable after any cleanup (read-only on `.proofs`):

```bash
LEDGER=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/2026-10-04-piece1-followups/proof-logs && mkdir -p "$LEDGER" && cp -cR /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-logs "$LEDGER/fu-logs" && cp -c /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-release-s194-pre-image.json /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/fu-release-counts.json "$LEDGER/" && ls "$LEDGER" && ls "$LEDGER/fu-logs" | wc -l
```
Expected: `fu-logs`, `fu-release-counts.json`, `fu-release-s194-pre-image.json`, and the log count. Then ask whether to remove it (nothing is removed without a yes): under `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/` — `fu-pre`, `fu-post`, `fu-pre-A`, `fu-pre-B`, `fu-post-B`, `fu-post-B2`, `fu-rel`, `fu-release-pre-site`, `fu-logs` (copied to the ledger above), `fu-release-export.sha256`, `fu-release-export.built_at`, `dbt-parse-a.duckdb`/`dbt-parse-b.duckdb` if present (APFS clones; each export holds about 2 GB of its own blocks), and Task 1's `fu-npmci` (its `npm ci` check tree); keep `fu-release-s194-pre-image.json` unless the owner says otherwise (it is the only record of the 16 rows before the live write, and `--revert`'s input); the scratch databases `govbudget_proof_fu_pre`, `govbudget_proof_fu_post` and `govbudget_proof_fu_rel`; the A worktree `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a`. On a yes:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
for n in fu_pre fu_post fu_rel; do "${GOVBUDGET_PG_BIN:?}/dropdb" --if-exists "govbudget_proof_$n"; done
git -C .. worktree remove --force /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families-fu-a && git -C .. worktree list | grep -c families-fu-a
cd "${GOVBUDGET_PROOFS:?}" && rm -rf fu-pre fu-post fu-pre-A fu-pre-B fu-post-B fu-post-B2 fu-rel fu-release-pre-site fu-logs fu-release-export.sha256 fu-release-export.built_at dbt-parse-a.duckdb dbt-parse-b.duckdb fu-npmci && ls -A "$GOVBUDGET_PROOFS"
```
Expected: `0` (the A worktree is gone), then `ls` shows `fu-release-s194-pre-image.json` and only what other work keeps there (`testpg`, `testpg.log`, and release 2's directories if it has started). If the owner said to remove the pre-image too: `rm "${GOVBUDGET_PROOFS:?}/fu-release-s194-pre-image.json"` (its copy stays in the ledger).
