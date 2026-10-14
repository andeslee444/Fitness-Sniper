<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G5 (2026-10-13). -->

### Task 22d: Release 1 — `llms.txt`, build, W4, verify-phase5, the owner's go-ahead, deploy, live checks

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §8 step 5 (the `llms.txt` commit built with `NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com`, RR-1; the build, W4 and vitest after the fingerprint check), step 6 (`verify-phase5`, the `deploy.sh --dry-run`; the owner's go-ahead names the moved totals §4.7, the totals-chart flip Q15 and `SAM_D`; the fingerprint check; `./scripts/launch/deploy.sh` by absolute path from this worktree), step 7 (the live checks added for this wave), §4.6, §5.7, §5.8, §3.4.

**Files:**
- Modify (by the build's `prepare-assets.mjs`): `site/public/llms.txt` (line 7, the citation count)
- Deploy (not a repo file): production at this worktree's HEAD; R2 `data/` and `citations/` replaced after `deploy.sh`'s rollback copy.

**Interfaces:**
Consumes: Task 22c's export, `tmp/fu-release-counts.json` and the fingerprint check; Task 21f's `p2b-report.json` and `p1-content.txt`; `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh` (`--dry-run` prints `0/3  preflight`, `provenance:      OK — …`, `untracked inputs: none …`, `R2 pdfs: …`, `rollback tag: …`, `Dry run complete — nothing was copied, uploaded or deployed.`; a real run prints `Rollback copy made and checked: …` and `Deploy complete: …`, and ends with `verify_live_assets.mjs`, which Task 15 extended to probe the three /years/ files); Task 15's `site/scripts/gates/yearsmatrix.mjs` `probeYearsOpeningFetches(baseUrl) -> Promise<{ requests, shards, problem }>` (gate leg k's probe; `problem` null when the page load fetched only the core); Task 22b's abort path (A1–A3), which a post-deploy rollback runs after LAUNCH.md's.
Produces: the deployed release (HEAD short sha, rollback tag) for Task 22e; logs `release-site-*.log`, `release-verify-phase5.log`, `release-deploy-dry.log`, `release-deploy.log`, `live-checks.txt`.

Measured for this task (2026-10-13, live, read-only): production `/.build-meta.json` `git_head` 916ae88e…; sitemap 4,349 URLs; `/program/0390DOM/` 404; `/json/budget-pdf-receipts/00.json` and `/json/budget-pdf-receipts/v2/000.json` 200; `/json-lite/search_quick.json` routes `alias:jassm` to `/program/0603000D8Z/` and `alias:c-130j` to `/program/2012C130J/` (`/json/search_quick.json` itself is not served: 404); a headless Chromium load of `/years/` (`site/node_modules/playwright`) requests only `/json/years_matrix.json`, and no element carries `data-shards`; `site/public/llms.txt` line 7 carries the citation count 143,841.

- [ ] **Step 1: Commit the build's `llms.txt` first**

Run Task 22c's fingerprint check first (a build over a `data/site` that is no longer the release export is wasted; on `STOP`, re-run Task 22c from Step 1 or take the abort path). Then:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com node scripts/prepare-assets.mjs > /dev/null && cd .. && git diff --stat -- site/public/llms.txt && git diff -- site/public/llms.txt | grep '^[-+][^-+]' | head -4; echo "placeholder lines: $(git diff -- site/public/llms.txt | grep -c 'govbudget-placeholder.example')"; uv run --project . python -c "import json; d=json.load(open('tmp/fu-release-counts.json')); print('N =', d['release']['citations'], '| WAVE_D =', d['WAVE_D'], '| SAM_D =', d['SAM_D'])"
```
Expected: `1 file changed, 1 insertion(+), 1 deletion(-)`, the two shown lines being line 7 (143,841 → `<N>`); `placeholder lines: 0`; the printed `N` equal to the new count. Any `govbudget-placeholder.example` line means the origin was unset: `git checkout -- site/public/llms.txt` and re-run. Commit it, filling the three numbers from the printed line:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/site/public/llms.txt && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "chore(site): llms.txt citation count after the follow-ups release-1 export and the SAM answers stored since 916ae88e (143,841 -> <N>: +<WAVE_D> 0390DOM, +<SAM_D> SAM registrations)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 2: Build, W4 and vitest at HEAD**

Run Task 22c's fingerprint check first. Port 4173 must be free:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fu-logs" && cd site
NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build > "$L/release-site-build.log" 2>&1; echo "build exit=$?"
NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run verify > "$L/release-site-verify.log" 2>&1; echo "verify exit=$?"; grep -E "^overall:" "$L/release-site-verify.log"
npm test > "$L/release-site-vitest.log" 2>&1; echo "vitest exit=$?"
cd .. && git -C .. status --porcelain -- GovBudget | grep -v '^??'; uv run --project . python -c "import json; print(json.load(open('site/out/.build-meta.json'))['git_head'])"; git rev-parse HEAD
grep -o '<loc>[^<]*</loc>' site/out/sitemap.xml | wc -l; ls site/out/json/budget-pdf-receipts
```
Expected: `build exit=0`, `verify exit=0`, `overall: PASS`, `vitest exit=0`; no tracked change (the rebuilt `llms.txt` equals the committed one); the two shas equal; `4350`; `v2`. A failure that cannot be cleared: the abort path (Task 22b).

- [ ] **Step 3: verify-phase5 (the full assembly, with verify-era-map a–h)**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -lt 23 ] || [ "$MIN" -gt 35 ]; then echo "WAIT: start between :23 and :35 (minute $MIN): verify-phase5 must finish before the next SAM tick"; exit 0; fi
L="${GOVBUDGET_PROOFS:?}/fu-logs" && S=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/sam/entities.parquet && S0=$(stat -f %m "$S") && T0=$(date +%s)
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data GOVBUDGET_PG_DSN=postgresql://localhost/govbudget NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com uv run --project . python -m govbudget verify-phase5 > "$L/release-verify-phase5.log" 2>&1; echo "exit=$?"; echo "runtime $(( $(date +%s) - T0 )) s, ended at minute $(date +%M)"; [ "$(stat -f %m "$S")" = "$S0" ] && echo "SAM parquet unchanged during verify-phase5" || echo "RE-RUN: the SAM parquet changed during verify-phase5"; grep -E "verify-era-map|gate eval|gate assembly|^verify-phase5:" "$L/release-verify-phase5.log" | tail -8
```
verify-phase5 runs every Python gate (`verify-phase5b1` about 4.5 minutes) and the paid 48-question eval, so it starts only early in the hour and checks that the SAM parquet did not change under it; record the runtime for release 2's window (Task 26b Step 1). Expected: `exit=0`; `runtime <s> s, ended at minute <m>` (the run must not have crossed :12–:22; if it did, the next line says whether the SAM job wrote meanwhile); `SAM parquet unchanged during verify-phase5`; the assembly lists `verify-era-map` PASS; `verify-phase5: PASS` with the eval score (`<x>/48`). Exit 2 (`BLOCKED`) is not a pass (ROADMAP #139): check that the API key reached the run (the `.env` link, Task 22a Step 5) and re-run. This runs the paid live eval (48 questions), as every release does. A failure that cannot be cleared: the abort path.

- [ ] **Step 4: Deploy dry run**

Run Task 22c's fingerprint check first. Then:

```bash
/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh --dry-run > /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-logs/release-deploy-dry.log 2>&1; echo "exit=$?"; grep -E "0/3|provenance:|untracked inputs|R2 pdfs|rollback tag|Dry run complete" /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-logs/release-deploy-dry.log
```
Expected: `exit=0`; `0/3  preflight`; `provenance:      OK — git_head matches HEAD; no tracked changes; no untracked build inputs`; `untracked inputs: none …`; the R2 PDF count; the would-be rollback tag; `Dry run complete — nothing was copied, uploaded or deployed.`

- [ ] **Step 5: ★ Owner go-ahead to deploy**

Tell the owner, filling `<…>` from `tmp/fu-release-counts.json`, `$L/p2b-report.json`, `$L/p1-content.txt` and `$L/release-verify-phase5.log`. The Q15 numbers come from the proof's own report, never from this text:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python -c "import json,sys; r=json.load(open(sys.argv[1]))['panel']; print({k: (v['programs'], v['of'], v['fy2024a_to_fy2026r_pct'], v['first_to_last_pct']) for k, v in sorted(r.items())})" "${GOVBUDGET_PROOFS:?}/fu-logs/p2b-report.json"
```
Expected: `{'a': (<A programs>, 1938, <A pct>, <A first-to-last>), 'b': (<B programs>, 1938, <B pct>, <B first-to-last>)}` — `(524, 1938, 9.34, 108.17)` and `(1063, 1938, -2.61, 103.71)` in the 2026-10-13 simulation (README decision 10). Then say:

"Ready to deploy the piece-1 follow-ups, release 1, at `<HEAD short sha>`. /years/ is now three files (the core is <core gzip> gzip bytes, under the 780,074 cap) and shows PB2017–PB2023 procurement: 14,985 more cells, each equal to the program page's point. /program/0390DOM/ is new (Chem Demilitarization - O&M; <e> points before PB2024 through batch B7); the Chem Demil RDT&E line stays an R-1 restatement of 0708081D + 0708083D with no page. Totals that move (PB2026, thousands): /programs/ universe 385,268,393 → 385,271,636 ($385.3B unchanged); flow chart Army 43,338,494 → 43,341,737 and A|0390D 210,039 → 213,282; not yet crosswalked 227,538,773 → 227,542,016 ($227.5B unchanged); coverage 77.9% unchanged; the 0390D account FY24A / FY25E / FY26R 1,002,560 / 754,762 / 210,039 → 1,089,964 / 775,507 / 213,282, the P-1's own total. The /years/ totals chart (Q15): its balanced panel grows from <A programs> to <B programs> of 1,938 programs and its FY2024A→FY2026R change turns from <A pct>% to <B pct>% (the caption's FY2015→FY2026 rise goes from <A first-to-last>% to <B first-to-last>%). On 2026-10-04 you were told 524 → 1,056 programs and +9.3% → about −2.5%; the measured panel is larger because the seven org-split rows (#207) now have their cells too. The export also publishes <SAM_D> SAM.gov registrations stored since 916ae88e (149 → <release companies_with_sam>). The 256 unread v1 receipt files leave the deploy. All gates green: verify-phase5 (eval <x>/48), 5b1, 5e, lineage, verify-era-map a–h, link coverage, npm verify, vitest. Deploy now?"

