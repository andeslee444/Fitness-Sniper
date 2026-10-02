<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 14: `verify-era-map` legs a–c and its CLI

**Spec:** §8 V4 legs (a) re-read of the seven era P-1 workbooks (key set = 6,927, printed code =
`line_item_code`, title = reviewed), (b) undecided or stale decisions, (c) the map's F-15 rows =
`ERA_MEMBERS` joined to `ERA_PROGRAM_CODES` (31 rows); the CLI with zero-argument defaults and a
single final verdict line (V4); S2 "`verify-era-map` legs a–c".

**Files:**
- Create: `GovBudget/src/govbudget/verify_era_map.py`
- Create: `GovBudget/tests/test_verify_era_map.py`
- Modify: `GovBudget/src/govbudget/cli.py` (new `cmd_verify_era_map` between
  `cmd_verify_lineage`, which ends at line 2429, and `cmd_export_site` at line 2432; new parser
  after `vlin.set_defaults(func=cmd_verify_lineage)` at line 3120)

**Interfaces:** Consumes: table `p1_era_line_map` (Task 13); `p1_loader.parse_p1_rollup(xlsx_path,
*, exhibit, fiscal_year) -> P1Parse` with `P1Parse.rows: list[P1Row]`, `P1Parse.era_line_keying`,
`P1Row.{pe_bli, account, organization, budget_activity, line_item_code, title, source_cells}`
(Task 6); `era_map.SEED_COLUMNS`, `era_map.keys_sha256` (Task 10); seed CSV (Tasks 11/12/15);
existing `f15_funding_history.ERA_MEMBERS` / `ERA_PROGRAM_CODES` (`f15_funding_history.py:30-50`),
`era_keys.is_era_procurement_key` / `era_key_anchor` (`era_keys.py:105-135`),
`rollup_loader.norm_header` (`rollup_loader.py:30-35`), `config.SITE_DIR`, `config.DUCKDB_PATH`,
`config.ROOT`. Produces: `govbudget.verify_era_map` with `LEGS = ("a","b","c","d","e","f")`,
`LEG_NAMES`, `ERA_P1_WORKBOOK_SHA256: dict[int, str]`, `EXPECTED_ERA_KEYS: dict[int, int]`,
`F15_ERA_ROWS = 31`, `DEFAULT_SEED_PATH`, `MAP_COLUMNS`,
`run_verify_era_map(*, site_dir: Path, duckdb_path: Path, seed_path: Path, legs: str = "abcdef") -> dict`
(`{"legs": {leg: {"ok": bool, "detail": {"summary": str, "failures": list[str]}}}, "verdict": "PASS"|"FAIL"}`),
`leg_a_workbooks(*, site_dir, map_rows, workbooks, expected_keys) -> dict`,
`leg_b_decisions(*, map_rows, seed_path) -> dict`, `leg_c_f15(*, map_rows) -> dict`,
`format_report(result: dict) -> list[str]`; CLI `govbudget verify-era-map [--legs abc]`.

The seven workbook shas are the `jbook_documents` rows `fy2017..fy2023/dod/p1_display.xlsx`
(ids 189, 261, 271, 282, 292, 302, 312), each present as `data/site/workbooks/<sha>.xlsx` —
measured read-only on 2026-10-02 from `data/parquet/jbooks/documents.parquet`. In every one,
'Line Number' is column F, 'Line Item' column I and 'Line Item Title' column J (header row 2).

- [ ] **Step 1: Write the failing tests**

Create `GovBudget/tests/test_verify_era_map.py`:

```python
"""verify-era-map legs a–c (families piece 1, spec §8 V4) on a hand-built corpus.

The corpus is built from the F-15 roster itself: for each PB2017–PB2023
edition, a real-layout era P-1 workbook (row 1 banner, row 2 wrapped headers,
column F 'Line Number', column I 'Line Item', column J 'Line Item Title')
holding exactly the ERA_MEMBERS lines with their ERA_PROGRAM_CODES codes —
31 keys — plus, in PB2019, one Army key summed from two cost-type rows and
a Non-Add memo row the loader drops. Each workbook is saved under its own
sha256 in site/workbooks/, the map table is written to a DuckDB file, and
the seed CSV carries one decision per (code, account) chain, hashed with
era_map.keys_sha256. Every leg passes on that corpus and fails on the defect
it exists for.
"""
import csv
import hashlib
from pathlib import Path

import duckdb
import pytest

from govbudget import cli, config, verify_era_map
from govbudget.f15_funding_history import ERA_MEMBERS, ERA_PROGRAM_CODES
from govbudget.jbooks.era_map import SEED_COLUMNS, keys_sha256
from govbudget.verify_era_map import (
    MAP_COLUMNS,
    leg_a_workbooks,
    leg_b_decisions,
    leg_c_f15,
    run_verify_era_map,
)

HEADERS = [
    "Account", "Account Title", "Organization", "Budget\nActivity", "Budget Activity Title",
    "Line\nNumber", "BSA", "BSA Title", "Line Item", "Line Item Title", "Cost\nType",
    "Cost Type Title", "Add/\nNon-Add",
]
HISTORY_CODES = {"F0150P", "F015E0"}


def _rows_for(edition: int) -> list[dict]:
    """Workbook rows (sheet row = 3 + index) for one edition."""
    rows = [dict(account="3010F", org="AF", ba=ba, line=f"{line}  ", code=ERA_PROGRAM_CODES[edition][line],
                 title=title, add="Add", amount=10 * line)
            for line, ba, title in ERA_MEMBERS[edition]]
    if edition == 2019:
        rows += [
            dict(account="2031A", org="ARMY", ba="01", line="1", code="9440A11300",
                 title="Utility F/W Aircraft", add="Add", amount=57529),
            dict(account="2031A", org="ARMY", ba="01", line="1", code="9440A11300",
                 title="Utility F/W Aircraft", add="Add", amount=1000),
            dict(account="2031A", org="ARMY", ba="01", line="1", code="9440A11300",
                 title="Utility F/W Aircraft", add="Non-Add", amount=999999),
        ]
    return rows


def _write_workbook(path: Path, edition: int, rows: list[dict]) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Exhibit P-1"
    ws.append([""] * 10 + ["Total of Displayed Rows"])
    ws.append(HEADERS + [f"FY {edition}\nTotal\nQuantity", f"FY {edition}\nTotal\nAmount"])
    for r in rows:
        ws.append([r["account"], "Procurement", r["org"], r["ba"], "Activity", r["line"], "01",
                   "Sub", r["code"], r["title"], "A", "Weapon System Cost", r["add"], 0, r["amount"]])
    wb.save(path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_map(duckdb_path: Path, rows: list[dict]) -> None:
    con = duckdb.connect(str(duckdb_path))
    types = {"edition": "integer", "keys_sha_ok": "boolean"}
    con.execute("create or replace table p1_era_line_map ("
                + ", ".join(f"{c} {types.get(c, 'varchar')}" for c in MAP_COLUMNS) + ")")
    con.executemany(f"insert into p1_era_line_map values ({', '.join('?' * len(MAP_COLUMNS))})",
                    [[r[c] for c in MAP_COLUMNS] for r in rows])
    con.close()


def _write_seed(seed_path: Path, rows: list[dict]) -> None:
    with open(seed_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SEED_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: (r.get(c) or "") for c in SEED_COLUMNS})


class Corpus:
    def __init__(self, root: Path):
        self.site_dir = root / "site"
        (self.site_dir / "workbooks").mkdir(parents=True)
        self.duckdb_path = root / "duckdb" / "govbudget.duckdb"
        self.duckdb_path.parent.mkdir()
        self.seed_path = root / "p1_era_code_decisions.csv"
        self.shas, self.expected, self.map_rows = {}, {}, []
        for edition in sorted(ERA_MEMBERS):
            rows = _rows_for(edition)
            tmp = root / f"p1_{edition}.xlsx"
            _write_workbook(tmp, edition, rows)
            sha = _sha(tmp)
            tmp.rename(self.site_dir / "workbooks" / f"{sha}.xlsx")
            self.shas[edition] = sha
            keys: dict[str, dict] = {}
            for i, r in enumerate(rows):
                if r["add"] != "Add":
                    continue
                era_key = f"{r['account']}-{r['org']}-L{r['line'].strip()}"
                k = keys.setdefault(era_key, dict(
                    edition=edition, account=r["account"], organization=r["org"],
                    budget_activity=r["ba"], era_key=era_key, line_item_code=r["code"],
                    filed_title=r["title"], source_document_sha256=sha, rows=[]))
                k["rows"].append(3 + i)
            self.expected[edition] = len(keys)
            for k in keys.values():
                k["source_cells"] = ",".join(f"I{n}" for n in k.pop("rows"))
                self.map_rows.append(k)
        chains: dict[tuple, list[dict]] = {}
        for k in self.map_rows:
            chains.setdefault((k["line_item_code"], k["account"]), []).append(k)
        self.seed = []
        for (code, account), keys in sorted(chains.items()):
            first, last = min(k["edition"] for k in keys), max(k["edition"] for k in keys)
            decision = "history_only" if code in HISTORY_CODES else "same_program"
            did = f"{code}|{account}||{first}-{last}"
            self.seed.append(dict(
                decision_id=did, line_item_code=code, account=account,
                first_edition=str(first), last_edition=str(last), decision=decision,
                n_keys=str(len(keys)),
                keys_sha256=keys_sha256((k["edition"], k["era_key"], k["budget_activity"],
                                         k["filed_title"]) for k in keys),
                decided_on="2026-10-02", decided_by="owner",
                ruling="R-DEC-ERA-HISTORY" if decision == "history_only" else "R-DEC-ERA-SAME"))
            for k in keys:
                k.update(program_key=code, program_account=None, program_org=None,
                         decision=decision, decision_id=did,
                         ruling=self.seed[-1]["ruling"], keys_sha_ok=True, successor_code=None)
        self.save()

    def save(self) -> None:
        _write_map(self.duckdb_path, self.map_rows)
        _write_seed(self.seed_path, self.seed)

    def row(self, edition: int, era_key: str) -> dict:
        return next(r for r in self.map_rows if (r["edition"], r["era_key"]) == (edition, era_key))

    def leg_a(self, **overrides) -> dict:
        args = dict(site_dir=self.site_dir, map_rows=verify_era_map._read_map(self.duckdb_path),
                    workbooks=self.shas, expected_keys=self.expected)
        args.update(overrides)
        return leg_a_workbooks(**args)

    def leg_b(self) -> dict:
        return leg_b_decisions(map_rows=verify_era_map._read_map(self.duckdb_path),
                               seed_path=self.seed_path)

    def leg_c(self) -> dict:
        return leg_c_f15(map_rows=verify_era_map._read_map(self.duckdb_path))


@pytest.fixture
def corpus(tmp_path) -> Corpus:
    return Corpus(tmp_path)


def _failures(result: dict) -> list[str]:
    return result["detail"]["failures"]


def test_the_fixture_is_the_f15_roster_plus_one_army_key(corpus):
    assert sum(corpus.expected.values()) == 32
    assert corpus.row(2019, "2031A-ARMY-L1")["source_cells"] == "I7,I8"


# --- leg a -----------------------------------------------------------------

def test_leg_a_passes_on_a_consistent_corpus(corpus):
    result = corpus.leg_a()
    assert result["ok"], _failures(result)
    assert result["detail"]["summary"].startswith("workbooks=7 keys_checked=32 expected=32")


def test_leg_a_fails_when_the_map_misreads_a_printed_code(corpus):
    corpus.row(2021, "3010F-AF-L4")["line_item_code"] = "F01500"
    corpus.save()
    failures = _failures(corpus.leg_a())
    assert any(f.startswith("2021/3010F-AF-L4: workbook ('3010F', 'AF', '01', 'F015EX', 'F-15EX')")
               for f in failures)
    assert "2021/3010F-AF-L4: I4 prints 'F015EX', the map says 'F01500'" in failures


def test_leg_a_fails_when_a_title_differs_from_the_workbook(corpus):
    corpus.row(2019, "3010F-AF-L30")["filed_title"] = "F-15 EPAWSS"
    corpus.save()
    assert ("2019/3010F-AF-L30: row 4 title 'F-15 EPAW' != filed_title 'F-15 EPAWSS'"
            in _failures(corpus.leg_a()))


def test_leg_a_fails_on_wrong_cells(corpus):
    corpus.row(2019, "2031A-ARMY-L1")["source_cells"] = "I7"
    corpus.save()
    assert ("2019/2031A-ARMY-L1: map cells 'I7' != workbook rows 'I7,I8'"
            in _failures(corpus.leg_a()))


def test_leg_a_fails_on_a_missing_key_and_an_edition_without_a_workbook(corpus):
    corpus.map_rows.remove(corpus.row(2019, "2031A-ARMY-L1"))
    corpus.map_rows.append(dict(corpus.row(2017, "3010F-AF-L21"), edition=2016))
    corpus.save()
    failures = _failures(corpus.leg_a())
    assert "2019/2031A-ARMY-L1: in the workbook, missing from the map" in failures
    assert ("2016: the map has 1 keys for an edition with no pinned era P-1 workbook"
            in failures)


def test_leg_a_fails_when_the_corpus_count_differs(corpus):
    result = corpus.leg_a(expected_keys={**corpus.expected, 2019: 989})
    assert "2019: the workbook parses to 5 era keys, the corpus has 989" in _failures(result)


def test_leg_a_fails_when_the_workbook_bytes_do_not_match_the_pin(corpus):
    path = corpus.site_dir / "workbooks" / f"{corpus.shas[2020]}.xlsx"
    path.write_bytes(path.read_bytes() + b"\0")
    failures = _failures(corpus.leg_a())
    assert any(f.startswith(f"2020: {corpus.shas[2020]}.xlsx hashes to ") for f in failures)


def test_leg_a_fails_when_a_workbook_is_missing(corpus):
    (corpus.site_dir / "workbooks" / f"{corpus.shas[2023]}.xlsx").unlink()
    assert any(f.startswith("2023: workbook missing: ") for f in _failures(corpus.leg_a()))


# --- leg b -----------------------------------------------------------------

def test_leg_b_passes_on_a_consistent_corpus(corpus):
    result = corpus.leg_b()
    assert result["ok"], _failures(result)
    assert result["detail"]["summary"] == "keys=32 undecided=0 decisions=6 failures=0"


def test_leg_b_fails_on_an_undecided_key(corpus):
    corpus.row(2019, "2031A-ARMY-L1").update(
        decision="undecided", decision_id=None, program_key=None, ruling=None, keys_sha_ok=None)
    corpus.seed = [s for s in corpus.seed if s["line_item_code"] != "9440A11300"]
    corpus.save()
    result = corpus.leg_b()
    assert _failures(result) == ["2019/2031A-ARMY-L1 (9440A11300): undecided"]


def test_leg_b_fails_on_a_stale_sql_hash(corpus):
    corpus.row(2019, "2031A-ARMY-L1")["keys_sha_ok"] = False
    corpus.save()
    assert ("2019/2031A-ARMY-L1: keys_sha_ok=False under 9440A11300|2031A||2019-2019"
            " (stale decision)") in _failures(corpus.leg_b())


def test_leg_b_recomputes_the_hash_in_python(corpus):
    seed_row = next(s for s in corpus.seed if s["line_item_code"] == "F15EWS")
    seed_row["keys_sha256"] = "0" * 64
    corpus.save()
    failures = _failures(corpus.leg_b())
    assert len(failures) == 1 and failures[0].startswith("F15EWS|3010F||2019-2023: binds 5 keys")


def test_leg_b_fails_on_a_seed_row_that_binds_nothing(corpus):
    corpus.seed.append(dict(corpus.seed[0], decision_id="ZZZ|3010F||2017-2017", line_item_code="ZZZ"))
    corpus.save()
    assert "ZZZ|3010F||2017-2017: in the seed, binds no era key" in _failures(corpus.leg_b())


def test_leg_b_fails_on_a_map_built_from_another_seed(corpus):
    next(s for s in corpus.seed if s["line_item_code"] == "F0150P")["decision"] = "exclude_reused_code"
    corpus.save()
    assert any(f.startswith("F0150P|3010F||2017-2020: map ('history_only'")
               for f in _failures(corpus.leg_b()))


def test_leg_b_fails_on_an_unreadable_seed(corpus):
    corpus.seed_path.write_text("decision_id,decision\n")
    result = corpus.leg_b()
    assert not result["ok"] and result["detail"]["summary"] == "seed unreadable"


# --- leg c -----------------------------------------------------------------

def test_leg_c_passes_on_the_roster(corpus):
    result = corpus.leg_c()
    assert result["ok"], _failures(result)
    assert result["detail"]["summary"] == "expected=31 map_rows=31 failures=0"


def test_leg_c_fails_on_a_missing_member_and_an_unreviewed_f15_title(corpus):
    corpus.map_rows.remove(corpus.row(2022, "3010F-AF-L4"))
    corpus.row(2019, "2031A-ARMY-L1")["filed_title"] = "F-15 Training Support"
    corpus.save()
    failures = _failures(corpus.leg_c())
    assert "missing from the map: (2022, '3010F-AF-L4', '01', 'F-15e', 'F015E0')" in failures
    assert ("in the map, not in ERA_MEMBERS x ERA_PROGRAM_CODES:"
            " (2019, '2031A-ARMY-L1', '01', 'F-15 Training Support', '9440A11300')") in failures


def test_leg_c_fails_when_an_f15_key_does_not_carry_its_code(corpus):
    corpus.row(2017, "3010F-AF-L69").update(decision="exclude_reused_code", program_key=None)
    corpus.save()
    assert ("2017/3010F-AF-L69: program_key None != printed code 'F0150P' (exclude_reused_code)"
            in _failures(corpus.leg_c()))


# --- run_verify_era_map and the CLI ----------------------------------------

@pytest.fixture
def pinned(corpus, monkeypatch) -> Corpus:
    monkeypatch.setattr(verify_era_map, "ERA_P1_WORKBOOK_SHA256", corpus.shas)
    monkeypatch.setattr(verify_era_map, "EXPECTED_ERA_KEYS", corpus.expected)
    monkeypatch.setattr(verify_era_map, "DEFAULT_SEED_PATH", corpus.seed_path)
    monkeypatch.setattr(config, "SITE_DIR", corpus.site_dir)
    monkeypatch.setattr(config, "DUCKDB_PATH", corpus.duckdb_path)
    return corpus


def test_run_verify_era_map_passes_legs_a_to_c(pinned):
    out = run_verify_era_map(site_dir=pinned.site_dir, duckdb_path=pinned.duckdb_path,
                             seed_path=pinned.seed_path, legs="abc")
    assert out["verdict"] == "PASS"
    assert list(out["legs"]) == ["a", "b", "c"]


def test_run_verify_era_map_rejects_unknown_legs(pinned):
    with pytest.raises(ValueError, match="legs must be letters from abcdef"):
        run_verify_era_map(site_dir=pinned.site_dir, duckdb_path=pinned.duckdb_path,
                           seed_path=pinned.seed_path, legs="az")


def test_a_missing_map_table_fails_every_leg(pinned, tmp_path):
    empty = tmp_path / "empty.duckdb"
    duckdb.connect(str(empty)).close()
    out = run_verify_era_map(site_dir=pinned.site_dir, duckdb_path=empty,
                             seed_path=pinned.seed_path, legs="abc")
    assert out["verdict"] == "FAIL"
    assert {leg: r["detail"]["summary"] for leg, r in out["legs"].items()} == {
        "a": "p1_era_line_map unreadable", "b": "p1_era_line_map unreadable",
        "c": "p1_era_line_map unreadable"}


def test_legs_d_to_f_fail_until_task_20(pinned):
    out = run_verify_era_map(site_dir=pinned.site_dir, duckdb_path=pinned.duckdb_path,
                             seed_path=pinned.seed_path)
    assert list(out["legs"]) == ["a", "b", "c", "d", "e", "f"]
    assert [leg for leg, r in out["legs"].items() if not r["ok"]] == ["d", "e", "f"]
    assert out["verdict"] == "FAIL"


def test_cli_passes_with_one_final_verdict_line(pinned, capsys):
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-era-map", "--legs", "abc"])
    out = capsys.readouterr().out.splitlines()
    assert exit_.value.code == 0
    assert out[-1] == "verify-era-map: PASS"
    assert [line for line in out if line.startswith("verify-era-map:")] == [out[-1]]
    assert out[0].startswith("leg a workbooks: workbooks=7 keys_checked=32")


def test_cli_fails_with_exit_1(pinned, capsys):
    pinned.row(2019, "2031A-ARMY-L1")["line_item_code"] = "9440A11301"
    pinned.save()
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-era-map", "--legs", "abc"])
    out = capsys.readouterr().out.splitlines()
    assert exit_.value.code == 1
    assert out[-1] == "verify-era-map: FAIL"


def test_cli_zero_arguments_runs_every_leg(pinned, capsys):
    with pytest.raises(SystemExit) as exit_:
        cli.main(["verify-era-map"])
    out = capsys.readouterr().out.splitlines()
    assert exit_.value.code == 1
    assert [line.split(":")[0] for line in out if line.startswith("leg ")] == [
        "leg a workbooks", "leg b decisions", "leg c f15",
        "leg d fact ids", "leg e published map", "leg f f15 history pin"]
    assert out[-1] == "verify-era-map: FAIL"
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `uv run --project . pytest tests/test_verify_era_map.py -q`

Expected: `1 error` during collection —
`ModuleNotFoundError: No module named 'govbudget.verify_era_map'`.

- [ ] **Step 3: Write the gate**

Create `GovBudget/src/govbudget/verify_era_map.py`:

```python
"""Families piece 1 release gate: verify-era-map (spec §8, V4).

CLI: `govbudget verify-era-map [--legs abc]`. With no arguments it checks
every leg against config.SITE_DIR, config.DUCKDB_PATH and the committed seed
(dbt/seeds/p1_era_code_decisions.csv), prints one line per leg and then
exactly one final line, `verify-era-map: PASS` or `verify-era-map: FAIL`,
and exits 1 on FAIL. It is built to fail: a missing table, workbook or seed
is a FAIL, never a skip.

  Leg (a) — workbooks. Re-read the seven PB2017–PB2023 P-1 workbooks the site
    ships (data/site/workbooks/<sha>.xlsx; the shas are pinned below and the
    file bytes must hash to them) with the loader's own parse
    (p1_loader.parse_p1_rollup). The era key set must be exactly the 6,927
    keys of the corpus (EXPECTED_ERA_KEYS) and equal p1_era_line_map's; for
    every key the account, organization, budget activity, printed code
    (line_item_code) and filed title must equal the map's, the map must cite
    the pinned workbook, and its source_cells must be the code column's cells
    of exactly the rows the parse summed. Then, independently of the parser,
    every cited cell must print the key's code, its row's 'Line Item Title'
    must equal filed_title, and its row's 'Line Number' must be the key's
    line.

  Leg (b) — decisions. No era key is undecided; every decided key's
    keys_sha_ok (the dbt-side drift hash) is true; the map was built from the
    seed on disk (each decided key's decision_id exists there with the same
    decision, ruling, pins and successor); no seed row binds zero keys; and,
    recomputed in Python with era_map.keys_sha256 over the keys each seed row
    binds, every seed row's keys_sha256 and n_keys still hold.

  Leg (c) — F-15. The map's F-15 rows — every key printing one of the
    ERA_PROGRAM_CODES codes or titled like F-15 — are exactly ERA_MEMBERS
    joined to ERA_PROGRAM_CODES (31 rows: edition, era key, budget activity,
    filed title, printed code), and each carries its printed code as
    program_key.

  Legs (d)–(f) are added by Task 20 (fact-ID recompute, published parquet vs
  dbt map, F-15 history sha pin). Until then they report FAIL, so the
  zero-argument run cannot pass vacuously.
"""
from __future__ import annotations

