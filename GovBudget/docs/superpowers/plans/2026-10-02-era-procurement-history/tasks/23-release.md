<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 23: Release (S6) — gates, deploy, ROADMAP stamp, publish

**Spec:** §8 V9 (link-coverage hard check), V10 (verify-phase5, -5b1, -5e, -lineage, -era-map, deploy live check), §9 S6, §1 success criteria.
**Files:**
- Modify (by the build): `site/public/llms.txt`
- Modify (only if `evals check` finds stale answers explained by this piece): `evals/phase5_questions.yaml`
- Modify: `docs/superpowers/ROADMAP.md` — new phase-ledger row directly above `| Post-launch |` (line 213 today); one sentence after the "Platform families (2026-10-02)" paragraph; a findings-log entry; a status marker on backlog #10 (SAM entity extract); a clause in the `Updated:` header line

Line numbers here are hints (anchor on the quoted text; line numbers are approximate). Blocks that read the live lake (Steps 1, 4, 5, 8) start with the SAM guard: on `WAIT: SAM window …`, wait until :23 and re-run the block.

**Timing (SAM job).** The main checkout's `com.fiscalreceipts.sam-daily` job writes `data/parquet/sam` at :17 of every hour (only the 00:xx UTC tick fetches; the next is 2026-10-05T00:18Z, about 20:18 EDT, with 39 of 200 families still owed), and every export reads that parquet at query time, so the release export also ships whatever SAM.gov registrations the job stored since the 2026-10-02 export (final review INT-1/RR-3). Run Steps 3–8 outside 00:10–00:25 UTC (20:10–20:25 EDT) and preferably before that next fetch: the export takes about 13–17 minutes (Task 21's exports ran 13 and 17), `verify-phase5b1` alone about 4.5 minutes, and the block guards check only a block's start minute. If a fetch lands between Step 3 and the deploy, the Step 11 fingerprint check catches nothing (the SAM parquet lives in the lake, not in `data/site`), but the SAM counts Step 3 records stay exact for the shipped export, because what ships is `data/site` as Step 3 exported it; the newer answers ship with the next export.
**Interfaces:**
Consumes: everything above; `govbudget link-coverage` + `data/research/link_coverage/baseline.json` (Task 5; CONTRACT ISSUE 7); `scripts/era/s4_report.py` and `.proofs/s4-logs/s4-report.json` (Task 21); `scripts/era/env.sh` (Task 1: `GOVBUDGET_PG_BIN`, `GOVBUDGET_PROOFS`; no Postgres binary is on `PATH`); `govbudget era-map check --strict` (Task 12); `govbudget jbooks export-facts` (exists; branch version from Task 7); `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh`; remotes `origin` (monorepo) and `govbudget` (fiscalreceipts).
Produces: the release export in the main lake's `data/site`, with its SAM and citation counts (`tmp/release-counts.json`) and fingerprint (`.proofs/release-export.sha256`, `.proofs/release-export.built_at`); production at the release HEAD; R2 rollback tag; ROADMAP stamp; monorepo `main` and fiscalreceipts `main` advanced.

Measured now: production `/.build-meta.json` `git_head aa714d7f…` (built 2026-10-02T02:09Z); production's export (`data/site` manifest `built_at` 2026-10-02T01:30Z) carries 125,409 citations, 62 SAM registrations (`json/sam`, `site_meta.counts.companies_with_sam`) and 163 dbt assertions, while the S5 build (`.proofs/s5`, branch code on the 2026-10-04 lake) carries 143,841 / 149 / 196 — the SAM job stored 87 more registrations after production's export, so `ERA_D` (the era share of the citation delta) is 18,345 and `SAM_D` is 87 today; the registration and citation counts move with every SAM fetch, the dbt count (196 test nodes in this worktree's `dbt/target/manifest.json`) and `ERA_D` do not; live sitemap 4,349 URLs; `https://assets.fiscalreceipts.com/data/budget_lines_decade.parquet` answers 206 to a range request; `govbudget/main` = `dbe24bcb` (a merge commit not in the monorepo) whose tree `d316ef7b…` equals `dc801fdb:GovBudget` — so the subtree split is not a fast-forward and needs the merge recipe (Step 20); the main checkout is on `main` at `dc801fdb` with one unrelated modified file (`CLAUDE.md` at the monorepo root); the F01500 PB2017 FY2015 actuals era leaf is `3bd9c921b2397209` ($498,314K, receipt complete in the PB2017 P-1 book); the decisions worktree's `tmp/pdfs` holds the 21 `*-program-pages-v1.json` caches; the main `.env` defines `ANTHROPIC_API_KEY`, `DATA_GOV_API_KEY`, `JEV_API_KEY`, `SAM_API_KEY`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_PUBLIC_URL` and no path variables.

- [ ] **Step 1: Preconditions**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git status --porcelain -- GovBudget | grep -v '^??'; git log --oneline -1; cd GovBudget && source scripts/era/env.sh && "$GOVBUDGET_PG_BIN/pg_isready" -h 127.0.0.1 -p 55432; GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest -q 2>&1 | tail -2
```
Expected: no tracked change; HEAD is Task 22's last commit; `127.0.0.1:55432 - accepting connections` (Task 1's throwaway cluster; `env.sh` points `GOVBUDGET_TEST_PG_DSN` at it); pytest ends `… passed` with 0 failed (skips only where a test skips today).

