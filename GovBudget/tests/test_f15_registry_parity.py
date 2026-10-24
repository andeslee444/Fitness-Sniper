"""F-15 registry parity and the one-off seed (families piece 2; spec §7.6, §8.1, §13).

The only literal copies of the 88538c6a F-15 constants live here."""
from __future__ import annotations

import csv
import gzip
import importlib
import json
import shutil
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import duckdb
import pytest

from govbudget import config
from govbudget import f15_funding_history as facade
from govbudget import platform_families as pf
from govbudget.jbooks import era_map
from govbudget.platform_families import (DEFAULT_PATHS, F15_SEED_RULING_TEXT, F15_SEED_SPEC,
                                         F15Constants, RegistryError, load_registry, registry_texts,
                                         seed_shipped_f15)
from platform_family_fixtures import (BL_COLS, DOCUMENT_COLUMNS, MAP_COLUMNS, World, tmp_paths,
                                      write_parquet, write_world)

# --- literal copies (88538c6a f15_funding_history.py:19-108) ---
MODERN_MEMBERS = {
    "0207134F": ("R-1", "3600F", "F-15E Squadrons"),
    "0207146F": ("R-1", "3600F", "F-15EX"),
    "0207171F": ("R-1", "3600F", "F-15 EPAWSS"),
    "F01500": ("P-1", "3010F", "F-15"),
    "F015EX": ("P-1", "3010F", "F-15EX"),
    "F15EWS": ("P-1", "3010F", "F-15 EPAW"),
}
# PB2017–23 P-1 line roster, confirmed against the imported official workbooks.
# Values: (line number, budget activity, exact title). Reused line numbers are
# intentionally repeated by edition; a bare Lxx is never an identity mapping.
ERA_MEMBERS = {
    2017: [(21, "05", "F-15"), (69, "07", "F-15")],
    2018: [(23, "05", "F-15"), (79, "07", "F-15"), (80, "07", "F-15")],
    2019: [(25, "05", "F-15"), (30, "05", "F-15 EPAW"), (79, "07", "F-15"), (80, "07", "F-15")],
    2020: [(3, "01", "F-15e"), (25, "05", "F-15"), (31, "05", "F-15 EPAW"), (79, "07", "F-15"), (80, "07", "F-15")],
    2021: [(3, "01", "F-15e"), (4, "01", "F-15EX"), (5, "01", "F-15EX"), (29, "05", "F-15"), (34, "05", "F-15 EPAW"), (80, "07", "F-15")],
    2022: [(4, "01", "F-15e"), (5, "01", "F-15EX"), (6, "01", "F-15EX"), (30, "05", "F-15"), (34, "05", "F-15 EPAW"), (78, "07", "F-15")],
    2023: [(5, "01", "F-15EX"), (6, "01", "F-15EX"), (28, "05", "F-15"), (32, "05", "F-15 EPAW"), (74, "07", "F-15")],
}
# The permanent code is read from the actual XLSX code column. These reviewed
# expectations prevent a changed or reused edition-local line from silently
# moving money into another matrix row. F0150P and F015E0 remain separate lines.
ERA_PROGRAM_CODES = {
    2017: {21: "F01500", 69: "F0150P"},
    2018: {23: "F01500", 79: "F01500", 80: "F0150P"},
    2019: {25: "F01500", 30: "F15EWS", 79: "F01500", 80: "F0150P"},
    2020: {3: "F015E0", 25: "F01500", 31: "F15EWS", 79: "F01500", 80: "F0150P"},
    2021: {3: "F015E0", 4: "F015EX", 5: "F015EX", 29: "F01500", 34: "F15EWS", 80: "F01500"},
    2022: {4: "F015E0", 5: "F015EX", 6: "F015EX", 30: "F01500", 34: "F15EWS", 78: "F01500"},
    2023: {5: "F015EX", 6: "F015EX", 28: "F01500", 32: "F15EWS", 74: "F01500"},
}
# A program note quotes the one budget-book sentence that states what a line
# bought, cited to that sentence's narrative receipt (spec §6.5; the owner
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
              "operationally representative test aircraft and two operational aircraft were purchased with "
              "procurement funds (F015E0, Line #3 [line 3 of the PB2020–21 P-1 (line 4 in PB2022)]))."),
        note_fact_id="e7d5bcfb4a30f458",
    ),
}
# What each note_fact_id must resolve to in the exported registry: the
# jbook_narrative receipt for that paragraph, in that exact PDF, under the
# budget line whose exhibit prints it (the code the note's first gloss names).
NOTE_RECEIPTS = {
    "e7d5bcfb4a30f458": dict(kind="jbook_narrative", page_number=71, pe_bli="F015EX",
                             sha256="528d14414585406684021e04e74632cccf4b40f8ba039f89f8af1ddebc7bc01e"),
}
PROGRAMS = [
    dict(id=f"{exhibit}:{account}:AF:{code}", code=code, title=title,
         program_slug=code if code in MODERN_MEMBERS else None,
         exhibit=exhibit, account=account, organization="AF",
         **PROGRAM_NOTES.get(code, {}))
    for code, exhibit, account, title in [
        ("0207134F", "R-1", "3600F", "F-15E Squadrons"),
        ("0207146F", "R-1", "3600F", "F-15EX"),
        ("0207171F", "R-1", "3600F", "F-15 EPAWSS"),
        ("F01500", "P-1", "3010F", "F-15"),
        ("F015EX", "P-1", "3010F", "F-15EX"),
        ("F15EWS", "P-1", "3010F", "F-15 EPAW"),
        ("F0150P", "P-1", "3010F", "F-15 (legacy support line)"),
        ("F015E0", "P-1", "3010F", "F-15e (FY2020 F-15EX Lot 1 aircraft)"),
    ]
]
SCOPE_NOTE = (
    "Recorded F-15-named research, development and procurement budget lines in "
    "the imported P-1/R-1 workbooks. This is a covered-record total, not the "
    "aircraft family's lifetime cost. Personnel, operations and maintenance, "
    "and unallocated shared support are outside this calculation."
)
COVERAGE_NOTES = [
    "Coverage begins with FY2015 actuals in PB2017. Earlier funding, including early F-15A–D development, is not represented.",
    "The locally imported records do not contain PE 0207130F; no amount or zero is invented for it.",
    "Historical procurement line numbers change between editions. Each legacy line is matched within its own budget edition, without asserting a modern-program or aircraft-variant allocation, except where a budget book states one (F015E0).",
    "Actuals, current-year figures and requests are separate snapshots. Requests and current-year figures are excluded from the cumulative actuals figure.",
    "Amounts are nominal dollars of total obligational authority (TOA), not contract obligations, cash outlays or inflation-adjusted dollars.",
    "Missing workbook figures are not zero spending. Some current-year columns contain requests adjusted for continuing resolutions rather than final enacted appropriations.",
    "The totals exclude classified funding and military construction.",
]
# --- end literal copies ---
EXPECTED_FROM = {"0207134F": 2017, "0207171F": 2017, "0207146F": 2021, "F01500": 2024,
                 "F015EX": 2024, "F15EWS": 2024, "F0150P": None, "F015E0": None}
