<!-- Part of the families piece-1 follow-ups plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first. Drafted by G4 (2026-10-13). Task 4 is split into 04a (propose and the shared module), 04b (ratify and the build order) and 04c (the review page); run them in that order. -->

### Task 4a: Era-map guards — `propose`, the successor search, atomic writes (#198)

**Spec:** [`2026-10-04-families-piece1-followups-design.md`](../../../specs/2026-10-04-families-piece1-followups-design.md) §6.2 "propose" (rule 4(b) via `_org_grain_clashes`, run in `propose` so clashing class-ruled chains go to review, red case the DISA and TJS A1 chains on code `15`; no silent overturns, with the old class row leaving the seed — Q25; atomic writes of all five outputs; `--decided-on` defaults to `CLASS_RULINGS_DECIDED_ON`; the successor search prefers the literal form across files; `"` escaped in evidence quotes; `EraKeyConflict` moves into `era_keys`), "Review page" (the own-account reason reworded; the rest is Task 4c), "Acceptance" (a scratch `propose` against the live lake reproduces the seed byte for byte, before the #194 write); §4.5 (why a changed class result must go to review); §2.3 Q25. Not here: "UNSAFE narrows to (0390D, RDT&E)" is Task 8's (it needs Task 6's route-safe seed); §6.9 keeps the digits-only successor search and the dict field in the frozen `Chain`.

**Files:**
- Modify: `src/govbudget/jbooks/era_keys.py` (a class inserted before `def era_procurement_key(account: str, org: str, line_number: str) -> str:`)
- Modify: `src/govbudget/jbooks/p1_loader.py` (the `era_keys` import, about line 13; the `class EraKeyConflict(ValueError):` block, about lines 96–100)
- Modify: `src/govbudget/jbooks/era_map.py` — imports (about lines 31–45); `search_successors` (about lines 634–703); `_prefill`'s two own-account returns (anchor on `f"{rule}: the code's own account ({dest_label}); also"` and on `f" by {', '.join(others) or 'no other account'} — confirm"`); `write_csv` (about lines 891–898); `propose` (four anchored edits, about lines 1286–1423); new helpers after `_row_editions` (anchor on `    return {k.edition for k in keys_by_chain.get(cid, ()) if first <= k.edition <= last}`)
- Modify: `src/govbudget/cli.py` — the `era-map propose --decided-on` argument (anchor on `"--decided-on", dest="decided_on", default="2026-10-02",`) and `cmd_era_map`'s propose call (anchor on `            out_dir=out_dir, seed_path=seed_path,\n            decided_on=date.fromisoformat(args.decided_on),`)
- Test: `tests/jbooks/test_era_map_propose.py` (imports, about lines 3–10; append at the end)
- Test: `tests/jbooks/test_era_map_ratify.py` (append at the end)
- Create: `tests/jbooks/test_era_map_198_gaps.py` — two of #198's test gaps the piece-1 reviews of Tasks 11 and 15 named ("a mere mention is not a successor"; "the lake is opened read-only"), in a file of their own so no other task's per-file count moves

**Interfaces:**
Consumes: Task 1's workspace. Independent of Tasks 2, 3 and 5. (If Task 3 ran first, `p1_loader.py` holds `class P1KeyConflict` between `P1Parse` and `_slug`; the `EraKeyConflict` removal below is anchored on that class's own lines and leaves `P1KeyConflict` in place.)
Produces (Task 8 adds the alias on top; Task 10 renders and ratifies B7 through these paths; Task 4b reuses the helpers):
- `govbudget.jbooks.era_keys.EraKeyConflict(ValueError)`; `govbudget.jbooks.p1_loader.EraKeyConflict` is the same object (re-exported); `govbudget.jbooks.era_map` no longer imports `p1_loader`.
- `era_map._org_grain_clashes(rows: Sequence[Mapping[str, str]], keys_by_chain: Mapping[str, Sequence[EraKey]], collision_codes: frozenset[str]) -> list[tuple[Mapping, Mapping, list[int]]]` — every pair `(a, b, shared editions)` of `same_program` rows of two different organizations on one `_page_grain`, in `rows` order.
- `era_map._clash_message(a, b, shared, collision_codes) -> str` — `"<a decision_id>: same_program collides with <b decision_id> — page <code>[ (<acct>/<org>)] would sum <a org> and <b org> in PB<e>[, …]; decide history_only for the organization whose page it is not"`.
- `era_map._hold_for_review(ruled, *, existing, owner_rows, keys_by_chain, collision_codes) -> tuple[list[dict], dict[str, tuple[str, str, str, str, str]]]` — the class-ruled rows `propose` keeps, and `{chain_id: (proposed_decision, reason, program_account, program_org, left_ruling_reason)}` for the ones it sends to review instead.
- `propose(...)`: same signature. A chain whose class result differs (decision, ruling or pins) from a class row the seed holds for it goes to `review.csv`, proposed as the new class result, with the reason `"<rule>: class result <decision> (<ruling>) differs from the seeded <old decision> (<old ruling>, <old decided_on>) — confirm or keep the seeded decision; no silent overturn"`, and `chains.csv` `left_ruling_reason` `"class result differs from the seeded decision"`; its old class row leaves the seed (Q25), so `era-map check --strict` and verify-era-map leg b fail on its keys until the owner's batch is ratified. A class-ruled `same_program` row that clashes under rule 4(b) goes to review with no proposal, the reason `"<rule>: " + _clash_message(…)` and `left_ruling_reason` `"one organization per page grain (rule 4(b))"`. Nothing is written until all five outputs (seed, `review.csv`, `chains.csv`, `keys.csv`, `counts.json`) are computed; each is then written through a temporary file and `os.replace`. `counts.json`'s keys do not change.
- `era_map.write_csv(path, columns, rows)` writes through `.<name>.tmp` + `os.replace` (so `write_seed` and `review_batch_page answer` are atomic too); new `era_map._csv_text(columns, rows) -> str`, `era_map._atomic_write_text(path, text) -> None`.
- `search_successors`: a literal-form match beats a short-form one wherever it is found; `successor_evidence` ends `quote="<sentence with \" and \\ escaped>"` (the `quote` field stays raw).
- `govbudget era-map propose` without `--decided-on` dates class-ruled rows `era_map.CLASS_RULINGS_DECIDED_ON`.