Then check that the live lake still carries what this branch built (read-only). Until the branch merges, a `jbooks export-facts` from the main checkout rewrites `data/parquet/jbooks/budget_lines.parquet` without `line_item_code` (G2 hazard 2), after which every budget query errors and the release export breaks. A main-checkout `govbudget build` only reverts the `stg_budget_lines` view (the exporter reads `line_item_code` from the `p1_era_line_map` table, not from staging), which matters for the next branch rebuild, not for the release export; the block below checks both, because `assert_p1_era_map_one_code` is the one era test that reads `line_item_code` from staging and a selection of only the era models does not pick it up (final review INT-2):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
mkdir -p tmp && uv run --project . python - <<'PY2'
import duckdb, os
data = os.environ["GOVBUDGET_DATA"]
con = duckdb.connect(os.environ["GOVBUDGET_DUCKDB"], read_only=True)
cols = [r[0] for r in con.execute("describe select * from read_parquet(?)", [f"{data}/parquet/jbooks/budget_lines.parquet"]).fetchall()]
print("budget_lines.parquet has line_item_code:", "line_item_code" in cols)
stg = [r[0] for r in con.execute("describe select * from stg_budget_lines").fetchall()]
print("stg_budget_lines has line_item_code:", "line_item_code" in stg)
tables = {r[0] for r in con.execute("select table_name from duckdb_tables()").fetchall()}
print("era tables:", sorted(t for t in tables if t in {"p1_era_code_decisions", "p1_era_line_map", "fct_program_decade_series"}))
PY2
MIN=$(date +%M); if [ "$MIN" -ge 15 ] && [ "$MIN" -le 20 ]; then echo "WAIT: minute $MIN is in the SAM window"; else uv run --project . python -m govbudget era-map check --strict > tmp/release-era-check.log; echo "era-map check exit=$?"; tail -1 tmp/release-era-check.log; uv run --project . dbt test --project-dir dbt --profiles-dir dbt --select p1_era_code_decisions p1_era_line_map fct_program_decade_series stg_budget_lines > tmp/release-dbt-test.log 2>&1; echo "dbt test exit=$?"; tail -1 tmp/release-dbt-test.log; fi
```
Expected: `budget_lines.parquet has line_item_code: True`; `stg_budget_lines has line_item_code: True`; `era tables: ['fct_program_decade_series', 'p1_era_code_decisions', 'p1_era_line_map']`; `era-map check exit=0`, `era-map check: 0 undecided chain(s), 0 stale decision(s)`; `dbt test exit=0`, `Done. PASS=<n> WARN=0 ERROR=0 SKIP=0 …` (`dbt test` only reads the warehouse; it also writes this worktree's own `dbt/target/manifest.json`, which the release export reads for `site_meta.build_checks.dbt_assertions` — 196 test nodes at HEAD 8c16206a, and the final-review fixes change no dbt tests; selecting `stg_budget_lines` also runs the tests that read it, `assert_p1_era_map_one_code` among them, so `<n>` is larger than with the three era models alone).

If any of these fails, restore the branch's lake state before Step 3 (SHARED LAKE WRITE: the contract's Task 23 write; outside the SAM window; no other session may hold the DuckDB file):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && MIN=$(date +%M) && if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: minute $MIN is in the SAM window (:15-:20, with margin)"; else uv run --project . python -m govbudget jbooks export-facts > tmp/release-export-facts.log 2>&1; echo "export-facts exit=$?"; uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select stg_budget_lines p1_era_code_decisions p1_era_line_map fct_program_decade_series > tmp/release-dbt-build.log 2>&1; echo "dbt build exit=$?"; tail -1 tmp/release-dbt-build.log; fi
```
Expected: `export-facts exit=0`, `dbt build exit=0`, `Done. PASS=<n> WARN=0 ERROR=0 SKIP=0 …`; then re-run the check block above (all four expectations). Record in the Step 13 findings entry that the lake had to be restored, and by which command.