REPLY_FILE = config.ROOT / "data/research/platform_families/f-15/owner-reply-R-DEC-FAM-F15-SEED.txt"
REPLY = "approved, would process with recommendation to approve all"
FIXTURES = config.ROOT / "tests" / "fixtures" / "f15"
DECISION_IDS = {"F01500": "F01500|3010F||2017-2023", "F015EX": "F015EX|3010F||2021-2023",
                "F15EWS": "F15EWS|3010F||2019-2023", "F0150P": "F0150P|3010F||2017-2020",
                "F015E0": "F015E0|3010F||2020-2022"}
DRIFT = {   # re-measured 2026-10-21 on the live lake; the hermetic world gives the same
    "0207134F": "3e712698ea139bb2e5353b817fad2dc8d7a6c557fdbc75d147ab515529cbbe9d",
    "0207146F": "ba44e832838c6dea94864a2b7ba01fb4509cd4b83a16b1b3e394587f2bf4a53c",
    "0207171F": "0ac8af1ee02fdc821e1b06fa2553f70b215bcf0b3fc3fd7b115b3750b25b3b68",
    "F01500": "01771b3d6a955ca8757b53d3648e9e2afd8cff3cade49a7befd6f999f932fdfd",
    "F015EX": "c9f52488401161fe17ff6751f197c1230c667ff157075d69abd0dee9adb823dc",
    "F15EWS": "a5fc0cd2f4f7e419b7a36a639f32860bfa1862bbb4a84483c87d5a1991684691",
    "F0150P": "a3973b968d31541ba0f3b4048ac1a20c2facc9eda28208be641ae27ea463302a",
    "F015E0": "3534b19978134f6408e33d2a1865bc3ae60662a1ca49f176fd3232b621ffa946",
}


