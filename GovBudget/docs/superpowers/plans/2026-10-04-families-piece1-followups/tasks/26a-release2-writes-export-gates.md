<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the README's Contract Notes, section G6, hold this group's contract notes. -->

### Task 26a: ★ Release 2 (#195) — the owner's go-ahead, live writes, export, release-state checks, gates, build

**Spec:** §8 (release 2; the steps of piece 1 Task 23 as amended, RR-1…RR-6 and INT-1…INT-5), §5.6, §2.2 Q19 (A), §2.3 Q24 (b) (the abort path uses `--revert`) and Q26, §7 W3–W6. Task 26 is split in two: 26a (this file, up to a built and verified site) and 26b (dry run, the owner's go-ahead, deploy, live checks, ROADMAP stamp, publish). Depends on Task 25c.
**Files:**
- Modify (by the build, committed only if it changed): `site/public/llms.txt`
- Modify (only if `evals check` finds stale answers explained by this release): `evals/phase5_questions.yaml`

**Shared-state writes in this task** (the plan README's shared-write list must name them; they are release 2's only ones besides the abort path):
1. live Postgres: `govbudget migrate` (applies `022_provenance_pages_printed_document.sql`: one nullable column and one check constraint on `provenance_pages`);
2. live Postgres: `govbudget jbooks narrative-provenance --lineage-evidence` (inserts the 19 lineage-evidence narrative rows that were never built; contract issue G6-3);
3. live Postgres: `scripts/fu/s195_narratives.py --apply` (updates the 4,386 relocated narrative rows' location columns and `built_at`, one transaction, pre-image first);
4. the live `data/site`: the release export (Step 4).
Each runs outside :12–:22, by absolute path from this worktree. No lake parquet, DuckDB table or dbt model changes in release 2.

**Hazard until Task 26b publishes.** The main checkout (and every older worktree that links `data/site`) runs code without #195 until Task 26b fast-forwards it. Its `export-site` would read a relocated row's page and box but cite the ATTACHED document's sha and URL — a page of the wrong book. Nothing scheduled runs `export-site` there (`launchctl list` shows only the SAM job, checked in Step 1), so keep the window between Step 3 and Task 26b's publish short, and take the abort path below if the release stops.

**Interfaces:**
Consumes: Task 25b/25c records in `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu2-logs/` (`digest-pre.txt` D0, `digest-mid.txt` D1, `digest-post.txt` D2, `max-id-before.txt`, `provenance-seq-before.txt`, `noise-fu2.json`, `relocation-report.json`) and the proven export `.proofs/fu2-Bpost/site`; `scripts/fu/s195_narratives.py` (`--digest`, `--apply`, `--revert`); `scripts/fu/narrative_relocation_report.py`; `govbudget verify-jbook-narratives`, `verify-phase5b1`, `verify-phase5e`, `verify-lineage`, `verify-era-map`, `evals check`, `link-coverage`; `govbudget proof diff`; `scripts/era/env.sh` (`GOVBUDGET_PG_BIN`, `GOVBUDGET_PROOFS`).
Produces: the release export in the main lake's `data/site`, its fingerprint `.proofs/fu2-release-export.sha256` and `.proofs/fu2-release-export.built_at`, its counts `tmp/fu2-release-counts.json`; the pre-release copy `.proofs/fu2-release-pre-site`; the live pre-image `.proofs/fu2-release-s195-pre-image.json` (the abort path's input); a built and verified `site/out` at HEAD. Task 26b deploys them.

**Measured now** (2026-10-13; Tasks 23c, 24 and 25b give the counts the release must reproduce): live digest D0 `3e61258310ef4ce9a7fae630daf8eb62`; `schema_migrations` ends at 021; the SAM job is finished (`data/parquet/sam/daily/state.json`: "all 200 published families have a stored SAM answer", every daily tick since 2026-10-06 fetched 0; `entities.parquet` and `answers.parquet` last written 2026-10-04 21:17), so a release export carries no SAM change the proof did not; `launchctl list` holds `com.fiscalreceipts.sam-daily` only.

- [ ] **Step 1: Preconditions — the live state is the proof's starting state**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git status --porcelain -- GovBudget | grep -v '^??'; git log --oneline -1; cd GovBudget && source scripts/era/env.sh && "$GOVBUDGET_PG_BIN/pg_isready" -h 127.0.0.1 -p 55432 && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q 2>&1 | tail -1; launchctl list | grep -i fiscalreceipts
```
Expected: no tracked change; HEAD is Task 25c's commit (or its ceiling commit); `accepting connections`; `… passed`, 0 failed; one line ending `com.fiscalreceipts.sam-daily`. Another `fiscalreceipts` job (a `refresh` plist loaded since): stop — it could export from the main checkout during the hazard window.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}"; L=/Users/andeslee/Documents/Cursor-Projects/GovBudget
uv run --project . python scripts/fu/s195_narratives.py --digest --dsn postgresql://localhost/govbudget; echo "D0 = $(cat "$P/fu2-logs/digest-pre.txt")"
"$GOVBUDGET_PG_BIN/psql" postgresql://localhost/govbudget -Atc "select count(*) from schema_migrations where name = '022_provenance_pages_printed_document.sql'"
echo "live max id $("$GOVBUDGET_PG_BIN/psql" postgresql://localhost/govbudget -Atc 'select max(id) from provenance_pages'), proof $(cat "$P/fu2-logs/max-id-before.txt")"
SEQ=$("$GOVBUDGET_PG_BIN/psql" postgresql://localhost/govbudget -At -F' ' -c "select last_value, is_called from provenance_pages_id_seq") && [ -n "$SEQ" ] && [ "$SEQ" = "$(cat "$P/fu2-logs/provenance-seq-before.txt")" ] && echo "provenance_pages_id_seq unchanged since the snapshot ($SEQ)" || echo "STOP: provenance_pages_id_seq is live '$SEQ', proof '$(cat "$P/fu2-logs/provenance-seq-before.txt")'"
for f in entities answers; do [ "$(shasum -a 256 < "$L/data/parquet/sam/$f.parquet")" = "$(shasum -a 256 < "$P/fu2/parquet/sam/$f.parquet")" ] && echo "sam/$f.parquet unchanged since the snapshot" || echo "STOP: sam/$f.parquet changed since the snapshot"; done
curl -s https://fiscalreceipts.com/.build-meta.json | python3 -c "import json,sys; print('live git_head', json.load(sys.stdin)['git_head'])"
"$GOVBUDGET_PG_BIN/psql" postgresql://localhost/govbudget -Atc "select count(*) from jbook_documents where file_path like '%/.claude/worktrees/%'"
```
Expected: `state digest: <D0>` equal to the `D0 =` line; `0` (022 not applied live); the two max ids equal; `provenance_pages_id_seq unchanged since the snapshot (<last_value> <t|f>)` (Task 25b Step 6's `provenance-seq-before.txt`: a value spent on live after the snapshot, even by a rolled-back insert, would give the 19 lineage-evidence rows other ids than D1 holds, and Step 3 would stop after writing them); both `sam/… unchanged since the snapshot`; the live `git_head` Task 25b Step 1 recorded (release 1's deploy); `0`. Any difference: the live state moved after Task 25b's snapshot. Do not write; re-run Task 25 (b and c) on a fresh snapshot, or ask the owner.

- [ ] **Step 2: Point the worktree at the main lake and the main `.env`**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && for d in site duckdb parquet raw raw_docs; do if [ -e data/${d} ] && [ ! -L data/${d} ]; then echo "STOP: data/${d} is a real directory"; else ln -sfn /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/${d} data/${d}; fi; done; [ -e .env ] || ln -s /Users/andeslee/Documents/Cursor-Projects/GovBudget/.env .env; ls -l data .env | grep -- '->'; git -C .. status --porcelain -- GovBudget/data GovBudget/.env
```
Expected: six symlinks (five lake directories and `.env`) and no status output. Never print `.env`'s contents.

- [ ] **Step 2b: ★ Owner go-ahead for the live Postgres writes**

Tell the owner: "The release-2 proof passed (Task 25c's findings-log entry; P2 equal, P1 within its rule list, the relocation and its `--revert` rehearsed on the fu2 snapshot) and the live database is in the state the proof started from (Step 1). Next I write live Postgres: migration 022 (one nullable column and one check constraint on `provenance_pages`), the 19 lineage-evidence narrative rows that were never built, and the relocation of 4,386 narrative rows, with a pre-image (`.proofs/fu2-release-s195-pre-image.json`) that `--revert` restores from. If anything fails before the deploy, `s195_narratives.py --revert` restores the 4,386 rows; migration 022's column and the 19 rows stay — no code before #195 reads the column, and the 19 rows cite pages of their own documents. Until release 2 is published, please run nothing from the main checkout. Go ahead?" Wait for an explicit yes. No reply is not a yes. On a no, stop: nothing is written.

- [ ] **Step 3: The live writes (SHARED POSTGRES WRITES 1–3), in the proof's order**

Each block starts with the SAM guard; run them one after another (no export or gate in between).

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
mkdir -p tmp && GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget migrate 2>&1 | tee tmp/fu2-release-migrate.log
```
Expected: `migrations applied: ['022_provenance_pages_printed_document.sql']`. Anything else applied: stop and read it (an unexpected migration is not this release's).

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}"; MAXID=$(cat "$P/fu2-logs/max-id-before.txt")
GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget jbooks narrative-provenance --lineage-evidence 2>&1 | tee tmp/fu2-release-lineage-evidence.log
"$GOVBUDGET_PG_BIN/psql" postgresql://localhost/govbudget -Atc "select count(*), count(printed_document_sha256), count(page_number) from provenance_pages where target_kind = 'narrative' and id > ${MAXID:?}"
uv run --project . python scripts/fu/s195_narratives.py --digest --dsn postgresql://localhost/govbudget; echo "D1 = $(cat "$P/fu2-logs/digest-mid.txt")"
```
Expected: `narrative-provenance: scoped to 92 lineage-evidence narrative(s)`, `narrative-provenance: 19 inserted; located 6115/11980 ({'ambiguous_first': 657, 'unique': 5458, 'unresolved': 5865})`; `19|0|19`; `state digest: <D1>` equal to the `D1 =` line. A different digest: stop before the relocation (the abort path's step 1 is not needed: nothing is relocated yet; the 19 rows are correct for every code version, Task 25b Step 6).

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}"; D1=$(cat "$P/fu2-logs/digest-mid.txt")
uv run --project . python scripts/fu/s195_narratives.py --apply --pre-image "$P/fu2-release-s195-pre-image.json" --expect-pre-digest "${D1:?}" --dsn postgresql://localhost/govbudget > tmp/fu2-release-s195-apply.log 2>&1; echo "exit=$?"; grep -v '^  cites ' tmp/fu2-release-s195-apply.log; echo "D2 = $(cat "$P/fu2-logs/digest-post.txt")"
```
Expected: `exit=0`; `pre-write digest: <D1>`; `rows 11717: kept 5776, located 4158, relocated 228, opening_only 111, unresolved 1444`; `pre-image: …/.proofs/fu2-release-s195-pre-image.json (11980 rows)`; `updated 4386 row(s); post-write digest: <D2>` equal to the `D2 =` line; `committed`. The live database is now exactly the proven state. A post-write digest that differs from D2 after `committed`: take the abort path at once.

**Abort path (SHARED WRITES: restores Postgres and `data/site`; Q24 (b) for release 2).** Any stop after the `--apply` above that does not end in a deploy — a failed check in Steps 4–8, a failure in Task 26b before its deploy, the owner's "no" — runs, each block outside :12–:22:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python scripts/fu/s195_narratives.py --revert --pre-image "${GOVBUDGET_PROOFS:?}/fu2-release-s195-pre-image.json" --dsn postgresql://localhost/govbudget; echo "D1 = $(cat "$GOVBUDGET_PROOFS/fu2-logs/digest-mid.txt")"
```
Expected: `reverted 4386 row(s); digest <D1> equals the pre-image's` (Task 25c Step 4 rehearsed it). Migration 022's column and the 19 lineage-evidence rows stay: no code before #195 reads the column, and those rows name no other volume, so the main checkout exports them as correct pages of their own documents. If Step 4's export has run, also restore `data/site`, keeping the aborted export aside (nothing is deleted):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
mv data/site data/site.fu2-release-aborted-$(date -u +%Y%m%dT%H%M%SZ) && cp -cR .proofs/fu2-release-pre-site data/site && shasum -a 256 data/site/manifest.json .proofs/fu2-release-pre-site/manifest.json
```
Expected: the two hashes are equal. Remove `data/site.fu2-release-aborted-*` only on the owner's word. If the stop comes after Task 26b's deploy, the owner decides first; on a yes, roll the site back by LAUNCH.md's rollback procedure (Vercel to the previous deployment, then R2 `data/` and `citations/` from `deploy.sh`'s rollback copy; the new `pdfs/` objects are content-addressed and may stay), then run both blocks above.

- [ ] **Step 4: Keep a local copy of the live export, then export (SHARED WRITE 4: data/site)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && P="${GOVBUDGET_PROOFS:?}" && { [ -e ${P}/fu2-release-pre-site ] || cp -cR /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site ${P}/fu2-release-pre-site; } && ls ${P}/fu2-release-pre-site/manifest.json && ls ${P}/fu2-release-pre-site/pdfs | wc -l
```
Expected: the manifest path, then release 1's PDF count (225 before release 1; release 1 adds none). Then, starting only between :21 and :45 past the hour (the export takes about 15 minutes; the SAM job writes at :17):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && MIN=$(date +%M) && if [ "$MIN" -lt 21 ] || [ "$MIN" -gt 45 ]; then echo "WAIT: start between :21 and :45 (now :$MIN)"; else S0=$(stat -f %m /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet) && GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget export-site > tmp/fu2-release-export.log 2>&1; echo "exit=$?"; S1=$(stat -f %m /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet); [ "$S0" = "$S1" ] && echo "SAM parquet unchanged during the export" || echo "RE-RUN: SAM parquet changed during the export"; grep -E '^lineage: .* rail evidence page' tmp/fu2-release-export.log; tail -2 tmp/fu2-release-export.log; fi
```
Expected: `exit=0`; `SAM parquet unchanged during the export`; the `lineage: <k> rail evidence page(s) taken from the narrative citations …` line with Task 25b Step 7's `<k>`; the `budget PDF receipts: …` and `export-site: … citations …` lines (the citation count of Task 25b's exports). On `RE-RUN`, export again in the next window.

Record the counts (citations and SAM registrations against the pre-release copy) and fingerprint the export, `pdfs/` included, because `upload_r2.sh` uploads the 20 new volumes from it:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python - <<'PY'
import json, os
from pathlib import Path

proofs = Path(os.environ["GOVBUDGET_PROOFS"])
live = Path("/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site")


def measure(site: Path) -> dict:
    meta = json.loads((site / "json" / "site_meta.json").read_text())
    return {"companies_with_sam": meta["counts"]["companies_with_sam"],
            "citations": meta["counts"]["citations"], "pdf_count": meta["pdf_count"],
            "pdf_files": len(list((site / "pdfs").glob("*.pdf"))),
            "built_at": json.loads((site / "manifest.json").read_text())["built_at"]}


pre, rel = measure(proofs / "fu2-release-pre-site"), measure(live)
out = {"pre": pre, "release": rel, "SAM_D": rel["companies_with_sam"] - pre["companies_with_sam"],
       "citations_D": rel["citations"] - pre["citations"], "new_pdfs": rel["pdf_files"] - pre["pdf_files"]}
Path("tmp/fu2-release-counts.json").write_text(json.dumps(out, indent=2) + "\n")
(proofs / "fu2-release-export.built_at").write_text(rel["built_at"] + "\n")
print(json.dumps(out, indent=2))
PY
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget && find data/site/data data/site/citations data/site/pdfs data/site/manifest.json -type f -print0 | sort -z | xargs -0 shasum -a 256 > .proofs/fu2-release-export.sha256 && wc -l < .proofs/fu2-release-export.sha256 && shasum -a 256 -c --quiet .proofs/fu2-release-export.sha256 && echo "release export fingerprinted"
```
Expected: `SAM_D` 0, `citations_D` 0 (#195 adds and removes no fact ID), `new_pdfs` 20, `release.pdf_count` = `pre.pdf_count` + 20, a newer `built_at`; then a line count and `release export fingerprinted`.

- [ ] **Step 5: Release-state checks — what ships is what was proven**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; L=/Users/andeslee/Documents/Cursor-Projects/GovBudget
uv run --project . python -m govbudget proof diff "$P/fu2-Bpost/site" "$L/data/site" --noise-from "$P/fu2-logs/noise-fu2.json" > tmp/fu2-release-vs-proof.txt 2>&1; echo "proof diff exit=$?"; tail -4 tmp/fu2-release-vs-proof.txt
uv run --project . python -m govbudget verify-jbook-narratives --site-dir "$L/data/site" --pg-dsn postgresql://localhost/govbudget > tmp/fu2-release-vjn.txt 2>&1; echo "vjn exit=$?"; head -1 tmp/fu2-release-vjn.txt; tail -1 tmp/fu2-release-vjn.txt
uv run --project . python scripts/fu/narrative_relocation_report.py --a "$P/fu2-release-pre-site" --b "$L/data/site" --pg-dsn postgresql://localhost/govbudget --unchanged e7d5bcfb4a30f458 --watch 136baeef904dd052 --report tmp/fu2-release-relocation.json | grep -E "^narrative citations|^PDFs only|136baeef|^narrative-relocation"
H=$(shasum -a 256 "$L/data/site/json/f15_funding_history.json" | cut -d' ' -f1); [ -n "$H" ] && [ "$H" = "$(cat tests/fixtures/f15/history.sha256)" ] && echo "F-15 history matches the pin" || echo "F-15 history DOES NOT match the pin — stop"
uv run --project . python -m govbudget link-coverage --site-dir "$L/data/site" --baseline data/research/link_coverage/baseline.json > tmp/fu2-release-link-coverage.txt 2>&1; echo "link-coverage exit=$?"
"$GOVBUDGET_PG_BIN/psql" postgresql://localhost/govbudget -Atc "select count(*) from jbook_documents where file_path like '%/.claude/worktrees/%'"
```
Expected: `proof diff exit=0` and `proof diff: EQUAL` (the release export equals the proven B export: same database state D2, same lake, same code, no SAM change); `vjn exit=0`, `narrative citations 11717: paged 10273 (printed 10162, opening_only 111 of at most 111); pageless 1444 (opening printed without its closing 77 of at most 77, opening printed nowhere 1367)`, `verify-jbook-narratives: PASS`; `narrative citations 11717: unchanged 7312, located 4177, relocated 228`, `PDFs only B hosts: 20 (162,040,168 bytes)`, the 136baeef line ending `'page_number': 100}`, `narrative-relocation: PASS`; `F-15 history matches the pin`; `link-coverage exit=0`; `0`. Any failure: stop and take Step 3's abort path.

- [ ] **Step 6: Python release gates (W3, W5)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
S=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet
for gate in verify-era-map verify-phase5b1 verify-phase5e verify-lineage; do MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN) before ${gate}: wait until :23 and re-run this block"; exit 0; fi; if [ "$gate" = verify-phase5b1 ] && { [ "$MIN" -lt 23 ] || [ "$MIN" -gt 50 ]; }; then echo "WAIT: verify-phase5b1 takes about 17 minutes (G6-7); start it between :23 and :50 — re-run this block then"; exit 0; fi; S0=$(stat -f %m "$S"); GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget ${gate} > tmp/fu2-release-${gate}.log 2>&1; echo "${gate} exit=$?"; [ "$(stat -f %m "$S")" = "$S0" ] || echo "RE-RUN ${gate}: the SAM parquet changed while it ran"; tail -1 tmp/fu2-release-${gate}.log; done; grep '^gate 5' tmp/fu2-release-verify-phase5b1.log
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN) before evals check: wait until :23 and re-run this block"; exit 0; fi
S0=$(stat -f %m "$S"); GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget evals check > tmp/fu2-release-evals.log 2>&1; echo "evals exit=$?"; [ "$(stat -f %m "$S")" = "$S0" ] || echo "RE-RUN evals check: the SAM parquet changed while it ran"; tail -2 tmp/fu2-release-evals.log
```
The guard sits inside the loop, before each gate: `verify-phase5b1` now reads the raw PDFs for gate 5 and takes about 1,026 s (G6-7), so the block runs longer than the gap between two SAM ticks, and the SAM job has fired off schedule after a wake (`logs/sam-daily.out.log` 2026-10-13 22:23 and 23:24 UTC); each gate also checks that `data/parquet/sam/entities.parquet` did not change under it. Expected: no `WAIT` and no `RE-RUN` line; each gate `exit=0` with `…: PASS`; `gate 5 narrative printed-in: → PASS`; `evals exit=0`, `evals check: <n> ok, 0 stale, <k> skipped` and `evals check: PASS` (release 2 moves no warehouse figure). On `WAIT` or `RE-RUN`, re-run the whole block from :23 (every gate is read-only and repeatable). A STALE answer cannot come from this release (it writes no lake table): stop and read it. A failed gate that cannot be cleared: take Step 3's abort path.

- [ ] **Step 7: The build's llms.txt**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com node scripts/prepare-assets.mjs > /dev/null && cd .. && git diff --stat -- site/public/llms.txt; echo "placeholder lines: $(git diff -- site/public/llms.txt | grep -c 'govbudget-placeholder.example')"
```
Expected: no diff (the citation count in `llms.txt` line 7 is unchanged: `citations_D` 0) and `placeholder lines: 0`. If Step 4 recorded a nonzero `citations_D`, `llms.txt` changes by that count: commit exactly that file (`chore(site): llms.txt citation count after the release-2 export (<pre> -> <release>)`, author and trailer as everywhere) so the build below is of a clean HEAD.

- [ ] **Step 8: Build, verify and test the site at HEAD**

First the `data/site` check that opens Task 26b Step 3 (read-only, seconds); on `STOP`, re-run Step 4 or take the abort path:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L=/Users/andeslee/Documents/Cursor-Projects/GovBudget
(cd "$L" && shasum -a 256 -c --quiet .proofs/fu2-release-export.sha256) || { echo "STOP: data/site is no longer the release export"; exit 1; }
B=$(uv run --project . python -c "import json; print(json.load(open('$L/data/site/manifest.json'))['built_at'])"); [ "$B" = "$(cat "$L/.proofs/fu2-release-export.built_at")" ] || { echo "STOP: manifest built_at ($B) is not the Step 4 export's"; exit 1; }
echo "data/site is the release export: built_at $B"
cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > ../tmp/fu2-release-site-build.log 2>&1; echo "build exit=$?"; NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run verify > ../tmp/fu2-release-site-verify.log 2>&1; echo "verify exit=$?"; grep -E "^overall:" ../tmp/fu2-release-site-verify.log; npm test > ../tmp/fu2-release-vitest.log 2>&1; echo "vitest exit=$?"; cd .. && git status --porcelain -- . | grep -v '^??'; uv run --project . python -c "import json; print(json.load(open('site/out/.build-meta.json'))['git_head'])"; git rev-parse HEAD
node -e 'const fs=require("fs"),z=require("zlib");const b=fs.readFileSync("site/out/program/0601102A/index.html");console.log("0601102A "+b.length.toLocaleString("en-US")+" / "+z.gzipSync(b,{level:9}).length.toLocaleString("en-US"))'
```
Expected: `data/site is the release export: built_at <Step 4's>`; `build exit=0`, `verify exit=0`, `overall: PASS`, `vitest exit=0`; no tracked change; the two shas equal; the heaviest program page at the weight Task 25c Step 5 stamped (same export, same code). A failure that cannot be cleared: take Step 3's abort path.
