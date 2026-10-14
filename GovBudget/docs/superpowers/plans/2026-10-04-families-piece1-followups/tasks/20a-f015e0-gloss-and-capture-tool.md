<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; the approved design is ../../../specs/2026-10-04-families-piece1-followups-design.md. -->

### Task 20a: the F015E0 gloss names its exhibit; the F-15 capture tool round-trips and writes atomically (#206 T9, #201)

Task 20 ("F-15 tooling and the F015E0 gloss") is split into 20a (the Python side: the gloss, its receipt check, the
capture tool), 20b (the site scripts' direct-run guard and verify.mjs notes) and 20c (the /families/f-15/ row name,
the family-history gate and the page snapshot). Run them in that order: 20c's snapshot file imports 20b's helper.
None of them re-pins `tests/fixtures/f15/`: Task 21 (P3) does, from B@fu-post, with the tool hardened here.

**Spec:** design §5.2 (T9: the note begins "This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include …" —
Q17 approved by the owner on 2026-10-04 in the amended form; `NOTE_RECEIPTS['e7d5bcfb4a30f458']` gains
`pe_bli='F015EX'`, which `check_program_notes` checks; a new test strips every `[…]` gloss with
`re.sub(r'\s*\[[^\]]*\]', '', note)` and requires the verbatim source sentence, the first gloss naming the receipt's
`pe_bli`; the pins `F015E0_NOTE` and the site test's `NOTE` change; the re-pin's first step computes the expected sha
hermetically, the only leaf difference allowed being `programs[F015E0].note`); design §6.6 (#201: "The capture tool
rebuilds from the gzip round-tripped fixture and writes its three files atomically after the check"); §7 P3, W1.

**Files:**
- Modify: `src/govbudget/f15_funding_history.py` (the comment above `PROGRAM_NOTES` :51-56 and its note :57-60;
  `NOTE_RECEIPTS` :66-70)
- Modify: `scripts/era/capture_f15_fixtures.py` (docstring :20-24; imports :39-44; `rebuild_from_fixture_bytes`,
  `round_trip_check`, `write_fixtures` before `main` :155; the writes in `main` :168-171)
- Modify: `tests/test_f15_funding_history.py` (imports :1-15; the S5 strings :286-292; a test before
  `test_a_program_note_ships_only_with_its_reviewed_narrative_receipt` :321, whose registries gain a wrong `pe_bli`)
- Create: `tests/test_capture_f15_fixtures.py`

Line numbers are hints measured at `532205c9` (anchor on the quoted text).

**Interfaces:**
Consumes: `f15_funding_history.build_history`, `build_program_matrix`, `_json_bytes`, `check_program_notes`
(compares every `NOTE_RECEIPTS` key against the registry citation); the committed fixtures
`tests/fixtures/f15/{builder_inputs.json.gz, history.json, history.sha256, page_snapshot.json}` (captured at piece-1
S5, `history.sha256` = `9f70c770…` lineage; unchanged by this task); `conftest.py` puts `scripts/` on `sys.path`
(`import era.capture_f15_fixtures`).
Produces: the F015E0 `note` (one string, below); `NOTE_RECEIPTS["e7d5bcfb4a30f458"]["pe_bli"] == "F015EX"`;
`capture_f15_fixtures.rebuild_from_fixture_bytes(gz: bytes) -> bytes`, `round_trip_check(fixture: dict, shipped:
bytes) -> bytes` (raises `SystemExit("capture_f15_fixtures: the round-tripped fixture does not rebuild the shipped
history")`), `write_fixtures(out_dir: Path, files: dict[str, bytes]) -> None`; the CLI keeps its flags (`--site-dir`,
`--duckdb`, `--out-dir`, `--expect-sha256`). For Task 21 (P3): the hermetic sha after this task, computed in Step 5 —
`d0de9e8bc6466de6d213f4dd2782faa467b82f961a26169eaf1345362f078d8f` on the committed fixtures (139,024 → 139,061 bytes,
only `programs[7].note` differs) — is the `--expect-sha256` for the capture from B@fu-post; B@fu-post's
`f15_funding_history.json` must hash to it.

**Red until Task 21 re-pins (by design):** `tests/test_f15_era_identity.py::test_golden_rebuild_from_fixtures_is_byte_identical`,
`::test_fresh_state_with_decade_era_map_receipts_keeps_every_byte` and
`::test_allowed_formula_competitor_changes_exactly_one_cell` compare a rebuild under the new note to the committed
`history.json`. They go green when Task 21g Step 3 (P3.3) rewrites `tests/fixtures/f15/{history.json, history.sha256,
builder_inputs.json.gz}`; no other test may fail.

Verified now (read-only, 2026-10-13): narrative `e7d5bcfb4a30f458` (`data/site/data/jbook_narratives.parquet`,
F015EX `LineItem[2]`, `description`) ends "Funding for this exhibit is contained in PE 0207146F. This exhibit does not
include the eight aircraft in Lot 1 which were funded outside this exhibit in FY 2020 (… (F015E0, Line #3))."; its
citation is `jbook_narrative`, page 71, sha `528d1441…`, `pe_bli` F015EX, both URLs ending `#page=71`.

The note after this task (the owner-approved string, Q17 amended):

> This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include the eight aircraft in Lot 1 which were funded
> outside this exhibit in FY 2020 (two test aircraft were purchased with RDT&E funds (PE 0207134F); four
> operationally representative test aircraft and two operational aircraft were purchased with procurement funds
> (F015E0, Line #3 [line 3 of the PB2020–21 P-1 (line 4 in PB2022)])).

- [ ] **Step 1: Write the failing tests**

In `tests/test_f15_funding_history.py` (:1-15), replace:

```python
import copy
import json
from decimal import Decimal

import pytest

from govbudget.f15_funding_history import (
    ERA_MEMBERS,
    ERA_PROGRAM_CODES,
    PROGRAMS,
    build_history,
    build_program_matrix,
    check_program_notes,
    member_row,
)
```

with:

```python
import copy
import json
import re
from decimal import Decimal

import pytest

from govbudget.f15_funding_history import (
    ERA_MEMBERS,
    ERA_PROGRAM_CODES,
    NOTE_RECEIPTS,
    PROGRAM_NOTES,
    PROGRAMS,
    build_history,
    build_program_matrix,
    check_program_notes,
    member_row,
)
```

In `tests/test_f15_funding_history.py` (:286-290), replace:

```python
# Spec §6.5 (S5): the strings the owner signed off.
F015E0_LABEL = "F-15e (FY2020 F-15EX Lot 1 aircraft)"
F015E0_NOTE = (
    "This exhibit does not include the eight aircraft in Lot 1 which were funded outside this exhibit in "
```

with:

```python
# Spec §6.5 (S5): the strings the owner signed off; the first gloss is the
# owner's 2026-10-04 amendment (#206 T9, design Q17: "F-15EX AP").
F015E0_LABEL = "F-15e (FY2020 F-15EX Lot 1 aircraft)"
F015E0_NOTE = (
    "This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include the eight aircraft in Lot 1"
    " which were funded outside this exhibit in "
```

In `tests/test_f15_funding_history.py` (:321-325), replace:

```python
def test_a_program_note_ships_only_with_its_reviewed_narrative_receipt():
    check_program_notes(PROGRAMS, {"e7d5bcfb4a30f458": dict(NARRATIVE)})
    for registry in ({}, {"e7d5bcfb4a30f458": {**NARRATIVE, "page_number": 70}},
                     {"e7d5bcfb4a30f458": {**NARRATIVE, "kind": "workbook"}},
                     {"e7d5bcfb4a30f458": {**NARRATIVE, "sha256": "f" * 64}}):
```

with:

```python
# The PB2026 AF Aircraft Procurement Vol I prints this sentence on PDF p.71 in
# the F-15EX AP (F015EX) P-40 description (narrative fact e7d5bcfb4a30f458,
# LineItem[2]; read 2026-10-13 from data/site/data/jbook_narratives.parquet).
SOURCE_SENTENCE = (
    "This exhibit does not include the eight aircraft in Lot 1 which were funded outside this exhibit in "
    "FY 2020 (two test aircraft were purchased with RDT&E funds (PE 0207134F); four operationally "
    "representative test aircraft and two operational aircraft were purchased with procurement funds "
    "(F015E0, Line #3))."
)


def test_the_f015e0_note_is_the_source_sentence_plus_bracketed_glosses():
    """#206 T9: "This exhibit" read as F015E0's own exhibit under the "BLI
    F015E0" label. The first gloss names the exhibit the receipt is; with every
    [..] gloss removed the note is the printed sentence, verbatim."""
    note = PROGRAM_NOTES["F015E0"]["note"]
    assert re.sub(r"\s*\[[^\]]*\]", "", note) == SOURCE_SENTENCE
    glosses = re.findall(r"\[([^\]]*)\]", note)
    assert glosses == ["the PB2026 F-15EX AP (F015EX) P-40", "line 3 of the PB2020–21 P-1 (line 4 in PB2022)"]
    receipt = NOTE_RECEIPTS[PROGRAM_NOTES["F015E0"]["note_fact_id"]]
    assert f"({receipt['pe_bli']})" in glosses[0]


def test_a_program_note_ships_only_with_its_reviewed_narrative_receipt():
    check_program_notes(PROGRAMS, {"e7d5bcfb4a30f458": dict(NARRATIVE)})
    for registry in ({}, {"e7d5bcfb4a30f458": {**NARRATIVE, "page_number": 70}},
                     {"e7d5bcfb4a30f458": {**NARRATIVE, "kind": "workbook"}},
                     {"e7d5bcfb4a30f458": {**NARRATIVE, "sha256": "f" * 64}},
                     {"e7d5bcfb4a30f458": {**NARRATIVE, "pe_bli": "F015E0"}}):
```

Create `tests/test_capture_f15_fixtures.py`:

```python
"""scripts/era/capture_f15_fixtures.py hardening (ROADMAP #201; follow-ups Task 20).

The capture's self-check rebuilt the history from its in-memory rows, not
from the fixture it then wrote, and it wrote its three files one by one, in
place. Now the bytes it writes are gzip round-tripped and rebuilt exactly as
tests/test_f15_era_identity.py rebuilds them, and the three files land
through temporary files, only after every check passed.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

import era.capture_f15_fixtures as capture  # scripts/ is on sys.path via conftest
from govbudget.f15_funding_history import _json_bytes

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "f15"


def _committed_inputs() -> dict:
    return json.loads(gzip.decompress((FIXTURES / "builder_inputs.json.gz").read_bytes()))


def test_round_trip_check_returns_the_bytes_it_proved():
    fixture = _committed_inputs()
    gz = gzip.compress(_json_bytes(fixture), mtime=0)
    assert capture.round_trip_check(fixture, capture.rebuild_from_fixture_bytes(gz)) == gz


def test_round_trip_check_refuses_a_history_the_written_fixture_does_not_rebuild():
    with pytest.raises(SystemExit, match="round-tripped fixture does not rebuild the shipped history"):
        capture.round_trip_check(_committed_inputs(), b"{}\n")


def test_the_check_rebuilds_from_the_written_bytes_not_the_in_memory_rows(monkeypatch):
    fixture = _committed_inputs()
    seen = []
    real = capture.build_history

    def spy(source_rows, series, **kwargs):
        seen.append(source_rows)
        return real(source_rows, series, **kwargs)

    monkeypatch.setattr(capture, "build_history", spy)
    gz = gzip.compress(_json_bytes(fixture), mtime=0)
    capture.round_trip_check(fixture, capture.rebuild_from_fixture_bytes(gz))
    assert seen and all(rows is not fixture["source_rows"] and rows == fixture["source_rows"]
                        for rows in seen)


FILES = {"history.json": b"{}\n", "history.sha256": b"0" * 64 + b"\n", "builder_inputs.json.gz": b"gz"}


def test_write_fixtures_replaces_all_three_files_and_leaves_no_temporaries(tmp_path):
    capture.write_fixtures(tmp_path, FILES)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == FILES


def test_write_fixtures_changes_nothing_when_a_write_fails(tmp_path, monkeypatch):
    old = {"history.json": b"old\n", "history.sha256": b"1" * 64 + b"\n", "builder_inputs.json.gz": b"old-gz"}
    for name, data in old.items():
        (tmp_path / name).write_bytes(data)
    real = Path.write_bytes

    def flaky(self, data):
        if "builder_inputs" in self.name:
            raise OSError("disk full")
        return real(self, data)

    monkeypatch.setattr(Path, "write_bytes", flaky)
    with pytest.raises(OSError, match="disk full"):
        capture.write_fixtures(tmp_path, FILES)
    monkeypatch.undo()
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == old
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_funding_history.py tests/test_capture_f15_fixtures.py -q`
Expected: `8 failed` — in `test_f15_funding_history.py` the retitle test (old note), the gloss test and the receipt
test (`NOTE_RECEIPTS` has no `pe_bli`, so the F015E0-`pe_bli` registry passes); all five capture tests
(`AttributeError: module 'era.capture_f15_fixtures' has no attribute …`) (scratch overlay of `532205c9`, 2026-10-13).

- [ ] **Step 3: Implement**

In `src/govbudget/f15_funding_history.py` (:51-60), replace:

```python
# signed off the exact strings, recorded in the ROADMAP). F015E0: PB2026 AF
# Aircraft Procurement Vol I, F015EX P-40 description, PDF p.71, the only page
# that prints it. The quote is verbatim; the [bracketed] gloss is ours, read
# from ERA_PROGRAM_CODES (F015E0 is line 3 in PB2020–21, line 4 in PB2022).
PROGRAM_NOTES = {
    "F015E0": dict(
        note=("This exhibit does not include the eight aircraft in Lot 1 which were funded outside this "
              "exhibit in FY 2020 (two test aircraft were purchased with RDT&E funds (PE 0207134F); four "
```

with:

```python
# signed off the exact strings, recorded in the ROADMAP). F015E0: PB2026 AF
# Aircraft Procurement Vol I, F015EX P-40 description, PDF p.71, the only page
# that prints it. The quote is verbatim; each [bracketed] gloss is ours. The
# first names the exhibit "This exhibit" means — the PB2026 F-15EX AP
# (F015EX) P-40, P-1 line #7, not the line-44 "F-15EX" P-40 in Vol II — so the
# sentence no longer reads as F015E0's own exhibit (owner, 2026-10-04; #206
# T9, design Q17). The second is read from ERA_PROGRAM_CODES (F015E0 is line 3
# in PB2020–21, line 4 in PB2022).
PROGRAM_NOTES = {
    "F015E0": dict(
        note=("This exhibit [the PB2026 F-15EX AP (F015EX) P-40] does not include the eight aircraft in "
              "Lot 1 which were funded outside this "
              "exhibit in FY 2020 (two test aircraft were purchased with RDT&E funds (PE 0207134F); four "
```

In `src/govbudget/f15_funding_history.py` (:66-70), replace:

```python
# What each note_fact_id must resolve to in the exported registry: the
# jbook_narrative receipt for that paragraph, in that exact PDF.
NOTE_RECEIPTS = {
    "e7d5bcfb4a30f458": dict(kind="jbook_narrative", page_number=71,
                             sha256="528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e"),
}
```

with:

```python
# What each note_fact_id must resolve to in the exported registry: the
# jbook_narrative receipt for that paragraph, in that exact PDF, under the
# budget line whose exhibit prints it (the code the note's first gloss names).
NOTE_RECEIPTS = {
    "e7d5bcfb4a30f458": dict(kind="jbook_narrative", page_number=71, pe_bli="F015EX",
                             sha256="528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e"),
}
```

In `scripts/era/capture_f15_fixtures.py` (docstring, :20-24), replace:

```python
Nothing is written unless all of these hold: the member-only rebuild equals
the full-lake rebuild; the previews rebuilt from the sha-named workbooks equal
the shipped workbook-cells entries; the rebuild from the captured inputs is
byte-identical to the shipped history; and that history's sha256 equals
--expect-sha256 (the value the owner-approved record pins).
```

with:

```python
Nothing is written unless all of these hold: the member-only rebuild equals
the full-lake rebuild; the previews rebuilt from the sha-named workbooks equal
the shipped workbook-cells entries; the rebuild from the captured inputs is
byte-identical to the shipped history; that history's sha256 equals
--expect-sha256 (the value the owner-approved record pins); and the fixture,
gzipped exactly as it is written and read back, rebuilds the shipped history
byte for byte the way tests/test_f15_era_identity.py rebuilds it (ROADMAP
#201: the check used to run on the in-memory rows). The three files are then
written to temporary siblings and moved into place, so a failed write leaves
the old fixtures.
```

In `scripts/era/capture_f15_fixtures.py` (:39-44), replace:

```python
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path
```

with:

```python
import argparse
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path
```

In `scripts/era/capture_f15_fixtures.py` (:155), replace:

```python
def main(argv: list[str] | None = None) -> int:
```

with:

```python
def rebuild_from_fixture_bytes(gz: bytes) -> bytes:
    """The history tests/test_f15_era_identity.py rebuilds from these fixture bytes."""
    inputs = json.loads(gzip.decompress(gz))
    payload, _, _, _ = build_history(
        inputs["source_rows"], inputs["series"], retrieved_at=inputs["retrieved_at"],
        current_fact_ids=set(inputs["current_fact_ids"]))
    rebuilt, _, _ = build_program_matrix(
        payload, inputs["previews"], existing_citations=inputs["registry"],
        retrieved_at=inputs["retrieved_at"])
    return _json_bytes(rebuilt)


def round_trip_check(fixture: dict, shipped: bytes) -> bytes:
    """gzip the fixture exactly as it will be written, read it back and rebuild;
    refuse unless that equals the shipped history. Returns the gzip bytes."""
    gz = gzip.compress(_json_bytes(fixture), mtime=0)
    if rebuild_from_fixture_bytes(gz) != shipped:
        raise SystemExit("capture_f15_fixtures: the round-tripped fixture does not rebuild the shipped history")
    return gz


def write_fixtures(out_dir: Path, files: dict[str, bytes]) -> None:
    """Write every file to a temporary sibling first, then os.replace each into
    place; a failed write leaves the old fixtures and no temporary behind."""
    out_dir.mkdir(parents=True, exist_ok=True)
    temps = {name: out_dir / f".{name}.tmp" for name in files}
    try:
        for name, data in files.items():
            temps[name].write_bytes(data)
        for name in files:
            os.replace(temps[name], out_dir / name)
    finally:
        for tmp in temps.values():
            tmp.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
```

In `scripts/era/capture_f15_fixtures.py` (in `main`, :168-171), replace:

```python
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "history.json").write_bytes(shipped)
    (args.out_dir / "history.sha256").write_text(actual + "\n")
    (args.out_dir / "builder_inputs.json.gz").write_bytes(gzip.compress(_json_bytes(fixture), mtime=0))
```

with:

```python
    gz = round_trip_check(fixture, shipped)
    write_fixtures(args.out_dir, {"history.json": shipped, "history.sha256": (actual + "\n").encode(),
                                  "builder_inputs.json.gz": gz})
```

- [ ] **Step 4: Run the tests**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/test_f15_funding_history.py tests/test_capture_f15_fixtures.py tests/test_f15_era_identity.py -q`
Expected: `3 failed`, exactly the three `test_f15_era_identity.py` tests named above (overlay: `3 failed, 40 passed`).
Anything else failing is a defect of this task.

- [ ] **Step 5: Preview the re-pin hermetically and record its sha for Task 21**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - <<'EOF'
"""Hermetic preview of the T9 re-pin: rebuild the F-15 history from the committed
fixtures with this task's code, list every leaf that differs from the committed
history.json, and print the sha256 Task 21 passes to capture --expect-sha256."""
import gzip
import hashlib
import json
from pathlib import Path

from govbudget.f15_funding_history import _json_bytes, build_history, build_program_matrix

fx = Path("tests/fixtures/f15")
inputs = json.loads(gzip.decompress((fx / "builder_inputs.json.gz").read_bytes()))
payload, _, _, _ = build_history(inputs["source_rows"], inputs["series"], retrieved_at=inputs["retrieved_at"],
                                 current_fact_ids=set(inputs["current_fact_ids"]))
rebuilt, _, _ = build_program_matrix(payload, inputs["previews"], existing_citations=inputs["registry"],
                                     retrieved_at=inputs["retrieved_at"])
data = _json_bytes(rebuilt)
old = json.loads((fx / "history.json").read_bytes())


def diff(a, b, at=()):
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in sorted(set(a) | set(b)) for d in diff(a.get(k), b.get(k), (*at, k))]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff(x, y, (*at, i))]
    return [] if a == b else [at]


print("diff leaves:", diff(old, json.loads(data)))
print("bytes:", len((fx / "history.json").read_bytes()), "->", len(data))
print("hermetic sha256:", hashlib.sha256(data).hexdigest())
EOF
```
Expected (measured 2026-10-13 on the overlay):

```
diff leaves: [('programs', 7, 'note')]
bytes: 139024 -> 139061
hermetic sha256: d0de9e8bc6466de6d213f4dd2782faa467b82f961a26169eaf1345362f078d8f
```
Any other leaf in the list means the note change moved something else: stop. Put the printed sha in the commit body
(Step 6); Task 21 P3 captures with `--expect-sha256` set to it.

- [ ] **Step 6: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/f15_funding_history.py GovBudget/scripts/era/capture_f15_fixtures.py GovBudget/tests/test_f15_funding_history.py GovBudget/tests/test_capture_f15_fixtures.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(f15): the F015E0 note names its exhibit, the PB2026 F-15EX AP (F015EX) P-40; capture round-trips its fixture (#206 T9, #201)" -m "Owner 2026-10-04 (Q17 amended). NOTE_RECEIPTS checks pe_bli F015EX; with the [..] glosses stripped the note is the printed sentence. capture_f15_fixtures rebuilds from the gzip round-trip and writes through temporaries. Hermetic re-pin sha d0de9e8bc6466de6d213f4dd2782faa467b82f961a26169eaf1345362f078d8f (only programs[7].note changes); the three test_f15_era_identity goldens fail until Task 21 P3 re-pins." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
