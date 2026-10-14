<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G4 (2026-10-13). Runs after 04b. -->

### Task 4c: Era-map guards — the owner review page (#198)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §6.2 "Review page": the manifest records `review.csv`'s sha256 and `answer` refuses if the file changed; a blank-proposal collision row names its missing pins; bad JSON, `int()` errors and a missing manifest raise `ReviewError` (exit 2); pluralize "era line(s)"; (the own-account reason is reworded in Task 4a, where it is generated). §6 (one CLI convention: `review_batch_page: ERROR — <message>`, exit 2). ROADMAP #198 also names an untested case: "the renderer's escaping test skips the successor block".

**Files:**
- Modify: `scripts/era/review_batch_page.py` — imports (about lines 30–38); `collision_pins_missing` (about lines 161–171); `_row_html` (about lines 174–211); `_split` (anchor on `        end = int(part.get("last_edition", last))`); `_load_answers` (about lines 349–362); `main` (the render manifest and the answer branch; the `except ReviewError` print)
- Test: `tests/test_era_review_batch_page.py` (imports, about lines 2–3; `test_render_then_answer_round_trip_through_the_cli`'s last two lines, about lines 279–281; append at the end)

**Interfaces:**
Consumes: Task 4a's atomic `era_map.write_csv` (the answer writes `review.csv` through it).
Produces (Task 10 renders and answers B7 with it):
- `render` writes the manifest key `review_sha256` (sha256 hex of `review.csv`'s bytes at render time).
- `answer` refuses, before reading the answers file, when the manifest is missing (`<out-dir>/B<n>.json is missing — render batch B<n> first`), is not JSON, lacks `review_sha256`, or `review.csv` no longer hashes to it (`<review> changed since batch B<n> was rendered (sha256 <12 hex> at render, <12 hex> now) — render the batch again`); an answers file that is missing or not JSON, and a split `last_edition` that is not a year, are `ReviewError`s.
- Every `ReviewError` prints `review_batch_page: ERROR — <message>` to stderr and exits 2.
- `collision_pins_missing(row, collision_codes)` also returns the blank pins for a row with no proposal on a collision code; the page then says `PB2026 collision code <code>: a same_program or history_only answer needs <pins> (ratify refuses it without both pins)`.
- The page prints `1 era line` for a one-key chain.

Measured for this task (2026-10-13): `tests/test_era_review_batch_page.py` 41 passed. Today a blank-proposal row on a collision code is marked "needs your decision" with no word about pins (`collision_pins_missing` returns `[]` unless the proposal is `same_program`/`history_only`); `main` calls `json.loads(manifest_path.read_text(…))` and `_load_answers` calls `json.loads(Path(path).read_text(…))` with no handler, and `_split` calls `int(part.get("last_edition", last))` with none; the page prints `{n_keys} era lines` whatever `n_keys` is; the manifest holds `batch`, `chain_ids`, `labels`, `actuals_k`, `undecided_before`. `test_page_escapes_every_source_string` passes `successor_evidence="<i>x</i>"` on a row whose `successor_code` is blank, so the successor block it means to test is never rendered.

- [ ] **Step 1: Write the failing tests**

In `tests/test_era_review_batch_page.py`, replace:

```python
import csv
import json
```

with:

```python
import csv
import hashlib
import json
```

In `test_render_then_answer_round_trip_through_the_cli`, replace:

```python
    assert main(["answer", "--batch", "2", "--review", str(review), "--out-dir", str(out),
                 "--answers", str(answers)]) == 2
    assert "already has a decision" in capsys.readouterr().err
```

with:

```python
    # the first answer rewrote review.csv, so the rendered page no longer
    # describes it (ROADMAP #198); apply_answers' own "already has a
    # decision" refusal is pinned by test_an_answered_chain_cannot_be_answered_twice
    assert main(["answer", "--batch", "2", "--review", str(review), "--out-dir", str(out),
                 "--answers", str(answers)]) == 2
    assert "changed since batch B2 was rendered" in capsys.readouterr().err
```

Append at the end of `tests/test_era_review_batch_page.py`:

```python


# ---------------------------------------------------------------------------
# ROADMAP #198 (follow-ups spec 2026-10-04 §6.2): the review page
# ---------------------------------------------------------------------------

def test_answer_refuses_a_review_file_changed_since_render(tmp_path, capsys):
    review, out = write_world(tmp_path, [row(1), row(2)]), tmp_path / "out"
    assert main(["render", "--batch", "2", "--review", str(review),
                 "--seed", str(tmp_path / "absent.csv"), "--out-dir", str(out)]) == 0
    manifest = json.loads((out / "B2.json").read_text())
    assert manifest["review_sha256"] == hashlib.sha256(review.read_bytes()).hexdigest()
    rows = era_map.read_csv(review)
    rows[0]["reason"] = "edited after the page was rendered"
    write_csv(review, REVIEW_COLUMNS, rows)
    before = review.read_bytes()
    capsys.readouterr()
    assert main(["answer", "--batch", "2", "--review", str(review), "--out-dir", str(out),
                 "--answers", str(answers_file(tmp_path, "B2", {}))]) == 2
    err = capsys.readouterr().err
    assert err.startswith("review_batch_page: ERROR — ")
    assert "changed since batch B2 was rendered" in err
    assert review.read_bytes() == before


def test_a_blank_proposal_on_a_collision_code_names_the_pins_it_needs():
    rows = [row(1, chain_id="20|0300D|DSS", proposed_decision="", program_account="0300D")]
    page = render_page("B1", rows, 0, chains_for(rows), collision_codes=frozenset({"20"}))
    assert '<span class="chip chip-other">needs your decision</span>' in page
    assert ("PB2026 collision code 20: a same_program or history_only answer needs"
            " program_org (ratify refuses it without both pins)") in page


@pytest.mark.parametrize("break_it, message", [
    (lambda out, answers: (out / "B2.json").unlink(), "B2.json is missing — render batch B2 first"),
    (lambda out, answers: (out / "B2.json").write_text("{not json"), "B2.json is not JSON"),
    (lambda out, answers: answers.write_text("{not json"), "B2.answers.json is not JSON"),
    (lambda out, answers: answers.unlink(), "B2.answers.json is missing"),
])
def test_unreadable_files_are_a_review_error_not_a_traceback(tmp_path, capsys, break_it, message):
    review, out = write_world(tmp_path, [row(1)]), tmp_path / "out"
    assert main(["render", "--batch", "2", "--review", str(review),
                 "--seed", str(tmp_path / "absent.csv"), "--out-dir", str(out)]) == 0
    answers = answers_file(tmp_path, "B2", {})
    break_it(out, answers)
    capsys.readouterr()
    assert main(["answer", "--batch", "2", "--review", str(review), "--out-dir", str(out),
                 "--answers", str(answers)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("review_batch_page: ERROR — ") and message in err


def test_a_split_edition_that_is_not_a_year_is_a_review_error():
    with pytest.raises(ReviewError, match="last_edition 'PB2020' is not a year"):
        apply_answers(three(), SHOWN, {"rows": {cid(1): {"split": [
            {"last_edition": "PB2020", "decision": "history_only"},
            {"decision": "same_program"}]}}})


def test_a_one_line_chain_says_era_line():
    rows = [row(1)]
    page = render_page("B1", rows, 1, chains_for(rows, n_keys="1"))
    assert "1 era line · class A1+R1" in page
    assert "1 undecided chain will remain after this batch" in page


def test_page_escapes_the_stated_successor_block():
    hostile = row(1, successor_code="<b>X</b>")
    page = render_page("B1", [hostile], 0, chains_for(
        [hostile], successor_account="<i>2035A</i>",
        successor_evidence='quote="a <script>x</script>"'))
    assert "<script>x" not in page and "<b>X</b>" not in page and "<i>2035A</i>" not in page
    assert "&lt;b&gt;X&lt;/b&gt;" in page and "&lt;i&gt;2035A&lt;/i&gt;" in page
    assert "quote=&quot;a &lt;script&gt;x&lt;/script&gt;&quot;" in page
```

Run:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_era_review_batch_page.py -q 2>&1 | tail -3
```

Expected: `9 failed, 41 passed` (50 tests). The failures: the round-trip test (the second answer still fails on "already has a decision"), the changed-review test (`KeyError: 'review_sha256'`), the blank-proposal test, the 4 unreadable-file cases (`FileNotFoundError` / `JSONDecodeError` escape `main`), the split-year test (`ValueError: invalid literal for int()`), and the one-line test (`1 era lines`). The successor-block escaping test passes already: it closes the gap #198 found.

- [ ] **Step 2: Imports**

In `scripts/era/review_batch_page.py`, replace:

```python
import argparse
import csv
import html
import json
```

with:

```python
import argparse
import csv
import hashlib
import html
import json
```

- [ ] **Step 3: Name the pins a blank proposal on a collision code needs**

Replace:

```python
def collision_pins_missing(row: dict, collision_codes: frozenset[str]) -> list[str]:
    """The pins ratify requires that this row's proposal leaves blank.

    On a PB2026 collision code, same_program and history_only need BOTH
    program_account and program_org (Task 12 ratify refuses either blank), so
    approving such a proposal as it stands could not be ratified."""
    code, _account, _org = parse_chain_id(row["chain_id"])
    if code not in collision_codes or row["proposed_decision"] not in ("same_program", "history_only"):
        return []
    return [f for f in ("program_account", "program_org") if not row[f].strip()]
```

with:

```python
def collision_pins_missing(row: dict, collision_codes: frozenset[str]) -> list[str]:
    """The pins ratify requires that this row leaves blank.

    On a PB2026 collision code, same_program and history_only need BOTH
    program_account and program_org (Task 12 ratify refuses either blank), so
    approving such a proposal as it stands could not be ratified. A row with
    NO proposal on a collision code names them too (ROADMAP #198): the
    owner's same_program or history_only answer will need them."""
    code, _account, _org = parse_chain_id(row["chain_id"])
    if code not in collision_codes or row["proposed_decision"] not in (
            "", "same_program", "history_only"):
        return []
    return [f for f in ("program_account", "program_org") if not row[f].strip()]
```

In `_row_html`, replace:

```python
    need_html = ""
    if missing:
        need_html = (f'<span class="pins">PB2026 collision code {_e(code)}: {_e(row["proposed_decision"])} '
                     f'needs {" and ".join(missing)} (ratify refuses it without them); answer the '
                     f"pin(s) or another decision</span>")
```

with:

```python
    need_html = ""
    if missing and row["proposed_decision"]:
        need_html = (f'<span class="pins">PB2026 collision code {_e(code)}: {_e(row["proposed_decision"])} '
                     f'needs {" and ".join(missing)} (ratify refuses it without them); answer the '
                     f"pin(s) or another decision</span>")
    elif missing:
        need_html = (f'<span class="pins">PB2026 collision code {_e(code)}: a same_program or '
                     f'history_only answer needs {" and ".join(missing)} (ratify refuses it '
                     f"without both pins)</span>")
```

- [ ] **Step 4: Pluralize the line count**

In `_row_html`, replace:

```python
        f'<p class="span">{_e(_editions(row))} · {_e(chain["n_keys"])} era lines · '
```

with:

```python
        f'<p class="span">{_e(_editions(row))} · {_e(chain["n_keys"])} era '
        f'line{"" if str(chain["n_keys"]).strip() == "1" else "s"} · '
```

- [ ] **Step 5: Unreadable input is a `ReviewError`**

In `_split`, replace:

```python
        end = int(part.get("last_edition", last))
```

with:

```python
        try:
            end = int(part.get("last_edition", last))
        except (TypeError, ValueError) as exc:
            raise ReviewError(f"{lbl}: last_edition {part.get('last_edition')!r} is not a year") from exc
```

Replace:

```python
def _load_answers(path: Path, batch: str) -> dict:
    answers = json.loads(Path(path).read_text(encoding="utf-8"))
    unknown = set(answers) - ANSWERS_KEYS
```

with:

```python
def _load_answers(path: Path, batch: str) -> dict:
    try:
        answers = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReviewError(f"{path} is missing") from exc
    except ValueError as exc:
        raise ReviewError(f"{path} is not JSON ({exc})") from exc
    if not isinstance(answers, dict):
        raise ReviewError(f"{path} must hold one JSON object")
    unknown = set(answers) - ANSWERS_KEYS
```

- [ ] **Step 6: Record and check `review.csv`'s sha; print the one error line**

In `main`, replace:

```python
            manifest_path.write_text(json.dumps({
                "batch": batch, "chain_ids": [r["chain_id"] for r in shown],
                "labels": [label(r) for r in shown], "actuals_k": str(total),
                "undecided_before": open_count,
            }, indent=2) + "\n", encoding="utf-8")
```

with:

```python
            manifest_path.write_text(json.dumps({
                "batch": batch, "chain_ids": [r["chain_id"] for r in shown],
                "labels": [label(r) for r in shown], "actuals_k": str(total),
                "undecided_before": open_count,
                # ROADMAP #198: `answer` refuses once review.csv changes
                "review_sha256": hashlib.sha256(args.review.read_bytes()).hexdigest(),
            }, indent=2) + "\n", encoding="utf-8")
```

Replace:

```python
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("batch") != batch:
            raise ReviewError(f"{manifest_path} is batch {manifest.get('batch')!r}, not {batch}")
        answers = _load_answers(args.answers, batch)
```

with:

```python
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ReviewError(f"{manifest_path} is missing — render batch {batch} first") from exc
        except ValueError as exc:
            raise ReviewError(f"{manifest_path} is not JSON ({exc})") from exc
        if manifest.get("batch") != batch:
            raise ReviewError(f"{manifest_path} is batch {manifest.get('batch')!r}, not {batch}")
        recorded = manifest.get("review_sha256")
        current = hashlib.sha256(args.review.read_bytes()).hexdigest()
        if recorded != current:
            raise ReviewError(
                f"{args.review} changed since batch {batch} was rendered (sha256"
                f" {str(recorded)[:12]} at render, {current[:12]} now) — render the batch again")
        answers = _load_answers(args.answers, batch)
```

Replace:

```python
    except ReviewError as exc:
        print(f"review_batch_page: {exc}", file=sys.stderr)
        return 2
```

with:

```python
    except ReviewError as exc:
        print(f"review_batch_page: ERROR — {exc}", file=sys.stderr)
        return 2
```

- [ ] **Step 7: Run the tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_era_review_batch_page.py tests/jbooks/test_era_map_ratify.py tests/jbooks/test_era_map_propose.py -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 scripts/era/review_batch_page.py | tail -1
```

Expected: `123 passed` (50 + 39 + 34); `All checks passed!`.

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/scripts/era/review_batch_page.py GovBudget/tests/test_era_review_batch_page.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(era-review): answer refuses a review.csv changed since render; unreadable input is an ERROR, exit 2; blank collision proposals name their pins; '1 era line' (#198)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `2 files changed`.