def literal_constants() -> F15Constants:
    return F15Constants(programs=PROGRAMS, modern_members=MODERN_MEMBERS, era_members=ERA_MEMBERS,
                        era_program_codes=ERA_PROGRAM_CODES, program_notes=PROGRAM_NOTES,
                        note_receipts=NOTE_RECEIPTS, scope_note=SCOPE_NOTE,
                        coverage_notes=COVERAGE_NOTES, expected_from=EXPECTED_FROM)


SHIPPED = literal_constants()


def make_f15_world(root: Path, *, drop_map: Sequence[tuple[int, int]] = (),
                   extra_programs: Sequence[tuple[str, str, str]] = ()) -> tuple[Path, Path]:
    """A fam2-shaped snapshot from the committed F-15 fixtures, in the Task 2c
    layout ({root}/duckdb/govbudget.duckdb beside {root}/parquet/jbooks/, and
    {root}/site/): the 467 workbook rows of builder_inputs.json.gz as
    budget_lines.parquet, its series as fct_decade_series, the literal 31-line
    roster as p1_era_line_map (minus the (edition, line) pairs in drop_map),
    the six modern codes (plus extra_programs) as dim_programs, and the pinned
    history as site/json/f15_funding_history.json. Returns (DuckDB path, site
    dir)."""
    inputs = json.loads(gzip.decompress((FIXTURES / "builder_inputs.json.gz").read_bytes()))
    bl_rows = []
    for r in inputs["source_rows"]:
        pe_bli, edition = r["pe_bli"], r["edition"]
        code = ERA_PROGRAM_CODES[edition][int(pe_bli.rsplit("L", 1)[1])] \
            if pe_bli.startswith("3010F-AF-L") else pe_bli
        bl_rows.append((r["exhibit"], str(edition), r["account"], r["account_title"], r["organization"],
                        r["budget_activity"], r["budget_activity_title"], pe_bli, r["title"],
                        r["amount_type"], str(r["amount_thousands"]), "1", r["sheet"], r["cells"], code))
    write_parquet(root / "parquet" / "jbooks" / "budget_lines.parquet", BL_COLS, bl_rows)
    write_parquet(root / "parquet" / "jbooks" / "documents.parquet", DOCUMENT_COLUMNS,
                  [("1", "AF", "p1", "2017", "p1_display.xlsx", "https://x.test/p1_display.xlsx",
                    "0" * 64, "1", "2026-01-01", "fy2017/af/p1_display.xlsx")])

    db = root / "duckdb" / "govbudget.duckdb"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    try:
        con.execute("create table fct_decade_series (pe_bli varchar, fy integer, edition_year integer,"
                    " amount_type_kind varchar, amount double, account varchar, organization varchar)")
        con.executemany("insert into fct_decade_series values (?, ?, ?, ?, ?, null, null)",
                        [[p["pe_bli"], p["fy"], p["edition"], p["kind"], p["amount"]]
                         for p in inputs["series"]])
        con.execute("create table p1_era_line_map (edition integer, "
                    + ", ".join(f"{c} varchar" for c in MAP_COLUMNS[1:]) + ")")
        dropped, map_rows = set(drop_map), []
        for edition, lines in ERA_MEMBERS.items():
            for line, ba, title in lines:
                if (edition, line) in dropped:
                    continue
                code = ERA_PROGRAM_CODES[edition][line]
                decision = "history_only" if code in ("F0150P", "F015E0") else "same_program"
                map_rows.append([edition, "3010F", "AF", ba, f"3010F-AF-L{line}", code, title, code,
                                 decision, DECISION_IDS[code]])
        con.executemany("insert into p1_era_line_map values (" + ", ".join("?" * len(MAP_COLUMNS)) + ")",
                        map_rows)
        con.execute("create table dim_programs (pe_bli varchar, account varchar, org varchar)")
        con.executemany("insert into dim_programs values (?, ?, ?)",
                        [[code, account, "F"] for code, (_exhibit, account, _title) in MODERN_MEMBERS.items()]
                        + [list(p) for p in extra_programs])
    finally:
        con.close()

    site = root / "site"
    history = site / "json" / "f15_funding_history.json"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_bytes((FIXTURES / "history.json").read_bytes())
    return db, site