Wait for an explicit yes. No reply is not a yes; the wait has no time limit, and Step 6's fingerprint check catches a re-export that lands meanwhile. On a no: the abort path (Task 22b), then report.

- [ ] **Step 6: Deploy**

Run Task 22c's fingerprint check first; any `STOP`: do not deploy. Then, by absolute path from this worktree (never from the main checkout, which holds another session's uncommitted files):

```bash
/Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/scripts/launch/deploy.sh > /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-logs/release-deploy.log 2>&1; echo "exit=$?"; head -5 /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-logs/release-deploy.log; grep -E "rollback tag|Rollback copy made|years_matrix|Deploy complete" /Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-logs/release-deploy.log
```
Expected: `0/3  preflight` among the first lines; `exit=0`; `rollback tag:    <YYYY-MM-DDTHHMMSSZ>`; `Rollback copy made and checked: r2:govbudget-assets/rollback/<tag>/`; the live-asset probes of `/json/years_matrix.json`, `/json/years_matrix/decade.json` and `/json/years_matrix/detail.json`; `Deploy complete: …, site/out/ live, live assets verified.` Record the tag. A failure after the copy prints the tag again; never re-run without reading it (a re-run copies what R2 serves then). A deploy that fails after its R2 upload leaves production half-changed: tell the owner at once with the tag; the owner decides (spec §8). On the owner's yes to a rollback: LAUNCH.md's rollback (Vercel to the previous deployment, then `rclone copy --checksum r2:govbudget-assets/rollback/<tag>/data/ r2:govbudget-assets/data/` and the same for `citations/`, as `deploy.sh` printed them), then Task 22b's abort path A1, A2 and A3, in order, each with its SAM guard.

