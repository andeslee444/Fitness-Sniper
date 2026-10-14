<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G4 (2026-10-13). -->

### Task 3: P-1 loader tripwires (#202)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §6.3: after `sums`, raise `P1KeyConflict(ValueError)` when two groups share an upsert key (account, organization, budget activity, pe_bli, **amount_type**; exhibit and fiscal year are fixed per parse), measured at 0 collisions across the 20 workbooks, while the four-part key without `amount_type` has one live case (PB2026 `3022F`/`F`/`03`/`SFV000`) that must keep loading; test a real modern P-1 shape for `line_item_code == pe_bli`; add the classified-title tripwire test; fix the comment at `p1_loader.py:183-186` and the S1b date at `crosswalk.py:424`. Lands before §4.3 (Task 6).

**Files:**
- Modify: `src/govbudget/jbooks/p1_loader.py` — new class before `def _slug(header: str) -> str:`; the grouping comment (anchor on `# key matches the DB unique constraint grain:`, about lines 183–186); the tripwire after the `EraKeyConflict` raise (anchor on `    if skipped_invalid:\n        logger.info(`)
- Modify: `src/govbudget/jbooks/crosswalk.py` — the `EMPTY_ORG` comment (anchor on `S1b loaded the seven PB2017-PB2023 P-1 Classified Programs lines, 2026-10-02)`, about line 424)
- Test: `tests/jbooks/test_p1_loader.py` (the import line, about line 7; append at the end)
- Test: `tests/jbooks/test_p1_loader_era.py` (the import block, about lines 18–25; append at the end)