import csv
import hashlib
import re
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path

from govbudget import config

LEGS = ("a", "b", "c", "d", "e", "f")
LEG_NAMES = {
    "a": "workbooks", "b": "decisions", "c": "f15",
    "d": "fact ids", "e": "published map", "f": "f15 history pin",
}

# The seven era P-1 display workbooks (jbook_documents rel_path
# fy<N>/dod/p1_display.xlsx), by edition — measured 2026-10-02.
ERA_P1_WORKBOOK_SHA256: dict[int, str] = {
    2017: "fa2d6711dc766be5cdf6148ed46b158e6420fe9653613900c43add4a28b26b31",
    2018: "863ea56b3d32294c4c61f12ec6e99622d74d12cfcce6a9c7c7c1e17e439cb318",
    2019: "af88e62619ba910915a5f5b68abb44652d75359cd1f8a46b07df609b8925d501",
    2020: "f019309be2f85fd523b00c5ec419c845747d867cd5d3af10908e979b171f584f",
    2021: "73aadc1b5bee700a4d4ea3f95b7a6be65dde58ae0bff6fc4fb33bef6b7362942",
    2022: "02a59dcc426aebf241c244f26698c7dd8ed1d2594507d2ea9b514857f1cee5fd",
    2023: "710db28120491ddcbed14a5b5e8bb71d183a7fe9d032002dbca40b2e7412c504",
}
# Era keys per edition (spec §3): 6,927 in all.
EXPECTED_ERA_KEYS: dict[int, int] = {
    2017: 969, 2018: 1029, 2019: 989, 2020: 975, 2021: 1005, 2022: 993, 2023: 967,
}
F15_ERA_ROWS = 31