def seed(tmp_path, *, world_kw=None, paths=None, **kw):
    db, site = make_f15_world(tmp_path / "fam2", **(world_kw or {}))
    args = dict(constants=literal_constants(), duckdb_path=db, site_dir=site,
                decided_on="2026-10-21", owner_reply=REPLY, paths=paths or tmp_paths(tmp_path / "seeds"))
    args.update(kw)
    return seed_shipped_f15(**args), args["paths"]


def test_literal_copies_equal_the_shipped_module():
    from govbudget import f15_funding_history as f15

    assert (f15.MODERN_MEMBERS, f15.ERA_MEMBERS, f15.ERA_PROGRAM_CODES, f15.PROGRAMS, f15.PROGRAM_NOTES,
            f15.NOTE_RECEIPTS, f15.SCOPE_NOTE, f15.COVERAGE_NOTES) == (
        MODERN_MEMBERS, ERA_MEMBERS, ERA_PROGRAM_CODES, PROGRAMS, PROGRAM_NOTES, NOTE_RECEIPTS,
        SCOPE_NOTE, COVERAGE_NOTES)


def test_owner_reply_file_is_the_verbatim_approval():
    assert REPLY_FILE.read_bytes() == (REPLY + "\n").encode("utf-8")


def _x1_registry(tmp_path):
    write_world(tmp_path / "seeds-x", World())
    return tmp_paths(tmp_path / "seeds-x" / "data-seeds")


def _f15_registry(tmp_path):
    seed(tmp_path / "first")
    return tmp_paths(tmp_path / "first" / "seeds")


def _site_one_byte_off(tmp_path):
    db, site = make_f15_world(tmp_path / "fam2-tampered")
    hist = site / "json" / "f15_funding_history.json"
    hist.write_bytes(hist.read_bytes() + b" ")
    return {"duckdb_path": db, "site_dir": site}