**Interfaces:**
Consumes: Task 1's workspace.
Produces (Task 6 builds the alias and the R-1 restatement rule on top of this parse; Task 7's `s194_chem_demil.py --check` parses PB2024–PB2026 with it):
- `class P1KeyConflict(ValueError)` in `govbudget.jbooks.p1_loader`, defined just before `_slug`.
- `parse_p1_rollup(...)` raises `P1KeyConflict` with the message `"<file> (<exhibit> PB<year>): <n> upsert key(s) (account, organization, budget activity, pe_bli, amount_type) hold more than one (account title, budget activity title, title): <account>/<organization>/<ba>/<pe_bli>/<amount_type>: titles […]; …"` (at most five keys listed), after the `EraKeyConflict` check and before the `skipped_invalid` log. `load_p1_rollup` and `jbooks load-rollups` therefore refuse such a workbook before writing anything.

Measured for this task (2026-10-13, read-only on `data/raw_docs`, outside :12–:22): `parse_p1_rollup` over all 20 P-1 and P-1R display workbooks (`data/raw_docs/fy2017…fy2026/dod/{p1,p1r}_display.xlsx`) with a scratch census grouping parsed rows by the five-part key and by the four-part key: five-part collisions 0 in every workbook; four-part collisions 1 in all (PB2026 P-1, `('3022F', 'F', '03', 'SFV000')`, titles "USSF Vehicles" and "USSF Replacement Vehicles"). Row counts: PB2017 P-1 6,832 / P-1R 3,080 · PB2018 13,468 / 3,055 · PB2019 12,948 / 3,289 · PB2020 8,838 / 2,169 · PB2021 10,120 / 2,300 · PB2022 3,000 / 651 · PB2023 2,925 / 582 · PB2024 4,575 / 582 · PB2025 2,426 / 450 · PB2026 3,163 / 403; `skipped_invalid` is 2 in each of PB2024–PB2026 P-1 (the 0390D `O&M`/`RDT&E` rows) and 0 elsewhere. `tests/jbooks/test_p1_loader.py` 12 passed, `tests/jbooks/test_p1_loader_era.py` 12 passed. The modern-P-1 test today covers P-1R only (`test_modern_and_p1r_rows_carry_pe_bli_as_code` builds an `Exhibit P-1R` sheet). The S1b live write ran 2026-10-03 (`docs/superpowers/reviews/families-s1b-proof.md`, "Summary (2026-10-03)").

- [ ] **Step 1: Write the failing tests**

In `tests/jbooks/test_p1_loader.py`, replace:

```python
from govbudget.jbooks.p1_loader import load_p1_rollup
```

with:

```python
import pytest

from govbudget.jbooks.p1_loader import P1KeyConflict, load_p1_rollup, parse_p1_rollup
```

Append at the end of `tests/jbooks/test_p1_loader.py`:

```python


# ---------------------------------------------------------------------------
# ROADMAP #202 (follow-ups spec 2026-10-04 §6.3): the upsert-key tripwire and
# a real modern P-1 shape
# ---------------------------------------------------------------------------

def _sfv_row(title, fy24, fy25, fy26):
    """The live PB2026 Space Force shape (3022F / F / 03 / SFV000)."""
    return ["3022F", "Procurement, Space Force", "F", "03", "Ground Vehicular Equipment",
            "12", "1", "Ground", "SFV000", title, "A", "Weapon System Cost", "Add",
            "", fy24, "", fy25, "", fy26, "U"]


def _modern_xlsx(tmp_path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Exhibit P-1"
    ws.append(P1_HEADERS)
    for r in rows:
        ws.append(r)
    p = tmp_path / "p1_display.xlsx"
    wb.save(p)
    return p


def test_modern_p1_rows_carry_their_budget_line_item_as_code(tmp_path):
    """A modern P-1 (Budget Line Item + Add/Non-Add) keeps the printed BLI as
    line_item_code; only era P-1 workbooks key rows by line number."""
    parsed = parse_p1_rollup(make_p1_xlsx(tmp_path), exhibit="P-1", fiscal_year=2026)
    assert parsed.era_line_keying is False
    assert len(parsed.rows) == 3
    assert {(r.pe_bli, r.line_item_code) for r in parsed.rows} == {("7001SA1000", "7001SA1000")}


def test_two_titles_on_one_upsert_key_raise(tmp_path):
    rows = [_sfv_row("USSF Vehicles", 100, "", ""),
            _sfv_row("USSF Replacement Vehicles", 7, "", "")]
    with pytest.raises(P1KeyConflict, match=r"1 upsert key\(s\).*3022F/F/03/SFV000/fy_2024_actuals"):
        parse_p1_rollup(_modern_xlsx(tmp_path, rows), exhibit="P-1", fiscal_year=2026)


def test_two_titles_on_disjoint_amount_columns_load_both(tmp_path):
    # The live PB2026 case: one title per amount column, so no upsert key is
    # written twice and nothing is lost. The four-part key without
    # amount_type would wrongly refuse this workbook.
    rows = [_sfv_row("USSF Vehicles", 100, 90, ""),
            _sfv_row("USSF Replacement Vehicles", "", "", 80)]
    parsed = parse_p1_rollup(_modern_xlsx(tmp_path, rows), exhibit="P-1", fiscal_year=2026)
    assert sorted((r.title, r.amount_type, r.amount_thousands) for r in parsed.rows) == [
        ("USSF Replacement Vehicles", "fy_2026_disc_request", Decimal("80")),
        ("USSF Vehicles", "fy_2024_actuals", Decimal("100")),
        ("USSF Vehicles", "fy_2025_enacted", Decimal("90")),
    ]
```

In `tests/jbooks/test_p1_loader_era.py`, replace:

```python
from govbudget.jbooks.p1_loader import (
    EraKeyConflict,
    P1Parse,
    P1Row,
    load_p1_rollup,
    parse_p1_rollup,
    write_p1_rows,
)
```

with:

```python
from govbudget.jbooks.p1_loader import (
    EraKeyConflict,
    P1KeyConflict,
    P1Parse,
    P1Row,
    load_p1_rollup,
    parse_p1_rollup,
    write_p1_rows,
)
```

Append at the end of `tests/jbooks/test_p1_loader_era.py`:

```python


def test_two_classified_titles_in_one_account_and_budget_activity_raise(tmp_path):
    """ROADMAP #202: two Classified Programs rows with different titles in
    one (account, budget activity) share the upsert key (organization '',
    code 9999999999); the S1 script caught it, `jbooks load-rollups` kept
    the last. The parse now refuses."""
    other = _row(OPAF, "", "04", "Other Base Maintenance and Support Equip", "",
                 "9999999999", "Classified Programs (Space)", "", "Add", 5, 6)
    with pytest.raises(P1KeyConflict, match=r"3080F//04/9999999999/fy_2019_base_oco"):
        parse_p1_rollup(make_era_xlsx(tmp_path, [CLASSIFIED, other]),
                        exhibit="P-1", fiscal_year=2021)
```

Run:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_p1_loader.py tests/jbooks/test_p1_loader_era.py -q 2>&1 | tail -4
```

Expected: `2 errors` during collection, each `ImportError: cannot import name 'P1KeyConflict' from 'govbudget.jbooks.p1_loader'`.

- [ ] **Step 2: Add the exception**

In `src/govbudget/jbooks/p1_loader.py`, replace:

```python
def _slug(header: str) -> str:
```

with:

```python
class P1KeyConflict(ValueError):
    """Two parsed groups that differ only in a title (account title, budget
    activity title or line title) share one budget_lines upsert key
    (exhibit, fiscal_year, account, organization, budget_activity, pe_bli,
    amount_type; exhibit and fiscal year are fixed per parse). Both would
    upsert into one row and the last write would win, so the parse refuses
    (ROADMAP #202)."""


def _slug(header: str) -> str:
```

Run the two files again; the tests now collect, and the tripwire tests fail for their own reason:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_p1_loader.py tests/jbooks/test_p1_loader_era.py -q 2>&1 | tail -4
```

Expected: `2 failed, 26 passed`. The two failures are the tripwire tests, `test_two_titles_on_one_upsert_key_raise` and `test_two_classified_titles_in_one_account_and_budget_activity_raise`, each `Failed: DID NOT RAISE <class 'govbudget.jbooks.p1_loader.P1KeyConflict'>`: the exception exists, the check does not yet (Step 4). The other two new tests pass already at HEAD's parse, because they pin behaviour that is right today (G4-3): `test_modern_p1_rows_carry_their_budget_line_item_as_code` (a modern P-1 keeps its printed BLI as `line_item_code`) and `test_two_titles_on_disjoint_amount_columns_load_both` (the live PB2026 case, which Step 4's tripwire must keep loading).