Measured for this task (2026-10-13, outside :12–:22): a scratch `era_map.propose(duckdb_path=config.DUCKDB_PATH, raw_docs_dir=config.RAW_DOCS_DIR, out_dir=<scratch>/out, seed_path=<scratch>/seed.csv, decided_on=era_map.CLASS_RULINGS_DECIDED_ON)` on a copy of the committed seed ran in 42 s and reproduced the committed seed and all four of `data/research/era_map/{review.csv,chains.csv,keys.csv,counts.json}` byte for byte (`6927 1253 {'R-DEC-ERA-SAME': 810, 'R-DEC-ERA-EXCLUDE': 47, 'R-DEC-ERA-HISTORY': 271} 0 125`: era keys, chains, class rulings, review rows, owner-batch chains). The live seed has `15|0300D|DISA|2021-2023` `same_program` R-DEC-ERA-SAME and `15|0300D|TJS|2020-2023` `history_only` (owner, "…page 15 is DISA's"), so no live chain is held by the new rules. `python -c "import govbudget.jbooks.era_map"` loads `govbudget.jbooks.p1_loader` (and with it psycopg and openpyxl) today. Test counts: `tests/jbooks/test_era_map_propose.py` 25, `tests/jbooks/test_era_map_ratify.py` 28, `tests/jbooks/test_era_map.py` 51, `tests/test_era_review_batch_page.py` 41, `tests/jbooks/test_p1_loader_era.py` 12 (13 once Task 3 has landed), `tests/jbooks/test_s1_reload_era_p1.py` 13 — all pass.

- [ ] **Step 1: Write the failing tests**

In `tests/jbooks/test_era_map_propose.py`, replace:

```python
import csv
import json
from datetime import date
from decimal import Decimal

import pytest
```

with:

```python
import csv
import json
import subprocess
import sys
from datetime import date
from decimal import Decimal

import duckdb
import pytest
```

Append at the end of `tests/jbooks/test_era_map_propose.py`:

```python


# ---------------------------------------------------------------------------
# ROADMAP #198 (follow-ups spec 2026-10-04 §6.2, §4.5, Q25)
# ---------------------------------------------------------------------------

def test_era_map_does_not_import_the_workbook_loader():
    code = ("import sys, govbudget.jbooks.era_map as m;"
            " print('govbudget.jbooks.p1_loader' in sys.modules, m.EraKeyConflict.__module__)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=True).stdout.split()
    assert out == ["False", "govbudget.jbooks.era_keys"]


def test_p1_loader_re_exports_the_era_keys_conflict():
    from govbudget.jbooks import era_keys, p1_loader

    assert p1_loader.EraKeyConflict is era_keys.EraKeyConflict is EraKeyConflict


# The live PB2021 shape (code 15: DISA's page, TJS's line), moved into this
# world's PB2022: both organizations print 15 under one title in the era
# edition and in PB2026, so both chains are A1 and class-ruled same_program.
CLASH_15 = [
    ("P-1", "2022", "0300D", "Acct", "DISA", "01", "BA", "0300D-DISA-L30", "Major Equipment",
     "fy_2020_actuals", "70", "22", "Exhibit P-1", "O30", "15"),
    ("P-1", "2022", "0300D", "Acct", "TJS", "01", "BA", "0300D-TJS-L31", "Major Equipment",
     "fy_2020_actuals", "9", "22", "Exhibit P-1", "O31", "15"),
    ("P-1", "2026", "0300D", "Acct", "DISA", "01", "BA", "15", "Major Equipment",
     "fy_2024_actuals", "80", "26", "Exhibit P-1", "O9", "15"),
    ("P-1", "2026", "0300D", "Acct", "TJS", "01", "BA", "15", "Major Equipment",
     "fy_2024_actuals", "10", "26", "Exhibit P-1", "O10", "15"),
]


def test_propose_sends_two_organizations_on_one_page_to_review(tmp_path, monkeypatch):
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"15", "20"}))
    db = make_lake(tmp_path / "lake", extra_era=CLASH_15)
    con = duckdb.connect(str(db))
    con.execute("insert into dim_programs values ('15', '0300D', 'DISA')")   # page 15 is DISA's
    con.close()
    out = tmp_path / "research" / "era_map"
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    era_map.propose(duckdb_path=db, raw_docs_dir=make_raw_docs(tmp_path), out_dir=out,
                    seed_path=seed, decided_on=ON)
    assert not [r for r in rows(seed) if r["line_item_code"] == "15"]
    review = {r["chain_id"]: r for r in rows(out / "review.csv")}
    for cid in ("15|0300D|DISA", "15|0300D|TJS"):
        assert review[cid]["proposed_decision"] == ""
        assert review[cid]["reason"] == (
            "A1: 15|0300D|DISA|2022-2022: same_program collides with 15|0300D|TJS|2022-2022"
            " — page 15 would sum DISA and TJS in PB2022; decide history_only for the"
            " organization whose page it is not")
    chains = {r["chain_id"]: r for r in rows(out / "chains.csv")}
    assert chains["15|0300D|TJS"]["left_ruling_reason"] == (
        "one organization per page grain (rule 4(b))")


def test_propose_never_silently_overturns_a_seeded_class_decision(tmp_path):
    _c, out, seed = run(tmp_path)
    seeded = rows(seed)
    ata = next(r for r in seeded if r["line_item_code"] == "ATA000")
    ata.update(decision="history_only", ruling="R-DEC-ERA-HISTORY")   # as an earlier lake ruled it
    era_map.write_seed(seed, seeded)
    db = tmp_path / "lake" / "duckdb" / "govbudget.duckdb"
    era_map.propose(duckdb_path=db, raw_docs_dir=tmp_path / "raw_docs", out_dir=out,
                    seed_path=seed, decided_on=ON)
    assert not [r for r in rows(seed) if r["line_item_code"] == "ATA000"]   # Q25
    held = {r["chain_id"]: r for r in rows(out / "review.csv")}["ATA000|3010F|"]
    assert held["proposed_decision"] == "same_program"
    assert held["reason"] == (
        "A1: class result same_program (R-DEC-ERA-SAME) differs from the seeded"
        " history_only (R-DEC-ERA-HISTORY, 2026-10-02) — confirm or keep the seeded"
        " decision; no silent overturn")
    chains = {r["chain_id"]: r for r in rows(out / "chains.csv")}
    assert chains["ATA000|3010F|"]["left_ruling_reason"] == (
        "class result differs from the seeded decision")
    undecided = era_map.check(duckdb_path=db, seed_path=seed)["undecided"]
    assert "ATA000|3010F|" in [u["chain_id"] for u in undecided]


def test_propose_writes_nothing_when_a_later_output_fails(tmp_path, monkeypatch):
    _c, out, seed = run(tmp_path)
    era_map.write_seed(seed, [r for r in rows(seed) if r["line_item_code"] != "ATA000"])
    before = {p.name: p.read_bytes() for p in [seed, *sorted(out.iterdir())]}

    def boom(code):
        raise RuntimeError("counts.json failed")

    monkeypatch.setattr(era_map, "is_successor_searchable", boom)   # read only for counts.json
    with pytest.raises(RuntimeError, match="counts.json failed"):
        era_map.propose(duckdb_path=tmp_path / "lake" / "duckdb" / "govbudget.duckdb",
                        raw_docs_dir=tmp_path / "raw_docs", out_dir=out, seed_path=seed,
                        decided_on=ON)
    assert {p.name: p.read_bytes() for p in [seed, *sorted(out.iterdir())]} == before


def test_write_csv_replaces_the_file_whole_or_not_at_all(tmp_path, monkeypatch):
    path = tmp_path / "x.csv"
    era_map.write_csv(path, ("a",), [{"a": "1"}])

    def fail(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(era_map.os, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        era_map.write_csv(path, ("a",), [{"a": "2"}])
    assert path.read_text() == "a\n1\n"
    assert [p.name for p in tmp_path.iterdir()] == ["x.csv"]


def test_a_literal_form_in_a_later_file_beats_an_earlier_short_form(tmp_path):
    short = tmp_path / "fy2026" / "a" / "xml" / "U_PROCUREMENT_JB_X_ARMY_PB_2026.xml"
    literal = tmp_path / "fy2025" / "a" / "xml" / "U_PROCUREMENT_JB_X_ARMY_PB_2025.xml"
    for p in (short, literal):
        p.parent.mkdir(parents=True)
    short.write_text("<a>Budget line D15610 is a continuation of budget line D15603.</a>\n")
    literal.write_text("<a>Line 5600D15603 continues under 5731D15610 from FY 2021.</a>\n")
    got = search_successors([chain("5600D15603", "2035A")], raw_docs_dir=tmp_path,
                            modern=modern(("5731D15610", "2035A")))
    s = got["5600D15603|2035A|"]
    assert (s["successor_code"], s["matched_form"], s["xml"]) == (
        "5731D15610", "literal", "fy2025/a/xml/U_PROCUREMENT_JB_X_ARMY_PB_2025.xml")


def test_a_double_quote_in_the_successor_sentence_is_escaped(tmp_path):
    xml = tmp_path / "fy2026" / "dw" / "xml" / "U_PROCUREMENT_JB_X_DW_PB_2026.xml"
    xml.parent.mkdir(parents=True)
    xml.write_text('<a>Line ABC123 continues under the "DEF456" line from FY 2024.</a>\n')
    got = search_successors([chain("ABC123", "0300D")], raw_docs_dir=tmp_path,
                            modern=modern(("DEF456", "0300D")))
    s = got["ABC123|0300D|"]
    assert s["quote"] == 'Line ABC123 continues under the "DEF456" line from FY 2024.'
    assert s["successor_evidence"].endswith(
        'quote="Line ABC123 continues under the \\"DEF456\\" line from FY 2024."')


def test_prefill_own_account_with_no_other_account_says_so(monkeypatch):
    # The live GPS03C|3022F| shape: R3 because the era edition printed the
    # code in two accounts, but PB2024-26 print it in its own account only.
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset())
    era = [ek(2022, "3022F", "AF", 9, "GPS03C", "GPS III Space Segment"),
           ek(2022, "3021F", "AF", 3, "GPS03C", "GPS III Space Segment")]
    modern_lines = [ml(2026, "GPS03C", "3022F", "F", "GPS III Space Segment")]
    decision, reason, pa, po = _prefill_for(era, modern_lines, chain_id="GPS03C|3022F|")
    assert decision == "same_program"
    assert reason == "R3: the code's own account (3022F); no other PB2024-26 account prints it"
    assert (pa, po) == ("", "")
```

