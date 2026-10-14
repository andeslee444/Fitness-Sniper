<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the README's Contract Notes, section G6, hold this group's contract notes. -->

### Task 25b: Release-2 proof — one snapshot, the rehearsed writes, four exports, P2 and P1

**Spec:** §7 (proofs on pinned snapshots with the hardened tooling of §6.1; a control export; judged diffs with `--noise-from`), §8 (release 2's own A/B on a fresh snapshot and its own rule list), §2.3 Q24 (b) as applied to release 2 (the write is rehearsed on the snapshot; Task 25c rehearses its `--revert`), §5.6. Depends on Task 25a and on Task 22 (release 1 deployed and published).
**Files:** none created or modified in the repository. Proof state, all under `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/` (APFS clones): the snapshot `fu2` and its scratch database `govbudget_proof_fu2`; clones `fu2-A`, `fu2-B` (before the writes), `fu2-Bpost`, `fu2-B2post` (after); logs and records in `fu2-logs/` (`a_sha.txt`, `b_sha.txt`, `snapshot.log`, `snapshot-shas.json`, `digest-pre.txt`, `digest-mid.txt`, `digest-post.txt`, `max-id-before.txt`, `rehearsal-s195-pre-image.json`, `noise-fu2.json`, the export, diff and report logs). The A code checks out in the detached worktree `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fu2-proof-a` (kept until Task 26b Step 8's cleanup offer; removed only on the owner's yes).

**Why this pairing.** One snapshot and one scratch database, written in sequence (the release-1 proof needed two snapshots because its A code could not export the post-write lake; here nothing stops A or B from exporting either state, but the "before" exports must run before the scratch writes):
- **P2 (code): A@before vs B@before.** A is the code release 1 deployed (proved equal below); B is this branch's HEAD. On the migrated, not yet relocated database no row names a printing volume, so B's export must be **identical** to A's: Tasks 23–24 change nothing until the data does. No rule list: the diff must read `EQUAL`.
- **P1 (data): B@before vs B@after**, with `expected-diff-r2-narratives.json` (Task 25a), judged field by field by `narrative_relocation_report.py`.
- **Control: B@after vs B2@after**, which writes the noise file both judged diffs read.

Every block that touches the live lake or takes the snapshot carries the SAM guard; exports and gates against the snapshot's clones read pinned copies and are exempt (README Global Constraints). Shell state does not persist: each block re-derives `P`, and the A sha is read back from `fu2-logs/a_sha.txt`.

**Interfaces:**
Consumes: `govbudget proof snapshot --out DIR --scratch-db NAME` and `govbudget proof diff A B [--control --write-noise FILE | --noise-from FILE] [--expect RULES] [--report FILE]` as Task 2 hardened them (Task 2 moves `NOISE_FILE_SCHEMA` to 2, so this task writes a fresh noise file; its last lines are `proof diff: EQUAL|DIFFERENT`, or `PASS|FAIL` with `--expect`); the snapshot's `env.sh [RUN_DIR]` (exports `GOVBUDGET_DATA`, `GOVBUDGET_DUCKDB`, `GOVBUDGET_PG_DSN`=`dbname=govbudget_proof_fu2 host=localhost`); `govbudget migrate`; `govbudget jbooks narrative-provenance --lineage-evidence` (Task 23a's builder); `scripts/fu/s195_narratives.py` (Task 23c); `scripts/fu/narrative_relocation_report.py` and `expected-diff-r2-narratives.json` (Task 25a); `govbudget verify-jbook-narratives` (Task 24); `govbudget export-site`; `dbt parse`; Task 23c Step 6's live digest and counts.
Produces: the records Task 25c and Task 26 read — `fu2-logs/digest-pre.txt` (D0: the live digest the release must still find), `digest-mid.txt` (D1: after the lineage-evidence build; the release's `--expect-pre-digest`), `digest-post.txt` (D2: what the live write must produce), `noise-fu2.json`, `p1-report.json`, `relocation-report.json`; the four exports.

**Measured now** (2026-10-13, read-only on the live database and `data/site`, Tasks 23c Step 6 and 24 Step 7's numbers): D0 = `3e61258310ef4ce9a7fae630daf8eb62`; the lineage-evidence build finds 92 evidence narratives and inserts 19 rows, all `unique`, all in their attached volume (printed_document_sha256 null), leaving `{'ambiguous_first': 657, 'unique': 5458, 'unresolved': 5865}` over 11,980 narrative rows; the relocation then plans rows 11,717: kept 5,776, located 4,158, relocated 228, opening_only 111, unresolved 1,444 (Task 23c's 11,698-row plan plus the 19 rows, all kept). Per citation field the P1 changes are: `page_number`, `hosted_pdf_url`, `official_url` 4,405 each; `top_pt`, `bottom_pt` 4,401; `x1` 4,378; `resolution` 4,340; `x0` 4,331; `sha256` and `retrieved_at` 4,206; `page_width`, `page_height` 4,177 (computed from the live plan against today's `citations.json`; floats that agree to 12 significant digits count as equivalent in `proof diff`, so the four box counts may read a few lower).

- [ ] **Step 1: Preconditions and the A commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git status --porcelain -- GovBudget | grep -v '^??'; git log --oneline -1; cd GovBudget && source scripts/era/env.sh && "$GOVBUDGET_PG_BIN/pg_isready" -h 127.0.0.1 -p 55432 && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q 2>&1 | tail -1; "$GOVBUDGET_PG_BIN/psql" postgresql://localhost/postgres -Atc "select count(*) from pg_database where datname = 'govbudget_proof_fu2'"; ls -d "${GOVBUDGET_PROOFS:?}"/fu2* 2>/dev/null | wc -l; git -C .. worktree list | grep -c fu2-proof-a
```
Expected: no tracked change; HEAD is Task 25a's commit; `127.0.0.1:55432 - accepting connections`; `… passed` with 0 failed; `0` (no scratch database of that name); `0` (no `.proofs/fu2*` yet); `0`. A leftover from an earlier attempt: read it, then remove it only on the owner's word.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"; mkdir -p "$P/fu2-logs"
cd .. && FIRST=$(git log --reverse --format=%H -- GovBudget/migrations/022_provenance_pages_printed_document.sql | head -1) && A_SHA=$(git rev-parse "${FIRST}^") && LIVE=$(curl -s https://fiscalreceipts.com/.build-meta.json | python3 -c "import json,sys; print(json.load(sys.stdin)['git_head'])") && git log -1 --format='first #195 commit: %h %s' "${FIRST}" && echo "A_SHA=${A_SHA} live=${LIVE}" && git diff --quiet "${LIVE}" "${A_SHA}" -- GovBudget/src GovBudget/dbt GovBudget/data-seeds GovBudget/scripts GovBudget/migrations && echo "A's code equals the deployed release 1" && echo "${A_SHA}" > "$P/fu2-logs/a_sha.txt" && git rev-parse HEAD > "$P/fu2-logs/b_sha.txt" && echo "recorded"
```
Expected: `first #195 commit: <sha> feat(jbooks): migration 022 — provenance_pages.printed_document_sha256, …` (Task 23a Step 4); the two shas; `A's code equals the deployed release 1`; `recorded`. If the code differs, a commit after release 1's deploy changed exported code before #195: stop and read it (the proof would mix it into P2).

Then the live digest, read-only (seconds; Postgres only):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python scripts/fu/s195_narratives.py --digest --dsn postgresql://localhost/govbudget
```
Expected: `state digest: 3e61258310ef4ce9a7fae630daf8eb62` (the value Task 23c Step 6 printed). A different value means a write to `provenance_pages`, `jbook_documents` or `detail_narratives` after Task 23c: find it before snapshotting, and re-run Task 23c Step 6 so the counts below are today's.

- [ ] **Step 2: Take the snapshot (creates the scratch database only)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
P="${GOVBUDGET_PROOFS:?}"; date +%H:%M && uv run --project . python -m govbudget proof snapshot --out "$P/fu2" --scratch-db govbudget_proof_fu2 > "$P/fu2-logs/snapshot.log" 2>&1; echo "exit=$?"; cat "$P/fu2-logs/snapshot.log"
uv run --project . python -c "import json,sys; m=json.load(open(sys.argv[1])); print(json.dumps({'created_at': m['created_at'], 'duckdb_sha256_at_copy': m['duckdb']['sha256_at_copy'], 'duckdb_sha256': m['duckdb']['sha256'], 'views_rewritten': m['duckdb']['views_rewritten'], 'site_sha256': m['site']['sha256'], 'raw_docs_sha256': m['raw_docs']['sha256'], 'manifest_jsonl_sha256': m['manifest_jsonl_sha256'], 'pg_dump_sha256': m['pg']['dump_sha256'], 'pg_scratch_dsn': m['pg']['scratch_dsn']}, indent=1))" "$P/fu2/snapshot.json" > "$P/fu2-logs/snapshot-shas.json" && cat "$P/fu2-logs/snapshot-shas.json"
```
Expected: `exit=0`, `proof snapshot: /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu2` and the duckdb / parquet / postgres lines of the snapshot log (`postgres govbudget -> govbudget_proof_fu2 …`); the JSON with every sha filled and `"pg_scratch_dsn": "dbname=govbudget_proof_fu2 host=localhost"`. On `WAIT` or a refusal inside the tool (`proof snapshot: refusing …`), wait until :23 and re-run (after a refusal "after the copy", `rm -rf "${GOVBUDGET_PROOFS:?}/fu2"` in a block that sources `env.sh` first).

- [ ] **Step 3: Migrate the scratch database; its digest is the live one**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P="${GOVBUDGET_PROOFS:?}"
(source "$P/fu2/env.sh" && echo "$GOVBUDGET_PG_DSN" && uv run --project . python -m govbudget migrate && uv run --project . python scripts/fu/s195_narratives.py --digest) > "$P/fu2-logs/scratch-migrate.log" 2>&1; echo "exit=$?"; cat "$P/fu2-logs/scratch-migrate.log"; grep '^state digest:' "$P/fu2-logs/scratch-migrate.log" | cut -d' ' -f3 > "$P/fu2-logs/digest-pre.txt"; cat "$P/fu2-logs/digest-pre.txt"
```
Expected: `exit=0`; `dbname=govbudget_proof_fu2 host=localhost`; `migrations applied: ['022_provenance_pages_printed_document.sql']` (nothing else: the snapshot is release 1's database); `state digest: 3e61258310ef4ce9a7fae630daf8eb62` — equal to Step 1's live digest, because the digest ignores `file_path` (the snapshot repoints it) and reads an unset `printed_document_sha256` exactly as a missing column. That value is D0, written to `digest-pre.txt`. Any other value: stop.

- [ ] **Step 4: Check out the A code and give it its own dbt manifest**

As piece 1 Task 21 Step 13: `export-site` reads the code checkout's `dbt/target/manifest.json` for `site_meta.build_checks.dbt_assertions`; `dbt parse` writes it without opening a warehouse.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && A_SHA=$(cat "${GOVBUDGET_PROOFS:?}/fu2-logs/a_sha.txt") && : "${A_SHA:?run Step 1 first}" && cd .. && git worktree add --detach /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fu2-proof-a "${A_SHA}" && cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fu2-proof-a/GovBudget && uv sync --frozen && source scripts/era/env.sh && GOVBUDGET_DUCKDB="$GOVBUDGET_PROOFS/fu2-dbt-parse-a.duckdb" uv run --project . dbt parse --project-dir dbt --profiles-dir dbt > "$GOVBUDGET_PROOFS/fu2-logs/dbt-parse-a.log" 2>&1; echo "parse exit=$?"; test ! -e "$GOVBUDGET_PROOFS/fu2-dbt-parse-a.duckdb" && echo no-warehouse-opened; uv run --project . python - /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/dbt/target/manifest.json dbt/target/manifest.json <<'PY'
import json, sys
counts = [sum(1 for n in json.load(open(p))["nodes"].values() if n.get("resource_type") == "test") for p in sys.argv[1:]]
print(f"dbt test nodes: B {counts[0]}, A {counts[1]}")
sys.exit(0 if counts[0] == counts[1] else 1)
PY
echo "count check exit=$?"; git log -1 --format='%h %s'
```
Expected: `Preparing worktree (detached HEAD …)`; the locked environment installs; `parse exit=0`; `no-warehouse-opened`; `dbt test nodes: B <n>, A <n>` with one `<n>` (release 1's count; #195 adds no dbt test); `count check exit=0`; A's subject (Task 22's last commit before #195).

Optional speed-up for every export below (the receipt step otherwise rescans its PDFs; the cache is keyed by PDF sha256): `for d in /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fu2-proof-a/GovBudget /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget; do mkdir -p ${d}/tmp/pdfs && cp -c /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/pdfs/*-program-pages-v1.json ${d}/tmp/pdfs/ 2>/dev/null; done; true`

- [ ] **Step 5: Export A and B on the migrated, not yet relocated database**

Both clones read the same scratch database, so both exports run before Step 6 writes it.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
cp -c -R "$P/fu2" "$P/fu2-A" && cp -c -R "$P/fu2" "$P/fu2-B"
(cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/fu2-proof-a/GovBudget && source "$P/fu2/env.sh" "$P/fu2-A" && uv run --project . python -m govbudget export-site) > "$P/fu2-logs/export-A.log" 2>&1; echo "A exit=$?"; tail -2 "$P/fu2-logs/export-A.log"
(source "$P/fu2/env.sh" "$P/fu2-B" && uv run --project . python -m govbudget export-site) > "$P/fu2-logs/export-B.log" 2>&1; echo "B exit=$?"; grep -c '^lineage: .* rail evidence page' "$P/fu2-logs/export-B.log"; tail -2 "$P/fu2-logs/export-B.log"
```
Expected: `A exit=0` and `B exit=0` (B also prints `0`: no rail page moves before the relocation), each followed by its `budget PDF receipts: …` and `export-site: <d> datasets, <N> citations, … -> …/.proofs/fu2-A/site` (`fu2-B/site`) lines, with one citation count `<N>` (release 1's; no fact ID is added by #195). About 15 minutes each.

- [ ] **Step 6: Rehearse release 2's writes on the scratch database, in Task 26's order**

First the lineage-evidence rows that were never built (contract issue G6-3), then the relocation. Record the highest row id and the id sequence's state first, so the new rows can be named and Task 26a Step 1 can prove the live sequence still stands where the snapshot copied it (the 19 inserted rows' ids are in D1):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
(source "$P/fu2/env.sh" && "$GOVBUDGET_PG_BIN/psql" "$GOVBUDGET_PG_DSN" -Atc "select max(id) from provenance_pages") > "$P/fu2-logs/max-id-before.txt"; cat "$P/fu2-logs/max-id-before.txt"
(source "$P/fu2/env.sh" && "$GOVBUDGET_PG_BIN/psql" "$GOVBUDGET_PG_DSN" -At -F' ' -c "select last_value, is_called from provenance_pages_id_seq") > "$P/fu2-logs/provenance-seq-before.txt"; cat "$P/fu2-logs/provenance-seq-before.txt"
(source "$P/fu2/env.sh" && uv run --project . python -m govbudget jbooks narrative-provenance --lineage-evidence) > "$P/fu2-logs/scratch-lineage-evidence.log" 2>&1; echo "exit=$?"; cat "$P/fu2-logs/scratch-lineage-evidence.log"
MAXID=$(cat "$P/fu2-logs/max-id-before.txt"); (source "$P/fu2/env.sh" && "$GOVBUDGET_PG_BIN/psql" "$GOVBUDGET_PG_DSN" -Atc "select count(*), count(printed_document_sha256), count(page_number) from provenance_pages where target_kind = 'narrative' and id > ${MAXID:?}")
(source "$P/fu2/env.sh" && uv run --project . python scripts/fu/s195_narratives.py --digest) | tee "$P/fu2-logs/digest-mid.log"; cut -d' ' -f3 "$P/fu2-logs/digest-mid.log" > "$P/fu2-logs/digest-mid.txt"
```
Expected: the max id (a number); `<last_value> <t|f>` (the sequence as `pg_dump` restored it from live: `provenance_pages_id_seq`'s `last_value` and `is_called`, in `provenance-seq-before.txt`); `exit=0`, `narrative-provenance: scoped to 92 lineage-evidence narrative(s)` and `narrative-provenance: 19 inserted; located 6115/11980 ({'ambiguous_first': 657, 'unique': 5458, 'unresolved': 5865})`; `19|0|19` (19 new rows, none naming another volume, all with a page: under piece-1 code each one already cites the page it names, which is why Task 26's abort path may leave them); `state digest: <32 hex>` — D1, in `digest-mid.txt`.

Then the relocation, the write Task 26 makes on the live database, with its pre-image:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs; D1=$(cat "$P/fu2-logs/digest-mid.txt")
(source "$P/fu2/env.sh" && uv run --project . python scripts/fu/s195_narratives.py --apply --pre-image "$P/fu2-logs/rehearsal-s195-pre-image.json" --expect-pre-digest "${D1:?}") > "$P/fu2-logs/scratch-s195-apply.log" 2>&1; echo "exit=$?"; grep -v '^  cites ' "$P/fu2-logs/scratch-s195-apply.log"; grep -c '^  cites superseded' "$P/fu2-logs/scratch-s195-apply.log"; grep -o 'post-write digest: [0-9a-f]*' "$P/fu2-logs/scratch-s195-apply.log" | cut -d' ' -f3 > "$P/fu2-logs/digest-post.txt"; cat "$P/fu2-logs/digest-post.txt"
```
Expected: `exit=0`; `pre-write digest: <D1>`; `narrative relocation (all editions): {'rows': 11717, 'kept': 5776, 'located': 4158, 'relocated': 228, 'opening_only': 111, 'unresolved': 1444}` and the same `rows 11717: …` line; `pre-image: …/rehearsal-s195-pre-image.json (11980 rows)`; `updated 4386 row(s); post-write digest: <D2>`; `committed`; then `20`; then D2 (in `digest-post.txt`). Any other count: stop and compare with Task 23c Step 6.

- [ ] **Step 7: Export B and the control B2 after the writes; the control must read EQUAL**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
cp -c -R "$P/fu2" "$P/fu2-Bpost" && cp -c -R "$P/fu2" "$P/fu2-B2post"
for d in fu2-Bpost fu2-B2post; do (source "$P/fu2/env.sh" "$P/$d" && uv run --project . python -m govbudget export-site) > "$P/fu2-logs/export-$d.log" 2>&1; echo "$d exit=$?"; grep -E '^lineage: .* rail evidence page' "$P/fu2-logs/export-$d.log"; tail -2 "$P/fu2-logs/export-$d.log"; done
uv run --project . python -m govbudget proof diff "$P/fu2-Bpost/site" "$P/fu2-B2post/site" --control --write-noise "$P/fu2-logs/noise-fu2.json" > "$P/fu2-logs/diff-control.txt" 2>&1; echo "control exit=$?"; tail -6 "$P/fu2-logs/diff-control.txt"
```
Expected: both exports `exit=0` with the same `<N>` citations as Step 5 and the lines `lineage: <k> rail evidence page(s) taken from the narrative citations (#195: …)` (Task 23b; `<k>` ≥ 1: 22 evidence narratives move); the control `changed 0 · only in A 0 · only in B 0`, any float-noise and reorder lines, `proof diff: EQUAL`, and `noise-fu2.json` written. `DIFFERENT`: stop — neither judged diff can be read without it.

- [ ] **Step 8: P2 — the code alone changes nothing**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
uv run --project . python -m govbudget proof diff "$P/fu2-A/site" "$P/fu2-B/site" --noise-from "$P/fu2-logs/noise-fu2.json" --report "$P/fu2-logs/p2-report.json" > "$P/fu2-logs/diff-p2.txt" 2>&1; echo "exit=$?"; tail -8 "$P/fu2-logs/diff-p2.txt"
```
Expected: `exit=0`; `changed 0 · only in A 0 · only in B 0` and last line `proof diff: EQUAL`. Any difference is code that acts without the data (for instance a rail page the export rewrote although no citation moved): stop and explain it; never add a rule.

- [ ] **Step 9: P1 — the data changes are exactly the relocation**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
uv run --project . python -m govbudget proof diff "$P/fu2-B/site" "$P/fu2-Bpost/site" --noise-from "$P/fu2-logs/noise-fu2.json" --expect docs/superpowers/plans/2026-10-04-families-piece1-followups/expected-diff-r2-narratives.json --report "$P/fu2-logs/p1-report.json" > "$P/fu2-logs/diff-p1.txt" 2>&1; echo "exit=$?"; grep -E "^  rule |UNEXPECTED|UNMET|^proof diff:" "$P/fu2-logs/diff-p1.txt"
```
Expected: `exit=0`; 19 rule lines — rule 0 (`sha256`) matched 4206, rule 1 (`page_number`) 4405, rules 2–5 (`x0`, `x1`, `top_pt`, `bottom_pt`) about 4331 / 4378 / 4401 / 4401, rules 6–7 (`page_width`, `page_height`) 4177, rule 8 (`resolution`) 4340, rules 9–10 (`hosted_pdf_url`, `official_url`) 4405, rule 11 (`retrieved_at`) 4206, rule 12 (the cite shards) the sum of the twelve (about 51,832), rule 13 (`citations.parquet`) 1, rule 14 (the audit's `citation_sha256`) 1, rule 15 (`pdfs/*.pdf` only in B) 20, rules 16–17 (`pdf_count`) 1 each, rule 18 (sidecar rails) ≥ 1; no `UNEXPECTED differences` and no `UNMET required rule`; last line `proof diff: PASS`. A FAIL names each unexpected path: stop and explain it; never widen the list without the owner.

- [ ] **Step 10: The relocation, field by field**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
(source "$P/fu2/env.sh" && uv run --project . python scripts/fu/narrative_relocation_report.py --a "$P/fu2-B/site" --b "$P/fu2-Bpost/site" --pg-dsn "$GOVBUDGET_PG_DSN" --unchanged e7d5bcfb4a30f458 --watch 136baeef904dd052 --watch 033016199ca94aa7 --watch 906bcdda2a0660d1 --report "$P/fu2-logs/relocation-report.json"); echo "exit=$?"
```
Expected:

```
narrative citations 11717: unchanged 7312, located 4177, relocated 228
PDFs only B hosts: 20 (162,040,168 bytes)
  e7d5bcfb4a30f458: A {'sha256': '528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e', 'page_number': 71} -> B {'sha256': '528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e', 'page_number': 71}
  136baeef904dd052: A {'sha256': 'a0b31f94ab70ce33e1b4300355ad55d2efd7e2722876998e39bf2c99b7b1a87f', 'page_number': None} -> B {'sha256': '184228d828aab1d64819d05f7cd66f24de5e7e28fbeccacf89db50fa15078195', 'page_number': 100}
  033016199ca94aa7: A {'sha256': '528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e', 'page_number': 71} -> B {'sha256': '8ef7d90e37f4efeaf2d01840ead847afe1953b6591ec3c63cac218fa95e93c39', 'page_number': 215}
  906bcdda2a0660d1: A {'sha256': 'f68f0afc0cb65fda994610b350f8e2fca4877986c9a0e3438fa3ee02b11a0aa6', 'page_number': None} -> B {'sha256': '1623a79d35fd922ba6c87e8e8cbe12f0e960accdef00395d00efff0dfb35b559', 'page_number': 185}
narrative-relocation: PASS
exit=0
```
(4,177 located = Task 23c's 4,158 plus the 19 lineage-evidence rows; 7,312 = 11,717 − 4,177 − 228. The 20 PDFs are the 20 superseded PB2026 volumes of Task 23c Step 6's list.) A FAIL lists its violations: stop.