DEFAULT_SEED_PATH = config.ROOT / "dbt" / "seeds" / "p1_era_code_decisions.csv"

MAP_COLUMNS = (
    "edition", "account", "organization", "budget_activity", "era_key",
    "line_item_code", "filed_title", "program_key", "program_account", "program_org",
    "decision", "decision_id", "ruling", "keys_sha_ok", "successor_code",
    "source_document_sha256", "source_cells",
)

_CELL_ROW_RE = re.compile(r"^([A-Z]+)([0-9]+)$")
_PRINTED_HEADERS = ("Line Number", "Line Item", "Line Item Title")
_MAX_LISTED = 25


def _leg(ok: bool, summary: str, failures: list[str]) -> dict:
    return {"ok": ok, "detail": {"summary": summary, "failures": failures}}


def _read_map(duckdb_path: Path) -> list[dict]:
    import duckdb

    con = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        cur = con.execute(
            f"select {', '.join(MAP_COLUMNS)} from p1_era_line_map order by edition, era_key")
        return [dict(zip(MAP_COLUMNS, row)) for row in cur.fetchall()]
    finally:
        con.close()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _printed_cells(xlsx_path: Path) -> tuple[dict[int, tuple], str]:
    """The era P-1 sheet's printed (Line Number, Line Item, Line Item Title) per
    worksheet row, read straight from openpyxl (not through the loader), and
    the column letter of 'Line Item'."""
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter

    from govbudget.jbooks.rollup_loader import norm_header

    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    try:
        ws = wb["Exhibit P-1"] if "Exhibit P-1" in wb.sheetnames else wb[wb.sheetnames[0]]
        header_row, cols = None, {}
        for i, row in enumerate(ws.iter_rows(min_row=1, max_row=20, values_only=True), start=1):
            found = {norm_header(v): j for j, v in enumerate(row) if v is not None}
            if all(h in found for h in _PRINTED_HEADERS):
                header_row, cols = i, found
                break
        if header_row is None:
            raise ValueError(
                f"{xlsx_path.name}: no header row with {_PRINTED_HEADERS} in the first 20 rows")
        idx = [cols[h] for h in _PRINTED_HEADERS]
        printed = {}
        for r, row in enumerate(ws.iter_rows(min_row=header_row + 1, values_only=True),
                                start=header_row + 1):
            printed[r] = tuple(row[j] if j < len(row) else None for j in idx)
        return printed, get_column_letter(cols["Line Item"] + 1)
    finally:
        wb.close()


