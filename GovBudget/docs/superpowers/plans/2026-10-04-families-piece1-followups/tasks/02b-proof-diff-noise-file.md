<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G4 (2026-10-13). Runs after 02a. -->

### Task 2b: Proof tooling hardening — numeric corners and the schema-2 noise file (#199)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §6.1 "Numeric corners": JSON-in-string `parse_float` keeps non-finite values as text (`1e400` ≠ `1e500`); `NOISE_FILE_SCHEMA` → 2, the marker goes inside the hashed classes, the file records tree digests, and a DIFFERENT control deletes a stale noise file ("This invalidates the old `.proofs` noise files, so §7's controls run fresh"); `--noise-from` help mentions `{fid}`. §6.9 keeps "dotted numeric text", "two noisy lenient columns", the 16-hex `{fid}` rule and a repeatable `--noise-from` out of this wave.

**Files:**
- Modify: `src/govbudget/proof.py` — new helpers after `_numeric_text` (anchor on `    return value if math.isfinite(value) else None`); `_leaf_equiv`, `_group_cell` and `_text_order` (their `json.loads` of a string leaf); `NOISE_FILE_SCHEMA`, `_classes_sha256`, `noise_file`, `write_noise_file`, `load_noise_classes` (about lines 1215–1305)
- Modify: `src/govbudget/cli.py` — the `--noise-from` and `--write-noise` help strings of `proof diff` (anchor on `prf_reorder.add_argument("--noise-from"`)
- Test: `tests/test_proof.py` — `test_load_noise_classes_validates_shape` (about line 853), `test_noise_file_records_verdict_trees_and_a_content_hash` (about line 1182), `test_noise_from_refuses_classes_that_are_not_fid_generalised` (about line 1389), and a new section appended at the end
- Test: `tests/test_era_fact_stability.py` — `test_cli_reads_a_noise_file` (about line 166), which hand-builds a noise file

**Interfaces:**
Consumes: Task 2a's `proof.py` and `cmd_proof`.
Produces (Task 21's controls and judged diffs, Task 2c's `fact_stability.py`):
- `proof.NOISE_FILE_SCHEMA == 2`. A noise file holds `schema_version`, `verdict`, `a`, `b`, `a_tree_sha256`, `b_tree_sha256` (each `proof._tree_digest(<tree>)["sha256"]`), `pointer_generalisation`, `classes_sha256`, `classes`.
- `proof._classes_sha256(classes: list, pointer_generalisation: str | None) -> str` = sha256 of `_canon({"classes": classes, "pointer_generalisation": pointer_generalisation})`.
- `proof.load_noise_classes(path)` refuses any `schema_version` but 2 (`… is noise-file schema 1, not 2 …`); every pre-wave `.proofs` noise file is therefore refused, and Task 21 writes fresh ones.
- `proof.write_noise_file(path, report)`: when `noise_file` refuses, an existing file at `path` is deleted and the `ValueError` says `the older <path> was removed`.
- A JSON-in-string leaf whose numbers overflow a double keeps them as text: `"[1e400]"` vs `"[1e500]"` is `changed`.

Measured for this task (2026-10-13): `tests/test_proof.py` 152 passed after Task 2a; `tests/test_era_fact_stability.py` 17 passed. `json.loads("[1e400]") == json.loads("[1e500]")` is `True` in Python 3.12 (both `[inf]`), which is why the two strings compare as identical JSON-in-string today. The live `.proofs` holds no noise file (only `testpg/` and `testpg.log`), so the schema bump strands nothing in use.

- [ ] **Step 1: Write the failing tests and update the four that build or read a noise file by hand**

In `tests/test_proof.py`, replace:

```python
    path.write_text(json.dumps({"verdict": "EQUAL", "a": "A", "b": "B", "classes": classes,
                                "classes_sha256": proof._classes_sha256(classes)}))
```

with:

```python
    path.write_text(json.dumps({"verdict": "EQUAL", "a": "A", "b": "B", "classes": classes,
                                "classes_sha256": proof._classes_sha256(classes, None)}))
```

Replace:

```python
    assert doc == {
        "schema_version": 1,
        "verdict": "EQUAL",
        "a": str(a.resolve()),
        "b": str(b.resolve()),
        "pointer_generalisation": "16-hex fact-ID pointer segments are {fid}",
        "classes_sha256": hashlib.sha256(
            json.dumps(classes, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")).hexdigest(),
        "classes": classes,
    }
```

with:

```python
    marker = "16-hex fact-ID pointer segments are {fid}"
    assert doc == {
        "schema_version": 2,
        "verdict": "EQUAL",
        "a": str(a.resolve()),
        "b": str(b.resolve()),
        "a_tree_sha256": proof._tree_digest(a)["sha256"],
        "b_tree_sha256": proof._tree_digest(b)["sha256"],
        "pointer_generalisation": marker,
        # schema 2 (#199): the generalisation marker is hashed WITH the classes
        "classes_sha256": hashlib.sha256(
            json.dumps({"classes": classes, "pointer_generalisation": marker},
                       sort_keys=True, ensure_ascii=False,
                       separators=(",", ":")).encode("utf-8")).hexdigest(),
        "classes": classes,
    }
```

Replace:

```python
    edit(doc)
    doc["classes_sha256"] = proof._classes_sha256(doc["classes"])
    noise.write_text(json.dumps(doc))
```

with:

```python
    edit(doc)
    doc["classes_sha256"] = proof._classes_sha256(doc["classes"], doc.get("pointer_generalisation"))
    noise.write_text(json.dumps(doc))
```

In `tests/test_era_fact_stability.py`, replace:

```python
                                 "classes_sha256": _classes_sha256(classes), "classes": classes}))
```

with:

```python
                                 "classes_sha256": _classes_sha256(classes, NOISE_POINTER_GENERALISATION),
                                 "classes": classes}))
```

Append at the end of `tests/test_proof.py`:

```python


# ---------------------------------------------------------------------------
# Families piece-1 follow-ups, ROADMAP #199 (spec 2026-10-04 §6.1): numeric
# corners and the schema-2 noise file
# ---------------------------------------------------------------------------


def test_overflowing_numbers_inside_a_json_string_are_not_equal(tmp_path):
    # json.loads reads both "1e400" and "1e500" as inf, so the two strings
    # used to compare identical. The parse now keeps a non-finite number as
    # its text.
    _json(tmp_path / "a" / "p.json", {"inputs": "[1e400, 2]"})
    _json(tmp_path / "b" / "p.json", {"inputs": "[1e500, 2]"})
    report = proof.diff_trees(tmp_path / "a", tmp_path / "b")
    assert report["files"]["p.json"]["status"] == "changed"
    assert _changes(report, "p.json") == [("/inputs", "changed", 1)]
    assert proof.is_equal(proof.diff_trees(tmp_path / "a", tmp_path / "a"))


def test_a_different_control_removes_an_older_noise_file(tmp_path, capsys):
    a, b = tmp_path / "a", tmp_path / "b"
    _json(a / "p.json", {"rows": [1, 2, 3]})
    _json(b / "p.json", {"rows": [3, 2, 1]})
    noise = tmp_path / "noise.json"
    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "diff", str(a), str(b), "--control", "--write-noise", str(noise)])
    assert exc.value.code == 0 and noise.is_file()
    _json(b / "p.json", {"rows": [3, 2, 1], "v": 2})          # the next control is DIFFERENT
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "diff", str(a), str(b), "--control", "--write-noise", str(noise)])
    assert exc.value.code == 1
    assert not noise.exists()
    assert f"the older {noise} was removed" in capsys.readouterr().err


def test_the_generalisation_marker_is_inside_the_content_hash(tmp_path, capsys):
    noise = _control_noise_file(tmp_path, {FID_1: _derived(["a", "b"])},
                                {FID_1: _derived(["b", "a"])})
    capsys.readouterr()
    doc = json.loads(noise.read_text())
    assert doc["schema_version"] == 2
    doc["pointer_generalisation"] += " (edited)"
    noise.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="classes_sha256"):
        proof.load_noise_classes(noise)


def test_a_schema_1_noise_file_is_refused(tmp_path, capsys):
    noise = _control_noise_file(tmp_path, {FID_1: _derived(["a", "b"])},
                                {FID_1: _derived(["b", "a"])})
    capsys.readouterr()
    doc = json.loads(noise.read_text())
    doc["schema_version"] = 1
    noise.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="noise-file schema 1, not 2"):
        proof.load_noise_classes(noise)


def test_noise_from_help_names_the_fid_rule(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["proof", "diff", "--help"])
    assert exc.value.code == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert "16-hex fact-ID segments read as {fid}" in help_text
```

