<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the README's Contract Notes, section G6, hold this group's contract notes. -->

### Task 26b: ★ Release 2 (#195) — dry run, the owner's go-ahead, deploy with the R2 upload, live checks, ROADMAP stamp, publish

**Spec:** §8 (release 2: "Its deploy uploads the superseded volumes the citations now name to R2 through `deploy.sh` (at most 20 PDFs, 162,040,168 B; §5.6), and the owner's go-ahead names that upload and the re-measured weight of the heaviest program page; its stamp names the 111 `opening_only` citations (Q26)"; steps 6–10), §5.6 ("File separately"), §2.3 Q26. Depends on Task 26a. Task 26a's abort path stays in force until Step 4's deploy completes.
**Files:**
- Modify: `docs/superpowers/ROADMAP.md` — a phase-ledger row directly above the `| Post-launch |` row; a findings-log entry as the first item under `## Findings log (what we learned; feeds future phases)`; a new `**Status:**` marker on backlog #195 (the earlier marker's label restyled, its text untouched); four new backlog entries after the last numbered entry; a clause at the front of the `**Updated:**` header line (line 3)
- Modify: `tests/test_roadmap_backlog.py` — `FAMILIES_FOLLOW_UPS_STILL_OPEN` and the comment above it, as Task 22e left them ("which Task 26 empties when release 2 closes #195", Task 22e's Interfaces), and a new subject list and test for the four new entries, appended at the end of the file

**Interfaces:**
Consumes: Task 26a's export (`data/site`, `.proofs/fu2-release-export.sha256`, `.proofs/fu2-release-export.built_at`, `tmp/fu2-release-counts.json`) and its built `site/out`; Task 25b's `fu2-logs/relocation-report.json` (`new_pdfs`: the 20 volumes' shas and bytes) and Task 25c's measured page weight; `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh` (R2 copy of `data/site/{pdfs,data,workbooks,citations}`, Vercel, `verify_live_assets.mjs`); `scripts/launch/verify_live_assets.mjs --skip-site --sha=<sha>…` (probes exactly those PDFs on the asset host); remotes `origin` (monorepo) and `govbudget` (fiscalreceipts).
Produces: production at the release-2 HEAD, its R2 rollback tag, the 20 superseded volumes on R2, the ROADMAP stamp, monorepo `main` and fiscalreceipts `main` advanced.

**Measured now** (2026-10-13): `verify_live_assets.mjs` assertion 1 probes only the `--count` newest cited PDFs (`DEFAULT_COUNT = 5`), so this task probes all 20 new volumes by sha (Step 5); assertion 5 re-reads every `data/` and `citations/` object. `govbudget/main` is a merge commit the monorepo does not hold after every publish so far (piece 1 Task 23 Step 18), so the split needs the merge recipe again. The highest numbered backlog entry today is #206 (Task 1 files #207 and #208, and Task 22e Step 3 (f) files Q23's entry, #209 unless another lands first): Step 5 (d) numbers the new entries from the highest at stamp time.

- [ ] **Step 1: verify-phase5 (the full assembly, gate 5 included)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -lt 23 ] || [ "$MIN" -gt 28 ]; then echo "WAIT: start between :23 and :28 (minute $MIN): verify-phase5 now runs gate 5 (about 17 minutes) and must finish before the next SAM tick"; exit 0; fi
R=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-logs/release-verify-phase5-runtime.txt; [ -f "$R" ] || R=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/2026-10-04-piece1-followups/proof-logs/fu-logs/release-verify-phase5-runtime.txt
RT=$(awk '/^runtime / {print $2}' "$R" 2>/dev/null); : "${RT:?no release-1 verify-phase5 runtime: Task 22d Step 3 writes release-verify-phase5-runtime.txt}"; echo "release 1 verify-phase5: ${RT} s [$R]; with gate 5 about $(( RT + 1026 )) s"
if [ $(( RT + 1026 )) -gt 2940 ]; then echo "STOP: about $(( (RT + 1026) / 60 )) minutes: no start fits between two SAM ticks; ask the owner"; exit 1; fi
if [ $(( RT + 1026 )) -gt 2640 ] && [ "$MIN" -ne 23 ]; then echo "WAIT: about $(( (RT + 1026) / 60 )) minutes: start at :23 exactly (minute $MIN)"; exit 0; fi
S=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet && S0=$(stat -f %m "$S") && T0=$(date +%s)
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com uv run --project . python -m govbudget verify-phase5 > tmp/fu2-release-verify-phase5.log 2>&1; echo "exit=$?"; echo "runtime $(( $(date +%s) - T0 )) s, ended at minute $(date +%M)"; [ "$(stat -f %m "$S")" = "$S0" ] && echo "SAM parquet unchanged during verify-phase5" || echo "RE-RUN: the SAM parquet changed during verify-phase5"; grep -E "verify-phase5b1|verify-era-map|gate eval|gate assembly|^verify-phase5:" tmp/fu2-release-verify-phase5.log | tail -8
```
verify-phase5 now runs gate 5 (about 1,026 s, G6-7) on top of release 1's runtime, which Task 22d Step 3 kept in `.proofs/fu-logs/release-verify-phase5-runtime.txt` (or, after Task 22e's cleanup, the ledger's `proof-logs/fu-logs/` copy); the block reads it: if that runtime plus 1,026 s is more than 44 minutes (2,640 s), a start at :28 would run past :12, so it waits for :23 exactly; if it is more than 49 minutes (2,940 s), no start fits between two SAM ticks, and it stops — ask the owner. The SAM parquet's mtime check is the backstop (the job has stored nothing since 2026-10-04). Expected: `release 1 verify-phase5: <s1> s [<file>]; with gate 5 about <s1 + 1026> s`; `exit=0`; `runtime <s> s, ended at minute <m>` (the run must not have crossed :12–:22; if it did, the next line says whether the SAM job wrote meanwhile); `SAM parquet unchanged during verify-phase5`; the assembly lists `verify-phase5b1` and `verify-era-map` PASS; `verify-phase5: PASS` (it runs the paid live eval, 48 questions, as every release has). Exit 2 (`BLOCKED`) is not a pass: check the `.env` link (Task 26a Step 2) and re-run. A failure that cannot be cleared: Task 26a Step 3's abort path.

- [ ] **Step 2: Deploy dry run**

First the `data/site` check that opens Step 3 (read-only). Then:

```bash
/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh --dry-run > /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/fu2-release-deploy-dry.log 2>&1; echo "exit=$?"; grep -E "0/3|provenance:|untracked inputs|R2 pdfs|Dry run complete" /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/fu2-release-deploy-dry.log
```
Expected: `exit=0`; `0/3  preflight`; `provenance:      OK — git_head matches HEAD; no tracked changes; no untracked build inputs`; `untracked inputs: none`; `R2 pdfs:         <n> binaries to sync` with `<n>` = `tmp/fu2-release-counts.json` `release.pdf_files` (release 1's count plus 20); `Dry run complete — nothing was copied, uploaded or deployed.`

- [ ] **Step 3: ★ The owner's go-ahead, then deploy**

Tell the owner in chat, filling `<…>` from `tmp/fu2-release-counts.json`, Task 25c Step 5 and Task 26a Step 8:

"Ready to deploy release 2 of the piece-1 follow-ups (#195) at `<HEAD short sha>`. Narrative citations now name the volume that prints them: 4,177 gain a page (4,158 PB2026 narratives printed in another volume of their book set, and 19 lineage-evidence narratives that never had a location) and 228 move to the page that prints their whole paragraph; fact IDs do not change. The deploy uploads the 20 superseded PB2026 volumes those citations name to R2 (162,040,168 B). 111 citations keep a page that prints the opening but not the closing words (the Q26 ratchet, 111), and 1,444 stay pageless: 1,367 printed in no PDF we hold (1,342 of them from the Navy RDTEN BA1–3 master XML, whose BA4–7 books are not in the corpus) and 77 whose opening alone is printed somewhere — they stay pageless rather than cite an opening, and gate 5 ratchets them at 77 the same way (the ratchet you approved at Task 24 Step 0 on <date>; design §5.6 had counted them as printed). Heaviest program page `/program/0601102A/`: `<raw> / <gzip>` against 1,180,000 / 151,000, ceilings unchanged. SAM registrations shipped: `<SAM_D>` (0 expected). All gates green (verify-phase5, -5b1 with the new gate 5, -5e, -lineage, -era-map, link coverage, npm verify). Deploy now?"

Wait for an explicit yes; a "no" takes Task 26a Step 3's abort path. Then confirm `data/site` is still the release export (other worktrees link it; `deploy.sh` checks only git state):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L=/Users/andeslee/Documents/Cursor-Projects/GovBudget
(cd "$L" && shasum -a 256 -c --quiet .proofs/fu2-release-export.sha256) || { echo "STOP: data/site is no longer the release export (fingerprint mismatch)"; exit 1; }
H=$(shasum -a 256 "$L/data/site/json/f15_funding_history.json" | cut -d' ' -f1); { [ -n "$H" ] && [ "$H" = "$(cat tests/fixtures/f15/history.sha256)" ]; } || { echo "STOP: F-15 history does not match the pin"; exit 1; }
B=$(uv run --project . python -c "import json; print(json.load(open('$L/data/site/manifest.json'))['built_at'])"); [ "$B" = "$(cat "$L/.proofs/fu2-release-export.built_at")" ] || { echo "STOP: manifest built_at ($B) is not Task 26a Step 4's"; exit 1; }
echo "data/site is the release export: built_at $B"
```
Expected: `data/site is the release export: built_at <Task 26a Step 4's>`. Any `STOP`: do not deploy; re-run Task 26a Steps 4–8 or take its abort path. Then:

```bash
/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh > /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/fu2-release-deploy.log 2>&1; echo "exit=$?"; head -5 /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/fu2-release-deploy.log; grep -E "COPY  pdfs|rollback tag|Rollback copy made|Deploy complete" /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/fu2-release-deploy.log
```
Always by this absolute path, from this worktree, never the main checkout. Expected: `0/3  preflight` first; `exit=0`; `COPY  pdfs/ → …`; `rollback tag:    <YYYY-MM-DDTHHMMSSZ>`; `Rollback copy made and checked: r2:govbudget-assets/rollback/<tag>/`; `Deploy complete: …, live assets verified.` Record the tag. A failure after the copy prints the tag again: never re-run without reading it.

- [ ] **Step 4: Live checks**

The 20 new volumes on the asset host, every one (assertion 1 of the deploy's own check samples only the newest few):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
ARGS=(${(f)"$(uv run --project . python -c "import json; print('\n'.join('--sha=' + s for s in sorted(json.load(open('${GOVBUDGET_PROOFS:?}/fu2-logs/relocation-report.json'))['new_pdfs'])))")"}); echo ${#ARGS[@]}; node scripts/launch/verify_live_assets.mjs --skip-site "${ARGS[@]}" > tmp/fu2-release-live-pdfs.txt 2>&1; echo "exit=$?"; tail -3 tmp/fu2-release-live-pdfs.txt
```
Expected: `20`; `exit=0` and the last line `All <n> live-asset assertions passed.` (one `PASS` per volume — 200/206 with a non-empty `%PDF-` body — plus the fixed-name `data/` and `citations/` objects; `--sha` skips the receipt probes, `--skip-site` the site host).

*(2026-10-19: corrected after the release-2 run. The block first built `ARGS` as one space-joined string and passed `$ARGS` unquoted; zsh, the shell these blocks run in, does not word-split an unquoted parameter, so the first live probe sent all 20 shas as a single `--sha` value, one URL, and got HTTP 400. It now builds an array, one `--sha=` per line split by zsh's `(f)` flag, and passes `"${ARGS[@]}"`; the re-run probed all 20 volumes and passed, 39/39 assertions.)*

Then the pages and citations readers open:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && H=$(git rev-parse HEAD) && curl -s https://fiscalreceipts.com/.build-meta.json | grep -c "\"git_head\": \"${H}\"" && for fid in 136baeef904dd052 033016199ca94aa7 e7d5bcfb4a30f458; do curl -s "https://fiscalreceipts.com/json/cite-shards/${fid:0:2}.json" | uv run --project . python -c "import json,sys; c=json.load(sys.stdin)['$fid']; print('$fid', c['sha256'][:12], c['page_number'], c['hosted_pdf_url'].rsplit('#', 1)[1])"; done && curl -s https://fiscalreceipts.com/program/5731D15610/ | grep -c '184228d828aab1d64819d05f7cd66f24de5e7e28fbeccacf89db50fa15078195.pdf#page=100' && curl -s -o /dev/null -w "%{http_code}\n" -r 0-3 https://assets.fiscalreceipts.com/pdfs/184228d828aab1d64819d05f7cd66f24de5e7e28fbeccacf89db50fa15078195.pdf && curl -s https://fiscalreceipts.com/families/f-15/ | grep -c 'data-history-note="F015E0"' && curl -s https://fiscalreceipts.com/sitemap.xml | grep -o '<loc>[^<]*</loc>' | wc -l
```
Expected, in order: `1`; `136baeef904dd052 184228d828aa 100 page=100`; `033016199ca94aa7 8ef7d90e37f4 215 page=215`; `e7d5bcfb4a30f458 528d14414585 71 page=71`; a count ≥ 1 (the JLTV page embeds its narrative citation with the BA1 book's page); `206`; `1`; the URL count release 1 left (4,350 per design §8; #195 adds no page). A failed line here or in the PDF probe above: tell the owner at once with the rollback tag (Step 3); the owner decides whether to roll back (spec §8). On a yes: LAUNCH.md's rollback (Vercel to the previous deployment, then R2 `data/` and `citations/` from the rollback tag, the commands `deploy.sh` printed; the new `pdfs/` objects are content-addressed and may stay), then Task 26a Step 3's abort path (the `--revert` block, then the `data/site` restore), each with its SAM guard — the live database must not stay in the release's state under the rolled-back site.

- [ ] **Step 5: ROADMAP stamp**

Values come from `tmp/fu2-release-counts.json`, the deploy log, Task 25c Step 5 and Task 26a Step 8; nothing is re-read from the lake. In `docs/superpowers/ROADMAP.md`:

(a) A phase-ledger row directly above the `| Post-launch |` row:

```markdown
| Families-1 follow-ups R2 | #195: each narrative citation names the volume of its book set that prints it — migration 022 (`provenance_pages.printed_document_sha256`), the book-set relocation (`provenance_pages.plan_narrative_relocations`, written once by `scripts/fu/s195_narratives.py` with a pre-image and `--revert`), the export citing and hosting the printing volume, and `verify-jbook-narratives` (verify-phase5b1 gate 5, full population) | release-2 A/B on one snapshot (P2 equal, P1 within `expected-diff-r2-narratives.json`, `narrative_relocation_report.py`), the write and its `--revert` rehearsed, gate 5 red before and green after | ✅ DEPLOYED <YYYY-MM-DD> at <short sha> (rollback tag <tag>) | 4,177 narrative citations gain a page and 228 move (fact IDs unchanged); 20 superseded PB2026 volumes hosted on R2 (162,040,168 B); 111 opening-only (Q26 ratchet) and 77 opening-seen pageless (ratchet the owner approved <date of Task 24 Step 0's yes>) citations; 1,444 pageless (1,342 of them Navy RDTEN BA1–3 master-XML narratives whose books are not in the corpus); `/program/0601102A/` <raw> / <gzip> of 1,180,000 / 151,000; gates: npm verify overall PASS, verify-phase5 PASS (eval <x>/48), 5b1 (gate 5)/5e/lineage/era-map PASS, link-coverage PASS, evals check PASS |
```

(b) A findings-log entry as the first item under `## Findings log`:

```markdown
- **<YYYY-MM-DD>: Families piece-1 follow-ups, release 2 (#195) deployed.** The
  live writes ran in the proven order (`govbudget migrate` → 022; `jbooks
  narrative-provenance --lineage-evidence` → the 19 lineage-evidence rows that
  had never been built; `scripts/fu/s195_narratives.py --apply` → 4,386 rows,
  pre-image `.proofs/fu2-release-s195-pre-image.json`), each digest equal to the
  proof's (<D0> → <D1> → <D2>). The release export equals the proven export
  (`proof diff: EQUAL` against `.proofs/fu2-Bpost/site`); against the pre-release
  copy `.proofs/fu2-release-pre-site`, 4,177 narrative citations gained a page and
  228 moved, nothing outside their location fields changed, and the 20 superseded
  PB2026 volumes they name (162,040,168 B) were hosted and uploaded to R2 by
  `deploy.sh` (rollback tag <tag>; all 20 probed live). The defect was systemic,
  as the follow-ups design found: `dedup_service_master_dups` keeps one volume per
  master XML and attaches every narrative of the master to it, and two volumes
  can embed regenerated copies of one master (Army RDT&E Vol 1, docs 344 and 351),
  so a narrative is searched in its whole book set (edition, organization,
  exhibit family), and a new location needs the opening, the closing within three
  pages and the PE anchor. Live: #195's JLTV continuation sentence
  (`136baeef904dd052`) cites the BA1 book p.100; `033016199ca94aa7` the F-15EX
  P-40 in Vol II p.215; the F015E0 note receipt stays on Vol I p.71, so the F-15
  history did not change. Still pageless: 1,444 — 1,367 printed in no PDF we hold
  (1,342 from the Navy RDTEN BA1–3 master XML, filed as #<n2>) and 77 whose opening
  alone is printed (an opening is not a location: `033016199ca94aa7` sat on the
  wrong exhibit by its opening); gate 5 ratchets the 77 (owner-approved <date of Task 24 Step 0's yes>), as it does the 111
  opening-only paged citations (Q26). Gate 5 also found 19 lineage-evidence
  narratives with no provenance row at all (filed and closed as #<n1>). SAM: <SAM_D>
  registrations shipped.
```

(c) Backlog #195: a new marker directly above its current newest `**Status:**` line (`**Status:** open (2026-10-02).` today, unless release 1 added one), at the entry's 2-space indentation, then the line `  *(Earlier marker below.)*`, and that older marker's label alone restyled to `**Status (<its date>):**`, its text untouched (the convention of piece 1 Task 23 Step 13 (d) and README Ledger conventions):

```markdown
  **Status:** CLOSED <YYYY-MM-DD> — fixed systemically in release 2 of the
  piece-1 follow-ups (deployed <short sha>): every narrative citation names the
  volume of its book set that prints it (4,177 located, 228 moved, 20 superseded
  volumes hosted), and `verify-jbook-narratives` (verify-phase5b1 gate 5) checks
  the whole population, ratcheting 111 opening-only and 77 opening-seen
  citations. The JLTV sentence cites the BA1 book p.100.
  *(Earlier marker below.)*
```

and the old line directly below it becomes `  **Status (2026-10-02):** open (2026-10-02).` (its label alone restyled).

(d) Four new entries after the last numbered backlog entry, numbered from the highest at stamp time (`grep -oE '^- \*\*#[0-9]+' docs/superpowers/ROADMAP.md | tr -dc '0-9\n' | sort -n | tail -1`; `<n1>` = that + 1, and so on), in the entries' own format:

```markdown
- **#<n1> Lineage-evidence narratives without a provenance row.** 19 of the 92
  narratives a stated lineage edge cites (PB2017–PB2025) had no
  `provenance_pages` row, so their citations shipped without a page although
  their own volume prints them; `jbooks narrative-provenance --lineage-evidence`
  had not been re-run since their edges were added. Found by
  `verify-jbook-narratives` (Task 24), fixed by release 2's write (all 19 in
  their own volume). Source: `src/govbudget/cli.py` (`narrative-provenance
  --lineage-evidence`). Effort: hours.
  **Status:** CLOSED <YYYY-MM-DD> — built in release 2 (<short sha>).

- **#<n2> The Navy RDTEN BA4–7 books are not in the corpus.** 1,342 PB2026
  narratives come from the Navy RDT&E master XML embedded in the BA1–3 book
  (`RDTEN_BA1-3_Book.pdf`), which prints only BA1–3; no PDF we hold prints them,
  so their citations stay pageless (verify-jbook-narratives counts them in
  "opening printed nowhere"). Fix: acquire the BA4–7 volumes and let the book-set
  search place them. Source: `src/govbudget/jbooks/service_fetch.py` (the Navy
  book set), `src/govbudget/jbooks/provenance_pages.py` (`book_set`). Effort:
  hours (acquisition) plus a release.
  **Status:** open (<YYYY-MM-DD>).

- **#<n3> Are the 8,021 unresolved J-book detail amounts the same species as
  #195?** Narrative citations were attached to the kept volume of a master XML;
  detail amounts (`budget_line_details`, `jbook_pdf` citations) were extracted
  from the same masters, and 8,021 of them resolve to no page. Measure how many
  are printed in another volume of their book set before deciding. Source:
  `src/govbudget/jbooks/provenance_pages.py` (`build_provenance_pages`). Effort:
  hours to measure.
  **Status:** open (<YYYY-MM-DD>).

- **#<n4> Army RDT&E Vol 1 narratives ship twice.** Docs 344 (BA1) and 351
  (BA2) embed two regenerations of the Vol 1 master XML, and both are kept
  (`dedup_service_master_dups` groups by identical master sha), so 1,189
  narratives are attached to each and 1,207 PB2026 narrative pairs share
  (pe_bli, kind, body); `/program/0601102A/` lists 106 + 106. Since #195 both
  copies cite the same printing page. Fix: collapse regenerated masters (same
  narratives, different bytes) the way identical ones are, or dedup the page's
  list. Source: `src/govbudget/jbooks/service_fetch.py`
  (`dedup_service_master_dups`). Effort: hours.
  **Status:** open (<YYYY-MM-DD>).
```

(e) The `**Updated:**` header (line 3): put `<YYYY-MM-DD> (piece-1 follow-ups release 2 deployed at <short sha>: #195);` directly after `**Updated:** `, leaving the rest of the line unchanged.

(f) In `tests/test_roadmap_backlog.py`, replace (as Task 22e left it):

```python
# The piece-1 follow-ups release 1 (docs/superpowers/plans/2026-10-04-families-
# piece1-followups/tasks/22e-*) closed four of the five; #195 stays open until
# release 2. A closed entry keeps its old marker relabelled "Status (<date>):"
# below the new plain one, so each entry still has exactly one grep-able line.
FAMILIES_FOLLOW_UPS_STILL_OPEN = {"JLTV continuation sentence"}
```

with:

```python
# The piece-1 follow-ups release 1 (docs/superpowers/plans/2026-10-04-families-
# piece1-followups/tasks/22e-*) closed four of the five, and release 2
# (tasks/26b-*) closed #195. A closed entry keeps its old marker relabelled
# "Status (<date>):" below the new plain one, so each entry still has exactly
# one grep-able line.
FAMILIES_FOLLOW_UPS_STILL_OPEN: set[str] = set()
```

and append at the end of the file:

```python


# Filed by release 2 of the piece-1 follow-ups (#195; tasks/26b-*), by phrase:
# the gap the new gate found and closed, and the three it measured and left.
FOLLOW_UPS_RELEASE_2 = [
    "Lineage-evidence narratives without a provenance row",
    "The Navy RDTEN BA4–7 books are not in the corpus",
    "Are the 8,021 unresolved J-book detail amounts the same species",
    "Army RDT&E Vol 1 narratives ship twice",
]


@pytest.mark.parametrize("subject", FOLLOW_UPS_RELEASE_2)
def test_the_release_2_follow_ups_are_filed_once_with_effort_and_source(subject):
    hits = [(num, body) for num, body in entries() if subject in body]
    assert len(hits) == 1, f"{subject!r} filed {len(hits)} times, want 1"
    num, body = hits[0]
    assert EFFORT_RE.search(body), f"#{num} has no `Effort: hours|days|weeks`"
    assert POINTER_RE.search(body), f"#{num} names no source path"
    assert body.rstrip().splitlines()[-1].strip().startswith("**Status:** "), (
        f"#{num} does not end with its Status line"
    )
```

- [ ] **Step 6: Run the ledger test, then commit the stamp**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_roadmap_backlog.py -q 2>&1 | tail -1`
Expected: `… passed`, 0 failed (Task 22e's count plus the 4 new cases). A failure names the entry: fix the stamp (numbering, one plain Status line, the effort word, a source path), never the test.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/docs/superpowers/ROADMAP.md GovBudget/tests/test_roadmap_backlog.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(roadmap): stamp release 2 of the piece-1 follow-ups (#195; <short sha>, rollback tag <tag>)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: ★ The owner's go-ahead to publish, then publish**

Ask: "Deploy verified. Push the branch to monorepo `main` (fast-forward only), fast-forward the main checkout, and publish GovBudget to fiscalreceipts `main`?" Wait for an explicit yes. Then, as piece 1 Task 23 Steps 16–20 (the same commands; only the branch names differ):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git fetch origin && git merge-base --is-ancestor origin/main HEAD && echo "fast-forward from origin/main" && git push origin "HEAD:refs/heads/main"
```
Expected: `fast-forward from origin/main` and the push. If the ancestor check prints nothing, stop: someone advanced `origin/main`; never force.

Only between :25 and :10 past the hour (the SAM tick starts at :17):

```bash
MIN=$(date +%M) && if [ "$MIN" -ge 10 ] && [ "$MIN" -lt 25 ]; then echo "WAIT: minute $MIN is near the SAM tick"; else cd /Users/andeslee/Documents/Cursor-Projects && git rev-parse --abbrev-ref HEAD && git merge --ff-only origin/main && git log --oneline -1 && git status --porcelain --untracked-files=no; fi
```
Expected: `main`, a fast-forward to the pushed sha, and only the workspace's own modified `CLAUDE.md`. This ends Task 26a's hazard window: the main checkout now runs #195's exporter. (Release 2 changes no dbt test, so the main checkout's `dbt/target/manifest.json` needs no new `dbt parse`.)

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git fetch govbudget && git subtree split --prefix=GovBudget -b publish-fu2 && SPLIT=$(git rev-parse publish-fu2) && echo "SPLIT=${SPLIT}" && (git merge-base --is-ancestor govbudget/main "${SPLIT}" && echo "fast-forward" || echo "needs merge")
```
Expected: the split sha and `needs merge`. (On `fast-forward`, park the split itself: `git branch publish-fu2-merge publish-fu2`, and skip the next block.) If the split stops with `fatal: branch 'publish-fu2' is not an ancestor of commit …`, a previous attempt left a stale `publish-fu2`: inspect it (`git log -1 publish-fu2`), `git branch -D publish-fu2`, and re-run this block (a leftover that is an ancestor is moved forward in place: `Updated branch 'publish-fu2'`). A leftover `publish-fu2-merge` makes the next block's `git branch` refuse: check it (`git log -1 publish-fu2-merge`), `git branch -D publish-fu2-merge`, and re-run that block.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && GT=$(git rev-parse 'govbudget/main^{tree}') && MATCH=$(git log --format=%H HEAD | while read c; do [ "$(git rev-parse "${c}:GovBudget")" = "${GT}" ] && echo "${c}" && break; done) && echo "govbudget/main tree = ${MATCH}:GovBudget" && SPLIT=$(git rev-parse publish-fu2) && MERGE=$(GIT_AUTHOR_NAME="Andes Lee" GIT_AUTHOR_EMAIL="andes.lee444@gmail.com" GIT_COMMITTER_NAME="Andes Lee" GIT_COMMITTER_EMAIL="andes.lee444@gmail.com" git commit-tree "${SPLIT}^{tree}" -p "${SPLIT}" -p govbudget/main -m "Merge the piece-1 follow-ups release 2 (#195) into fiscalreceipts" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>") && git merge-base --is-ancestor govbudget/main "${MERGE}" && [ "$(git rev-parse "${MERGE}^{tree}")" = "$(git rev-parse HEAD:GovBudget)" ] && git branch publish-fu2-merge "${MERGE}" && echo "MERGE=${MERGE} ok, parked in refs/heads/publish-fu2-merge"
```
Expected: one monorepo commit whose `GovBudget` tree equals `govbudget/main`'s (release 1's publish); then `MERGE=<sha> ok, parked …`. No match: stop — fiscalreceipts holds content the monorepo lacks; reconcile, never force.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families || exit 1
git rev-parse --verify -q refs/heads/publish-fu2-merge > /dev/null || { echo "STOP: refs/heads/publish-fu2-merge is missing"; exit 1; }
git push govbudget publish-fu2-merge:refs/heads/main && git branch -D publish-fu2 publish-fu2-merge && git fetch govbudget && [ "$(git rev-parse 'govbudget/main^{tree}')" = "$(git rev-parse HEAD:GovBudget)" ] && echo "fiscalreceipts main == monorepo GovBudget"
```
Expected: the push, both branches deleted, `fiscalreceipts main == monorepo GovBudget`. (The push cannot deploy: `GovBudget/vercel.json` `git.deploymentEnabled: false`.)

- [ ] **Step 8: Report and offer the cleanup**

Report to the owner: the deployed sha and rollback tag, the counts of Step 3's go-ahead, the publish shas. First copy the release-2 proof and release logs into the worktree ledger, so the proof entry's bracketed log names stay readable after any cleanup (read-only on `.proofs`):

```bash
LEDGER=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/.superpowers/sdd/2026-10-04-piece1-followups/proof-logs && mkdir -p "$LEDGER/fu2-release" && cp -cR /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu2-logs "$LEDGER/fu2-logs" && cp -c /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/fu2-release-* /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu2-release-s195-pre-image.json "$LEDGER/fu2-release/" && ls "$LEDGER" && ls "$LEDGER/fu2-release" | wc -l
```
Expected: `fu-logs` (Task 22e's copy), `fu2-logs` and `fu2-release`, and the count of release-2 files copied. Then ask whether to remove the release-2 proof state (nothing is removed without a yes): under `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/`: `fu2`, `fu2-A`, `fu2-B`, `fu2-Bpost`, `fu2-B2post`, `fu2-logs` (copied above), `fu2-release-pre-site` (APFS clones holding their own exports), `fu2-release-export.sha256`, `fu2-release-export.built_at` and `fu2-release-s195-pre-image.json` (keep the pre-image at least until the owner is satisfied: it is the only record of the rows before the relocation); the scratch database `govbudget_proof_fu2`; the release-2 A worktree `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fu2-proof-a` (Task 25b's; kept until now, README "On a yes only"). On a yes:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && "${GOVBUDGET_PG_BIN:?}/dropdb" govbudget_proof_fu2 && git -C .. worktree remove --force /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fu2-proof-a && git -C .. worktree list | grep -c fu2-proof-a; cd "${GOVBUDGET_PROOFS:?}" && rm -rf fu2 fu2-A fu2-B fu2-Bpost fu2-B2post fu2-logs fu2-release-pre-site fu2-release-export.sha256 fu2-release-export.built_at && ls -A "$GOVBUDGET_PROOFS" | grep -c '^fu2'
```
Expected: `0` (the A worktree is gone), then `1` (only `fu2-release-s195-pre-image.json` left, unless the owner said to remove it too: then `rm "${GOVBUDGET_PROOFS:?}/fu2-release-s195-pre-image.json"` and `0`; its copy stays in the ledger).