Append at the end of `tests/jbooks/test_era_map_ratify.py`:

```python


def test_cli_propose_defaults_to_the_class_rulings_date(cli_world, capsys, monkeypatch):
    # ROADMAP #198: the default was the literal "2026-10-02", a second copy
    # of era_map.CLASS_RULINGS_DECIDED_ON.
    from govbudget.cli import main

    monkeypatch.setattr(era_map, "CLASS_RULINGS_DECIDED_ON", date(2027, 1, 2))
    main(["era-map", "propose"])
    seed = cli_world / "dbt" / "seeds" / "p1_era_code_decisions.csv"
    assert {r["decided_on"] for r in read(seed)} == {"2027-01-02"}
```

Create `tests/jbooks/test_era_map_198_gaps.py`:

```python
"""Two ROADMAP #198 test gaps (families piece-1 follow-ups Task 4a; the piece-1
reviews of plan Tasks 11 and 15 named them): a sentence that merely mentions an
era code beside a PB2024-26 code is not a successor statement, and `propose`
opens the warehouse read-only. Both already hold; these tests pin them."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import duckdb

from govbudget.jbooks import era_map
from govbudget.jbooks.era_map import Chain, ModernLine, search_successors
from jbooks.era_map_fixtures import make_lake, make_raw_docs


def _era_only_chain(code: str, account: str) -> Chain:
    return Chain(chain_id=f"{code}|{account}|", line_item_code=code, account=account,
                 organization="", keys=((2022, "k"),), classes=frozenset({"H"}),
                 titles_by_edition={2022: "t"}, actuals_k=Decimal(0), n_keys=1,
                 keys_sha256="")


def test_a_mere_mention_is_not_a_successor(tmp_path):
    xml = tmp_path / "fy2026" / "n" / "xml" / "U_PROCUREMENT_JB_X_NAVY_PB_2026.xml"
    xml.parent.mkdir(parents=True)
    chains = [_era_only_chain("ABC123", "0300D")]
    modern = [ModernLine(edition=2026, code="DEF456", account="0300D", organization="A",
                         title="t")]
    xml.write_text("<a>Line ABC123 and line DEF456 are both shown in this exhibit.</a>\n"
                   "<a>Funds for ABC123 moved to DEF456 in FY 2024.</a>\n")
    assert search_successors(chains, raw_docs_dir=tmp_path, modern=modern) == {}
    # the same two codes with continuation wording are a successor statement
    xml.write_text("<a>Line ABC123 continues under line DEF456 from FY 2024.</a>\n")
    got = search_successors(chains, raw_docs_dir=tmp_path, modern=modern)
    assert {cid: s["successor_code"] for cid, s in got.items()} == {"ABC123|0300D|": "DEF456"}


def test_propose_opens_the_lake_read_only(tmp_path, monkeypatch):
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"20"}))  # the miniature world
    db = make_lake(tmp_path / "lake")
    raw = make_raw_docs(tmp_path)
    real, opened = duckdb.connect, []

    def spy(database=":memory:", *args, **kwargs):
        opened.append((str(database), bool(kwargs.get("read_only", False))))
        return real(database, *args, **kwargs)

    monkeypatch.setattr(duckdb, "connect", spy)
    era_map.propose(duckdb_path=db, raw_docs_dir=raw, out_dir=tmp_path / "out",
                    seed_path=tmp_path / "seed.csv", decided_on=date(2026, 10, 2))
    lake = [read_only for path, read_only in opened if path == str(db)]
    assert lake and all(lake), opened
```