SEED_REFUSALS = [
    # (case id, how -> seed() keyword overrides, fragment)
    ("registry-holds-a-family", lambda t: {"paths": _x1_registry(t)}, "registry already holds x-1"),
    ("f15-exists", lambda t: {"paths": _f15_registry(t)}, "f-15 already in platform_families.json"),
    ("site-sha", _site_one_byte_off, "pin"),
    ("programs", lambda t: {"constants": replace(literal_constants(), programs=[
        dict(p, title="F-15 EX") if p["code"] == "F015EX" else p for p in PROGRAMS])}, "programs[4].title"),
    ("scope-note", lambda t: {"constants": replace(literal_constants(), scope_note=SCOPE_NOTE + " ")},
     "scope_note"),
    ("coverage-notes", lambda t: {"constants": replace(literal_constants(), coverage_notes=COVERAGE_NOTES[:-1])},
     "coverage_notes"),
    ("roster", lambda t: {"world_kw": {"drop_map": [(2023, 74)]}}, "roster"),
    ("blank-reply", lambda t: {"owner_reply": " "}, "owner_reply"),
    ("non-iso-date", lambda t: {"decided_on": "21 Oct 2026"}, "decided_on"),
    ("stage-one", lambda t: {"constants": replace(literal_constants(),
                                                  expected_from=dict(EXPECTED_FROM, **{"0207146F": 2016}))},
     "coverage_expected_from_edition"),
    ("stage-two", lambda t: {"world_kw": {"extra_programs": [("F01500", "3011F", "F")]}}, "collision"),
]


@pytest.mark.parametrize("how,fragment", [c[1:] for c in SEED_REFUSALS], ids=[c[0] for c in SEED_REFUSALS])
def test_seed_refusal(tmp_path, how, fragment):
    kw = how(tmp_path)
    paths = kw.get("paths") or tmp_paths(tmp_path / "seeds")
    before = {p: p.read_bytes() for p in (paths.json, paths.members, paths.era_lines) if p.exists()}
    with pytest.raises(RegistryError) as exc:
        seed(tmp_path, **kw)
    assert any(fragment in line for line in exc.value.errors), "\n".join(exc.value.errors)
    assert {p: p.read_bytes() for p in (paths.json, paths.members, paths.era_lines) if p.exists()} == before


def test_seed_lists_every_input_refusal_at_once(tmp_path):
    with pytest.raises(RegistryError) as exc:
        seed(tmp_path, owner_reply="", decided_on="2026-10-32",
             constants=replace(literal_constants(), scope_note="x"))
    text = str(exc.value)
    assert "owner_reply" in text and "decided_on" in text and "scope_note" in text