def _workbook_keys(parse) -> dict[str, dict]:
    """{era_key: {"identity": {(account, org, ba, code, title)}, "rows": {row}}}"""
    from govbudget.jbooks.era_keys import is_era_procurement_key

    keys: dict[str, dict] = {}
    for row in parse.rows:
        if not is_era_procurement_key(row.pe_bli):
            continue  # the classified aggregate (S1b) is not an era key
        k = keys.setdefault(row.pe_bli, {"identity": set(), "rows": set()})
        k["identity"].add((row.account, row.organization, row.budget_activity,
                           row.line_item_code, row.title))
        for cell in row.source_cells:
            m = _CELL_ROW_RE.match(cell)
            if m is None:
                raise ValueError(f"{row.pe_bli}: unparseable source cell {cell!r}")
            k["rows"].add(int(m.group(2)))
    return keys


def leg_a_workbooks(
    *, site_dir: Path, map_rows: list[dict],
    workbooks: Mapping[int, str], expected_keys: Mapping[int, int],
) -> dict:
    """Leg (a): the shipped era P-1 workbooks vs p1_era_line_map."""
    from govbudget.jbooks.era_keys import era_key_anchor
    from govbudget.jbooks.p1_loader import parse_p1_rollup

    failures: list[str] = []
    by_edition: dict[int, dict[str, dict]] = defaultdict(dict)
    for r in map_rows:
        by_edition[r["edition"]][r["era_key"]] = r
    for edition in sorted(set(by_edition) - set(workbooks)):
        failures.append(f"{edition}: the map has {len(by_edition[edition])} keys for an"
                        " edition with no pinned era P-1 workbook")
    checked = 0
    for edition, sha in sorted(workbooks.items()):
        path = Path(site_dir) / "workbooks" / f"{sha}.xlsx"
        if not path.is_file():
            failures.append(f"{edition}: workbook missing: {path}")
            continue
        actual_sha = _sha256_file(path)
        if actual_sha != sha:
            failures.append(f"{edition}: {path.name} hashes to {actual_sha}, not its pinned sha")
            continue
        try:
            parse = parse_p1_rollup(path, exhibit="P-1", fiscal_year=edition)
            if not parse.era_line_keying:
                failures.append(f"{edition}: the parse did not use era line keying")
                continue
            wb_keys = _workbook_keys(parse)
            printed, code_col = _printed_cells(path)
        except Exception as e:  # a tripwire (EraKeyConflict) or a bad file is a FAIL
            failures.append(f"{edition}: {type(e).__name__}: {e}")
            continue
        want = expected_keys.get(edition)
        if len(wb_keys) != want:
            failures.append(f"{edition}: the workbook parses to {len(wb_keys)} era keys,"
                            f" the corpus has {want}")
        mapped = by_edition.get(edition, {})
        for key in sorted(set(wb_keys) - set(mapped)):
            failures.append(f"{edition}/{key}: in the workbook, missing from the map")
        for key in sorted(set(mapped) - set(wb_keys)):
            failures.append(f"{edition}/{key}: in the map, not in the workbook")
        for key in sorted(set(wb_keys) & set(mapped)):
            checked += 1
            wk, m = wb_keys[key], mapped[key]
            if len(wk["identity"]) != 1:
                failures.append(f"{edition}/{key}: the workbook prints {len(wk['identity'])}"
                                " identities for one key")
                continue
            account, org, ba, code, title = next(iter(wk["identity"]))
            got = (m["account"], m["organization"], m["budget_activity"],
                   m["line_item_code"], m["filed_title"])
            if got != (account, org, ba, code, title):
                failures.append(f"{edition}/{key}: workbook {(account, org, ba, code, title)!r}"
                                f" != map {got!r}")
            if m["source_document_sha256"] != sha:
                failures.append(f"{edition}/{key}: map cites {m['source_document_sha256']},"
                                f" not the pinned workbook")
            want_cells = ",".join(f"{code_col}{r}" for r in sorted(wk["rows"]))
            if m["source_cells"] != want_cells:
                failures.append(f"{edition}/{key}: map cells {m['source_cells']!r}"
                                f" != workbook rows {want_cells!r}")
            for r in sorted(wk["rows"]):
                line, printed_code, printed_title = printed.get(r, (None, None, None))
                if (str(printed_code).strip() if printed_code is not None else None) != m["line_item_code"]:
                    failures.append(f"{edition}/{key}: {code_col}{r} prints {printed_code!r},"
                                    f" the map says {m['line_item_code']!r}")
                if printed_title != m["filed_title"]:
                    failures.append(f"{edition}/{key}: row {r} title {printed_title!r}"
                                    f" != filed_title {m['filed_title']!r}")
                if (str(line).strip() if line is not None else None) != era_key_anchor(key):
                    failures.append(f"{edition}/{key}: row {r} line number {line!r}"
                                    " is not the key's line")
    total = sum(expected_keys.get(e, 0) for e in workbooks)
    return _leg(not failures,
                f"workbooks={len(workbooks)} keys_checked={checked} expected={total}"
                f" failures={len(failures)}", failures)


