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