- [ ] **Step 2: Point the worktree at the main lake and the main `.env`**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && for d in site duckdb parquet raw raw_docs; do if [ -e data/${d} ] && [ ! -L data/${d} ]; then echo "STOP: data/${d} is a real directory"; else ln -sfn /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/${d} data/${d}; fi; done; [ -e .env ] || ln -s /Users/andeslee/Documents/Cursor-Projects/GovBudget/.env .env; ls -l data .env | grep -- '->'; git -C .. status --porcelain -- GovBudget/data GovBudget/.env
```
Expected: six symlinks (five lake dirs and `.env`) and no status output (all excluded/ignored). Never print `.env`'s contents.

- [ ] **Step 3: Keep a local copy of the live export, then export (SHARED LAKE WRITE: data/site)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && P="${GOVBUDGET_PROOFS:?}" && { [ -e ${P}/release-pre-site ] || cp -cR /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site ${P}/release-pre-site; } && mkdir -p /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/pdfs && cp -c /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/decisions/GovBudget/tmp/pdfs/*-program-pages-v1.json /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/pdfs/ 2>/dev/null; ls ${P}/release-pre-site/manifest.json
```
Then, starting only between :21 and :45 past the hour (the export takes about 13–17 minutes including the receipt pass; the SAM job writes `data/parquet/sam` at :17, and tonight's daily fetch is due 00:18Z — see Timing above):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && MIN=$(date +%M) && if [ "$MIN" -lt 21 ] || [ "$MIN" -gt 45 ]; then echo "WAIT: start between :21 and :45 (now :$MIN)"; else S0=$(stat -f %m /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet) && GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget export-site > tmp/release-export.log 2>&1; echo "exit=$?"; S1=$(stat -f %m /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet); [ "$S0" = "$S1" ] && echo "SAM parquet unchanged during the export" || echo "RE-RUN: SAM parquet changed during the export"; tail -3 tmp/release-export.log; fi
```
Expected: `exit=0`, `SAM parquet unchanged during the export`, the `budget PDF receipts: …` and `export-site: … citations …` lines. On `RE-RUN`, run the export again in the next window.

Record what the export ships. Because every export reads the SAM parquet live, the release also carries the SAM.gov registrations the daily job stored since the production export, and no families proof (`s4_report.py` compares only program sidecars and PDF receipts) sees them; this block measures them so the commit message, the owner go-ahead and the ROADMAP stamp can split the citation delta honestly (final review INT-1/RR-3). It reads only `data/site` and `.proofs`, so it needs no SAM guard:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python - <<'PY3'
import json, os
from pathlib import Path

proofs = Path(os.environ["GOVBUDGET_PROOFS"])
live = Path("/Users/andeslee/Documents/Cursor-Projects/GovBudget")


def measure(site: Path) -> dict:
    meta = json.loads((site / "json" / "site_meta.json").read_text())
    return {
        "sam_files": len(list((site / "json" / "sam").glob("*.json"))),
        "companies_with_sam": meta["counts"]["companies_with_sam"],
        "citations": meta["counts"]["citations"],
        "dbt_assertions": meta["build_checks"]["dbt_assertions"],
        "built_at": json.loads((site / "manifest.json").read_text())["built_at"],
    }


pre, rel = measure(proofs / "release-pre-site"), measure(live / "data" / "site")
sam_d = rel["companies_with_sam"] - pre["companies_with_sam"]
era_d = rel["citations"] - pre["citations"] - sam_d
out = {"pre": pre, "release": rel, "SAM_D": sam_d, "ERA_D": era_d}
Path("tmp").mkdir(exist_ok=True)
Path("tmp/release-counts.json").write_text(json.dumps(out, indent=2) + "\n")
(proofs / "release-export.built_at").write_text(rel["built_at"] + "\n")
print(json.dumps(out, indent=2))
if rel["sam_files"] - pre["sam_files"] != sam_d:
    print("NOTE: the json/sam file delta differs from the companies_with_sam delta; use companies_with_sam for SAM_D and say so in the Step 13 entry")
PY3
```
Expected: `pre` is production's export — `sam_files` 62, `companies_with_sam` 62, `citations` 125409, `dbt_assertions` 163, `built_at` 2026-10-02T01:30Z (anything else means `release-pre-site` is not the production export: stop and read). `release` has `sam_files` and `companies_with_sam` ≥ 149 (149 on the 2026-10-04 lake; more after each nightly fetch), `citations` 143841 when that count is 149 (one more per further SAM registration), `dbt_assertions` 196 and a newer `built_at`; `SAM_D` is the `companies_with_sam` delta (87 at 149; each published registration carries exactly one derived citation, which is why the split uses it and not the manifest's `derived` kind, which the era rows also move) and `ERA_D` is the citation delta minus `SAM_D` (18,345 whatever the SAM count; read why before going on if it differs); no `NOTE` line. `tmp/release-counts.json` holds `N` (= `release.citations`), `SAM_D`, `ERA_D` and both SAM counts for Steps 6, 10 and 13.

Then fingerprint the release export (the fixed-name objects `upload_r2.sh` overwrites, plus the manifest whose `built_at` changes on every export). Step 11 re-checks it before the deploy, because Steps 4–10 can take hours and other worktrees link this same `data/site` (final review RR-2, INT-4):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget && find data/site/data data/site/citations data/site/manifest.json -type f -print0 | sort -z | xargs -0 shasum -a 256 > .proofs/release-export.sha256 && wc -l .proofs/release-export.sha256 && shasum -a 256 -c --quiet .proofs/release-export.sha256 && echo "release export fingerprinted"
```
Expected: one line per file (the count is informational) and `release export fingerprinted`.

**Abort path (SHARED LAKE WRITE: restores `data/site`; authorised as a Task 23 shared write, final review RR-2(d)).** Any stop after this step that does not end in a deploy — a failed gate in Steps 4–9, an owner "no" at Step 10, a `STOP` from the check that opens Step 11 — leaves an era-shaped `data/site` under the pre-era code the main checkout still runs until Step 17 (and under every other worktree linking it). Restore the pre-release copy, keeping the aborted export aside for diagnosis (nothing is deleted):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget && mv data/site data/site.release-aborted-$(date -u +%Y%m%dT%H%M%SZ) && cp -cR .proofs/release-pre-site data/site && shasum -a 256 data/site/manifest.json .proofs/release-pre-site/manifest.json
```
Expected: the two hashes are equal. `data/site` stays a real directory at the same path, so the other worktrees' symlinks still resolve. Remove `data/site.release-aborted-*` only on the owner's word. A later retry re-runs Step 3's export block (the pre-release copy is kept) and re-records the counts and fingerprint.