Run:

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_era_map_propose.py tests/jbooks/test_era_map_ratify.py -q 2>&1 | tail -3
GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_era_map_198_gaps.py -q 2>&1 | tail -1
```

Expected: `10 failed, 53 passed` (63 tests). The 10 are the new ones: `['True', 'govbudget.jbooks.p1_loader']`; `AttributeError: module 'govbudget.jbooks.era_keys' has no attribute 'EraKeyConflict'`; the seed still holds both `15` chains; the seed still holds ATA000 (now `same_program`); the seed was rewritten before the failure; `AttributeError: … has no attribute 'os'`; `'short' == 'literal'`; the unescaped quote; `'… also printed by no other account'`; and `{'2026-10-02'} == {'2027-01-02'}`. The second command prints `2 passed`: both gaps already hold at HEAD (G4-3; measured 2026-10-13 on a scratch copy of HEAD and on one with every task of this plan applied, `.superpowers/sdd/2026-10-04-piece1-followups/work/fixpass/`), and the tests keep them held.

- [ ] **Step 2: Move `EraKeyConflict` into `era_keys`**

In `src/govbudget/jbooks/era_keys.py`, replace:

```python
def era_procurement_key(account: str, org: str, line_number: str) -> str:
```

with:

```python
class EraKeyConflict(ValueError):
    """An era key ('{account}-{org}-L{line}') printed more than one budget
    line code, title or budget activity across its rows. The era key is a
    display line; if it ever carries two programs, keying by line number
    would silently merge them, so the parse refuses.

    Defined here, beside the key it is about, so jbooks/era_map.py (a pure
    module) need not import the workbook loader (ROADMAP #198);
    jbooks/p1_loader.py re-exports it."""


def era_procurement_key(account: str, org: str, line_number: str) -> str:
```

In `src/govbudget/jbooks/p1_loader.py`, replace:

```python
from govbudget.jbooks.era_keys import era_procurement_key
```

with:

```python
from govbudget.jbooks.era_keys import EraKeyConflict, era_procurement_key
```

and delete these lines (the class and the two blank lines after it):

```python
class EraKeyConflict(ValueError):
    """An era key ('{account}-{org}-L{line}') printed more than one budget
    line code, title or budget activity across its rows. The era key is a
    display line; if it ever carries two programs, keying by line number
    would silently merge them, so the parse refuses."""


```

In `src/govbudget/jbooks/era_map.py`, replace:

```python
import csv
import hashlib
import json
import re
from collections import defaultdict
```

with:

```python
import csv
import hashlib
import io
import json
import os
import re
from collections import defaultdict
```

and replace:

```python
from govbudget.jbooks.collision_keys import require_resolved
from govbudget.jbooks.era_keys import is_era_procurement_key
from govbudget.jbooks.p1_loader import EraKeyConflict
```

with:

```python
from govbudget.jbooks.collision_keys import require_resolved
from govbudget.jbooks.era_keys import EraKeyConflict, is_era_procurement_key
```

- [ ] **Step 3: The successor search — literal first, escaped quotes**

In `search_successors`, replace:

```python
    names several). The first qualifying sentence in successor_xml_files
    order wins."""
```

with:

```python
    names several). The first qualifying sentence in successor_xml_files
    order wins, except that a literal-form match beats a short-form one
    wherever it is found (ROADMAP #198)."""
```

replace:

```python
    found: dict[str, dict] = {}
    for xml in successor_xml_files(raw_docs_dir):
        if len(found) == len(targets):
            break
```

with:

```python
    found: dict[str, dict] = {}
    for xml in successor_xml_files(raw_docs_dir):
        if len(found) == len(targets) and all(
                s["matched_form"] == "literal" for s in found.values()):
            break
```

replace:

```python
                for cid, form in era_forms.get(token, ()):
                    if cid in found:
                        continue
```

with:

```python
                for cid, form in era_forms.get(token, ()):
                    prior = found.get(cid)
                    # Literal before short, across sentences and files
                    # (ROADMAP #198): a short-form hit stands only until a
                    # literal one turns up.
                    if prior is not None and (prior["matched_form"] == "literal"
                                              or form != "literal"):
                        continue
```

and replace:

```python
                    parts += [f"form={form}", f'quote="{quote}"']
```

with:

```python
                    # ROADMAP #198: '"' and '\' inside the quote are escaped,
                    # so the evidence string stays one key=value list.
                    escaped = quote.replace("\\", "\\\\").replace('"', '\\"')
                    parts += [f"form={form}", f'quote="{escaped}"']
```

- [ ] **Step 4: Reword the own-account reasons**

In `_prefill`, replace:

```python
            if is_own:
                others = sorted({a for a, o, _t in destinations if (a, o) != own})
                return ("same_program",
                        f"{rule}: the code's own account ({dest_label}); also"
                        f" printed by {', '.join(others) or 'no other account'}",
                        pa, po)