- [ ] **Step 3: Correct the grouping comment**

Replace:

```python
    # key matches the DB unique constraint grain:
    # (account, account_title, organization, ba, ba_title, bli, title)
    # line_number is intentionally excluded so all cost-type sub-rows for the same
    # BLI aggregate into a single bucket before insert (avoiding last-write-wins collision).
```

with:

```python
    # Grouping key: (account, account_title, organization, ba, ba_title, bli,
    # title). It is NOT the DB upsert key, which holds no title: (exhibit,
    # fiscal_year, account, organization, budget_activity, pe_bli,
    # amount_type). The P1KeyConflict tripwire after the loop refuses two
    # groups that would upsert into one row (ROADMAP #202). line_number is
    # intentionally excluded so all cost-type sub-rows for the same BLI
    # aggregate into a single bucket before insert (avoiding last-write-wins
    # collision).
```

- [ ] **Step 4: Add the tripwire**

Replace:

```python
    if skipped_invalid:
        logger.info(
            "parse_p1_rollup(%s): skipped %d row(s) with an invalid/non-BLI"
```

with:

```python
    # ROADMAP #202: the grouping key holds three titles the upsert key does
    # not, so two groups can share one upsert key and the last write would
    # win. 0 cases in the 20 P-1/P-1R workbooks (measured 2026-10-13); the
    # key WITHOUT amount_type has one (PB2026 3022F/F/03/SFV000, two titles
    # on disjoint amount columns, nothing lost), so amount_type belongs in it.
    upsert_owner: dict[tuple, tuple] = {}
    key_clashes: dict[tuple, set[tuple]] = defaultdict(set)
    for key, amounts in sums.items():
        account, _a_title, organization, ba, _ba_title, pe_bli, _title = key
        for amount_type in amounts:
            upsert = (account, organization, ba, pe_bli, amount_type)
            first = upsert_owner.setdefault(upsert, key)
            if first != key:
                key_clashes[upsert] |= {first, key}
    if key_clashes:
        detail = "; ".join(
            f"{'/'.join('' if p is None else str(p) for p in upsert)}: titles"
            f" {sorted({(g[1], g[4], g[6]) for g in groups}, key=repr)}"
            for upsert, groups in sorted(key_clashes.items(), key=lambda kv: repr(kv[0]))[:5]
        )
        raise P1KeyConflict(
            f"{xlsx_path.name} ({exhibit} PB{fiscal_year}): {len(key_clashes)} upsert"
            " key(s) (account, organization, budget activity, pe_bli, amount_type) hold"
            f" more than one (account title, budget activity title, title): {detail}"
        )

    if skipped_invalid:
        logger.info(
            "parse_p1_rollup(%s): skipped %d row(s) with an invalid/non-BLI"
```