def _read_seed(seed_path: Path) -> dict[str, dict]:
    from govbudget.jbooks.era_map import SEED_COLUMNS

    with open(seed_path, newline="") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != tuple(SEED_COLUMNS):
            raise ValueError(f"{seed_path.name}: header {reader.fieldnames} != SEED_COLUMNS")
        rows = {}
        for row in reader:
            clean = {k: (v if v != "" else None) for k, v in row.items()}
            if clean["decision_id"] in rows:
                raise ValueError(f"{seed_path.name}: duplicate decision_id {clean['decision_id']}")
            rows[clean["decision_id"]] = clean
        return rows


def leg_b_decisions(*, map_rows: list[dict], seed_path: Path) -> dict:
    """Leg (b): nothing undecided, nothing stale, and the map is this seed's."""
    from govbudget.jbooks.era_map import keys_sha256

    failures: list[str] = []
    try:
        seed = _read_seed(Path(seed_path))
    except (OSError, ValueError) as e:
        return _leg(False, "seed unreadable", [f"{type(e).__name__}: {e}"])
    undecided = [r for r in map_rows if r["decision"] == "undecided"]
    for r in undecided:
        failures.append(f"{r['edition']}/{r['era_key']} ({r['line_item_code']}): undecided")
    bound: dict[str, list[dict]] = defaultdict(list)
    for r in map_rows:
        if r["decision"] == "undecided":
            continue
        if r["keys_sha_ok"] is not True:
            failures.append(f"{r['edition']}/{r['era_key']}: keys_sha_ok={r['keys_sha_ok']}"
                            f" under {r['decision_id']} (stale decision)")
        bound[r["decision_id"]].append(r)
    for did, rows in sorted(bound.items()):
        s = seed.get(did)
        if s is None:
            failures.append(f"{did}: in the map, not in {Path(seed_path).name} (stale build)")
            continue
        for r in rows:
            got = (r["decision"], r["ruling"], r["program_account"], r["program_org"],
                   r["successor_code"])
            want = (s["decision"], s["ruling"], s["program_account"], s["program_org"],
                    s["successor_code"])
            if got != want:
                failures.append(f"{did}: map {got!r} != seed {want!r} (stale build)")
                break
        sha = keys_sha256((r["edition"], r["era_key"], r["budget_activity"], r["filed_title"])
                          for r in rows)
        if sha != s["keys_sha256"] or str(len(rows)) != (s["n_keys"] or ""):
            failures.append(f"{did}: binds {len(rows)} keys hashing to {sha[:12]}…, the seed"
                            f" reviewed {s['n_keys']} hashing to {(s['keys_sha256'] or '')[:12]}…")
    for did in sorted(set(seed) - set(bound)):
        failures.append(f"{did}: in the seed, binds no era key")
    return _leg(not failures,
                f"keys={len(map_rows)} undecided={len(undecided)} decisions={len(seed)}"
                f" failures={len(failures)}", failures)


