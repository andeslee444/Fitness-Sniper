<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G4 (2026-10-13). Runs after 02b. -->

### Task 2c: Proof tooling hardening — proof scripts and the two proof notes (#199)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §6.1 "Proof scripts" (`fact_stability.py` uses a public proof API and type-strict equality; the `s4_report` docstring names `decade_absent`) and "Proof notes" (dated corrections on `families-s1-proof.md`, the 1e-6 absolute and 1e-12 relative tolerances, and `families-s1b-proof.md`, the code commit e25945b7 with identical source). §6.9 keeps expected-diff rules 5–8, 17, 33 and 35 for piece 2.

**Files:**
- Modify: `src/govbudget/proof.py` (public names after `_json_noise`; anchor on `        total += n\n    return total\n\n\ndef _row_noise(`)
- Modify: `scripts/era/fact_stability.py` (the `govbudget.proof` import; `_is_noise`; `compare_citations`)
- Modify: `scripts/era/s4_report.py` (module docstring, the `sidecars` paragraph)
- Modify: `docs/superpowers/reviews/families-s1-proof.md` (a dated correction before `## Summary (2026-10-03)`)
- Modify: `docs/superpowers/reviews/families-s1b-proof.md` (a dated correction before `## Summary (2026-10-03)`)
- Test: `tests/test_era_fact_stability.py`, `tests/test_era_s4_report.py` (append at the end of each)

