<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G4 (2026-10-13). Runs after 04a. -->

### Task 4b: Era-map guards — `ratify`, and the one build after a decision change (#198)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §6.2 "ratify" (reads `chains.csv` only when a row names a successor; collects every error per row; tests for its untested branches — ROADMAP #198 lists successor only on history_only, lake-side drift, no-such-chain, holds-no-key, missing columns, integers, CLI exit codes), rule 4(b) through the shared `_org_grain_clashes` (§6.2 "propose": extracted from ratify `:1595-1613`; #198: the ratify check "is order-dependent (only the second org's same_program is refused)"), and "Build order" (write the one-invocation build into ratify's success message; prove in scratch that a map-only build fails conservation and the single invocation passes). Appendix A's note on Task 22: "§6.2 sets the rule that order must meet (a map-only build fails conservation; Task 4 proves in scratch which build passes)".

**Files:**
- Modify: `src/govbudget/jbooks/era_map.py` — `ratify` (its docstring's last line; the `stated = …` line; the per-row loop from `    errors: list[str] = []` through the `new.append(seed_row(` call; the overlap/clash loop after it)
- Modify: `src/govbudget/cli.py` — `cmd_era_map`'s ratify success print (anchor on `print(f"era-map ratify: {n} decision row(s) added as R-DEC-ERA-{args.batch}"`)
- Test: `tests/jbooks/test_era_map_ratify.py` (imports, about lines 4–12; append at the end)
- Local only: `/Users/andeslee/Documents/Cursor-Projects/GovBudget/.proofs/fu-t4b-buildorder/` (Step 6's scratch dbt project and two DuckDB clones; removed at the end of the step)

**Interfaces:**
Consumes: Task 4a's `_org_grain_clashes`, `_clash_message`, `write_csv` (atomic).
Produces (Task 10 ratifies B7 through it; Tasks 21 and 22 run the build it names):
- `ratify(*, review_csv, seed_path, batch, decided_on, duckdb_path) -> int` — same signature. It reports every error of every row in one `ValueError("era-map ratify refused; nothing written:\n  …")`; it reads `chains.csv` only when a decided row names a `successor_code`; a rule-4(b) clash is reported once per pair, as `_clash_message(a, b, …)` with `a` the earlier row in seed-then-batch order, so both organizations are named.
- `govbudget era-map ratify` prints a second line on success: `era-map ratify: next, ONE build: uv run --project . dbt build --project-dir dbt --profiles-dir dbt --select p1_era_code_decisions p1_era_line_map fct_program_decade_series (a map-only build fails assert_program_decade_conservation)`. Task 8 adds `p1_route_safe_codes` to that selection (and to this task's test pin), because from Task 8 on `p1_era_line_map` reads that seed; Task 10 quotes the amended line.
- The proof (Step 6) that one `dbt build --select p1_era_code_decisions p1_era_line_map fct_program_decade_series` after a decision change passes, while `--select p1_era_code_decisions p1_era_line_map` alone fails `assert_program_decade_conservation`. Task 22's B7 sequence must include a build of all three in one invocation (or end with one); see the README's Contract Notes, G4-2, and Binding Cross-Task Decision 3.

Measured for this task (2026-10-13, outside :12–:22): on two APFS clones of the live `govbudget.duckdb` (23,080,960 B), with a scratch copy of `dbt/` whose seed row `000042|3020F||2017-2023` (R-DEC-ERA-B5) was flipped from `same_program` to `history_only`: `dbt build --select p1_era_code_decisions p1_era_line_map` exited 1 with `20 of 20 FAIL 21 assert_program_decade_conservation` and `Done. PASS=19 WARN=0 ERROR=1 SKIP=0 NO-OP=0 TOTAL=20`; `dbt build --select p1_era_code_decisions p1_era_line_map fct_program_decade_series` on the other clone exited 0 with `23 of 35 PASS assert_program_decade_conservation` and `Done. PASS=35 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=35`. Both ran in under 10 s. In the miniature world (`tests/jbooks/era_map_fixtures.py`), chain `1045|1612N|` holds one key (PB2022), `10|0300D|TJS` is class-ruled `10|0300D|TJS|2022-2023` and `10|0300D|DPAA` is reviewed as `10|0300D|DPAA|2022-2022`. `tests/jbooks/test_era_map_ratify.py`: 29 passed after Task 4a.

- [ ] **Step 1: Write the failing tests**

In `tests/jbooks/test_era_map_ratify.py`, replace:

```python
import csv
from datetime import date
from pathlib import Path
```

with:

```python
import csv
import re
from datetime import date
from pathlib import Path
```

Append at the end of `tests/jbooks/test_era_map_ratify.py`:

```python


# ---------------------------------------------------------------------------
# ROADMAP #198 (follow-ups spec 2026-10-04 §6.2): ratify
# ---------------------------------------------------------------------------

def test_ratify_reads_chains_csv_only_for_a_successor(world):
    decide(world, GOOD, SPLIT)
    (world["out"] / "chains.csv").unlink()
    assert ratify(world) == 5


def test_ratify_reports_every_error_of_a_row(world):
    decide(world, {"1045|1612N|": {"decision": "same", "first_edition": "2017"}})
    with pytest.raises(ValueError) as exc:
        ratify(world)
    message = str(exc.value)
    assert "1045|1612N|: decision 'same' not in" in message
    assert "1045|1612N|: range 2017-2022 outside the chain (2022-2022)" in message


def test_ratify_names_both_organizations_of_a_clash(clash_world):
    decide(clash_world, {"10|0300D|DPAA": {"decision": "same_program"}})
    with pytest.raises(ValueError) as exc:
        ratify(clash_world)
    assert [ln for ln in str(exc.value).splitlines() if "collides with" in ln] == [
        "  10|0300D|TJS|2022-2023: same_program collides with 10|0300D|DPAA|2022-2022 — page 10"
        " would sum TJS and DPAA in PB2022; decide history_only for the organization whose"
        " page it is not"]


@pytest.mark.parametrize("edits, extra, message", [
    ({}, [("1045|1612N|", {"chain_id": "NOPE|3010F|", "decision": "same_program"})],
     "NOPE|3010F|: no such chain in the lake"),
    ({"1045|1612N|": {"decision": "same_program", "first_edition": "20x2"}}, [],
     "1045|1612N|: first/last edition must be integers"),
    ({"50|0300D|": {"decision": "exclude_reused_code", "successor_code": "5731D15610"}}, [],
     "50|0300D|: successor_code only on history_only rows"),
])
def test_ratify_refuses_the_branches_piece_1_left_untested(world, edits, extra, message):
    decide(world, edits, extra)
    before = world["seed"].read_bytes()
    with pytest.raises(ValueError, match=re.escape(message)):
        ratify(world)
    assert world["seed"].read_bytes() == before


def test_ratify_refuses_a_range_that_holds_no_key(tmp_path):
    # chain 50|0300D| with keys in PB2020, PB2022 and PB2023: PB2021 holds none
    gap = ("P-1", "2020", "0300D", "Acct", "WHS", "01", "BA", "0300D-WHS-L50",
           "Indian Financing Act", "fy_2018_actuals", "0", "22", "Exhibit P-1", "O50", "50")
    db = make_lake(tmp_path / "lake", extra_era=[gap])
    out = tmp_path / "research" / "era_map"
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    era_map.propose(duckdb_path=db, raw_docs_dir=make_raw_docs(tmp_path), out_dir=out,
                    seed_path=seed, decided_on=ON)
    gap_world = {"db": db, "out": out, "seed": seed, "review": out / "review.csv"}
    decide(gap_world, {"50|0300D|": {"decision": "history_only", "first_edition": "2021",
                                     "last_edition": "2021"}})
    with pytest.raises(ValueError, match=re.escape("50|0300D|: range 2021-2021 holds no era key")):
        ratify(gap_world)


def test_ratify_refuses_a_chain_the_lake_changed_after_review(world, tmp_path):
    decide(world, GOOD, SPLIT)
    later = ("P-1", "2023", "1612N", "Acct", "NAVY", "01", "BA", "1612N-NAVY-L4",
             "OHIO Replacement Submarine", "fy_2021_actuals", "0", "23", "Exhibit P-1", "O4",
             "1045")
    drifted = make_lake(tmp_path / "drifted", extra_era=[later])
    before = world["seed"].read_bytes()
    with pytest.raises(ValueError,
                       match=re.escape("1045|1612N|: keys_sha256 changed since review")):
        era_map.ratify(review_csv=world["review"], seed_path=world["seed"], batch="B1",
                       decided_on=DECIDED, duckdb_path=drifted)
    assert world["seed"].read_bytes() == before


def test_ratify_refuses_a_review_file_missing_a_column(world):
    decide(world, GOOD, SPLIT)
    rows = read(world["review"])
    era_map.write_csv(world["review"], [c for c in era_map.REVIEW_COLUMNS if c != "note"], rows)
    with pytest.raises(ValueError, match=r"missing columns \['note'\]"):
        ratify(world)


def test_cli_ratify_names_the_one_build_that_keeps_conservation(cli_world, capsys):
    from govbudget.cli import main

    main(["era-map", "propose"])
    decide({"review": cli_world / "data" / "research" / "era_map" / "review.csv"}, GOOD, SPLIT)
    capsys.readouterr()
    main(["era-map", "ratify", "--batch", "B1", "--decided-on", "2026-10-05"])
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("era-map ratify: 5 decision row(s) added as R-DEC-ERA-B1")
    assert out[1] == (
        "era-map ratify: next, ONE build: uv run --project . dbt build --project-dir dbt"
        " --profiles-dir dbt --select p1_era_code_decisions p1_era_line_map"
        " fct_program_decade_series (a map-only build fails"
        " assert_program_decade_conservation)")
```

Run:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_era_map_ratify.py -q 2>&1 | tail -3
```

Expected: `4 failed, 35 passed` (39 tests). The failures: the `chains.csv` test (`FileNotFoundError`), the every-error test (only the first error is reported), the clash test (today's line names DPAA first: `10|0300D|DPAA|2022-2022: same_program collides with 10|0300D|TJS|2022-2023 — … sum DPAA and TJS …`), and the CLI test (`IndexError: list index out of range`). The other new tests pass already: they pin branches #198 found untested.

- [ ] **Step 2: Read `chains.csv` lazily and collect every error per row**

In `src/govbudget/jbooks/era_map.py` (`ratify`), replace:

```python
    stated = {r["chain_id"]: r for r in read_csv(review_csv.parent / "chains.csv")}
```

with:

```python
    # chains.csv is read only when a decided row names a successor (ROADMAP #198)
    stated: dict[str, dict] | None = None
```

Replace the per-row loop — from:

```python
    errors: list[str] = []
    new: list[dict] = []
    for r in decided:
        cid = r["chain_id"]
        decision = r["decision"].strip()
        ch = by_id.get(cid)
        if ch is None:
            errors.append(f"{cid}: no such chain in the lake")
            continue
        if r["keys_sha256"] != ch.keys_sha256:
            errors.append(f"{cid}: keys_sha256 changed since review"
                          f" ({r['keys_sha256'][:12]} -> {ch.keys_sha256[:12]});"
                          " re-run propose and re-review")
            continue
        if decision not in DECISIONS:
            errors.append(f"{cid}: decision {decision!r} not in {DECISIONS}")
            continue
```

through:

```python
            successor = {f: book[f] for f in
                         ("successor_code", "successor_account", "successor_evidence")}
        new.append(seed_row(
```

— with:

```python
    errors: list[str] = []
    new: list[dict] = []
    for r in decided:
        cid = r["chain_id"]
        decision = r["decision"].strip()
        ch = by_id.get(cid)
        if ch is None:
            errors.append(f"{cid}: no such chain in the lake")
            continue
        if r["keys_sha256"] != ch.keys_sha256:
            # everything below reads the chain as it was reviewed
            errors.append(f"{cid}: keys_sha256 changed since review"
                          f" ({r['keys_sha256'][:12]} -> {ch.keys_sha256[:12]});"
                          " re-run propose and re-review")
            continue
        # Every independent check runs, so one refusal lists all of a row's
        # problems, not only the first (ROADMAP #198).
        row_errors: list[str] = []
        if decision not in DECISIONS:
            row_errors.append(f"{cid}: decision {decision!r} not in {DECISIONS}")
        first = last = None
        try:
            first, last = int(r["first_edition"]), int(r["last_edition"])
        except ValueError:
            row_errors.append(f"{cid}: first/last edition must be integers")
        n_keys, sha = 0, ""
        if first is not None:
            if not (ch.first_edition <= first <= last <= ch.last_edition):
                row_errors.append(f"{cid}: range {first}-{last} outside the chain"
                                  f" ({ch.first_edition}-{ch.last_edition})")
            else:
                n_keys, sha = range_sha(keys_by_chain[cid], first, last)
                if n_keys == 0:
                    row_errors.append(f"{cid}: range {first}-{last} holds no era key")
        pa, po = r["program_account"].strip(), r["program_org"].strip()
        pinned = (ch.line_item_code in inputs.collision_codes
                  and decision in ("same_program", "history_only"))
        if pinned:
            ident = (ch.line_item_code, pa, po)
            if not pa or not po:
                row_errors.append(f"{cid}: collision code — program_account and"
                                  " program_org are required")
            elif decision == "same_program" and ident not in inputs.modern_pages:
                row_errors.append(f"{cid}: {ident} is not a PB2026 page")
            elif decision == "history_only":
                own = {(k.account, _modern_org(k.organization))
                       for k in keys_by_chain[cid]}
                if ident not in line_idents and (pa, po) not in own:
                    row_errors.append(f"{cid}: {ident} is not a PB2024-26 P-1 line or"
                                      f" the chain's own identity {sorted(own)}")
        elif pa or po:
            row_errors.append(f"{cid}: program_account/program_org are only set for"
                              " collision-code same_program/history_only rows")
        successor: dict[str, str] = {}
        succ = r["successor_code"].strip()
        if succ:
            if decision != "history_only":
                row_errors.append(f"{cid}: successor_code only on history_only rows")
            else:
                if stated is None:
                    stated = {s["chain_id"]: s
                              for s in read_csv(review_csv.parent / "chains.csv")}
                book = stated.get(cid, {})
                if book.get("successor_code") != succ:
                    row_errors.append(
                        f"{cid}: successor {succ!r} is not the book-stated"
                        f" successor {book.get('successor_code') or '(none)'!r}")
                else:
                    successor = {f: book[f] for f in
                                 ("successor_code", "successor_account", "successor_evidence")}
        if row_errors:
            errors.extend(row_errors)
            continue
        new.append(seed_row(
```

(The `new.append(seed_row(` call and its arguments after it stay as they are.)

- [ ] **Step 3: Rule 4(b) through the shared helper, both sides named**

Replace:

```python
    cc = inputs.collision_codes
    for i, a in enumerate(new):
        for b in existing + new[:i]:
            if _ranges_overlap(a, b):
                errors.append(f"{a['decision_id']} overlaps {b['decision_id']}")
            if (a["decision"] == b["decision"] == "same_program"
                    and a["organization"] and b["organization"]
                    and a["organization"] != b["organization"]
                    and _page_grain(a, cc) == _page_grain(b, cc)):
                shared = sorted(_row_editions(a, keys_by_chain)
                                & _row_editions(b, keys_by_chain))
                if shared:
                    code, pin_a, pin_o = _page_grain(a, cc)
                    page = f"{code} ({pin_a}/{pin_o})" if pin_o else code
                    errors.append(
                        f"{a['decision_id']}: same_program collides with"
                        f" {b['decision_id']} — page {page} would"
                        f" sum {a['organization']} and {b['organization']} in"
                        f" {', '.join(f'PB{e}' for e in shared)}; decide"
                        " history_only for the organization whose page it is not")
```

with:

```python
    cc = inputs.collision_codes
    for i, a in enumerate(new):
        for b in existing + new[:i]:
            if _ranges_overlap(a, b):
                errors.append(f"{a['decision_id']} overlaps {b['decision_id']}")
    # Rule 4(b) over the whole seed-to-be, reported once per pair with both
    # organizations named, whichever came first (ROADMAP #198; propose runs
    # the same _org_grain_clashes on class-ruled rows).
    new_ids = {r["decision_id"] for r in new}
    for a, b, shared in _org_grain_clashes(existing + new, keys_by_chain, cc):
        if a["decision_id"] in new_ids or b["decision_id"] in new_ids:
            errors.append(_clash_message(a, b, shared, cc))
```

And in `ratify`'s docstring replace:

```python
        ranges, or leave its decision blank (defer it) until it is.
    Returns the number of rows added."""
```

with:

```python
        ranges, or leave its decision blank (defer it) until it is.
    Every error of every row is reported at once (ROADMAP #198); chains.csv
    is read only when a row names a successor. Returns the number of rows
    added."""
```

- [ ] **Step 4: Name the one build in the CLI's success message**

In `src/govbudget/cli.py`, replace:

```python
        print(f"era-map ratify: {n} decision row(s) added as R-DEC-ERA-{args.batch}"
              f" -> {seed_path}")
```

with:

```python
        print(f"era-map ratify: {n} decision row(s) added as R-DEC-ERA-{args.batch}"
              f" -> {seed_path}")
        # ROADMAP #198, follow-ups spec §6.2 (proved in plan Task 4b): a
        # map-only build fails assert_program_decade_conservation until the
        # program table is rebuilt; one invocation builds the seed, the map
        # and the program table in DAG order and tests after all three.
        print("era-map ratify: next, ONE build: uv run --project . dbt build --project-dir dbt"
              " --profiles-dir dbt --select p1_era_code_decisions p1_era_line_map"
              " fct_program_decade_series (a map-only build fails"
              " assert_program_decade_conservation)")
```

- [ ] **Step 5: Run the tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_era_map_ratify.py tests/jbooks/test_era_map_propose.py tests/test_era_review_batch_page.py -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/jbooks/era_map.py | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/cli.py | grep '^Found'
```

Expected: `114 passed` (39 + 34 + 41); `All checks passed!`; `Found 5 errors.` (the `cli.py` HEAD baseline).

- [ ] **Step 6: Prove the build order in scratch**

Read-only on the live lake (two APFS clones of the DuckDB file and a copy of `dbt/`; the views keep reading the live parquet read-only). Nothing outside `.proofs/fu-t4b-buildorder/` is written, and the directory is removed at the end.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
SCR="${GOVBUDGET_PROOFS:?}/fu-t4b-buildorder"
rm -rf "${SCR:?}" && mkdir -p "$SCR"
test -e "$GOVBUDGET_DUCKDB.wal" && { echo "a DuckDB write is unfinished; retry later"; exit 1; }
cp -c "$GOVBUDGET_DUCKDB" "$SCR/map-only.duckdb" && cp -c "$GOVBUDGET_DUCKDB" "$SCR/single.duckdb"
cp -R dbt "$SCR/dbt" && rm -rf "$SCR/dbt/target" "$SCR/dbt/logs" "$SCR/dbt/.user.yml"
# one owner decision changes (B5's 000042|3020F|, same_program -> history_only), as a correction batch would
sed -i '' 's/^\(000042|3020F||2017-2023,000042,3020F,,2017,2023,\)same_program,/\1history_only,/' "$SCR/dbt/seeds/p1_era_code_decisions.csv"
diff dbt/seeds/p1_era_code_decisions.csv "$SCR/dbt/seeds/p1_era_code_decisions.csv" | grep -c '^[<>]'
GOVBUDGET_DUCKDB="$SCR/map-only.duckdb" uv run --project . dbt build --project-dir "$SCR/dbt" --profiles-dir "$SCR/dbt" --select p1_era_code_decisions p1_era_line_map > "$SCR/map-only.log" 2>&1; echo "map-only exit=$?"
sed 's/\x1b\[[0-9;]*m//g' "$SCR/map-only.log" | grep -E 'FAIL [0-9]+ assert_program_decade_conservation|Done\. PASS'
GOVBUDGET_DUCKDB="$SCR/single.duckdb" uv run --project . dbt build --project-dir "$SCR/dbt" --profiles-dir "$SCR/dbt" --select p1_era_code_decisions p1_era_line_map fct_program_decade_series > "$SCR/single.log" 2>&1; echo "single exit=$?"
sed 's/\x1b\[[0-9;]*m//g' "$SCR/single.log" | grep -E 'PASS assert_program_decade_conservation|Done\. PASS'
rm -rf "${SCR:?}"
```

Expected (measured 2026-10-13 on the HEAD `dbt/`; the counts grow if Task 9 has added tests, the verdicts do not change):

```
2
map-only exit=1
… 20 of 20 FAIL 21 assert_program_decade_conservation .... [FAIL 21 in …s]
… Done. PASS=19 WARN=0 ERROR=1 SKIP=0 NO-OP=0 TOTAL=20
single exit=0
… 23 of 35 PASS assert_program_decade_conservation .... [PASS in …s]
… Done. PASS=35 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=35
```

If the map-only build passes, or the single build fails, stop: the message added in Step 4 would be wrong.

- [ ] **Step 7: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/jbooks/era_map.py GovBudget/src/govbudget/cli.py GovBudget/tests/jbooks/test_era_map_ratify.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(era-map): ratify reports every error, reads chains.csv only for a successor, names both sides of a rule-4(b) clash; the success message names the one build that keeps conservation (#198)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `3 files changed`.