def _looks_f15(title: str | None) -> bool:
    t = (title or "").upper()
    return "F-15" in t or "F15" in t


def leg_c_f15(*, map_rows: list[dict]) -> dict:
    """Leg (c): the map's F-15 rows are ERA_MEMBERS x ERA_PROGRAM_CODES."""
    from govbudget.f15_funding_history import ERA_MEMBERS, ERA_PROGRAM_CODES

    failures: list[str] = []
    expected = set()
    for edition, members in ERA_MEMBERS.items():
        for line, ba, title in members:
            code = ERA_PROGRAM_CODES.get(edition, {}).get(line)
            if code is None:
                failures.append(f"{edition}/L{line}: ERA_MEMBERS line has no ERA_PROGRAM_CODES code")
                continue
            expected.add((edition, f"3010F-AF-L{line}", ba, title, code))
    if len(expected) != F15_ERA_ROWS:
        failures.append(f"ERA_MEMBERS x ERA_PROGRAM_CODES has {len(expected)} rows, not {F15_ERA_ROWS}")
    codes = {c for per in ERA_PROGRAM_CODES.values() for c in per.values()}
    f15 = [r for r in map_rows if r["line_item_code"] in codes or _looks_f15(r["filed_title"])]
    actual = {(r["edition"], r["era_key"], r["budget_activity"], r["filed_title"],
               r["line_item_code"]) for r in f15}
    for row in sorted(expected - actual):
        failures.append(f"missing from the map: {row!r}")
    for row in sorted(actual - expected):
        failures.append(f"in the map, not in ERA_MEMBERS x ERA_PROGRAM_CODES: {row!r}")
    for r in f15:
        if r["program_key"] != r["line_item_code"]:
            failures.append(f"{r['edition']}/{r['era_key']}: program_key {r['program_key']!r}"
                            f" != printed code {r['line_item_code']!r} ({r['decision']})")
    return _leg(not failures,
                f"expected={len(expected)} map_rows={len(actual)} failures={len(failures)}",
                failures)