```

with:

```python
            if is_own:
                others = sorted({a for a, o, _t in destinations if (a, o) != own})
                # ROADMAP #198: "also printed by no other account" read as a
                # contradiction (GPS03C|3022F|, 0182|1508N|).
                printed = (f"also printed by {', '.join(others)}" if others
                           else "no other PB2024-26 account prints it")
                return ("same_program",
                        f"{rule}: the code's own account ({dest_label}); {printed}",
                        pa, po)
```

and replace:

```python
        if is_own:
            others = sorted({a for a, o, _t in destinations if (a, o) != own})
            return ("",
                    f"{rule}: the code's own account ({dest_label}) prints"
                    f" '{dest_title}', not this line's title; also printed"
                    f" by {', '.join(others) or 'no other account'} — confirm"
                    " same_program by hand", pa, po)
```

with:

```python
        if is_own:
            others = sorted({a for a, o, _t in destinations if (a, o) != own})
            printed = (f"also printed by {', '.join(others)}" if others
                       else "no other PB2024-26 account prints it")
            return ("",
                    f"{rule}: the code's own account ({dest_label}) prints"
                    f" '{dest_title}', not this line's title; {printed} — confirm"
                    " same_program by hand", pa, po)
```

- [ ] **Step 5: Atomic CSV writes**

Replace:

```python
def write_csv(path: Path, columns: Sequence[str], rows: Iterable[Mapping]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(columns), lineterminator="\n",
                           extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})
```

with:

```python
def _csv_text(columns: Sequence[str], rows: Iterable[Mapping]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(columns), lineterminator="\n",
                       extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in columns})
    return buf.getvalue()