- [ ] **Step 4: Release-state data checks**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
H=$(shasum -a 256 /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/json/f15_funding_history.json | cut -d' ' -f1); if [ -n "$H" ] && [ "$H" = "$(cat tests/fixtures/f15/history.sha256)" ]; then echo "F-15 history matches the S5 pin"; else echo "F-15 history DOES NOT match the S5 pin (got ${H:-nothing}) — stop"; fi; uv run --project . python scripts/era/s4_report.py --a /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/release-pre-site --b /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site --report /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/release-report.json | tail -1; uv run --project . python -m govbudget link-coverage --site-dir /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site --baseline data/research/link_coverage/baseline.json > tmp/release-link-coverage.txt 2>&1; echo "link-coverage exit=$?"; tail -5 tmp/release-link-coverage.txt; source scripts/era/env.sh && "$GOVBUDGET_PG_BIN/psql" postgresql://localhost/govbudget -At -c "select count(*) from jbook_documents where file_path like '%/.claude/worktrees/%';"
```
Expected: `F-15 history matches the S5 pin` (the pin is `c59ccf4f06c73db7fb47b0c505c178fc3e530c9993cf5ef95c311e66eeb2f2ee`; production's export still holds `9f70c770…`, so the pin can match only after Step 3); `s4-report: PASS` (pre-release live export → release: only era points/`decade_absent` moved in the program sidecars and PDF receipts it compares, no complete receipt lost, F-15 default 67/67; its gain numbers should equal Task 21's — it cannot see the SAM and `/company/` changes, which Step 3's counts cover); `link-coverage exit=0` (budget figures 100% source-linked, no figure lost a complete receipt — V9); `0` worktree paths recorded (LAUNCH.md rule of 2026-09-12). Any failure: stop and take Step 3's abort path (the pre-release copy is at `.proofs/release-pre-site`).

- [ ] **Step 5: Python release gates (V10)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
for gate in verify-era-map verify-phase5b1 verify-phase5e verify-lineage; do GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget ${gate} > tmp/release-${gate}.log 2>&1; echo "${gate} exit=$?"; tail -1 tmp/release-${gate}.log; done; GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget evals check > tmp/release-evals.log 2>&1; echo "evals exit=$?"; tail -3 tmp/release-evals.log
```
Expected: each gate `exit=0` with its last line `verify-era-map: PASS`, `verify-phase5b1: PASS`, `verify-phase5e: PASS`, `verify-lineage: PASS`; `evals check: <n> ok, 0 stale, <k> skipped` and `evals check: PASS`. A failed gate that cannot be cleared: take Step 3's abort path. If `evals check` lists STALE answers: read each `expected=… live=…`; only when every one is explained by this piece's lake changes (the S1b classified `9999999999` rows, the new era tables) refresh and re-check (the guard applies: both read the live lake) — otherwise stop:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data uv run --project . python -m govbudget evals refresh && GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget evals check > tmp/release-evals.log 2>&1; echo "evals exit=$?"; tail -3 tmp/release-evals.log; git -C .. status --porcelain -- GovBudget/evals
```
Expected: `evals check: PASS` and ` M GovBudget/evals/phase5_questions.yaml` (the file `govbudget.evals_refresh.EVAL_PATH` names). Then commit exactly that file:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/evals/phase5_questions.yaml && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "chore(evals): refresh answers moved by the era procurement export" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: `1 file changed`.

- [ ] **Step 6: Commit the build's llms.txt first**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com node scripts/prepare-assets.mjs > /dev/null && cd .. && git diff --stat -- site/public/llms.txt && git diff -- site/public/llms.txt | grep '^[-+][^-+]' | head -6; echo "placeholder lines: $(git diff -- site/public/llms.txt | grep -c 'govbudget-placeholder.example')"; uv run --project . python -c "import json; d=json.load(open('tmp/release-counts.json')); print('N =', d['release']['citations'], '| ERA_D =', d['ERA_D'], '| SAM_D =', d['SAM_D'])"
```
`prepare-assets.mjs` takes the origin from `NEXT_PUBLIC_SITE_URL` (placeholder `https://govbudget-placeholder.example` when unset, which would rewrite every route line of the tracked `llms.txt`; ROADMAP #18), so the variable is part of the command. Expected: `1 file changed, 1 insertion(+), 1 deletion(-)`, the two shown lines being line 7, the citation count (125,409 to the release `<N>`: 143,841 when the release export carries 149 SAM registrations, more after further fetches); `placeholder lines: 0`; and the printed `N` equal to the new count in `llms.txt`. Any `govbudget-placeholder.example` line means the origin was unset: run `git checkout -- site/public/llms.txt` and re-run. Commit it so the build below is of a clean HEAD (deploy.sh refuses otherwise), filling the three numbers from the printed line:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/site/public/llms.txt && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "chore(site): llms.txt citation count after the era procurement export and the SAM answers stored since aa714d7f (125,409 -> <N>: +<ERA_D> era, +<SAM_D> SAM registrations)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: Build, verify and test the site at HEAD**

First run the `data/site` check that opens Step 11 (read-only, seconds): a build over a `data/site` that is no longer the release export is wasted. On `STOP`, re-run Step 3 or take its abort path.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > ../tmp/release-site-build.log 2>&1; echo "build exit=$?"; NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run verify > ../tmp/release-site-verify.log 2>&1; echo "verify exit=$?"; grep -E "^overall:" ../tmp/release-site-verify.log; npm test > ../tmp/release-vitest.log 2>&1; echo "vitest exit=$?"; cd .. && git status --porcelain -- . | grep -v '^??'; uv run --project . python -c "import json; print(json.load(open('site/out/.build-meta.json'))['git_head'])"; git rev-parse HEAD
```
Expected: `build exit=0`, `verify exit=0`, `overall: PASS`, `vitest exit=0`; no tracked change (the rebuilt `llms.txt` equals the committed one); the two shas are equal. A failure here that cannot be cleared: take Step 3's abort path.

Then check the home page's trust-anchor copy in the build (final review T1: `p1_era_line_map` ships uncited, so a universal "every published dataset carries a citation tier" is false from this release on, and production's home page still says it):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && grep -c 'every published dataset carries a citation tier\.' site/out/index.html; grep -c 'every published dataset that holds amounts carries a citation tier' site/out/index.html
```
Expected: `0`, then a count ≥ 1. If the copy fix shipped different words, grep for the clause it did ship (`grep -n 'every published dataset' site/src/app/page.tsx`); if the first count is not 0, stop: the fix is missing from this HEAD.

- [ ] **Step 8: verify-phase5 (full assembly, includes verify-era-map)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com uv run --project . python -m govbudget verify-phase5 > tmp/release-verify-phase5.log 2>&1; echo "exit=$?"; grep -E "verify-era-map|gate eval|gate assembly|^verify-phase5:" tmp/release-verify-phase5.log | tail -8
```
Expected: `exit=0`; the assembly lists `verify-era-map` PASS among its phases; `verify-phase5: PASS`. Exit 2 (`BLOCKED`) is not a pass (ROADMAP #139): check the API key reached the run (`.env` symlink, Step 2) and re-run; a failure or BLOCKED that cannot be cleared: take Step 3's abort path. This runs the paid live eval (48 questions) as every release has.

- [ ] **Step 9: Deploy dry run**

First run the `data/site` check that opens Step 11 (read-only); the dry run does not look at `data/site`'s contents. On `STOP`, re-run Step 3 or take its abort path.

```bash
/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh --dry-run > /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/release-deploy-dry.log 2>&1; echo "exit=$?"; grep -E "0/3|provenance:|untracked inputs|R2 pdfs|rollback tag|Dry run complete" /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/release-deploy-dry.log
```
Expected: `exit=0`; `0/3  preflight`; `provenance:      OK — git_head matches HEAD; no tracked changes; no untracked build inputs`; `untracked inputs: none`; the R2 PDF count; `Dry run complete — nothing was copied, uploaded or deployed.` A failure that cannot be cleared: take Step 3's abort path.

- [ ] **Step 10: Owner go-ahead**

Tell the owner in chat: "Ready to deploy families piece 1 at `<HEAD short sha>`: <gained.pb2026> PB2026 and <gained.decade_only> decade-only procurement pages gain PB2017–PB2023 points; it also publishes <SAM_D> SAM.gov registrations the daily job stored since the last deploy (<pre companies_with_sam> → <release companies_with_sam> on the company pages and in the /methodology/ SAM sentence; from `tmp/release-counts.json`; the next fetch ships with the next export); all gates green (verify-phase5, -5b1, -5e, -lineage, -era-map, link coverage, npm verify). Deploy now?" Wait for an explicit yes. The wait has no time limit and other worktrees link this `data/site`; Step 11's first block catches a re-export that lands meanwhile.

- [ ] **Step 11: Deploy**

First confirm `data/site` is still the release export (final review RR-2, INT-4). `deploy.sh` checks git state only and `upload_r2.sh` uploads whatever `data/site` holds, and four older worktrees link that directory with pre-branch code, so a re-export between Step 3 and now would push pre-era `data/` and `citations/` to R2 beneath era pages with nothing flagging it. This block (also run at the start of Steps 7 and 9) reads only `data/site` and `.proofs`, so it needs no SAM guard:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L=/Users/andeslee/Documents/Cursor-Projects/GovBudget
(cd "$L" && shasum -a 256 -c --quiet .proofs/release-export.sha256) || { echo "STOP: data/site is no longer the release export (fingerprint mismatch)"; exit 1; }
H=$(shasum -a 256 "$L/data/site/json/f15_funding_history.json" | cut -d' ' -f1); { [ -n "$H" ] && [ "$H" = "$(cat tests/fixtures/f15/history.sha256)" ]; } || { echo "STOP: F-15 history does not match the S5 pin (got ${H:-nothing})"; exit 1; }
for f in data/p1_era_line_map.parquet json/era_map_summary.json; do [ -s "$L/data/site/$f" ] || { echo "STOP: $f is missing from data/site"; exit 1; }; done
B=$(uv run --project . python -c "import json; print(json.load(open('$L/data/site/manifest.json'))['built_at'])"); [ "$B" = "$(cat "$L/.proofs/release-export.built_at")" ] || { echo "STOP: manifest built_at ($B) is not the Step 3 export's"; exit 1; }
echo "data/site is the release export: built_at $B"
```
Expected: `data/site is the release export: built_at <the built_at Step 3 recorded>`. Any `STOP`: do not deploy; on a fingerprint mismatch `shasum -c` names the differing files just above the `STOP`, so read them first. Re-run Step 3 (then Steps 4–9 again) or take Step 3's abort path. Then deploy:

```bash
/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh > /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/release-deploy.log 2>&1; echo "exit=$?"; head -5 /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/release-deploy.log; grep -E "rollback tag|Rollback copy made|Deploy complete" /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/release-deploy.log
```
Always launch by this absolute path: it deploys the checkout it lives in (this worktree's `site/out/` and, through the symlink, the main lake's `data/site`). Expected: the first lines show `0/3  preflight`; `exit=0`; `rollback tag:    <YYYY-MM-DDTHHMMSSZ>`; `Rollback copy made and checked: r2:govbudget-assets/rollback/<tag>/`; `Deploy complete: live data/ + citations/ copied to … (rollback tag <tag>), assets synced, site/out/ live, live assets verified.` Record the tag. A failure after the copy prints the tag again; never re-run without reading it.

- [ ] **Step 12: Live checks**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && H=$(git rev-parse HEAD) && curl -s https://fiscalreceipts.com/.build-meta.json | grep -c "\"git_head\": \"${H}\"" && curl -s https://fiscalreceipts.com/program/F01500/ | grep -c 'data-fact-id="3bd9c921b2397209"' && curl -s https://fiscalreceipts.com/json/cite-shards/3b.json | uv run --project . python -c "import json,sys; c=json.load(sys.stdin)['3bd9c921b2397209']; print(c['kind'], c['pe_bli'], c['amount_thousands'])" && curl -s https://fiscalreceipts.com/json/budget-pdf-receipts/v2/3bd.json | uv run --project . python -c "import json,sys; print('complete:', json.load(sys.stdin)['3bd9c921b2397209']['complete'])" && curl -s https://fiscalreceipts.com/families/f-15/ | grep -c 'F-15e (FY2020 F-15EX Lot 1 aircraft)' && curl -s https://fiscalreceipts.com/families/f-15/ | grep -c 'data-history-note="F015E0"' && curl -s https://fiscalreceipts.com/data/ | grep -c 'p1_era_line_map' && curl -s -o /dev/null -w "%{http_code}\n" -r 0-3 https://assets.fiscalreceipts.com/data/p1_era_line_map.parquet && curl -s -o /dev/null -w "%{http_code}\n" https://fiscalreceipts.com/fact/3134a6e0 && curl -s https://fiscalreceipts.com/sitemap.xml | grep -o '<loc>[^<]*</loc>' | wc -l
```
Expected, in order: `1`; a count ≥ 1 (F01500's PB2017 FY2015 actuals era point is on its page); `workbook F01500 498314.0`; `complete: True`; ≥ 1; `1`; ≥ 1; `206`; `200`; `4349`.

Then the home page's trust anchor (final review T1: production's home page still says every dataset carries a tier, which is false once `p1_era_line_map` ships uncited). These two are separate commands, since `grep -c` exits 1 on a zero count and would break an `&&` chain:

```bash
curl -s https://fiscalreceipts.com/ | grep -c 'every published dataset carries a citation tier\.'; curl -s https://fiscalreceipts.com/ | grep -c 'every published dataset that holds amounts carries a citation tier'
```
Expected: `0`, then a count ≥ 1 (the qualified wording; if the copy fix shipped different words, grep for the clause it did ship). A `1` from the first command means the deploy shipped a HEAD without the copy fix: tell the owner at once.

Then one decade-only and one more PB2026 page from the release report's samples:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python - <<'PY'
import json, urllib.request
report = json.load(open("/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/release-report.json"))
for kind in ("decade_only", "pb2026"):
    slug = report["sidecars"]["samples"][kind][0]
    side = json.load(open(f"/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/json/program_details/{slug}.json"))
    fid = next(p["fid"] for points in side["decade_series"].values() for p in points if p["edition"] <= 2023)
    html = urllib.request.urlopen(f"https://fiscalreceipts.com/program/{slug}/").read().decode()
    print(kind, slug, fid, "on live page:", f'data-fact-id="{fid}"' in html)
PY
```
Expected: two lines ending `on live page: True`.

- [ ] **Step 13: ROADMAP stamp**

In `docs/superpowers/ROADMAP.md`:

Values that move with SAM fetches (`<N>`, `<SAM_D>`, `<a>`, `<b>`) come from `tmp/release-counts.json` (Step 3), never from a later read of the lake: they describe the export that shipped. `<ERA_D>` and `<n>` (196 expected) do not move with SAM fetches.

(a) Add a phase-ledger row directly above the `| Post-launch |` row (line 213 today), filled from Task 21's `s4-report.json`, this task's `release-report.json`, `tmp/release-counts.json`, the deploy log and the export log:

```markdown
| Families-1 | Procurement history before FY2024 (platform families piece 1): PB2017–PB2023 P-1 points on procurement program pages through dated owner decisions on the printed budget code — `line_item_code` captured on every era P-1 row (migration 021), `p1_era_line_map` (6,927 era keys; class rulings R-DEC-ERA-SAME/EXCLUDE/HISTORY + owner batches R-DEC-ERA-B1…B6), `fct_program_decade_series`; F-15 fenced; F015E0 relabeled with its cited Lot 1 sentence | verify-era-map (legs a–f, in verify-phase5) + V5 F-15 identity + S4 A/B proof (diff = spec §10) + link-coverage V9 | ✅ DEPLOYED <YYYY-MM-DD> at <short sha> (rollback tag <tag>) | <gained.pb2026>/892 PB2026 + <gained.decade_only>/89 decade-only procurement pages gain era points (<all_seven_editions.pb2026> with all seven editions), <new_points> points; citations 125,409 → <N> (+<ERA_D> era, +<SAM_D> SAM #10); era P-1 receipts complete PB2017–PB2023 <c/f per edition>; F-15 default cells 67/67; gates: npm verify overall PASS, verify-phase5 PASS (eval <x>/48), 5b1/5e/lineage/era-map PASS, evals check PASS |
```

(b) Append after the "Platform families (2026-10-02)" paragraph's last sentence (today the `*Correction (2026-10-04):*` sentence ending "was the option the controller offered in chat."):

```markdown
**Piece 1 deployed (<YYYY-MM-DD>, <short sha>):** procurement history now reaches
PB2017 on <gained.pb2026 + gained.decade_only> procurement pages; next is piece 2
(family registry), per the [overview](specs/2026-10-02-platform-families-overview.md).
```

(c) Add a findings-log entry as the first item under `## Findings log`:

```markdown
- **<YYYY-MM-DD>: Families piece 1 released.** Release export from the main lake
  (pre-release copy `.proofs/release-pre-site`); against it, in the program
  sidecars and PDF receipts that `scripts/era/s4_report.py` compares, the release
  moved only era decade points and decade-only `decade_absent` blocks, lost no
  complete PDF receipt and kept the F-15 default cells 67/67; link coverage held
  against the S0 baseline; the F-15 history matched its S5 pin. The export also
  shipped the SAM.gov registrations the #10 daily job had stored since the
  2026-10-02 export, which no families proof compares: `json/sam` <a> → <b>
  receipts, `site_meta.counts.companies_with_sam` <a> → <b>, one derived citation
  each (the citation count 125,409 → <N> is +<ERA_D> era and +<SAM_D> SAM), the
  `/company/` pages and the `/methodology/` sentence "<a> of the published
  families also carry a cited SAM.gov registration" (now <b>); the counts are
  Step 3's (`tmp/release-counts.json`), exact for the shipped export even where
  the daily job fetched again afterwards. Deployed by `deploy.sh` from the
  families worktree (rollback tag <tag>); live: `/.build-meta.json` <short sha>,
  F01500's PB2017 FY2015 actuals point
  (`3bd9c921b2397209`, receipt complete) on its page with `pe_bli` F01500,
  `/families/f-15/` shows the F015E0 label and note, `p1_era_line_map.parquet`
  served from R2, sitemap 4,349 URLs. As spec §10's 2026-10-02 correction expects,
  the release also moves `/methodology/`'s dbt-assertion count and
  `site_meta.build_checks.dbt_assertions` from 163 to <n> (196 expected; Tasks 13,
  15 and 16 added dbt tests; `<n>` from the release `data/site/json/site_meta.json`),
  and `/data/` gains the `p1_era_line_map` inventory row (re-measured in the S4
  proof). A final review before the release (four lenses: integration and merge
  hazards, reader-visible copy truthfulness, deferred-minor triage, release
  readiness) found and had fixed, before the deploy, the home page's "every
  published dataset carries a citation tier" (false once `p1_era_line_map` ships
  uncited), the `/methodology/` clause "the rest stay data only" (now "no program
  page"), the `/years/` procurement-cell tooltip and the dataset scope sentences;
  its other findings are filed as follow-ups #198–#205.
```
Fill the follow-up range from the backlog as filed (`grep -nE '^- \*\*#(19[89]|20[0-9]) ' docs/superpowers/ROADMAP.md`; #198–#205 from the final review's triage block, renumbered if another branch landed first). If Step 1's restore block ran, add to the entry that the lake had to be restored, and by which command.

(d) Add a dated status marker to backlog #10 (SAM entity extract / Splink; the numbered entry whose newest marker today, at about line 5162 before (a)–(c) shift it, starts `**Status:** PARTIAL 2026-10-02 — 62 registrations are live, each citing`). Existing markers are never reworded; follow dc801fdb's convention for the previous one: the new marker goes directly above it as a plain `**Status:**` (what `grep '**Status:**'` finds), and the old marker's label alone changes, `**Status:** PARTIAL 2026-10-02` becoming `**Status (2026-10-02): PARTIAL 2026-10-02**`, its body untouched. Read the owed count first (read-only; the job writes `state.json`, so it carries the SAM guard):

```bash
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; else python3 -c "import json; s=json.load(open('/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/daily/state.json')); print(s['last_message']); print('retry_until', s['retry_until'])"; fi
```
Expected: the job's last message, ending `<k> of 200 still owed`. Insert, at the 4-space indentation of its neighbours:

```markdown
    **Status:** PARTIAL <YYYY-MM-DD> — <b> registrations are live (<SAM_D> more
    than the 62 of aa714d7f), shipped with the families piece 1 deploy at
    <short sha> (rollback tag <tag>): the daily job stored them after the
    2026-10-02 export and the release export carried them (`json/sam` <a> → <b>
    receipts, `site_meta.counts.companies_with_sam` <a> → <b>, one derived
    citation each). <k> of 200 families are still owed
    (`data/parquet/sam/daily/state.json`, read <YYYY-MM-DD>); each later answer
    reaches the site at the next `export-site` and deploy.
    *(Earlier markers below.)*

```
`<b>` is the shipped export's count from Step 3, not the lake's `registered` figure if a fetch landed afterwards.

(e) Add a clause to the `Updated:` header (line 3). Replace the line's opening `**Updated:** 2026-10-02 (platform families:` with `**Updated:** <YYYY-MM-DD> (families piece 1 deployed at <short sha>; SAM #10 status); 2026-10-04 (families piece 1: S4 proof, B6 correction, F015E0 correction, final review; era-map review closed 2026-10-03); 2026-10-02 (platform families:` and leave the rest of the line unchanged (when the deploy date is 2026-10-04, merge the first two clauses into one).

- [ ] **Step 14: Commit the stamp**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/docs/superpowers/ROADMAP.md && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "docs(roadmap): stamp the families piece 1 deploy (<short sha>, rollback tag <tag>)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 15: Owner go-ahead to publish the code**

Ask the owner: "Deploy verified. Push the branch to monorepo `main` (fast-forward only) and publish GovBudget to fiscalreceipts `main`?" Wait for an explicit yes.

- [ ] **Step 16: Fast-forward monorepo main**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git fetch origin && git merge-base --is-ancestor origin/main HEAD && echo "fast-forward from origin/main" && git push origin "HEAD:refs/heads/main"
```
Expected: `fast-forward from origin/main`, then the push `dc801fdb..<sha>  HEAD -> main`. If the ancestor check prints nothing and the push is skipped (`&&` chain stops), stop and report: someone advanced `origin/main`; never force.

- [ ] **Step 17: Fast-forward the main checkout (the SAM job runs from it)**

Only between :25 and :10 past the hour (the SAM tick starts at :17):

```bash
MIN=$(date +%M) && if [ "$MIN" -ge 10 ] && [ "$MIN" -lt 25 ]; then echo "WAIT: minute $MIN is near the SAM tick"; else cd /Users/andeslee/Documents/Cursor-Projects && git rev-parse --abbrev-ref HEAD && git merge --ff-only origin/main && git log --oneline -1 && git status --porcelain --untracked-files=no && cd GovBudget && uv run --no-sync dbt parse --project-dir dbt --profiles-dir dbt > /dev/null && python3 -c "import json; m=json.load(open('dbt/target/manifest.json')); print('dbt test nodes:', sum(1 for n in m['nodes'].values() if n['resource_type'] == 'test'))"; fi
```
Expected: `main`, a fast-forward to the pushed sha, only ` M CLAUDE.md` (the workspace file this piece never touched), then `dbt test nodes: 196`, the worktree manifest's count (the final-review fixes change no dbt tests). `dbt parse` writes only the main checkout's gitignored `dbt/target`, takes no warehouse lock, and `--no-sync` leaves the venv the SAM job runs from untouched. Without it that manifest stays at the pre-era 163 tests, and the next export from the main checkout would put "163 dbt data-model assertions" back on `/methodology/` while gate 24 leg e, which recounts the same stale file, stays green (final review INT-3). A count other than the worktree manifest's: stop and report. If `--ff-only` refuses, stop and report.

- [ ] **Step 18: Split the subtree**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git fetch govbudget && git subtree split --prefix=GovBudget -b publish-families-2026-10-02 && SPLIT=$(git rev-parse publish-families-2026-10-02) && echo "SPLIT=${SPLIT}" && (git merge-base --is-ancestor govbudget/main "${SPLIT}" && echo "fast-forward" || echo "needs merge")
```
Expected: the split commit sha; `needs merge` (govbudget/main `dbe24bcb` is a merge commit that is not in the monorepo; measured 2026-10-02). On `fast-forward`, skip Step 19 and park the split itself for Step 20: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git branch publish-families-merge publish-families-2026-10-02`.

- [ ] **Step 19: Confirm the standalone repo holds nothing the monorepo lacks, then merge**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && GT=$(git rev-parse 'govbudget/main^{tree}') && MATCH=$(git log --format=%H HEAD | while read c; do [ "$(git rev-parse "${c}:GovBudget")" = "${GT}" ] && echo "${c}" && break; done) && echo "govbudget/main tree = ${MATCH}:GovBudget" && git log -1 --format='%h %s' "${MATCH}"
```
Expected: one monorepo commit, `dc801fdb` (unless another publish happened since; any commit of this branch's history is fine). If nothing matches, stop: fiscalreceipts holds content the monorepo lacks — reconcile, never force. Then:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && SPLIT=$(git rev-parse publish-families-2026-10-02) && MERGE=$(GIT_AUTHOR_NAME="Andes Lee" GIT_AUTHOR_EMAIL="andes.lee444@gmail.com" GIT_COMMITTER_NAME="Andes Lee" GIT_COMMITTER_EMAIL="andes.lee444@gmail.com" git commit-tree "${SPLIT}^{tree}" -p "${SPLIT}" -p govbudget/main -m "Merge families piece 1 (procurement history before FY2024) into fiscalreceipts" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>") && git merge-base --is-ancestor govbudget/main "${MERGE}" && [ "$(git rev-parse "${MERGE}^{tree}")" = "$(git rev-parse HEAD:GovBudget)" ] && git branch publish-families-merge "${MERGE}" && echo "MERGE=${MERGE} ok, parked in refs/heads/publish-families-merge"
```
Expected: `MERGE=<sha> ok, parked in refs/heads/publish-families-merge`. Shell variables do not survive to the next block, so Step 20 pushes this local ref by name, never a `${MERGE}` that could be empty (an empty source would make `:refs/heads/main` a delete refspec). If `git branch` refuses because the ref already exists, a previous attempt left it: check it (`git log -1 publish-families-merge`), `git branch -D publish-families-merge`, and re-run this block.

- [ ] **Step 20: Publish to fiscalreceipts and clean up the temp branch**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families || exit 1
git rev-parse --verify -q refs/heads/publish-families-merge > /dev/null || { echo "STOP: refs/heads/publish-families-merge is missing: run Step 19 (or Step 18's fast-forward line) first"; exit 1; }
git push govbudget publish-families-merge:refs/heads/main && git branch -D publish-families-2026-10-02 publish-families-merge && git fetch govbudget && [ "$(git rev-parse 'govbudget/main^{tree}')" = "$(git rev-parse HEAD:GovBudget)" ] && echo "fiscalreceipts main == monorepo GovBudget"
```
(The pushed commit is the merge Step 19 parked, or the split itself when Step 18 printed `fast-forward`.) Expected: `dbe24bcb..<sha>  publish-families-merge -> main`, `Deleted branch publish-families-2026-10-02 (was …)`, `Deleted branch publish-families-merge (was …)`, `fiscalreceipts main == monorepo GovBudget`. The push cannot deploy (`GovBudget/vercel.json` `git.deploymentEnabled: false`); deploys stay `deploy.sh`-only.

- [ ] **Step 21: Report and offer cleanup**

Report to the owner: the deployed sha, rollback tag, the page-gain numbers, the SAM registrations that shipped alongside (<SAM_D>), and the publish shas. Then ask whether to remove the proof state (it is not removed without a yes), all under `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/`: the snapshots `s0` (Task 8) and `s1` (Task 9), their logs `s1-logs` and `s1b-logs`, Task 17's `task17`, Task 19's `t19-data-hoist` and `t19-era-summary`, this plan's `s4`, `s4-A`, `s4-B`, `s4-B2` (Task 21's control clone), `s4-logs`, `s5` and `release-pre-site` (APFS clones; the exports inside hold ~2 GB each of their own blocks) and this task's `release-report.json`, `release-export.sha256` and `release-export.built_at` (`tmp/release-counts.json` sits in the worktree's ignored `tmp/` and needs no cleanup); the scratch database `govbudget_proof_s4`; and the throwaway test cluster. On a yes:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && "${GOVBUDGET_PG_BIN:?}/dropdb" govbudget_proof_s4 && "$GOVBUDGET_PG_BIN/pg_ctl" -D "${GOVBUDGET_PROOFS:?}/testpg" stop && cd "${GOVBUDGET_PROOFS:?}" && rm -rf s0 s1 s1-logs s1b-logs task17 t19-data-hoist t19-era-summary s4 s4-A s4-B s4-B2 s4-logs s5 release-pre-site release-export.sha256 release-export.built_at release-report.json && ls -A "$GOVBUDGET_PROOFS"
```
Expected: `waiting for server to shut down.... done` and `server stopped`, then only `testpg` and `testpg.log` remain (keep them for the next piece, or `rm -rf testpg testpg.log` on the owner's word; the cluster restarts with Task 1 Step 5's command).
