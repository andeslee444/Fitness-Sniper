<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 23: Release (S6) — gates, deploy, ROADMAP stamp, publish

**Spec:** §8 V9 (link-coverage hard check), V10 (verify-phase5, -5b1, -5e, -lineage, -era-map, deploy live check), §9 S6, §1 success criteria.
**Files:**
- Modify (by the build): `site/public/llms.txt`
- Modify (only if `evals check` finds stale answers explained by this piece): `evals/phase5_questions.yaml`
- Modify: `docs/superpowers/ROADMAP.md` — new phase-ledger row directly above `| Post-launch |` (line 184 today); one sentence after the "Platform families (2026-10-02)" paragraph; a findings-log entry
**Interfaces:**
Consumes: everything above; `govbudget link-coverage` + `data/research/link_coverage/baseline.json` (Task 5; CONTRACT ISSUE 7); `scripts/era/s4_report.py` and `.proofs/s4-logs/s4-report.json` (Task 21); `scripts/era/env.sh` (Task 1: `GOVBUDGET_PG_BIN`, `GOVBUDGET_PROOFS`; no Postgres binary is on `PATH`); `govbudget era-map check --strict` (Task 12); `govbudget jbooks export-facts` (exists; branch version from Task 7); `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh`; remotes `origin` (monorepo) and `govbudget` (fiscalreceipts).
Produces: the release export in the main lake's `data/site`; production at the release HEAD; R2 rollback tag; ROADMAP stamp; monorepo `main` and fiscalreceipts `main` advanced.

Measured now: production `/.build-meta.json` `git_head aa714d7f…` (built 2026-10-02T02:09Z); live sitemap 4,349 URLs; `https://assets.fiscalreceipts.com/data/budget_lines_decade.parquet` answers 206 to a range request; `govbudget/main` = `dbe24bcb` (a merge commit not in the monorepo) whose tree `d316ef7b…` equals `dc801fdb:GovBudget` — so the subtree split is not a fast-forward and needs the merge recipe (Step 20); the main checkout is on `main` at `dc801fdb` with one unrelated modified file (`CLAUDE.md` at the monorepo root); the F01500 PB2017 FY2015 actuals era leaf is `3bd9c921b2397209` ($498,314K, receipt complete in the PB2017 P-1 book); the decisions worktree's `tmp/pdfs` holds the 21 `*-program-pages-v1.json` caches; the main `.env` defines `ANTHROPIC_API_KEY`, `DATA_GOV_API_KEY`, `JEV_API_KEY`, `SAM_API_KEY` and no path variables.