- [ ] **Step 2: Run them — they fail**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_proof.py tests/test_era_fact_stability.py -q 2>&1 | tail -3
```

Expected: `11 failed, 163 passed` (157 + 17 = 174 tests). The failures: the 5 new tests (`'equivalent' == 'changed'`; the old file still exists; `schema_version` is 1 twice; the help text lacks `{fid}`), and the 6 updated callers of `_classes_sha256` or the noise-file layout — `test_load_noise_classes_validates_shape`, `test_noise_file_records_verdict_trees_and_a_content_hash`, the 3 `test_noise_from_refuses_classes_that_are_not_fid_generalised` cases and `test_cli_reads_a_noise_file` (`TypeError: _classes_sha256() takes 1 positional argument but 2 were given`, or the layout assertion).

- [ ] **Step 3: Keep non-finite JSON-in-string numbers as text**

In `src/govbudget/proof.py`, replace:

```python
    return value if math.isfinite(value) else None


def _multiset_canon(value):
```

with:

```python
    return value if math.isfinite(value) else None


def _finite_or_text(text: str):
    """json.loads parse_float hook (ROADMAP #199): a JSON number that
    overflows a double ("1e400") keeps its literal text, so two different
    overflowing numbers never compare equal as inf == inf."""
    value = float(text)
    return value if math.isfinite(value) else text


def _loads_text(s: str):
    """json.loads for a JSON-in-string leaf (ruling 2), keeping non-finite
    numbers as text."""
    return json.loads(s, parse_float=_finite_or_text)


def _multiset_canon(value):
```

In `_leaf_equiv`, replace:

```python
    try:
        pa, pb = json.loads(a), json.loads(b)
    except ValueError:
        return None
```

with:

```python
    try:
        pa, pb = _loads_text(a), _loads_text(b)
    except ValueError:
        return None
```

In `_group_cell`, replace:

```python
        try:
            parsed = json.loads(value)
        except ValueError:
            return value
```

with:

```python
        try:
            parsed = _loads_text(value)
        except ValueError:
            return value
```

In `_text_order`, replace:

```python
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        parsed = None
```

with:

```python
    try:
        parsed = _loads_text(value)
    except (TypeError, ValueError):
        parsed = None
```

- [ ] **Step 4: Schema 2: the marker inside the hash, tree digests, stale files removed**

Replace:

```python
NOISE_FILE_SCHEMA = 1
#: Recorded in every noise file (Fix round 5) and required by
#: load_noise_classes: says how its class pointers are keyed.
NOISE_POINTER_GENERALISATION = "16-hex fact-ID pointer segments are {fid}"


def _classes_sha256(classes: list) -> str:
    """sha256 of the classes' canonical JSON (sorted keys, no whitespace,
    UTF-8): the noise file's timestamp-free content hash (Fix round 4)."""
    return hashlib.sha256(_canon(classes).encode("utf-8")).hexdigest()
```

with:

```python
#: Schema 2 (ROADMAP #199, follow-ups spec §6.1): the generalisation marker
#: is hashed with the classes, and the file records both trees' digests.
#: load_noise_classes refuses any other schema, so schema-1 files from
#: piece 1's proofs are never reused.
NOISE_FILE_SCHEMA = 2
#: Recorded in every noise file (Fix round 5) and required by
#: load_noise_classes: says how its class pointers are keyed.
NOISE_POINTER_GENERALISATION = "16-hex fact-ID pointer segments are {fid}"


def _classes_sha256(classes: list, pointer_generalisation: str | None) -> str:
    """sha256 of the canonical JSON (sorted keys, no whitespace, UTF-8) of
    {"classes": …, "pointer_generalisation": …}: the noise file's
    timestamp-free content hash (Fix round 4). Schema 2 hashes the marker
    with the classes, so editing either one breaks the hash."""
    return hashlib.sha256(_canon({
        "classes": classes, "pointer_generalisation": pointer_generalisation,
    }).encode("utf-8")).hexdigest()
```

Replace:

```python
    classes = report["reorder_classes"]
    return {
        "schema_version": NOISE_FILE_SCHEMA,
        "verdict": "EQUAL",
        "a": str(Path(report["a"]).resolve()),
        "b": str(Path(report["b"]).resolve()),
        "pointer_generalisation": NOISE_POINTER_GENERALISATION,
        "classes_sha256": _classes_sha256(classes),
        "classes": classes,
    }


def write_noise_file(path: Path, report: dict) -> None:
    """Write noise_file(report) to path; raises (and writes nothing) when
    noise_file refuses."""
    doc = noise_file(report)
    Path(path).write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

with:

```python
    classes = report["reorder_classes"]
    a, b = Path(report["a"]).resolve(), Path(report["b"]).resolve()
    return {
        "schema_version": NOISE_FILE_SCHEMA,
        "verdict": "EQUAL",
        "a": str(a),
        "b": str(b),
        # what the control compared, not only where (ROADMAP #199)
        "a_tree_sha256": _tree_digest(a)["sha256"],
        "b_tree_sha256": _tree_digest(b)["sha256"],
        "pointer_generalisation": NOISE_POINTER_GENERALISATION,
        "classes_sha256": _classes_sha256(classes, NOISE_POINTER_GENERALISATION),
        "classes": classes,
    }


def write_noise_file(path: Path, report: dict) -> None:
    """Write noise_file(report) to path. When noise_file refuses (a DIFFERENT
    control, or no control at all) nothing is written, and an older file at
    path is DELETED before the refusal propagates (ROADMAP #199): a stale
    noise file must not survive for a later --noise-from."""
    path = Path(path)
    try:
        doc = noise_file(report)
    except ValueError as e:
        if path.exists():
            path.unlink()
            raise ValueError(f"{e}; the older {path} was removed") from e
        raise
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

In `load_noise_classes`, replace:

```python
    if data.get("classes_sha256") != _classes_sha256(classes):
        raise ValueError(f"proof diff --noise-from: {path}'s classes do not match its"
                         f" classes_sha256 — edited after the control run?")
    if data.get("pointer_generalisation") != NOISE_POINTER_GENERALISATION:
```

with:

```python
    if data.get("classes_sha256") != _classes_sha256(classes, data.get("pointer_generalisation")):
        raise ValueError(f"proof diff --noise-from: {path}'s classes do not match its"
                         f" classes_sha256 — edited after the control run?")
    if data.get("schema_version") != NOISE_FILE_SCHEMA:
        raise ValueError(
            f"proof diff --noise-from: {path} is noise-file schema"
            f" {data.get('schema_version')!r}, not {NOISE_FILE_SCHEMA} — written before"
            f" the ROADMAP #199 hardening; re-run the --control"
        )
    if data.get("pointer_generalisation") != NOISE_POINTER_GENERALISATION:
```

Also update the docstring sentence of `load_noise_classes` that lists what it refuses: replace

```python
    or that predates Fix round 5's fact-ID generalisation (no
    `pointer_generalisation` marker, or a class pointer that still holds a
    raw 16-hex segment). `count` is provenance only — matching is by
    (path, pointer pattern) alone."""
```

with:

```python
    or that predates Fix round 5's fact-ID generalisation (no
    `pointer_generalisation` marker, or a class pointer that still holds a
    raw 16-hex segment), or whose schema_version is not NOISE_FILE_SCHEMA
    (ROADMAP #199). `count` is provenance only — matching is by (path,
    pointer pattern) alone."""
```

- [ ] **Step 5: Name the `{fid}` rule in the CLI help**

In `src/govbudget/cli.py`, replace:

```python
    prf_reorder.add_argument("--noise-from", type=Path, default=None, dest="noise_from",
                             help="trust only the (path, pointer) reorder classes a prior"
                                  " --control run wrote to this file")
    prf_diff.add_argument("--write-noise", type=Path, default=None, dest="write_noise",
                          help="with --control: when the control is EQUAL, write its verdict,"
                               " source trees and reorder classes (JSON, sorted, with counts"
                               " and a content hash) here; a DIFFERENT control writes nothing")
```

with:

```python
    prf_reorder.add_argument("--noise-from", type=Path, default=None, dest="noise_from",
                             help="trust only the (path, pointer) reorder classes a prior"
                                  " --control run wrote to this file; a class pointer's"
                                  " 16-hex fact-ID segments read as {fid}, so one class"
                                  " covers that field under every fact")
    prf_diff.add_argument("--write-noise", type=Path, default=None, dest="write_noise",
                          help="with --control: when the control is EQUAL, write its verdict,"
                               " source trees and their digests, and reorder classes (JSON,"
                               " sorted, with counts and a content hash) here; a DIFFERENT"
                               " control writes nothing and removes an older file there")
```

- [ ] **Step 6: Run the tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_proof.py tests/test_era_fact_stability.py tests/test_era_s4_report.py -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/proof.py | tail -1
```

Expected: `181 passed` (157 + 17 + 7); `All checks passed!`.

- [ ] **Step 7: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/proof.py GovBudget/src/govbudget/cli.py GovBudget/tests/test_proof.py GovBudget/tests/test_era_fact_stability.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(proof): non-finite JSON-in-string numbers stay text; noise file schema 2 (marker hashed with classes, tree digests, stale file removed); --noise-from help names {fid} (#199)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `4 files changed`.