def test_seed_writes_atomically(tmp_path, monkeypatch):
    def fail(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(era_map.os, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        seed(tmp_path)
    assert not (tmp_path / "seeds").exists() or not any((tmp_path / "seeds").iterdir())


def test_seed_writes_the_entry_and_returns_counts(tmp_path):
    counts, paths = seed(tmp_path)
    assert counts == {"members": 8, "era_lines": 31, "rulings": 1}
    reg = load_registry(paths)
    f15 = reg["f-15"]
    assert [f.platform_family for f in reg.published()] == ["f-15"]
    assert (f15.status, f15.published_ruling_id, f15.short_name, f15.history_dataset, f15.on_partial_corpus) == (
        "published", "R-DEC-FAM-F15-SEED", "F-15", "f15_funding_history", "skip")
    assert [m.member_id for m in f15.counted] == [p["id"] for p in PROGRAMS]
    assert [m.code for m in f15.code_keyed] == list(MODERN_MEMBERS)
    assert [m.coverage_expected_from_edition for m in f15.counted] == [EXPECTED_FROM[p["code"]] for p in PROGRAMS]
    assert {m.code: m.drift_sha256 for m in f15.counted} == DRIFT
    assert f15.counted[4].titles_seen == ((2024, "F-15EX"), (2025, "F-15EX"), (2026, "F-15EX"))
    assert len(f15.era_lines) == 31 and len(f15.counted[0].titles_seen) == 10
    assert f15.program_notes["P-1:3010F:AF:F015E0"].note == PROGRAM_NOTES["F015E0"]["note"]
    assert (f15.scope_note, list(f15.coverage_notes)) == (SCOPE_NOTE, COVERAGE_NOTES)
    ruling = reg.rulings["R-DEC-FAM-F15-SEED"]
    assert (ruling.kind, ruling.platform_family, ruling.decided_by, ruling.decided_on, ruling.owner_reply,
            ruling.seed_basis, ruling.spec, ruling.text) == (
        "class", "f-15", "owner", "2026-10-21", REPLY, True, F15_SEED_SPEC, F15_SEED_RULING_TEXT)
    assert F15_SEED_SPEC == ("docs/superpowers/specs/2026-10-20-families-piece2-registry-design.md"
                             "#81-r-dec-fam-f15-seed-class-ruling-pending-owner-approval-with-this-spec")
    assert F15_SEED_RULING_TEXT == (
        "The F-15 family's registry entry records the eight budget lines the shipped F-15 history counts,"
        " as they ship at main 88538c6a. It records: their order, identities and display titles; the"
        " coverage rule (which lines are expected in which editions); the 31-line era roster; the F015E0"
        " note and its receipt; the family's scope and coverage notes. It changes no published figure,"
        " text or fact ID. Its evidence basis is the shipped family history (the F-15 family funding"
        " correction recorded in the ROADMAP on 2026-09-24), the piece-1 era decisions and the page's"
        " record-link narratives. Piece 3 must add an independent signal for each line before any F-15"
        " row changes.")


def test_seed_strips_exactly_one_trailing_newline_from_the_reply(tmp_path):     # D13
    for i, (given, kept) in enumerate([(REPLY_FILE.read_text(encoding="utf-8"), REPLY),
                                       (REPLY + "\n\n", REPLY + "\n")]):
        _counts, paths = seed(tmp_path / str(i), owner_reply=given)
        assert load_registry(paths).rulings["R-DEC-FAM-F15-SEED"].owner_reply == kept


def _f15_slice_texts(committed, out) -> dict[Path, str]:
    """The committed registry cut to the F-15 entry (family f-15, ruling R-DEC-FAM-F15-SEED, the f-15
    member and era-line rows), serialized by registry_texts at `out`'s paths. Tasks 8a and 8b add the
    F-35 beside the entry; the slice never sees it."""
    doc = json.loads(committed.json.read_text(encoding="utf-8"))

    def f15_rows(path):
        with path.open(encoding="utf-8", newline="") as fh:
            return [row for row in csv.DictReader(fh) if row["platform_family"] == "f-15"]

    doc.update(rulings=[r for r in doc["rulings"] if r["ruling_id"] == "R-DEC-FAM-F15-SEED"],
               sources=[],  # the F-15 entry cites no source (§7.6)
               families=[f for f in doc["families"] if f["platform_family"] == "f-15"])
    return registry_texts(out, doc=doc, members=f15_rows(committed.members),
                          era_lines=f15_rows(committed.era_lines))


def test_seed_reproduces_the_committed_f15_entry_byte_for_byte(tmp_path):
    _counts, paths = seed(tmp_path, owner_reply=REPLY_FILE.read_text(encoding="utf-8"))
    for path, text in _f15_slice_texts(DEFAULT_PATHS, paths).items():
        assert path.read_bytes() == text.encode("utf-8"), path.name


def test_committed_registry_loads_with_the_f15_published():
    reg = load_registry()
    f15 = reg["f-15"]
    assert (f15.status, f15.published_ruling_id, len(f15.members), len(f15.era_lines)) == (
        "published", "R-DEC-FAM-F15-SEED", 8, 31)
    assert reg.rulings["R-DEC-FAM-F15-SEED"].platform_family == "f-15"
    assert "f-15" in [f.platform_family for f in reg.published()]


FACADE_FIELDS = {
    "MODERN_MEMBERS": "modern_members", "ERA_MEMBERS": "era_members",
    "ERA_PROGRAM_CODES": "era_program_codes", "PROGRAMS": "programs",
    "PROGRAM_NOTES": "program_notes", "NOTE_RECEIPTS": "note_receipts",
    "SCOPE_NOTE": "scope_note", "COVERAGE_NOTES": "coverage_notes",
}


@pytest.mark.parametrize("name,field", sorted(FACADE_FIELDS.items()))
def test_facade_constant_equals_its_88538c6a_literal(name, field):
    assert getattr(facade, name) == getattr(SHIPPED, field)


def test_facade_constants_keep_the_88538c6a_order_and_types():
    assert list(facade.MODERN_MEMBERS) == ["0207134F", "0207146F", "0207171F", "F01500", "F015EX", "F15EWS"]
    assert list(facade.ERA_MEMBERS) == list(range(2017, 2024)) == list(facade.ERA_PROGRAM_CODES)
    for edition, rows in facade.ERA_MEMBERS.items():
        assert [line for line, _, _ in rows] == sorted(line for line, _, _ in rows)
        assert list(facade.ERA_PROGRAM_CODES[edition]) == sorted(facade.ERA_PROGRAM_CODES[edition])
    assert sum(map(len, facade.ERA_MEMBERS.values())) == 31
    assert [p["code"] for p in facade.PROGRAMS] == [
        "0207134F", "0207146F", "0207171F", "F01500", "F015EX", "F15EWS", "F0150P", "F015E0"]
    assert type(facade.COVERAGE_NOTES) is list and len(facade.COVERAGE_NOTES) == 7


def test_registry_coverage_columns_reproduce_the_88538c6a_expected_rule():
    counted = {m.code: m for m in facade.F15.counted}
    assert {code: m.coverage_expected_from_edition for code, m in counted.items()} == dict(SHIPPED.expected_from)
    assert all(m.valid_to_edition == 2026 for m in counted.values() if m.coverage_expected_from_edition is not None)


def test_a_registry_fault_at_import_names_the_file_and_the_row(tmp_path, monkeypatch):
    bad = pf.RegistryPaths(*(tmp_path / p.name for p in (pf.DEFAULT_PATHS.json, pf.DEFAULT_PATHS.members,
                                                          pf.DEFAULT_PATHS.era_lines)))
    for src, dst in zip((pf.DEFAULT_PATHS.json, pf.DEFAULT_PATHS.members, pf.DEFAULT_PATHS.era_lines),
                        (bad.json, bad.members, bad.era_lines)):   # RegistryPaths is not iterable
        shutil.copyfile(src, dst)
    row = "f-15|R-1:3600F:AF:0207146F|2021-2026"
    lines = bad.members.read_text(encoding="utf-8").split("\n")
    lines = [l.replace(",counted,approved,", ",counted,maybe,", 1) if l.startswith(row + ",") else l for l in lines]
    bad.members.write_text("\n".join(lines), encoding="utf-8")
    monkeypatch.setattr(pf, "DEFAULT_PATHS", bad)
    try:
        with pytest.raises(pf.RegistryError) as raised:
            importlib.reload(facade)
    finally:
        monkeypatch.undo()
        importlib.reload(facade)
    assert "platform_family_members.csv" in str(raised.value) and row in str(raised.value)


# program_pdf_receipts.py:274-276 at 88538c6a, in order.
RECEIPT_TAILS_88538C6A = [
    r" for reviewed F-15 members, PB20\d{2}, FY20\d{2} (?:actuals|enacted|request); one selected scenario column per workbook line",
    r" for workbook program (?:P-1|R-1):[A-Za-z0-9:]+, PB20\d{2}, FY20\d{2} (?:actuals|enacted|request); each selected workbook input once",
    r" via annual reviewed F-15 actuals totals, FY20\d{2}–FY20\d{2}; each fiscal year once, nominal USD thousands; excludes enacted/current-year figures and requests",
]


def test_family_formula_tails_equal_the_88538c6a_strings():
    from govbudget.platform_families import load_registry   # local: Task 6 may land before Task 3b's imports
    from govbudget.program_pdf_receipts import family_formula_tails
    assert family_formula_tails(load_registry()) == RECEIPT_TAILS_88538C6A