- [ ] **Step 7: Live checks**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
L="${GOVBUDGET_PROOFS:?}/fu-logs" && H=$(git rev-parse HEAD) && LIVE=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site
{
echo "build-meta head: $(curl -s https://fiscalreceipts.com/.build-meta.json | grep -c "\"git_head\": \"$H\"")"
for f in years_matrix.json years_matrix/decade.json years_matrix/detail.json; do curl -s "https://fiscalreceipts.com/json/$f" | uv run --project . python -c "import json,sys; d=json.load(sys.stdin); print('$f', d.get('schema_version'), d.get('build_id'))"; done
echo "v1 receipt 00.json: $(curl -s -o /dev/null -w '%{http_code}' https://fiscalreceipts.com/json/budget-pdf-receipts/00.json) | v2 000.json: $(curl -s -o /dev/null -w '%{http_code}' https://fiscalreceipts.com/json/budget-pdf-receipts/v2/000.json)"
echo "/program/0390DOM/: $(curl -s -o /dev/null -w '%{http_code}' https://fiscalreceipts.com/program/0390DOM/) | address sentence: $(curl -s https://fiscalreceipts.com/program/0390DOM/ | grep -c 'its address uses 0390DOM')"
echo "sitemap: $(curl -s https://fiscalreceipts.com/sitemap.xml | grep -o '<loc>[^<]*</loc>' | wc -l | tr -d ' ')"
curl -s https://fiscalreceipts.com/json-lite/search_quick.json | uv run --project . python -c "import json,sys; print('aliases', {x['id']: x['url'] for x in json.load(sys.stdin)['docs'] if x['id'] in ('alias:jassm', 'alias:c-130j')})"
echo "F-15 gloss: $(curl -s https://fiscalreceipts.com/families/f-15/ | grep -c 'the PB2026 F-15EX AP (F015EX) P-40')"
for f in data/p1_era_line_map.parquet data/budget_lines.parquet; do [ "$(curl -s "https://assets.fiscalreceipts.com/$f" | shasum -a 256 | cut -d' ' -f1)" = "$(shasum -a 256 "$LIVE/$f" | cut -d' ' -f1)" ] && echo "R2 $f = release export" || echo "R2 $f DIFFERS from the release export"; done
} 2>&1 | tee "$L/live-checks.txt"
cd site && node -e "import('./scripts/gates/yearsmatrix.mjs').then(async (m) => console.log('years load:', JSON.stringify(await m.probeYearsOpeningFetches('https://fiscalreceipts.com'))))" | tee -a "$L/live-checks.txt"
```
Expected, in order: `build-meta head: 1`; `years_matrix.json 2 <build_id>`, `years_matrix/decade.json 2 <same build_id>`, `years_matrix/detail.json 2 <same build_id>` (Task 13: every file carries `schema_version` 2 and the one `build_id`); `v1 receipt 00.json: 404 | v2 000.json: 200`; `/program/0390DOM/: 200 | address sentence: <n ≥ 1>`; `sitemap: 4350`; `aliases {'alias:jassm': '/program/0207325F/', 'alias:c-130j': '/program/0401132F/'}`; `F-15 gloss: <n ≥ 1>`; `R2 data/p1_era_line_map.parquet = release export` and `R2 data/budget_lines.parquet = release export`; `years load: {"requests":["/json/years_matrix.json"],"shards":"core","problem":null}` (Task 15's `probeYearsOpeningFetches`, gate leg k's probe: only the core on load; the lazy shards wait for a picker chip or an expanded row). A failed line: tell the owner at once with the rollback tag; the owner decides whether to roll back (spec §8). On a yes: LAUNCH.md's rollback (Vercel to the previous deployment, then R2 `data/` and `citations/` from the rollback tag, the commands `deploy.sh` printed), then Task 22b's abort path A1, A2 and A3, in order, each with its SAM guard — the live database and lake must not stay in the release's state under the rolled-back site.

Then one 0390DOM point and one era cell on /years/, from the release export:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python - <<'PY'
import json, urllib.request
site = "/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/site"
side = json.load(open(f"{site}/json/program_details/0390DOM.json"))
fid = next(p["fid"] for pts in side["decade_series"].values() for p in pts if p["edition"] <= 2023)
html = urllib.request.urlopen("https://fiscalreceipts.com/program/0390DOM/").read().decode()
print("0390DOM era point", fid, "on live page:", f'data-fact-id="{fid}"' in html)
side = json.load(open(f"{site}/json/program_details/F01500.json"))
fid = next(p["fid"] for p in side["decade_series"]["actuals"] if p["edition"] == 2017)
core = json.loads(urllib.request.urlopen("https://fiscalreceipts.com/json/years_matrix.json").read())
cells = [r["cells"].get("fy2015a") for o in core["orgs"] for r in o["programs"] if r["pe_bli"] == "F01500"]
print("F01500 FY2015 actuals on live /years/ core:", cells, "== sidecar", fid, ":", bool(cells) and cells[0] and cells[0]["fid"] == fid)
PY
```
Expected: `0390DOM era point <fid> on live page: True`; `F01500 FY2015 actuals on live /years/ core: [{'fid': '3bd9c921b2397209', 'v': 498314.0}] == sidecar 3bd9c921b2397209 : True` (piece 1's anchor point, now on /years/ too; FY2015 actuals is a default column, so it is in the core).
