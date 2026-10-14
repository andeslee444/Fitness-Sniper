<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the approved design is ../../../specs/2026-10-04-families-piece1-followups-design.md. -->

### Task 9c: verify-era-map exits 2 on a bad `--legs`; leg a and leg b failure branches tested (#203)

Third part of Task 9 (after 9a and 9b).

**Spec:** design §6.4 (#203): "Tests for leg a's classified filter and its failure branches", "A bad `--legs` value
exits 2"; design §6 (one CLI convention for the tools this wave touches — `proof`, `link-coverage`,
`verify-era-map`, `review_batch_page`: a tool error prints `<tool>: ERROR — <message>` and exits 2, a failed check
still exits 1); ROADMAP #203's Task 14 list (wrong sha, wrong line number, non-era parse, multi-identity key, stale
build); §7 W1/W3.

**Files:**
- Modify: `src/govbudget/cli.py` (`cmd_verify_era_map`, :2432-2444)
- Modify: `src/govbudget/verify_era_map.py` (module docstring, :3-8)
- Modify: `tests/test_verify_era_map.py` (imports; tests inserted before `test_leg_a_fails_on_a_duplicated_map_row`,
  `test_leg_b_fails_on_an_unreadable_seed` and `test_cli_fails_with_exit_1`)

Line numbers are hints measured at `532205c9` (anchor on the quoted text; 9a moved the test file's later lines).

**Interfaces:**
Consumes: Task 9a's `tests/test_verify_era_map.py` (`Corpus`, `_rows_for`, `_write_workbook`, `_sha`, `pinned`; the map
fixture with `decided_on`); `verify_era_map.leg_a_workbooks`, `_printed_cells`, `run_verify_era_map` (raises
`ValueError("legs must be letters from …; got …")`); `govbudget.jbooks.p1_loader.parse_p1_rollup` and
`P1Parse`/`P1Row` (frozen dataclasses), `govbudget.jbooks.era_keys.is_era_procurement_key` (both imported inside
leg a at call time, so a test can patch the module attribute).
Produces: `govbudget verify-era-map --legs <bad>` prints exactly `verify-era-map: ERROR — <message>` as its last line
and exits 2 (no leg line, no traceback). `verify_phase5`'s assembly reads no PASS/FAIL/BLOCKED there and infers FAIL
from the exit code (`verify_phase5.py:1235-1239`). Task 11 extends the letters to `abcdefgh`; the new test matches the
message's prefix, so it holds then.

Leg a's branches are all live already; these tests plant each defect the leg exists for (#203 "failure branches are
untested"). Each one would fail if its branch were removed; the classified-filter test also carries its own negative
control (with the filter defeated the same workbook fails).

- [ ] **Step 1: Write the tests**

In `tests/test_verify_era_map.py` (:14-16), replace:

```python
import csv
import hashlib
from pathlib import Path
```

with:

```python
import csv
import dataclasses
import hashlib
from pathlib import Path
```

In `tests/test_verify_era_map.py` (:237, before `test_leg_a_fails_on_a_duplicated_map_row`), replace:

```python
def test_leg_a_fails_on_a_duplicated_map_row(corpus):
```

with:

```python
def _rewrite_workbook(corpus: Corpus, edition: int, rows: list[dict]) -> None:
    """Replace one edition's workbook with `rows` (sheet row = 3 + index), re-pin
    its sha, and point that edition's map rows at it."""
    old = corpus.site_dir / "workbooks" / f"{corpus.shas[edition]}.xlsx"
    tmp = corpus.site_dir.parent / f"p1_{edition}_rewritten.xlsx"
    _write_workbook(tmp, edition, rows)
    sha = _sha(tmp)
    old.unlink()
    tmp.rename(corpus.site_dir / "workbooks" / f"{sha}.xlsx")
    corpus.shas[edition] = sha
    for r in corpus.map_rows:
        if r["edition"] == edition:
            r["source_document_sha256"] = sha
    corpus.save()


def test_leg_a_skips_the_classified_programs_line(corpus, monkeypatch):
    """ROADMAP #203: leg a's classified-row filter had no test. An era
    workbook's Classified Programs line (blank Line Number, Line Item
    9999999999; S1b loads it under that code) is not an era key, so leg a
    neither looks for it in the map nor counts it. With the filter defeated
    the same workbook fails, so the filter is what passes it."""
    from govbudget.jbooks import era_keys

    classified = dict(account="3010F", org="AF", ba="07", line="", code="9999999999",
                      title="Classified Programs", add="Add", amount=1234)
    _rewrite_workbook(corpus, 2019, _rows_for(2019) + [classified])
    result = corpus.leg_a()
    assert result["ok"], _failures(result)
    assert result["detail"]["summary"].startswith("workbooks=7 keys_checked=32 expected=32")
    monkeypatch.setattr(era_keys, "is_era_procurement_key", lambda pe_bli: True)
    assert "2019/9999999999: in the workbook, missing from the map" in _failures(corpus.leg_a())


def test_leg_a_fails_when_the_map_cites_another_workbook(corpus):
    corpus.row(2021, "3010F-AF-L4")["source_document_sha256"] = "0" * 64
    corpus.save()
    assert (f"2021/3010F-AF-L4: map cites {'0' * 64}, not the pinned workbook"
            in _failures(corpus.leg_a()))


def test_leg_a_fails_when_a_cited_row_prints_another_line_number(corpus, monkeypatch):
    # Leg a re-reads the printed Line Number without the loader; a reader that
    # disagrees with the parse about a row's line is a FAIL.
    real = verify_era_map._printed_cells

    def shifted(path):
        printed, code_col = real(path)
        if path.name == f"{corpus.shas[2019]}.xlsx":
            _line, code, title = printed[7]
            printed[7] = ("2", code, title)
        return printed, code_col

    monkeypatch.setattr(verify_era_map, "_printed_cells", shifted)
    assert "2019/2031A-ARMY-L1: row 7 line number '2' is not the key's line" in _failures(corpus.leg_a())


def _wrap_parse(monkeypatch, edition, change):
    from govbudget.jbooks import p1_loader

    real = p1_loader.parse_p1_rollup

    def wrapped(path, *, exhibit, fiscal_year):
        parse = real(path, exhibit=exhibit, fiscal_year=fiscal_year)
        return change(parse) if fiscal_year == edition else parse

    monkeypatch.setattr(p1_loader, "parse_p1_rollup", wrapped)


def test_leg_a_fails_on_a_parse_without_era_line_keying(corpus, monkeypatch):
    _wrap_parse(monkeypatch, 2020, lambda parse: dataclasses.replace(parse, era_line_keying=False))
    assert "2020: the parse did not use era line keying" in _failures(corpus.leg_a())


def test_leg_a_fails_when_one_key_carries_two_identities(corpus, monkeypatch):
    def doubled(parse):
        row = next(r for r in parse.rows if r.pe_bli == "2031A-ARMY-L1")
        return dataclasses.replace(
            parse, rows=[*parse.rows, dataclasses.replace(row, title="Utility F/W Aircraft II")])

    _wrap_parse(monkeypatch, 2019, doubled)
    assert "2019/2031A-ARMY-L1: the workbook prints 2 identities for one key" in _failures(corpus.leg_a())


def test_leg_a_reports_a_parse_error_as_a_failure(corpus, monkeypatch):
    def refuse(parse):
        raise ValueError("an era key prints two codes")

    _wrap_parse(monkeypatch, 2017, refuse)
    assert "2017: ValueError: an era key prints two codes" in _failures(corpus.leg_a())


def test_leg_a_fails_on_a_duplicated_map_row(corpus):
```

In `tests/test_verify_era_map.py` (before `test_leg_b_fails_on_an_unreadable_seed`), replace:

```python
def test_leg_b_fails_on_an_unreadable_seed(corpus):
```

with:

```python
def test_leg_b_fails_on_a_map_decision_the_seed_no_longer_holds(corpus):
    # ROADMAP #203: the stale-build branch for a decision_id the seed dropped.
    corpus.seed = [s for s in corpus.seed if s["line_item_code"] != "9440A11300"]
    corpus.save()
    assert ("9440A11300|2031A||2019-2019: in the map, not in p1_era_code_decisions.csv"
            " (stale build)") in _failures(corpus.leg_b())


def test_leg_b_fails_on_an_unreadable_seed(corpus):
```

In `tests/test_verify_era_map.py` (:372), replace:

```python
def test_cli_fails_with_exit_1(pinned, capsys):
```

with:

```python
def test_cli_refuses_unknown_legs_with_exit_2(pinned, capsys):
    """ROADMAP #203 and the follow-ups CLI convention (design §6): a tool error
    prints one `verify-era-map: ERROR — …` line and exits 2, never a traceback;
    a failed check still exits 1."""
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-era-map", "--legs", "az"])
    out = capsys.readouterr().out.splitlines()
    assert exit_.value.code == 2
    assert out[-1].startswith("verify-era-map: ERROR — legs must be letters from abcdef")
    assert out[-1].endswith("got 'az'")
    assert not any(line.startswith("leg ") for line in out)


def test_cli_fails_with_exit_1(pinned, capsys):
```

- [ ] **Step 2: Run them; only the CLI test fails**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_verify_era_map.py -q`
Expected: one failure, `test_cli_refuses_unknown_legs_with_exit_2` (`ValueError: legs must be letters from abcdef; got 'az'`
propagates as a traceback). The seven leg-a/leg-b tests pass: the branches exist, and now each is planted (scratch
overlay of `532205c9` + 9a + 9b, 2026-10-13: `1 failed, 35 passed`).

- [ ] **Step 3: Print an ERROR line and exit 2 on a tool error**

In `src/govbudget/cli.py` (:2432-2440), replace:

```python
def cmd_verify_era_map(args) -> None:
    from govbudget import verify_era_map

    out = verify_era_map.run_verify_era_map(
        site_dir=config.SITE_DIR,
        duckdb_path=config.DUCKDB_PATH,
        seed_path=verify_era_map.DEFAULT_SEED_PATH,
        legs=args.legs,
    )
```

with:

```python
def cmd_verify_era_map(args) -> None:
    from govbudget import verify_era_map

    # Follow-ups CLI convention (design §6; ROADMAP #203): a tool error prints
    # one ERROR line and exits 2; a failed check prints FAIL and exits 1.
    try:
        out = verify_era_map.run_verify_era_map(
            site_dir=config.SITE_DIR,
            duckdb_path=config.DUCKDB_PATH,
            seed_path=verify_era_map.DEFAULT_SEED_PATH,
            legs=args.legs,
        )
    except ValueError as e:
        print(f"verify-era-map: ERROR — {e}")
        sys.exit(2)
```

In `src/govbudget/verify_era_map.py` (:3-8), replace:

```python
CLI: `govbudget verify-era-map [--legs abc]`. With no arguments it checks
every leg against config.SITE_DIR, config.DUCKDB_PATH and the committed seed
(dbt/seeds/p1_era_code_decisions.csv), prints one line per leg and then
exactly one final line, `verify-era-map: PASS` or `verify-era-map: FAIL`,
and exits 1 on FAIL. It is built to fail: a missing table, workbook or seed
is a FAIL, never a skip.
```

with:

```python
CLI: `govbudget verify-era-map [--legs abc]`. With no arguments it checks
every leg against config.SITE_DIR, config.DUCKDB_PATH and the committed seed
(dbt/seeds/p1_era_code_decisions.csv), prints one line per leg and then
exactly one final line, `verify-era-map: PASS` or `verify-era-map: FAIL`,
and exits 1 on FAIL. It is built to fail: a missing table, workbook or seed
is a FAIL, never a skip. A tool error (an unknown --legs letter) prints
`verify-era-map: ERROR — <message>` instead and exits 2.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_verify_era_map.py tests/test_verify_era_map_def.py tests/test_verify_phase5.py -q`
Expected: no failures (overlay: `59 passed` for the first two files).

- [ ] **Step 5: Check the CLI by hand**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && uv run --project . python -m govbudget verify-era-map --legs az; echo "exit $?"`
Expected (it fails before reading anything, so no SAM guard is needed):

```
verify-era-map: ERROR — legs must be letters from abcdef; got 'az'
exit 2
```

- [ ] **Step 6: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/cli.py GovBudget/src/govbudget/verify_era_map.py GovBudget/tests/test_verify_era_map.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(verify-era-map): a bad --legs exits 2 with one ERROR line; plant leg a's classified filter and failure branches (#203)" -m "Follow-ups CLI convention: tool error = ERROR line + exit 2, failed check = FAIL + exit 1. Leg a: classified row skipped (with a defeated-filter control), map citing another workbook, printed line number, non-era parse, two identities for one key, a parse error; leg b: a decision the seed dropped." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