Also add one sentence to the `parse_p1_rollup` docstring. Replace:

```python
    Raises EraKeyConflict when an era key prints more than one code, title
    or budget activity across its Add rows.
    """
```

with:

```python
    Raises EraKeyConflict when an era key prints more than one code, title
    or budget activity across its Add rows, and P1KeyConflict when two
    groups would upsert into one budget_lines row (ROADMAP #202).
    """
```

- [ ] **Step 5: Correct the S1b date in `crosswalk.py`**

In `src/govbudget/jbooks/crosswalk.py`, replace:

```python
#: How an empty organization code prints in a refusal (20 live identities since
#: S1b loaded the seven PB2017-PB2023 P-1 Classified Programs lines, 2026-10-02).
```

with:

```python
#: How an empty organization code prints in a refusal (20 live identities since
#: S1b loaded the seven PB2017-PB2023 P-1 Classified Programs lines, 2026-10-03).
```

- [ ] **Step 6: Run the tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_p1_loader.py tests/jbooks/test_p1_loader_era.py tests/jbooks/test_s1_reload_era_p1.py tests/jbooks/test_era_keys.py -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/jbooks/p1_loader.py src/govbudget/jbooks/crosswalk.py | tail -1
grep -c 'Classified Programs lines, 2026-10-03)' src/govbudget/jbooks/crosswalk.py
```

Expected: `49 passed` (15 + 13 + 13 + 8); `All checks passed!`; `1`.

- [ ] **Step 7: Re-run the census over every real workbook (no refusal)**

Read-only on the live `raw_docs`.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python - <<'EOF'
from pathlib import Path
from govbudget import config
from govbudget.jbooks.p1_loader import P1KeyConflict, parse_p1_rollup

parsed = refused = rows = 0
for fy in range(2017, 2027):
    for name, exhibit in (("p1_display.xlsx", "P-1"), ("p1r_display.xlsx", "P-1R")):
        try:
            rows += len(parse_p1_rollup(Path(config.RAW_DOCS_DIR) / f"fy{fy}" / "dod" / name,
                                        exhibit=exhibit, fiscal_year=fy).rows)
            parsed += 1
        except P1KeyConflict as e:
            refused += 1
            print(f"REFUSED PB{fy} {exhibit}: {e}")
print(f"{parsed} workbooks parsed, {refused} refused, {rows:,} rows")
EOF
```

Expected: `20 workbooks parsed, 0 refused, 84,856 rows` (the sum of the 20 row counts above; live Postgres holds 84,872 P-1/P-1R rows, the 16 stale 0390D rows of Task 7 being the difference). A refusal means a workbook changed on disk since 2026-10-13: stop and report it.

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/jbooks/p1_loader.py GovBudget/src/govbudget/jbooks/crosswalk.py GovBudget/tests/jbooks/test_p1_loader.py GovBudget/tests/jbooks/test_p1_loader_era.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(jbooks): P1KeyConflict when two P-1 groups share a budget_lines upsert key; modern P-1 code test; comment and S1b date corrections (#202)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `4 files changed`.