def _atomic_write_text(path: Path, text: str) -> None:
    """Write text through a temporary file beside path and os.replace, so a
    reader never sees a half-written file (ROADMAP #198)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8", newline="")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def write_csv(path: Path, columns: Sequence[str], rows: Iterable[Mapping]) -> None:
    _atomic_write_text(Path(path), _csv_text(columns, rows))
```

- [ ] **Step 6: Add the shared rule-4(b) and hold helpers**

Replace:

```python
    return {k.edition for k in keys_by_chain.get(cid, ()) if first <= k.edition <= last}


def ratify(
```

with:

```python
    return {k.edition for k in keys_by_chain.get(cid, ()) if first <= k.edition <= last}


def _org_grain_clashes(
    rows: Sequence[Mapping[str, str]],
    keys_by_chain: Mapping[str, Sequence[EraKey]],
    collision_codes: frozenset[str],
) -> list[tuple[Mapping[str, str], Mapping[str, str], list[int]]]:
    """Rule 4(b), one organization per page grain and edition (piece-1 spec
    §5.3; ROADMAP #198): every pair (a, b, shared editions) of same_program
    rows of two different organizations on one page grain (_page_grain)
    whose chains both hold keys in a shared edition, a before b in `rows`
    order. propose checks class-ruled rows with it, ratify batch rows."""
    out: list[tuple[Mapping[str, str], Mapping[str, str], list[int]]] = []
    same = [r for r in rows if r["decision"] == "same_program" and r["organization"]]
    for i, a in enumerate(same):
        for b in same[i + 1:]:
            if (a["organization"] != b["organization"]
                    and _page_grain(a, collision_codes) == _page_grain(b, collision_codes)):
                shared = sorted(_row_editions(a, keys_by_chain)
                                & _row_editions(b, keys_by_chain))
                if shared:
                    out.append((a, b, shared))
    return out


def _clash_message(a: Mapping[str, str], b: Mapping[str, str], shared: Sequence[int],
                   collision_codes: frozenset[str]) -> str:
    code, pin_a, pin_o = _page_grain(a, collision_codes)
    page = f"{code} ({pin_a}/{pin_o})" if pin_o else code
    return (f"{a['decision_id']}: same_program collides with {b['decision_id']} — page"
            f" {page} would sum {a['organization']} and {b['organization']} in"
            f" {', '.join(f'PB{e}' for e in shared)}; decide history_only for the"
            " organization whose page it is not")


def _hold_for_review(
    ruled: Sequence[dict], *, existing: Sequence[Mapping[str, str]],
    owner_rows: Sequence[Mapping[str, str]],
    keys_by_chain: Mapping[str, Sequence[EraKey]], collision_codes: frozenset[str],
) -> tuple[list[dict], dict[str, tuple[str, str, str, str, str]]]:
    """The class-ruled rows propose must NOT write to the seed (ROADMAP #198;
    follow-ups spec §4.5, §6.2, Q25), as (rows kept, {chain_id: (proposed
    decision, reason, program_account, program_org, left_ruling_reason)}):

      * no silent overturn: a chain whose class result differs (decision,
        ruling or pins) from a class row the seed holds for it goes to
        review, proposed as the new class result. Its old class row leaves
        the seed with it, so the owner's batch can be ratified; until then
        `era-map check --strict` fails on its keys (fail-closed).
      * rule 4(b): a class-ruled same_program row that clashes with another
        same_program row (class-ruled or owner-decided) goes to review with
        no proposal.
    """
    prior: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for r in existing:
        if r["ruling"] in CLASS_RULINGS:
            prior[chain_id(r["line_item_code"], r["account"], r["organization"])].append(r)
    held: dict[str, tuple[str, str, str, str, str]] = {}
    for row in ruled:
        cid = chain_id(row["line_item_code"], row["account"], row["organization"])
        moved = [o for o in prior.get(cid, ())
                 if any(o[f] != row[f] for f in
                        ("decision", "ruling", "program_account", "program_org"))]
        if moved:
            old = moved[0]
            held[cid] = (
                row["decision"],
                f"{row['proposed_rule']}: class result {row['decision']} ({row['ruling']})"
                f" differs from the seeded {old['decision']} ({old['ruling']},"
                f" {old['decided_on']}) — confirm or keep the seeded decision;"
                " no silent overturn",
                row["program_account"], row["program_org"],
                "class result differs from the seeded decision",
            )

    def cid_of(r: Mapping[str, str]) -> str:
        return chain_id(r["line_item_code"], r["account"], r["organization"])

    kept = [r for r in ruled if cid_of(r) not in held]
    for a, b, shared in _org_grain_clashes([*owner_rows, *kept], keys_by_chain,
                                           collision_codes):
        for side in (a, b):
            if side["ruling"] in CLASS_RULINGS and cid_of(side) not in held:
                held[cid_of(side)] = (
                    "",
                    f"{side['proposed_rule']}: "
                    + _clash_message(a, b, shared, collision_codes),
                    side["program_account"], side["program_org"],
                    "one organization per page grain (rule 4(b))",
                )
    return [r for r in kept if cid_of(r) not in held], held


def ratify(
```

- [ ] **Step 7: `propose` holds those rows and writes all five files at the end**

In `propose`, replace:

```python
            row["decided_on"] = old["decided_on"]
    write_seed(Path(seed_path), owner_rows + ruled)

    ruled_ids = {chain_id(r["line_item_code"], r["account"], r["organization"]): r
                 for r in ruled}
    review = []
    left_reason: dict[str, str] = {}
    for ch in left:
        keys = keys_by_chain[ch.chain_id]
        ci = info[ch.chain_id]
        decision, reason, pa, po = _prefill(ch, keys, ctx, ci,
                                            inputs.collision_codes,
                                            inputs.modern_pages, org_editions)
        if ch.classes == frozenset({"A1"}):
            left_reason[ch.chain_id] = "collision code without a matching PB2026 page"
```

with:

```python
            row["decided_on"] = old["decided_on"]
    ruled, held = _hold_for_review(
        ruled, existing=existing, owner_rows=owner_rows, keys_by_chain=keys_by_chain,
        collision_codes=inputs.collision_codes)
    left = sorted([*left, *(by_id[cid] for cid in held)], key=lambda c: c.chain_id)

    ruled_ids = {chain_id(r["line_item_code"], r["account"], r["organization"]): r
                 for r in ruled}
    review = []
    left_reason: dict[str, str] = {}
    for ch in left:
        keys = keys_by_chain[ch.chain_id]
        ci = info[ch.chain_id]
        if ch.chain_id in held:
            decision, reason, pa, po, left_reason[ch.chain_id] = held[ch.chain_id]
        else:
            decision, reason, pa, po = _prefill(ch, keys, ctx, ci,
                                                inputs.collision_codes,
                                                inputs.modern_pages, org_editions)
            if ch.classes == frozenset({"A1"}):
                left_reason[ch.chain_id] = "collision code without a matching PB2026 page"
```

Replace:

```python
    out_dir = Path(out_dir)
    write_csv(out_dir / "review.csv", REVIEW_COLUMNS, review)
    chain_rows = []
```

with:

```python
    out_dir = Path(out_dir)
    chain_rows = []
```

Replace:

```python
    write_csv(out_dir / "chains.csv", CHAIN_COLUMNS, chain_rows)
    key_rows = []
```

with:

```python
    key_rows = []
```

Replace:

```python
    key_rows.sort(key=lambda r: (int(r["edition"]), r["era_key"]))
    write_csv(out_dir / "keys.csv", KEY_COLUMNS, key_rows)
```

with:

```python
    key_rows.sort(key=lambda r: (int(r["edition"]), r["era_key"]))
```

Replace:

```python
    (out_dir / "counts.json").write_text(json.dumps(counts, indent=1, sort_keys=True) + "\n")
    return counts
```

with:

```python
    # ROADMAP #198: every output is computed above; only now is anything
    # written, each file whole through a temporary file and os.replace.
    outputs = {
        Path(seed_path): _csv_text(SEED_COLUMNS, sorted(
            owner_rows + ruled, key=lambda r: r["decision_id"])),
        out_dir / "review.csv": _csv_text(REVIEW_COLUMNS, review),
        out_dir / "chains.csv": _csv_text(CHAIN_COLUMNS, chain_rows),
        out_dir / "keys.csv": _csv_text(KEY_COLUMNS, key_rows),
        out_dir / "counts.json": json.dumps(counts, indent=1, sort_keys=True) + "\n",
    }
    for path, text in outputs.items():
        _atomic_write_text(path, text)
    return counts
```

Finally, add one sentence to `propose`'s docstring. Replace:

```python
    class-ruled rows of the seed. Owner batch rows already in the seed
    (ruling not a class ruling) are kept verbatim and their chains are
    neither class-ruled nor re-proposed. Returns the counts dict."""
```

with:

```python
    class-ruled rows of the seed. Owner batch rows already in the seed
    (ruling not a class ruling) are kept verbatim and their chains are
    neither class-ruled nor re-proposed. A class result that would
    overturn a seeded decision, or break rule 4(b), goes to review instead
    (_hold_for_review). Nothing is written until all five outputs are
    computed. Returns the counts dict."""
```

- [ ] **Step 8: `--decided-on` defaults to the constant**

In `src/govbudget/cli.py`, replace:

```python
    em_prop.add_argument(
        "--decided-on", dest="decided_on", default="2026-10-02",
        help="decided_on for class-ruled rows (default: the rulings' approval"
             " date, 2026-10-02)",
    )
```

with:

```python
    em_prop.add_argument(
        "--decided-on", dest="decided_on", default=None,
        help="decided_on for class-ruled rows (default: era_map."
             "CLASS_RULINGS_DECIDED_ON, the rulings' approval date)",
    )
```

and replace:

```python
            out_dir=out_dir, seed_path=seed_path,
            decided_on=date.fromisoformat(args.decided_on),
        )
```

with:

```python
            out_dir=out_dir, seed_path=seed_path,
            decided_on=(date.fromisoformat(args.decided_on) if args.decided_on
                        else era_map.CLASS_RULINGS_DECIDED_ON),
        )
```

- [ ] **Step 9: Run the tests — they pass**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_era_map_propose.py tests/jbooks/test_era_map_ratify.py tests/jbooks/test_era_map.py tests/test_era_review_batch_page.py tests/jbooks/test_p1_loader_era.py tests/jbooks/test_s1_reload_era_p1.py tests/jbooks/test_era_map_198_gaps.py -q 2>&1 | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/jbooks/era_map.py src/govbudget/jbooks/era_keys.py src/govbudget/jbooks/p1_loader.py tests/jbooks/test_era_map_198_gaps.py | tail -1
uvx --offline ruff check --isolated --select F,E9 src/govbudget/cli.py | grep '^Found'
```

Expected: `182 passed` (34 + 29 + 51 + 41 + 12 + 13 + 2; `183 passed` if Task 3 has landed and added its 13th `test_p1_loader_era` test); `All checks passed!`; `Found 5 errors.` (the `cli.py` HEAD baseline).

- [ ] **Step 10: Acceptance — a scratch `propose` on the live lake reproduces all five files**

Read-only on the live lake; writes only under `.proofs/fu-t4a-propose/`. Run before Task 7's write and Task 8's alias (spec §6.2).

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
SCR="${GOVBUDGET_PROOFS:?}/fu-t4a-propose"
rm -rf "${SCR:?}" && mkdir -p "$SCR/out" && cp dbt/seeds/p1_era_code_decisions.csv "$SCR/seed.csv"
uv run --project . python - "$SCR" <<'EOF'
import sys
from pathlib import Path
from govbudget import config
from govbudget.jbooks import era_map
scr = Path(sys.argv[1])
c = era_map.propose(duckdb_path=config.DUCKDB_PATH, raw_docs_dir=config.RAW_DOCS_DIR,
                    out_dir=scr / "out", seed_path=scr / "seed.csv",
                    decided_on=era_map.CLASS_RULINGS_DECIDED_ON)
print(c["era_keys"], c["chains"], c["rulings"], c["review_rows"], c["owner_batch_chains"])
EOF
cmp "$SCR/seed.csv" dbt/seeds/p1_era_code_decisions.csv && echo seed-identical
for f in review.csv chains.csv keys.csv counts.json; do cmp "$SCR/out/$f" "data/research/era_map/$f" && echo "$f identical"; done
ls -A "$SCR/out" | grep -c '\.tmp$'
rm -rf "${SCR:?}"
```

Expected (about 45 s): `6927 1253 {'R-DEC-ERA-SAME': 810, 'R-DEC-ERA-EXCLUDE': 47, 'R-DEC-ERA-HISTORY': 271} 0 125`, then `seed-identical`, `review.csv identical`, `chains.csv identical`, `keys.csv identical`, `counts.json identical`, then `0` (no temporary file left). Any difference means a new rule holds a live chain or changed an output: stop and report the `diff`.

- [ ] **Step 11: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families && git add GovBudget/src/govbudget/jbooks/era_keys.py GovBudget/src/govbudget/jbooks/p1_loader.py GovBudget/src/govbudget/jbooks/era_map.py GovBudget/src/govbudget/cli.py GovBudget/tests/jbooks/test_era_map_propose.py GovBudget/tests/jbooks/test_era_map_ratify.py GovBudget/tests/jbooks/test_era_map_198_gaps.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "fix(era-map): propose holds overturns and rule-4(b) clashes for review, writes atomically; literal successors first; escaped quotes; EraKeyConflict in era_keys; tests pin that a mere mention is not a successor and that propose opens the lake read-only (#198)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `7 files changed`.