def run_verify_era_map(
    *, site_dir: Path, duckdb_path: Path, seed_path: Path, legs: str = "abcdef",
) -> dict:
    """Run the selected legs. Returns {"legs": {leg: {"ok", "detail"}}, "verdict"}."""
    unknown = sorted(set(legs) - set(LEGS))
    if unknown or not legs:
        raise ValueError(f"legs must be letters from {''.join(LEGS)}; got {legs!r}")
    import duckdb

    try:
        map_rows, map_error = _read_map(Path(duckdb_path)), None
    except duckdb.Error as e:
        map_rows, map_error = [], f"cannot read p1_era_line_map from {duckdb_path}: {e}"
    results: dict[str, dict] = {}
    for leg in (x for x in LEGS if x in legs):
        if leg in "abc" and map_error:
            results[leg] = _leg(False, "p1_era_line_map unreadable", [map_error])
        elif leg == "a":
            results[leg] = leg_a_workbooks(
                site_dir=Path(site_dir), map_rows=map_rows,
                workbooks=ERA_P1_WORKBOOK_SHA256, expected_keys=EXPECTED_ERA_KEYS)
        elif leg == "b":
            results[leg] = leg_b_decisions(map_rows=map_rows, seed_path=Path(seed_path))
        elif leg == "c":
            results[leg] = leg_c_f15(map_rows=map_rows)
        else:
            results[leg] = _leg(False, "not implemented",
                                [f"leg {leg} is added by families piece 1 Task 20"])
    verdict = "PASS" if all(r["ok"] for r in results.values()) else "FAIL"
    return {"legs": results, "verdict": verdict}


def format_report(result: dict) -> list[str]:
    """One line per leg plus its first failures; the CLI prints the verdict after."""
    lines = []
    for leg, r in result["legs"].items():
        lines.append(f"leg {leg} {LEG_NAMES[leg]}: {r['detail']['summary']}"
                     f" → {'PASS' if r['ok'] else 'FAIL'}")
        for failure in r["detail"]["failures"][:_MAX_LISTED]:
            lines.append(f"  FAIL {failure}")
        extra = len(r["detail"]["failures"]) - _MAX_LISTED
        if extra > 0:
            lines.append(f"  … and {extra} more")
    return lines
```

- [ ] **Step 4: Run the tests — the gate passes, the CLI tests fail**

Run: `uv run --project . pytest tests/test_verify_era_map.py -q`

Expected: `3 failed, 23 passed`; the three `test_cli_*` tests fail on
`assert 2 == 0` / `assert 2 == 1` after argparse prints
`argument cmd: invalid choice: 'verify-era-map'`.

- [ ] **Step 5: Wire the CLI**

In `GovBudget/src/govbudget/cli.py`, add the command after `cmd_verify_lineage`. Before
(lines 2428-2432):

```python
    print("verify-lineage:", "PASS" if gates_ok else "FAIL")
    sys.exit(0 if gates_ok else 1)


def cmd_export_site(args) -> None:
```

After:

```python
    print("verify-lineage:", "PASS" if gates_ok else "FAIL")
    sys.exit(0 if gates_ok else 1)


def cmd_verify_era_map(args) -> None:
    from govbudget import verify_era_map

    out = verify_era_map.run_verify_era_map(
        site_dir=config.SITE_DIR,
        duckdb_path=config.DUCKDB_PATH,
        seed_path=verify_era_map.DEFAULT_SEED_PATH,
        legs=args.legs,
    )
    for line in verify_era_map.format_report(out):
        print(line)
    print(f"verify-era-map: {out['verdict']}")
    sys.exit(0 if out["verdict"] == "PASS" else 1)


def cmd_export_site(args) -> None:
```

And register the parser after `verify-lineage`. Before (lines 3120-3122):

```python
    vlin.set_defaults(func=cmd_verify_lineage)

    v5 = sub.add_parser(
```

After:

```python
    vlin.set_defaults(func=cmd_verify_lineage)

    vera = sub.add_parser(
        "verify-era-map",
        help="families piece 1 release gate: era P-1 map vs the shipped"
             " workbooks, owner decisions, F-15 roster (legs a-f)",
    )
    vera.add_argument(
        "--legs", default="abcdef",
        help="legs to run, letters from abcdef (default: all six)",
    )
    vera.set_defaults(func=cmd_verify_era_map)

    v5 = sub.add_parser(
```

(If Task 12's `era-map` parser landed between these lines, keep it and insert the block right
after `vlin.set_defaults(func=cmd_verify_lineage)`.)

- [ ] **Step 6: Run the tests to see them pass**

Run: `uv run --project . pytest tests/test_verify_era_map.py -q`

Expected: `26 passed`.

- [ ] **Step 7: Run legs a and c against the live map (read-only)**

Requires Task 13 Step 12. Run from `GovBudget/` in the worktree:

```bash
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data \
uv run --project . python -m govbudget verify-era-map --legs ac; echo "exit=$?"
```

Expected (about 2 s; measured on 2026-10-02 against the seven real workbooks and a map built
from the live lake):
```
leg a workbooks: workbooks=7 keys_checked=6927 expected=6927 failures=0 → PASS
leg c f15: expected=31 map_rows=31 failures=0 → PASS
verify-era-map: PASS
exit=0
```

Then leg b, which stays FAIL until Task 15 ratifies the last review batch:

```bash
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data \
uv run --project . python -m govbudget verify-era-map --legs b; echo "exit=$?"
```

Expected while review is open:
```
leg b decisions: keys=6927 undecided=<n> decisions=<seed rows> failures=<n> → FAIL
  FAIL <edition>/<era_key> (<code>): undecided
  …
verify-era-map: FAIL
exit=1
```
with `<n>` equal to Task 13 Step 13's count and no `stale`, `binds no era key` or
`stale build` lines (any of those is a real defect: fix it before Task 15). Once Task 15 has
ratified everything: `leg b decisions: keys=6927 undecided=0 … failures=0 → PASS`.

- [ ] **Step 8: Commit**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/verify_era_map.py GovBudget/tests/test_verify_era_map.py GovBudget/src/govbudget/cli.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(verify): verify-era-map legs a-c — workbook re-read, decisions, F-15 roster (families piece 1, V4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