- [ ] **Step 1: Preconditions**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git status --porcelain -- GovBudget | grep -v '^??'; git log --oneline -1; cd GovBudget && source scripts/era/env.sh && "$GOVBUDGET_PG_BIN/pg_isready" -h 127.0.0.1 -p 55432; uv run --project . pytest -q 2>&1 | tail -2
```
Expected: no tracked change; HEAD is Task 22's last commit; `127.0.0.1:55432 - accepting connections` (Task 1's throwaway cluster; `env.sh` points `GOVBUDGET_TEST_PG_DSN` at it); pytest ends `… passed` with 0 failed (skips only where a test skips today).

Then check that the live lake still carries what this branch built (read-only). Until the branch merges, a `jbooks export-facts` from the main checkout rewrites `data/parquet/jbooks/budget_lines.parquet` without `line_item_code` (G2 hazard 2), and a main-checkout `govbudget build` rebuilds `stg_budget_lines` without it — either would break the release export:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && mkdir -p tmp && uv run --project . python - <<'PY2'
import duckdb, os
data = os.environ["GOVBUDGET_DATA"]
con = duckdb.connect(os.environ["GOVBUDGET_DUCKDB"], read_only=True)
cols = [r[0] for r in con.execute("describe select * from read_parquet(?)", [f"{data}/parquet/jbooks/budget_lines.parquet"]).fetchall()]
print("budget_lines.parquet has line_item_code:", "line_item_code" in cols)
tables = {r[0] for r in con.execute("select table_name from duckdb_tables()").fetchall()}
print("era tables:", sorted(t for t in tables if t in {"p1_era_code_decisions", "p1_era_line_map", "fct_program_decade_series"}))
PY2
MIN=$(date +%M); if [ "$MIN" -ge 15 ] && [ "$MIN" -le 20 ]; then echo "WAIT: minute $MIN is in the SAM window"; else uv run --project . python -m govbudget era-map check --strict > tmp/release-era-check.log; echo "era-map check exit=$?"; tail -1 tmp/release-era-check.log; uv run --project . dbt test --project-dir dbt --profiles-dir dbt --select p1_era_code_decisions p1_era_line_map fct_program_decade_series > tmp/release-dbt-test.log 2>&1; echo "dbt test exit=$?"; tail -1 tmp/release-dbt-test.log; fi
```
Expected: `budget_lines.parquet has line_item_code: True`; `era tables: ['fct_program_decade_series', 'p1_era_code_decisions', 'p1_era_line_map']`; `era-map check exit=0`, `era-map check: 0 undecided chain(s), 0 stale decision(s)`; `dbt test exit=0`, `Done. PASS=<n> WARN=0 ERROR=0 SKIP=0 …` (`dbt test` only reads the warehouse; it also writes this worktree's own `dbt/target/manifest.json`, which the release export reads for `site_meta.build_checks.dbt_assertions`).

If any of these fails, restore the branch's lake state before Step 3 (SHARED LAKE WRITE: the contract's Task 23 write; outside the SAM window; no other session may hold the DuckDB file):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && MIN=$(date +%M) && if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: minute $MIN is in the SAM window (:15-:20, with margin)"; else uv run --project . python -m govbudget jbooks export-facts > tmp/release-export-facts.log 2>&1; echo "export-facts exit=$?"; uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select stg_budget_lines p1_era_code_decisions p1_era_line_map fct_program_decade_series > tmp/release-dbt-build.log 2>&1; echo "dbt build exit=$?"; tail -1 tmp/release-dbt-build.log; fi
```
Expected: `export-facts exit=0`, `dbt build exit=0`, `Done. PASS=<n> WARN=0 ERROR=0 SKIP=0 …`; then re-run the check block above (all four expectations). Record in the Step 13 findings entry that the lake had to be restored, and by which command.

- [ ] **Step 2: Point the worktree at the main lake and the main `.env`**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && for d in site duckdb parquet raw raw_docs; do if [ -e data/${d} ] && [ ! -L data/${d} ]; then echo "STOP: data/${d} is a real directory"; else ln -sfn /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/${d} data/${d}; fi; done; [ -e .env ] || ln -s /Users/andeslee/Documents/Cursor-Projects/GovBudget/.env .env; ls -l data .env | grep -- '->'; git -C .. status --porcelain -- GovBudget/data GovBudget/.env
```
Expected: six symlinks (five lake dirs and `.env`) and no status output (all excluded/ignored). Never print `.env`'s contents.

- [ ] **Step 3: Keep a local copy of the live export, then export (SHARED LAKE WRITE: data/site)**

