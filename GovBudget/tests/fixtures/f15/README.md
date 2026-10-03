# F-15 identity fixtures

Spec: `docs/superpowers/specs/2026-10-02-era-procurement-history-design.md` §8 V5,
§9 S0, §6.2, §6.5. Captured once at S0; re-pinned only by the owner-approved F-15
correction (S5).

| File | Content | Written by |
|---|---|---|
| `history.json` | Byte copy of `data/site/json/f15_funding_history.json` at the pin | `scripts/era/capture_f15_fixtures.py` |
| `history.sha256` | Its sha256: 64 lowercase hex characters and a newline. `verify-era-map` leg f compares the live export to it | same |
| `builder_inputs.json.gz` | What `build_history` and `build_program_matrix` read: the F-15 member workbook rows, their `fct_decade_series` rows, the member fact IDs already in `budget_lines`, the 207 workbook-cell previews, and every derived citation with an F-15 workbook leaf among its inputs | same |
| `page_snapshot.json` | Normalized `/families/f-15/` page from a fresh site build at the pin | `site/scripts/f15-page-snapshot.mjs --out` |

`tests/test_f15_era_identity.py` rebuilds the history from `builder_inputs.json.gz`
with no lake and no `data/site`, and fails (never skips) when a file is missing.

## Re-pin (S5 only, after the owner approves the exact F-15 changes)

S5 does not write the live `data/site`. The S5 history is produced on a proof
clone of the S4 export, `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/s5`
(its `site/`, `duckdb/govbudget.duckdb` and `parquet/`, the `govbudget proof
snapshot` layout; plan Task 22 Step 12). The live export changes
only at the release (plan Task 23). Re-pin from the clone, never from the main lake.

History, sha pin and builder inputs, from `GovBudget/`, once the S5 history diff
check has passed (plan Task 22 Step 14). The `<S5 sha>` is the digest the
first command prints:

    P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
    shasum -a 256 $P/s5/site/json/f15_funding_history.json
    uv run --project . python scripts/era/capture_f15_fixtures.py \
      --site-dir $P/s5/site --duckdb $P/s5/duckdb/govbudget.duckdb \
      --out-dir tests/fixtures/f15 --expect-sha256 <S5 sha>

Page snapshot, from a fresh build against the same clone. From `GovBudget/`,
point the worktree's lake links at the clone, build, snapshot, then put the
links and the regenerated `llms.txt` back:

    P=/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs
    for d in site duckdb parquet; do ln -sfn $P/s5/$d data/$d; done
    (cd site && NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com npm run build \
      && node scripts/f15-page-snapshot.mjs out/families/f-15/index.html \
           --out ../tests/fixtures/f15/page_snapshot.json)
    for d in site duckdb parquet; do ln -sfn /Users/andeslee/Documents/Cursor-Projects/GovBudget/data/$d data/$d; done
    git checkout -- site/public/llms.txt

Do not set `GOVBUDGET_DATA` to the main lake for a re-pin: its `data/site` keeps
the pre-release export until the release. Never capture from the main checkout's
`site/out` (it can be a stale build).