**Interfaces:**
Consumes: Task 2b's `proof.py`.
Produces (Task 21's fact-stability run):
- `proof.NoiseMode` (the class `_Mode`) and `proof.json_noise(a, b, *, group=None, mode=None, key_pointer="") -> int | None` (the rule `_json_noise` applies), for scripts outside the module.
- `scripts/era/fact_stability.py` imports only public names from `govbudget.proof`, and `compare_citations` treats a field whose value keeps its equality but changes type (`1` → `1.0`, `True` → `1`) as `changed`.

Measured for this task (2026-10-13): `scripts/era/fact_stability.py:38` reads `from govbudget.proof import _json_noise, _Mode, load_noise_classes`; `compare_citations` skips a field on `if va == vb:` (so `1 == 1.0 == True`); `tests/test_era_fact_stability.py` 17 passed and `tests/test_era_s4_report.py` 7 passed. `git diff --stat e25945b7 99ebde61` → only `GovBudget/tests/jbooks/test_era_keys.py | 13 +++++++++++++`. `proof._FLOAT_REL_TOL` is `10.0 ** -12` and `proof._FLOAT_ABS_TOL` is `1e-6` (`proof.py:224`, `:236`). Gate 21 leg k is the site gate that value-checks `decade_absent` (ROADMAP #199, Task 21 bullet).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_era_fact_stability.py`:

```python


# ROADMAP #199 (follow-ups spec 2026-10-04 §6.1)

def test_fact_stability_imports_no_private_proof_helper():
    import ast
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "scripts" / "era" / "fact_stability.py"
    names = [alias.name for node in ast.walk(ast.parse(src.read_text()))
             if isinstance(node, ast.ImportFrom) and node.module == "govbudget.proof"
             for alias in node.names]
    assert names and not [n for n in names if n.startswith("_")], names


@pytest.mark.parametrize("va, vb", [(1, 1.0), (True, 1), (0, False)])
def test_a_type_change_with_an_equal_value_is_a_change(va, vb):
    a, b = a_side(), b_side()
    a["w1"]["n_inputs"], b["w1"]["n_inputs"] = va, vb
    report = compare_citations(a, b, LEAVES, expected_f15=1)
    assert not report["ok"]
    assert [(c["fact_id"], c["field"]) for c in report["changed"]] == [("w1", "n_inputs")]
```

Append to `tests/test_era_s4_report.py`:

```python


def test_the_docstring_says_decade_absent_is_checked_for_presence_only():
    # ROADMAP #199: s4_report compares decade_absent's presence, not its
    # value; site gate 21 leg k value-checks it. The docstring says so.
    import era.s4_report as s4_report

    doc = " ".join(s4_report.__doc__.split())
    assert "decade_absent is compared for presence only" in doc
    assert "gate 21 leg k" in doc
```

Run:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_era_fact_stability.py tests/test_era_s4_report.py -q 2>&1 | tail -3
```

Expected: `5 failed, 24 passed`: the import test (`['_json_noise', '_Mode', 'load_noise_classes']`), the 3 type-change cases (`assert not True`), and the docstring test.

- [ ] **Step 2: Export the noise rule under public names**

In `src/govbudget/proof.py`, replace:

```python
        total += n
    return total


def _row_noise(ra: tuple, rb: tuple, lenient: list[tuple[int, str, str]],
```

with:

```python
        total += n
    return total


#: Public names for proof scripts outside this module (scripts/era/
#: fact_stability.py; ROADMAP #199): the diff's own noise rules, so a script
#: never reaches into a private helper whose shape may change.
NoiseMode = _Mode


def json_noise(a, b, *, group: str | None = None, mode: "_Mode | None" = None,
               key_pointer: str = "") -> int | None:
    """The JSON noise rule diff_trees applies (see _json_noise): how many
    leaves of a and b differ by float, numeric-text or JSON-in-string noise
    only, or None when they differ in any other way."""
    return _json_noise(a, b, group=group, mode=mode, key_pointer=key_pointer)


def _row_noise(ra: tuple, rb: tuple, lenient: list[tuple[int, str, str]],
```

- [ ] **Step 3: Use them in `fact_stability.py`, with type-strict equality**

In `scripts/era/fact_stability.py`, replace:

```python
from govbudget.proof import _json_noise, _Mode, load_noise_classes
```

with:

```python
from govbudget.proof import NoiseMode, json_noise, load_noise_classes
```

Replace:

```python
def _is_noise(fid: str, field: str, va, vb, mode: _Mode) -> bool:
    """proof diff's verdict on one citations.json leaf: equivalent export noise?"""
    probe = mode.fork()
    if _json_noise(va, vb, group=CITATIONS_GROUP, mode=probe, key_pointer=f"/{fid}/{field}") is None:
        return False
```

with:

```python
def _is_noise(fid: str, field: str, va, vb, mode: NoiseMode) -> bool:
    """proof diff's verdict on one citations.json leaf: equivalent export noise?"""
    probe = mode.fork()
    if json_noise(va, vb, group=CITATIONS_GROUP, mode=probe, key_pointer=f"/{fid}/{field}") is None:
        return False
```

Replace:

```python
    mode = _Mode(trusted={(c["path"], c["pointer"]) for c in noise_classes or []})
```

with:

```python
    mode = NoiseMode(trusted={(c["path"], c["pointer"]) for c in noise_classes or []})
```

Replace:

```python
            va, vb = ca.get(field), cb.get(field)
            if va == vb:
                continue
```

with:

```python
            va, vb = ca.get(field), cb.get(field)
            # type-strict (ROADMAP #199): 1 vs 1.0, or True vs 1, is a change
            if type(va) is type(vb) and va == vb:
                continue
```

- [ ] **Step 4: Say what `s4_report` does not check**

In `scripts/era/s4_report.py`, replace:

```python
          B shows unchanged. B adds points only from PB2017-PB2023 and only
          on procurement pages; decade_absent appears or vanishes nowhere.
```

with:

```python
          B shows unchanged. B adds points only from PB2017-PB2023 and only
          on procurement pages; decade_absent appears or vanishes nowhere.
          decade_absent is compared for presence only: its value
          (first_edition, edition_count) is not checked here; site gate 21
          leg k value-checks it (ROADMAP #199).
```

- [ ] **Step 5: Run the tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_era_fact_stability.py tests/test_era_s4_report.py tests/test_proof.py -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/proof.py scripts/era/fact_stability.py scripts/era/s4_report.py | tail -1
```

Expected: `186 passed` (21 + 8 + 157); `All checks passed!`.

- [ ] **Step 6: Dated corrections on the two proof notes**

In `docs/superpowers/reviews/families-s1-proof.md`, replace:

```
Live = the shared database and lake after the same migrate/apply/export-facts.

## Summary (2026-10-03)
```

with:

```
Live = the shared database and lake after the same migrate/apply/export-facts.

*Correction (2026-10-04, families piece-1 follow-ups design §6.1, ROADMAP #199; nothing
above reworded).* "Values equal to 12 significant digits" is not the whole float rule this
proof ran under. `govbudget proof diff` (`src/govbudget/proof.py`, `_float_close`) treats
two floats as noise when their relative difference is at most 1e-12 (`_FLOAT_REL_TOL`) OR
their absolute difference is at most 1e-6 (`_FLOAT_ABS_TOL`), and applies the same rule to
numeric text. On a total above about $1T, the relative tolerance alone can absorb a dollar
or more per trillion.

## Summary (2026-10-03)
```

In `docs/superpowers/reviews/families-s1b-proof.md`, replace:

```
data/research/edition_manifest.json budget_lines counts are load-time records (no gate reads them) and stay at their pre-S1b values.

## Summary (2026-10-03)
```

with:

```
data/research/edition_manifest.json budget_lines counts are load-time records (no gate reads them) and stay at their pre-S1b values.

*Correction (2026-10-04, families piece-1 follow-ups design §6.1, ROADMAP #199; nothing above
reworded).* The exports ran under e25945b7 ("feat(jbooks): load the era P-1 Classified
Programs line under 9999999999 …"), not the 99ebde61 the `Code:` line names. 99ebde61 is the
next commit and adds only a test (`git diff --stat e25945b7 99ebde61` lists
`tests/jbooks/test_era_keys.py` alone), so the source the proof ran is identical.

## Summary (2026-10-03)
```

Run:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && grep -c 'follow-ups design §6.1, ROADMAP #199' docs/superpowers/reviews/families-s1-proof.md docs/superpowers/reviews/families-s1b-proof.md
```

Expected: `docs/superpowers/reviews/families-s1-proof.md:1` and `docs/superpowers/reviews/families-s1b-proof.md:1`.

- [ ] **Step 7: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/proof.py GovBudget/scripts/era/fact_stability.py GovBudget/scripts/era/s4_report.py GovBudget/docs/superpowers/reviews/families-s1-proof.md GovBudget/docs/superpowers/reviews/families-s1b-proof.md GovBudget/tests/test_era_fact_stability.py GovBudget/tests/test_era_s4_report.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(proof): fact_stability uses the public noise API with type-strict equality; s4_report names its decade_absent limit; dated proof-note corrections (#199)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `7 files changed`.