```bash
P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs && { [ -e ${P}/release-pre-site ] || cp -cR /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site ${P}/release-pre-site; } && mkdir -p /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/pdfs && cp -c /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/decisions/GovBudget/tmp/pdfs/*-program-pages-v1.json /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/pdfs/ 2>/dev/null; ls ${P}/release-pre-site/manifest.json
```
Then, starting only between :21 and :45 past the hour (the export takes about 5 minutes plus the receipt pass; the SAM job writes `data/parquet/sam` at :17):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && MIN=$(date +%M) && if [ "$MIN" -lt 21 ] || [ "$MIN" -gt 45 ]; then echo "WAIT: start between :21 and :45 (now :$MIN)"; else S0=$(stat -f %m /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet) && GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget export-site > tmp/release-export.log 2>&1; echo "exit=$?"; S1=$(stat -f %m /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet); [ "$S0" = "$S1" ] && echo "SAM parquet unchanged during the export" || echo "RE-RUN: SAM parquet changed during the export"; tail -3 tmp/release-export.log; fi
```
Expected: `exit=0`, `SAM parquet unchanged during the export`, the `budget PDF receipts: …` and `export-site: … citations …` lines. On `RE-RUN`, run the export again in the next window.

- [ ] **Step 4: Release-state data checks**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && grep -q "$(shasum -a 256 /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site/json/f15_funding_history.json | cut -d' ' -f1)" tests/fixtures/f15/history.sha256 && echo "F-15 history matches the S5 pin"; uv run --project . python scripts/era/s4_report.py --a /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/release-pre-site --b /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site --report /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/release-report.json | tail -1; uv run --project . python -m govbudget link-coverage --site-dir /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site --baseline data/research/link_coverage/baseline.json > tmp/release-link-coverage.txt 2>&1; echo "link-coverage exit=$?"; tail -5 tmp/release-link-coverage.txt; source scripts/era/env.sh && "$GOVBUDGET_PG_BIN/psql" postgresql://localhost/govbudget -At -c "select count(*) from jbook_documents where file_path like '%/.claude/worktrees/%';"
```
Expected: `F-15 history matches the S5 pin`; `s4-report: PASS` (pre-release live export → release: only era points/`decade_absent` moved, no complete receipt lost, F-15 default 67/67; its gain numbers should equal Task 21's); `link-coverage exit=0` (budget figures 100% source-linked, no figure lost a complete receipt — V9); `0` worktree paths recorded (LAUNCH.md rule of 2026-09-12). Any failure: stop; the pre-release copy is at `.proofs/release-pre-site`.

- [ ] **Step 5: Python release gates (V10)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && for gate in verify-era-map verify-phase5b1 verify-phase5e verify-lineage; do GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget ${gate} > tmp/release-${gate}.log 2>&1; echo "${gate} exit=$?"; tail -1 tmp/release-${gate}.log; done; GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget uv run --project . python -m govbudget evals check > tmp/release-evals.log 2>&1; echo "evals exit=$?"; tail -3 tmp/release-evals.log
```
Expected: each gate `exit=0` with its last line `verify-era-map: PASS`, `verify-phase5b1: PASS`, `verify-phase5e: PASS`, `verify-lineage: PASS`; `evals check: <n> ok, 0 stale, <k> skipped` and `evals check: PASS`. If `evals check` lists STALE answers: read each `expected=… live=…`; only when every one is explained by this piece's lake changes (the S1b classified `9999999999` rows, the new era tables) run `GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data uv run --project . python -m govbudget evals refresh`, re-run `evals check` (PASS) and commit `GovBudget/evals/phase5_questions.yaml` with message `chore(evals): refresh answers moved by the era procurement export` — otherwise stop.

- [ ] **Step 6: Commit the build's llms.txt first**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && node scripts/prepare-assets.mjs > /dev/null && cd .. && git diff --stat -- site/public/llms.txt && git diff -- site/public/llms.txt | grep '^[-+][^-+]' | head -6
```
Expected: `llms.txt` changed only in its counts (the citation count moves from 125,409 to the release `<N>`). Commit it so the build below is of a clean HEAD (deploy.sh refuses otherwise):

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/site/public/llms.txt && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "chore(site): llms.txt citation count after the era procurement export (125,409 -> <N>)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: Build, verify and test the site at HEAD**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > ../tmp/release-site-build.log 2>&1; echo "build exit=$?"; NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run verify > ../tmp/release-site-verify.log 2>&1; echo "verify exit=$?"; grep -E "^overall:" ../tmp/release-site-verify.log; npm test > ../tmp/release-vitest.log 2>&1; echo "vitest exit=$?"; cd .. && git status --porcelain -- . | grep -v '^??'; uv run --project . python -c "import json; print(json.load(open('site/out/.build-meta.json'))['git_head'])"; git rev-parse HEAD
```
Expected: `build exit=0`, `verify exit=0`, `overall: PASS`, `vitest exit=0`; no tracked change (the rebuilt `llms.txt` equals the committed one); the two shas are equal.

- [ ] **Step 8: verify-phase5 (full assembly, includes verify-era-map)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com uv run --project . python -m govbudget verify-phase5 > tmp/release-verify-phase5.log 2>&1; echo "exit=$?"; grep -E "verify-era-map|gate eval|gate assembly|^verify-phase5:" tmp/release-verify-phase5.log | tail -8
```
Expected: `exit=0`; the assembly lists `verify-era-map` PASS among its phases; `verify-phase5: PASS`. Exit 2 (`BLOCKED`) is not a pass (ROADMAP #139): check the API key reached the run (`.env` symlink, Step 2) and re-run. This runs the paid live eval (48 questions) as every release has.

- [ ] **Step 9: Deploy dry run**

```bash
/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh --dry-run > /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/release-deploy-dry.log 2>&1; echo "exit=$?"; grep -E "0/3|provenance:|untracked inputs|R2 pdfs|rollback tag|Dry run complete" /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/release-deploy-dry.log
```
Expected: `exit=0`; `0/3  preflight`; `provenance:      OK — git_head matches HEAD; no tracked changes; no untracked build inputs`; `untracked inputs: none`; the R2 PDF count; `Dry run complete — nothing was copied, uploaded or deployed.`

- [ ] **Step 10: Owner go-ahead**

Tell the owner in chat: "Ready to deploy families piece 1 at `<HEAD short sha>`: <gained.pb2026> PB2026 and <gained.decade_only> decade-only procurement pages gain PB2017–PB2023 points; all gates green (verify-phase5, -5b1, -5e, -lineage, -era-map, link coverage, npm verify). Deploy now?" Wait for an explicit yes.

- [ ] **Step 11: Deploy**

```bash
/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh > /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/release-deploy.log 2>&1; echo "exit=$?"; head -5 /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/release-deploy.log; grep -E "rollback tag|Rollback copy made|Deploy complete" /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/tmp/release-deploy.log
```
Always launch by this absolute path: it deploys the checkout it lives in (this worktree's `site/out/` and, through the symlink, the main lake's `data/site`). Expected: the first lines show `0/3  preflight`; `exit=0`; `rollback tag:    <YYYY-MM-DDTHHMMSSZ>`; `Rollback copy made and checked: r2:govbudget-assets/rollback/<tag>/`; `Deploy complete: live data/ + citations/ copied to … (rollback tag <tag>), assets synced, site/out/ live, live assets verified.` Record the tag. A failure after the copy prints the tag again; never re-run without reading it.

- [ ] **Step 12: Live checks**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && H=$(git rev-parse HEAD) && curl -s https://fiscalreceipts.com/.build-meta.json | grep -c "\"git_head\": \"${H}\"" && curl -s https://fiscalreceipts.com/program/F01500/ | grep -c 'data-fact-id="3bd9c921b2397209"' && curl -s https://fiscalreceipts.com/json/cite-shards/3b.json | uv run --project . python -c "import json,sys; c=json.load(sys.stdin)['3bd9c921b2397209']; print(c['kind'], c['pe_bli'], c['amount_thousands'])" && curl -s https://fiscalreceipts.com/json/budget-pdf-receipts/v2/3bd.json | uv run --project . python -c "import json,sys; print('complete:', json.load(sys.stdin)['3bd9c921b2397209']['complete'])" && curl -s https://fiscalreceipts.com/families/f-15/ | grep -c 'F-15e (FY2020 F-15EX Lot 1 aircraft)' && curl -s https://fiscalreceipts.com/families/f-15/ | grep -c 'data-history-note="F015E0"' && curl -s https://fiscalreceipts.com/data/ | grep -c 'p1_era_line_map' && curl -s -o /dev/null -w "%{http_code}\n" -r 0-3 https://assets.fiscalreceipts.com/data/p1_era_line_map.parquet && curl -s -o /dev/null -w "%{http_code}\n" https://fiscalreceipts.com/fact/3134a6e0 && curl -s https://fiscalreceipts.com/sitemap.xml | grep -o '<loc>[^<]*</loc>' | wc -l
```
Expected, in order: `1`; a count ≥ 1 (F01500's PB2017 FY2015 actuals era point is on its page); `workbook F01500 498314.0`; `complete: True`; ≥ 1; `1`; ≥ 1; `206`; `200`; `4349`.

Then one decade-only and one more PB2026 page from the release report's samples:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && uv run --project . python - <<'PY'
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

(a) Add a phase-ledger row directly above the `| Post-launch |` row (line 184 today), filled from Task 21's `s4-report.json`, this task's `release-report.json`, the deploy log and the export log:

```markdown
| Families-1 | Procurement history before FY2024 (platform families piece 1): PB2017–PB2023 P-1 points on procurement program pages through dated owner decisions on the printed budget code — `line_item_code` captured on every era P-1 row (migration 021), `p1_era_line_map` (6,927 era keys; class rulings R-DEC-ERA-SAME/EXCLUDE/HISTORY + owner batches R-DEC-ERA-B1…B<k>), `fct_program_decade_series`; F-15 fenced; F015E0 relabeled with its cited Lot 1 sentence | verify-era-map (legs a–f, in verify-phase5) + V5 F-15 identity + S4 A/B proof (diff = spec §10) + link-coverage V9 | ✅ DEPLOYED <YYYY-MM-DD> at <short sha> (rollback tag <tag>) | <gained.pb2026>/892 PB2026 + <gained.decade_only>/89 decade-only procurement pages gain era points (<all_seven_editions.pb2026> with all seven editions), <new_points> points; citations 125,409 → <N>; era P-1 receipts complete PB2017–PB2023 <c/f per edition>; F-15 default cells 67/67; gates: npm verify overall PASS, verify-phase5 PASS (eval <x>/48), 5b1/5e/lineage/era-map PASS, evals check PASS |
```

(b) Append after the "Platform families (2026-10-02)" paragraph's last sentence:

```markdown
**Piece 1 deployed (<YYYY-MM-DD>, <short sha>):** procurement history now reaches
PB2017 on <gained.pb2026 + gained.decade_only> procurement pages; next is piece 2
(family registry), per the [overview](specs/2026-10-02-platform-families-overview.md).
```

(c) Add a findings-log entry as the first item under `## Findings log`:

```markdown
- **<YYYY-MM-DD>: Families piece 1 released.** Release export from the main lake
  (pre-release copy `.proofs/release-pre-site`); against it the release moved only
  era decade points and decade-only `decade_absent` blocks, lost no complete PDF
  receipt and kept the F-15 default cells 67/67 (`scripts/era/s4_report.py`);
  link coverage held against the S0 baseline; the F-15 history matched its S5 pin.
  Deployed by `deploy.sh` from the families worktree (rollback tag <tag>); live:
  `/.build-meta.json` <short sha>, F01500's PB2017 FY2015 actuals point
  (`3bd9c921b2397209`, receipt complete) on its page with `pe_bli` F01500,
  `/families/f-15/` shows the F015E0 label and note, `p1_era_line_map.parquet`
  served from R2, sitemap 4,349 URLs. Outside spec §10 but expected: the release
  also moves `/methodology/`'s dbt-assertion count and
  `site_meta.build_checks.dbt_assertions` from 163 to <n> (Tasks 13, 15 and 16
  added dbt tests; `<n>` from the release `data/site/json/site_meta.json`), and
  `/data/` gains the `p1_era_line_map` inventory row (re-measured in the S4 proof).
```

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
MIN=$(date +%M) && if [ "$MIN" -ge 10 ] && [ "$MIN" -lt 25 ]; then echo "WAIT: minute $MIN is near the SAM tick"; else cd /Users/andeslee/Documents/Cursor-Projects && git rev-parse --abbrev-ref HEAD && git merge --ff-only origin/main && git log --oneline -1 && git status --porcelain --untracked-files=no; fi
```
Expected: `main`, a fast-forward to the pushed sha, and only ` M CLAUDE.md` (the workspace file this piece never touched). If `--ff-only` refuses, stop and report.

- [ ] **Step 18: Split the subtree**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git fetch govbudget && git subtree split --prefix=GovBudget -b publish-families-2026-10-02 && SPLIT=$(git rev-parse publish-families-2026-10-02) && echo "SPLIT=${SPLIT}" && (git merge-base --is-ancestor govbudget/main "${SPLIT}" && echo "fast-forward" || echo "needs merge")
```
Expected: the split commit sha; `needs merge` (govbudget/main `dbe24bcb` is a merge commit that is not in the monorepo; measured 2026-10-02). On `fast-forward`, skip Step 19 and push `${SPLIT}` in Step 20.

- [ ] **Step 19: Confirm the standalone repo holds nothing the monorepo lacks, then merge**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && GT=$(git rev-parse 'govbudget/main^{tree}') && MATCH=$(git log --format=%H HEAD | while read c; do [ "$(git rev-parse "${c}:GovBudget")" = "${GT}" ] && echo "${c}" && break; done) && echo "govbudget/main tree = ${MATCH}:GovBudget" && git log -1 --format='%h %s' "${MATCH}"
```
Expected: one monorepo commit, `dc801fdb` (unless another publish happened since; any commit of this branch's history is fine). If nothing matches, stop: fiscalreceipts holds content the monorepo lacks — reconcile, never force. Then:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && SPLIT=$(git rev-parse publish-families-2026-10-02) && MERGE=$(GIT_AUTHOR_NAME="Andes Lee" GIT_AUTHOR_EMAIL="andes.lee444@gmail.com" GIT_COMMITTER_NAME="Andes Lee" GIT_COMMITTER_EMAIL="andes.lee444@gmail.com" git commit-tree "${SPLIT}^{tree}" -p "${SPLIT}" -p govbudget/main -m "Merge families piece 1 (procurement history before FY2024) into fiscalreceipts" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>") && git merge-base --is-ancestor govbudget/main "${MERGE}" && [ "$(git rev-parse "${MERGE}^{tree}")" = "$(git rev-parse HEAD:GovBudget)" ] && echo "MERGE=${MERGE} ok"
```
Expected: `MERGE=<sha> ok`.

- [ ] **Step 20: Publish to fiscalreceipts and clean up the temp branch**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git push govbudget "${MERGE}:refs/heads/main" && git branch -D publish-families-2026-10-02 && git fetch govbudget && [ "$(git rev-parse 'govbudget/main^{tree}')" = "$(git rev-parse HEAD:GovBudget)" ] && echo "fiscalreceipts main == monorepo GovBudget"
```
(`${MERGE}` from Step 19, or `${SPLIT}` when Step 18 printed `fast-forward`; braces matter in zsh.) Expected: `dbe24bcb..<sha>  <sha> -> main`, `Deleted branch publish-families-2026-10-02`, `fiscalreceipts main == monorepo GovBudget`. The push cannot deploy (`GovBudget/vercel.json` `git.deploymentEnabled: false`); deploys stay `deploy.sh`-only.

- [ ] **Step 21: Report and offer cleanup**

Report to the owner: the deployed sha, rollback tag, the page-gain numbers, and the publish shas. Then ask whether to remove the proof state (it is not removed without a yes), all under `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/`: the snapshots `s0` (Task 8) and `s1` (Task 9), their logs `s1-logs` and `s1b-logs`, Task 17's `task17`, Task 19's `t19-data-hoist` and `t19-era-summary`, this plan's `s4`, `s4-A`, `s4-B`, `s4-logs`, `s5` and `release-pre-site` (APFS clones; the exports inside hold ~2 GB each of their own blocks); the scratch database `govbudget_proof_s4`; and the throwaway test cluster. On a yes:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && "$GOVBUDGET_PG_BIN/dropdb" govbudget_proof_s4 && "$GOVBUDGET_PG_BIN/pg_ctl" -D "$GOVBUDGET_PROOFS/testpg" stop && cd "$GOVBUDGET_PROOFS" && rm -rf s0 s1 s1-logs s1b-logs task17 t19-data-hoist t19-era-summary s4 s4-A s4-B s4-logs s5 release-pre-site && ls -A "$GOVBUDGET_PROOFS"
```
Expected: `waiting for server to shut down.... done` and `server stopped`, then only `testpg` and `testpg.log` remain (keep them for the next piece, or `rm -rf testpg testpg.log` on the owner's word; the cluster restarts with Task 1 Step 5's command).
