<!-- Part of the families piece-1 plan. Read ../README.md (Global Constraints, Binding Cross-Task Decisions) first; ../notes.md has background. -->

### Task 11: propose: lake read, research outputs, class rulings to seed, successor search

**Spec:** §4.6 (`keys.csv`, `chains.csv`, `review.csv` sorted by dollars, `counts.json`), §4.3 (the
class-ruled seed rows, `decided_by=owner`, ruling ids, `decided_on`), §5.2 (rulings applied at
propose time; owner batch rows kept), §5.3 (pre-filled `proposed_decision` + reason), §5.4 (stated
successors: literal code, then without the 4-digit prefix; continuation wording only; JLTV found,
F015E0 not).

**Files:**
- Modify: `src/govbudget/jbooks/era_map.py` (append after the Task 10 content, i.e. after the last
  line `    return rows, left`)
- Create: `tests/jbooks/era_map_fixtures.py`
- Test: `tests/jbooks/test_era_map_propose.py`
- Create (real-data step, committed): `data/research/era_map/keys.csv`, `data/research/era_map/chains.csv`,
  `data/research/era_map/review.csv`, `data/research/era_map/counts.json`,
  `dbt/seeds/p1_era_code_decisions.csv`

**Interfaces:** Consumes: everything Task 10 produces; `EraKeyConflict` (Task 6); the lake column
`line_item_code` in `data/parquet/jbooks/budget_lines.parquet` (Tasks 7–8: migration 021,
`export_facts` column, S1 reload + `jbooks export-facts`); Task 9's classified rows (excluded here
because `9999999999` is not an era key); `fct_decade_series` and `dim_programs` in DuckDB (exist
today); `make_pdf` (`tests/pdf_factory.py:13`). / Produces: `SUCCESSOR_RE`, `SUCCESSOR_EDITION_DIRS`,
`code_forms(code)`, `successor_xml_files(raw_docs_dir)`, `search_successors(chains, *, raw_docs_dir,
modern) -> dict[str, dict]` (keys `successor_code`, `successor_account`, `successor_evidence`,
`matched_form`, `xml`, `line`, `quote`), dataclass `LakeInputs(era, modern, collision_codes,
modern_pages)`, `jbooks_parquet(duckdb_path, name)`, `load_era_keys(duckdb_path, *, with_amounts=True)
-> list[EraKey]`, `load_inputs(duckdb_path) -> LakeInputs`, `read_csv`, `write_csv`, `read_seed`,
`write_seed`, `propose(*, duckdb_path, raw_docs_dir, out_dir, seed_path, decided_on) -> dict`;
private helpers `_org_editions(era, split)` and `_org_clash(ch, ctx, collision_codes, page,
org_editions)` behind the CONTRACT ISSUE 9c pre-fill; test helpers
`jbooks.era_map_fixtures.make_lake(root, *, code_column=True, blank_code=False, extra_era=(),
org_clash=False)` (with `ERA_ORG_CLASH`, `MODERN_ORG_CLASH`) and `make_raw_docs(root)`; the
committed research files and the class-ruled seed (1,128 rows).

`successor_evidence` format: `xml=<path under raw_docs>:<line>; xml_sha256=<sha>; pdf=<sibling PDF>;
pdf_sha256=<sha>; pdf_page=<n>; form=<literal|short>; quote="<sentence>"` (the three `pdf` parts only
when the XML sits in a `<book>__xml/` directory beside `<book>.pdf`).

- [ ] **Step 1: Write the test fixtures**

Create `tests/jbooks/era_map_fixtures.py`:

```python
"""A miniature lake for the era-map tests (families piece 1, plan Tasks 11–12).

Layout mirrors the live one: {root}/duckdb/govbudget.duckdb holds
fct_decade_series + dim_programs; {root}/parquet/jbooks/{budget_lines,
documents}.parquet sit beside it (all-varchar, as `jbooks export-facts`
writes them); {root}/raw_docs/fy2026/... holds PB2026 XML and one PDF.

The world (editions 2022–2023 era, 2026 modern):
  ATA000|3010F|      A1 both editions          → R-DEC-ERA-SAME
  3010|1611N|        A1, collision (account)   → SAME pinned 1611N/N
  20|0300D|DTRA      A1, collision (org)       → SAME pinned 0300D/DTRA
  20|0300D|DSS       R2 (DSS has no page)      → review, pre-fill DCSA
  20|0300D|DHRA      A1, collision, no page    → review, pre-fill history_only
  FY2017CR|2031A|    CR                        → EXCLUDE placeholder
  O&M|0390D|         UNSAFE                    → EXCLUDE route-unsafe
  5600D15603|2035A|  H, drift-free             → HISTORY + successor 5731D15610
  F015E0|3010F|      H, drift-free             → HISTORY, no successor
  50|0300D|          H, titles drift           → review
  1045|1612N|        R2 (code under 1611N)     → review

make_lake(..., org_clash=True) adds two organizations printing one code in
one edition, where the page is the other organization's (the live
PB2018 `10`: TJS's page, DPAA's line; PB2017-22 `500`: DLA's page, DCMA's
line). Tests using it set ORG_SPLIT_CODES to {'10', '20'}:
  10|0300D|TJS       A1, not a collision code  → SAME (page 10 is TJS's)
  10|0300D|DPAA      R2, PB2022 beside TJS     → review, pre-fill history_only
  20|0300D|DLA       R2, title = DTRA's page   → review, pre-fill history_only
                                                  pinned to its own 0300D/DLA
"""
from __future__ import annotations

from pathlib import Path

import duckdb

from pdf_factory import make_pdf

BL_COLS = ("exhibit", "fiscal_year", "account", "account_title", "organization",
           "budget_activity", "budget_activity_title", "pe_bli", "title",
           "amount_type", "amount_thousands", "source_document_id",
           "source_sheet", "source_cells", "line_item_code")
DOC_SHA = {"22": "22" * 32, "23": "23" * 32, "26": "26" * 32}

# (edition, account, org, line, code, title, actuals_k, enacted_k)
ERA = [
    (2022, "3010F", "AF", "1", "ATA000", "F-35", "100", "150"),
    (2023, "3010F", "AF", "1", "ATA000", "F-35", "200", "250"),
    (2023, "1611N", "NAVY", "5", "3010", "LPD Flight II", "900", None),
    (2022, "0300D", "DSS", "20", "20", "Major Equipment", "40", None),
    (2022, "0300D", "DTRA", "21", "20", "Vehicles", "30", None),
    (2023, "0300D", "DHRA", "22", "20", "Personnel Administration", "5", None),
    (2022, "2031A", "ARMY", "99", "FY2017CR", "FY 2017 CR Adjustment", None, None),
    (2023, "0390D", "CBDP", "2", "O&M", "Operation & Maintenance", "60", None),
    (2022, "2035A", "ARMY", "7", "5600D15603", "Joint Light Tactical Vehicle", "3000", None),
    (2023, "2035A", "ARMY", "7", "5600D15603", "JOINT LIGHT TACTICAL VEHICLE", "1000", None),
    (2022, "3010F", "AF", "3", "F015E0", "F-15e", "600", None),
    (2023, "3010F", "AF", "4", "F015E0", "F-15e", "20", None),
    (2022, "0300D", "DTRA", "50", "50", "Indian Financing Act", "7", None),
    (2023, "0300D", "DTRA", "50", "50", "DTRA Cyber Activities", None, None),
    (2022, "1612N", "NAVY", "3", "1045", "OHIO Replacement Submarine", "500", None),
]
# (code, account, org, title, actuals_k, has a PB2026 page in dim_programs)
MODERN = [
    ("ATA000", "3010F", "F", "F-35", "250", True),
    ("3010", "1611N", "N", "LPD Flight II", "950", True),
    ("3010", "1810N", "N", "Shipboard Tactical Communications", "20", True),
    ("20", "0300D", "DCSA", "Major Equipment", "45", True),
    ("20", "0300D", "DTRA", "Vehicles", "31", True),
    ("20", "0300D", "DHRA", "Personnel Administration", "6", False),
    ("5731D15610", "2035A", "A", "Joint Light Tactical Vehicle (JLTV)", "900", True),
    ("1045", "1611N", "N", "Columbia Class Submarine", "2000", True),
]
# make_lake(org_clash=True) only
ERA_ORG_CLASH = [
    (2022, "0300D", "TJS", "43", "10", "Major Equipment, TJS", "600", None),
    (2023, "0300D", "TJS", "44", "10", "Major Equipment, TJS", "700", None),
    (2022, "0300D", "DPAA", "22", "10", "Major Equipment, DPAA", "90", None),
    (2022, "0300D", "DLA", "23", "20", "Vehicles", "8", None),
]
MODERN_ORG_CLASH = [
    ("10", "0300D", "TJS", "Major Equipment, TJS", "800", True),
]
JLTV_SENTENCE = (
    "NOTE: This budget line D15610 is a continuation of an existing effort"
    " where prior year funds through FY 2020 are reflected under the previous"
    " budget line D15603."
)
F15_SENTENCE = (
    "This exhibit does not include the eight aircraft in Lot 1 which were"
    " funded outside this exhibit in FY 2020 (two test aircraft were purchased"
    " with RDT&amp;E funds (PE 0207134F); four operationally representative test"
    " aircraft and two operational aircraft were purchased with procurement"
    " funds (F015E0, Line #3))."
)


def era_key(account: str, org: str, line: str) -> str:
    return f"{account}-{org}-L{line}"


def _era_bl_rows(era, blank_code: bool):
    rows = []
    for ed, acct, org, line, code, title, act, enacted in era:
        pe = era_key(acct, org, line)
        for slot, amt in ((f"fy_{ed - 2}_actuals", act or "0"),
                          (f"fy_{ed - 1}_total", enacted or "0")):
            cells = f"O{line}" if slot.endswith("actuals") else f"Q{line}"
            rows.append(("P-1", str(ed), acct, "Acct", org, "01", "BA", pe, title,
                         slot, amt, str(ed - 2000), "Exhibit P-1", cells,
                         "" if blank_code else code))
    return rows


def _modern_bl_rows(modern):
    return [("P-1", "2026", acct, "Acct", org, "01", "BA", code, title,
             "fy_2024_actuals", act, "26", "Exhibit P-1", "O9", code)
            for code, acct, org, title, act, _page in modern]


def _write_parquet(path: Path, cols, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("create table t (" + ", ".join(f'"{c}" varchar' for c in cols) + ")")
    if rows:
        con.executemany("insert into t values (" + ", ".join("?" * len(cols)) + ")", rows)
    con.execute(f"copy t to '{path}' (format parquet)")
    con.close()


def make_lake(root: Path, *, code_column: bool = True, blank_code: bool = False,
              extra_era: list[tuple] = (), org_clash: bool = False) -> Path:
    """Write the miniature lake under root; return the DuckDB path."""
    era = ERA + (ERA_ORG_CLASH if org_clash else [])
    modern = MODERN + (MODERN_ORG_CLASH if org_clash else [])
    cols = BL_COLS if code_column else BL_COLS[:-1]
    rows = _era_bl_rows(era, blank_code) + _modern_bl_rows(modern) + list(extra_era)
    if not code_column:
        rows = [r[:-1] for r in rows]
    _write_parquet(root / "parquet" / "jbooks" / "budget_lines.parquet", cols, rows)
    _write_parquet(
        root / "parquet" / "jbooks" / "documents.parquet",
        ("id", "org", "exhibit_family", "fiscal_year", "title", "source_url",
         "sha256", "bytes", "downloaded_at", "rel_path"),
        [(i, "DOD", "rollup", f"20{i}", "p1_display.xlsx", "https://x.test",
          sha, "1", "2026-01-01", f"fy20{i}/dod/p1_display.xlsx")
         for i, sha in DOC_SHA.items()],
    )
    db = root / "duckdb" / "govbudget.duckdb"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db))
    con.execute("create table fct_decade_series (pe_bli varchar, account varchar,"
                " organization varchar, fy integer, edition_year integer,"
                " amount_type_kind varchar, amount double)")
    for ed, acct, org, line, _code, _t, act, enacted in era:
        pe = era_key(acct, org, line)
        if act is not None:
            con.execute("insert into fct_decade_series values (?,null,null,?,?,'actuals',?)",
                        [pe, ed - 2, ed, float(act)])
        if enacted is not None:
            con.execute("insert into fct_decade_series values (?,null,null,?,?,'enacted',?)",
                        [pe, ed - 1, ed, float(enacted)])
    for code, acct, org, _t, act, _page in modern:
        a = acct if code == "3010" else None
        o = org if code == "20" else None
        con.execute("insert into fct_decade_series values (?,?,?,2024,2026,'actuals',?)",
                    [code, a, o, float(act)])
    con.execute("create table dim_programs (pe_bli varchar, account varchar, org varchar)")
    con.executemany("insert into dim_programs values (?,?,?)",
                    [(code, acct, org) for code, acct, org, _t, _a, page in modern
                     if page])
    con.close()
    return db


def make_raw_docs(root: Path) -> Path:
    """PB2026 XML: the JLTV continuation in its own BA1 JB (and in a master
    MJB of another volume, which must lose), F-15's 'funded outside' sentence;
    a sibling PDF printing the JLTV sentence on page 2."""
    raw = root / "raw_docs"
    ba1 = raw / "fy2026" / "a" / "Other Procurement - BA1 - Tactical & Support Vehicles__xml"
    mjb = raw / "fy2026" / "a" / "Other Procurement - BA 3, 4 & 6 - Other__xml"
    af = raw / "fy2026" / "f" / "xml"
    for d in (ba1, mjb, af):
        d.mkdir(parents=True, exist_ok=True)
    body = ("<proc:Justification>JLTV allocations are based on fielding plans.\n\n"
            f"{JLTV_SENTENCE}\n\nIn accordance with Section 1815.</proc:Justification>")
    (ba1 / "U_PROCUREMENT_JB_2506261600ZZZZ_ARMY_PB_2026.xml").write_text(
        "<?xml version='1.0'?>\n<root>\n" + body + "\n</root>\n")
    (mjb / "U_PROCUREMENT_MJB_2506261600XAYF_ARMY_PB_2026.xml").write_text(
        "<?xml version='1.0'?>\n<root>\n\n\n" + body + "\n</root>\n")
    (af / "U_PROCUREMENT_JB_2506261600ZZZZ_AF_PB_2026.xml").write_text(
        f"<?xml version='1.0'?>\n<root><proc:Description>{F15_SENTENCE}"
        "</proc:Description></root>\n")
    make_pdf(ba1.parent / "Other Procurement - BA1 - Tactical & Support Vehicles.pdf", [
        ["Exhibit P-40, Budget Line Item Justification", "Joint Light Tactical Vehicle"],
        ["NOTE: This budget line D15610 is a continuation of an existing effort",
         "where prior year funds through FY 2020 are reflected under the previous",
         "budget line D15603."],
    ])
    return raw
```

- [ ] **Step 2: Write the failing tests**

Create `tests/jbooks/test_era_map_propose.py`:

```python
"""era_map lake reading, successor search and propose (plan Task 11; spec
§4.3, §4.6, §5.2, §5.4) on the miniature lake in era_map_fixtures."""
from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal

import pytest

from govbudget.jbooks import era_map
from govbudget.jbooks.era_map import Chain, ModernLine, search_successors
from govbudget.jbooks.p1_loader import EraKeyConflict
from jbooks.era_map_fixtures import (
    JLTV_SENTENCE,
    make_lake,
    make_raw_docs,
)

ON = date(2026, 10, 2)
JB = ("fy2026/a/Other Procurement - BA1 - Tactical & Support Vehicles__xml/"
      "U_PROCUREMENT_JB_2506261600ZZZZ_ARMY_PB_2026.xml")


@pytest.fixture(autouse=True)
def _mini_org_split(monkeypatch):
    # the miniature world splits only code '20' by organization
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"20"}))


def rows(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def run(tmp_path, seed=None, decided_on=ON):
    db = make_lake(tmp_path / "lake")
    raw = make_raw_docs(tmp_path)
    out = tmp_path / "research" / "era_map"
    seed = seed or tmp_path / "seeds" / "p1_era_code_decisions.csv"
    counts = era_map.propose(duckdb_path=db, raw_docs_dir=raw, out_dir=out,
                             seed_path=seed, decided_on=decided_on)
    return counts, out, seed


# ---------------------------------------------------------------------------
# lake reading
# ---------------------------------------------------------------------------

def test_load_era_keys_reads_code_sha_cells_and_amounts(tmp_path):
    era = {k.era_key + f"@{k.edition}": k
           for k in era_map.load_era_keys(make_lake(tmp_path))}
    assert len(era) == 15
    k = era["2035A-ARMY-L7@2022"]
    assert k.line_item_code == "5600D15603"
    assert k.filed_title == "Joint Light Tactical Vehicle"
    assert (k.organization, k.budget_activity) == ("ARMY", "01")
    assert k.source_document_sha256 == "22" * 32
    assert k.source_cells == ("O7", "Q7")
    assert k.actuals_k == Decimal("3000")
    assert k.enacted_k is None


def test_load_inputs_modern_collisions_and_pages(tmp_path):
    inputs = era_map.load_inputs(make_lake(tmp_path))
    assert inputs.collision_codes == frozenset({"3010", "20"})
    assert ("20", "0300D", "DCSA") in inputs.modern_pages
    lines = {(m.code, m.account, m.organization): m for m in inputs.modern}
    assert lines[("ATA000", "3010F", "F")].actuals_k == Decimal("250")
    assert lines[("3010", "1810N", "N")].actuals_k == Decimal("20")
    assert lines[("20", "0300D", "DCSA")].actuals_k == Decimal("45")


def test_missing_line_item_code_column_is_a_clear_precondition(tmp_path):
    db = make_lake(tmp_path, code_column=False)
    with pytest.raises(RuntimeError, match="no line_item_code column.*Tasks 7-8"):
        era_map.load_era_keys(db)


def test_blank_line_item_code_refuses(tmp_path):
    db = make_lake(tmp_path, blank_code=True)
    with pytest.raises(RuntimeError, match="blank line_item_code"):
        era_map.load_era_keys(db)


def test_a_key_printing_two_codes_raises(tmp_path):
    clash = ("P-1", "2022", "3010F", "Acct", "AF", "01", "BA", "3010F-AF-L1",
             "F-35", "fy_2022_request", "5", "22", "Exhibit P-1", "S1", "B02100")
    db = make_lake(tmp_path, extra_era=[clash])
    with pytest.raises(EraKeyConflict, match="3010F-AF-L1.*code"):
        era_map.load_era_keys(db)


# ---------------------------------------------------------------------------
# successor search (§5.4)
# ---------------------------------------------------------------------------

def chain(code, account, classes=("H",)):
    return Chain(chain_id=f"{code}|{account}|", line_item_code=code,
                 account=account, organization="", keys=((2022, "k"),),
                 classes=frozenset(classes), titles_by_edition={2022: "t"},
                 actuals_k=Decimal(0), n_keys=1, keys_sha256="")


def modern(*codes):
    return [ModernLine(edition=2026, code=c, account=a, organization="A", title="t")
            for c, a in codes]


def test_jltv_short_form_successor_with_pdf_page(tmp_path):
    raw = make_raw_docs(tmp_path)
    got = search_successors(
        [chain("5600D15603", "2035A"), chain("F015E0", "3010F")],
        raw_docs_dir=raw, modern=modern(("5731D15610", "2035A"), ("F01500", "3010F")))
    assert list(got) == ["5600D15603|2035A|"]          # F015E0: no continuation wording
    s = got["5600D15603|2035A|"]
    assert (s["successor_code"], s["successor_account"], s["matched_form"]) == (
        "5731D15610", "2035A", "short")
    assert (s["xml"], s["line"]) == (JB, 5)                # the volume's JB beats a master MJB
    assert s["quote"] == JLTV_SENTENCE
    ev = s["successor_evidence"]
    assert ev.startswith(f"xml={JB}:5; xml_sha256=")
    assert ("pdf=fy2026/a/Other Procurement - BA1 - Tactical & Support Vehicles.pdf;"
            in ev)
    assert "pdf_page=2;" in ev and "form=short;" in ev
    assert ev.endswith(f'quote="{JLTV_SENTENCE}"')


def test_literal_form_and_only_era_only_chains(tmp_path):
    xml = tmp_path / "fy2025" / "dw" / "xml" / "U_PROCUREMENT_JB_X_DW_PB_2025.xml"
    xml.parent.mkdir(parents=True)
    xml.write_text("<a>Line ABC123 continues under line DEF456 from FY 2024.</a>\n"
                   "<a>Line QRS789 continues under line DEF456 too.</a>\n")
    got = search_successors(
        [chain("ABC123", "0300D"), chain("QRS789", "0300D", classes=("A1",))],
        raw_docs_dir=tmp_path, modern=modern(("DEF456", "0300D")))
    assert {cid: s["successor_code"] for cid, s in got.items()} == {
        "ABC123|0300D|": "DEF456"}
    assert got["ABC123|0300D|"]["matched_form"] == "literal"
    assert "pdf=" not in got["ABC123|0300D|"]["successor_evidence"]


def test_ambiguous_or_numeric_codes_record_nothing(tmp_path):
    xml = tmp_path / "fy2026" / "n" / "xml" / "U_PROCUREMENT_JB_X_NAVY_PB_2026.xml"
    xml.parent.mkdir(parents=True)
    xml.write_text(
        "<a>Line ABC123 is a continuation of DEF456 and GHI789.</a>\n"
        "<a>Line 1234 is a continuation of line 5678.</a>\n")
    got = search_successors(
        [chain("ABC123", "0300D"), chain("1234", "1611N")], raw_docs_dir=tmp_path,
        modern=[*modern(("DEF456", "0400D"), ("GHI789", "0500D")),
                ModernLine(2026, "5678", "1611N", "N", "t")])
    assert got == {}


def test_successor_prefers_the_chains_own_account(tmp_path):
    xml = tmp_path / "fy2026" / "n" / "xml" / "U_PROCUREMENT_JB_X_NAVY_PB_2026.xml"
    xml.parent.mkdir(parents=True)
    xml.write_text("<a>Line ABC123 continues under DEF456 and GHI789.</a>\n")
    got = search_successors(
        [chain("ABC123", "0300D")], raw_docs_dir=tmp_path,
        modern=modern(("DEF456", "0300D"), ("GHI789", "0500D")))
    assert got["ABC123|0300D|"]["successor_code"] == "DEF456"


# ---------------------------------------------------------------------------
# propose
# ---------------------------------------------------------------------------

def test_propose_counts(tmp_path):
    counts, out, _seed = run(tmp_path)
    assert counts["era_keys"] == 15 and counts["chains"] == 11
    assert counts["chain_groups"] == {
        "a1_only": 4, "cr": 1, "h_drift_free": 2, "h_drifting": 1,
        "r_containing": 2, "unsafe": 1}
    assert counts["key_classes"] == {"CR": 1, "UNSAFE": 1, "R3": 0, "A1": 5,
                                     "A2": 0, "R1": 0, "R2": 2, "H": 6}
    assert counts["rulings"] == {"R-DEC-ERA-SAME": 3, "R-DEC-ERA-EXCLUDE": 2,
                                 "R-DEC-ERA-HISTORY": 2}
    assert counts["review_rows"] == 4 and counts["left_ruling"] == 1
    assert counts["successors"] == {"5600D15603|2035A|": "5731D15610"}
    assert counts["era_actuals_k"] == "6462"
    assert counts["collision_codes"] == ["20", "3010"]
    assert counts["org_split_codes"] == ["20"]
    assert json.loads((out / "counts.json").read_text()) == counts


def test_propose_seed_rows(tmp_path):
    _counts, _out, seed = run(tmp_path)
    got = {r["decision_id"]: r for r in rows(seed)}
    assert list(got) == sorted(got)
    assert set(got) == {
        "3010|1611N||2023-2023", "5600D15603|2035A||2022-2023",
        "ATA000|3010F||2022-2023", "F015E0|3010F||2022-2023",
        "FY2017CR|2031A||2022-2022", "O&M|0390D||2023-2023",
        "20|0300D|DTRA|2022-2022"}
    assert (got["3010|1611N||2023-2023"]["program_account"],
            got["3010|1611N||2023-2023"]["program_org"]) == ("1611N", "N")
    assert got["20|0300D|DTRA|2022-2022"]["program_org"] == "DTRA"
    jltv = got["5600D15603|2035A||2022-2023"]
    assert (jltv["decision"], jltv["ruling"], jltv["successor_code"],
            jltv["successor_account"]) == (
        "history_only", "R-DEC-ERA-HISTORY", "5731D15610", "2035A")
    assert got["F015E0|3010F||2022-2023"]["successor_code"] == ""
    ata = got["ATA000|3010F||2022-2023"]
    assert ata["modern_title"] == "F-35"
    assert ata["evidence"] == "title_jaccard=1.00; continuity=1/1; actuals_k=300"
    assert {r["decided_by"] for r in got.values()} == {"owner"}
    assert {r["decided_on"] for r in got.values()} == {"2026-10-02"}


def test_propose_review_rows_sorted_by_dollars(tmp_path):
    _counts, out, _seed = run(tmp_path)
    review = rows(out / "review.csv")
    assert tuple(review[0]) == era_map.REVIEW_COLUMNS
    assert [r["chain_id"] for r in review] == [
        "1045|1612N|", "20|0300D|DSS", "50|0300D|", "20|0300D|DHRA"]
    ohio, dss, fifty, dhra = review
    assert (ohio["proposed_decision"], ohio["program_account"]) == ("same_program", "")
    assert ohio["accounts"] == "era=1612N; modern=1611N"
    assert (dss["proposed_decision"], dss["program_account"], dss["program_org"]) == (
        "same_program", "0300D", "DCSA")
    assert fifty["proposed_decision"] == "history_only"
    # A1 on a collision code with no PB2026 page: data only, pinned to its line
    assert (dhra["proposed_decision"], dhra["program_account"], dhra["program_org"]) == (
        "history_only", "0300D", "DHRA")
    assert fifty["titles_by_edition"] == (
        "2022: Indian Financing Act; 2023: DTRA Cyber Activities")
    assert {r["decision"] for r in review} == {""}
    assert all(len(r["keys_sha256"]) == 64 for r in review)


def test_propose_keys_and_chains_csv(tmp_path):
    _counts, out, _seed = run(tmp_path)
    keys = rows(out / "keys.csv")
    assert len(keys) == 15 and tuple(keys[0]) == era_map.KEY_COLUMNS
    k = next(r for r in keys if r["era_key"] == "2035A-ARMY-L7" and r["edition"] == "2022")
    assert (k["line_number"], k["class"], k["chain_id"], k["source_rows"],
            k["source_cells"]) == ("7", "H", "5600D15603|2035A|", "7", "O7,Q7")
    chains = {r["chain_id"]: r for r in rows(out / "chains.csv")}
    assert len(chains) == 11
    assert chains["20|0300D|DHRA"]["left_ruling_reason"] == (
        "collision code without a matching PB2026 page")
    assert chains["5600D15603|2035A|"]["successor_evidence"].startswith(f"xml={JB}:5;")
    assert chains["FY2017CR|2031A|"]["ruling"] == "R-DEC-ERA-EXCLUDE"
    assert chains["50|0300D|"]["ruling"] == ""


def test_propose_is_byte_stable_and_keeps_class_ruling_dates(tmp_path):
    _c, out, seed = run(tmp_path)
    first = {p.name: p.read_bytes() for p in [seed, *sorted(out.iterdir())]}
    era_map.propose(duckdb_path=tmp_path / "lake" / "duckdb" / "govbudget.duckdb",
                    raw_docs_dir=tmp_path / "raw_docs", out_dir=out, seed_path=seed,
                    decided_on=date(2027, 1, 1))
    second = {p.name: p.read_bytes() for p in [seed, *sorted(out.iterdir())]}
    assert first == second


def test_propose_keeps_owner_batch_rows_and_skips_their_chains(tmp_path):
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    owner = {c: "" for c in era_map.SEED_COLUMNS}
    owner.update({"decision_id": "50|0300D||2022-2023", "line_item_code": "50",
                  "account": "0300D", "first_edition": "2022", "last_edition": "2023",
                  "decision": "exclude_reused_code", "n_keys": "2",
                  "keys_sha256": "x" * 64, "decided_on": "2026-10-05",
                  "decided_by": "owner", "ruling": "R-DEC-ERA-B1"})
    era_map.write_seed(seed, [owner])
    counts, out, _ = run(tmp_path, seed=seed)
    assert counts["owner_batch_chains"] == 1
    assert "50|0300D|" not in {r["chain_id"] for r in rows(out / "review.csv")}
    assert next(r for r in rows(seed) if r["ruling"] == "R-DEC-ERA-B1") == owner


def test_propose_prefills_history_only_on_another_organizations_page(
        tmp_path, monkeypatch):
    # PB2022 prints `10` for TJS (the page's organization) and DPAA, and `20`
    # for DTRA (page 20-DTRA) and DLA, whose title matches DTRA's page:
    # same_program would put DPAA's / DLA's dollars on the other's page.
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"10", "20"}))
    db = make_lake(tmp_path / "lake", org_clash=True)
    out = tmp_path / "research" / "era_map"
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    counts = era_map.propose(duckdb_path=db, raw_docs_dir=make_raw_docs(tmp_path),
                             out_dir=out, seed_path=seed, decided_on=ON)
    assert counts["org_split_codes"] == ["10", "20"]
    assert counts["collision_codes"] == ["20", "3010"]
    review = {r["chain_id"]: r for r in rows(out / "review.csv")}
    dpaa, dla, dss = review["10|0300D|DPAA"], review["20|0300D|DLA"], review["20|0300D|DSS"]
    assert (dpaa["proposed_decision"], dpaa["program_account"], dpaa["program_org"],
            dpaa["reason"]) == (
        "history_only", "", "", "R2: code also printed by TJS in PB2022; page 10 is TJS's")
    # a collision code pins the chain's own identity, apart from page 20-DTRA
    assert (dla["proposed_decision"], dla["program_account"], dla["program_org"],
            dla["reason"]) == (
        "history_only", "0300D", "DLA",
        "R2: code also printed by DTRA in PB2022; page 20-DTRA (title match) is DTRA's")
    # DSS -> DCSA: page 20-DCSA has no era keys beside DSS's, an organization rename
    assert (dss["proposed_decision"], dss["program_org"]) == ("same_program", "DCSA")
    seeded = {r["decision_id"]: r for r in rows(seed)}
    assert (seeded["10|0300D|TJS|2022-2023"]["ruling"],
            seeded["10|0300D|TJS|2022-2023"]["program_org"]) == ("R-DEC-ERA-SAME", "")


def test_propose_refuses_to_overwrite_unratified_decisions(tmp_path):
    _c, out, seed = run(tmp_path)
    review = rows(out / "review.csv")
    review[0]["decision"] = "same_program"
    era_map.write_csv(out / "review.csv", era_map.REVIEW_COLUMNS, review)
    before = (seed.read_bytes(), (out / "review.csv").read_bytes())
    with pytest.raises(RuntimeError, match="not ratified yet.*1045"):
        era_map.propose(duckdb_path=tmp_path / "lake" / "duckdb" / "govbudget.duckdb",
                        raw_docs_dir=tmp_path / "raw_docs", out_dir=out,
                        seed_path=seed, decided_on=ON)
    assert (seed.read_bytes(), (out / "review.csv").read_bytes()) == before


def test_propose_refuses_a_changed_org_split(tmp_path, monkeypatch):
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"10", "20"}))
    with pytest.raises(RuntimeError, match="org-split codes changed"):
        run(tmp_path)
```

- [ ] **Step 3: Run the tests and watch them fail**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_era_map_propose.py -q`

Expected: collection error, ending
```
E   ImportError: cannot import name 'search_successors' from 'govbudget.jbooks.era_map' (.../src/govbudget/jbooks/era_map.py)
1 error in 0.2s
```

- [ ] **Step 4: Append the lake reader, successor search and propose**

Append to the end of `src/govbudget/jbooks/era_map.py`, leaving two blank lines after
`    return rows, left`:

```python
# ---------------------------------------------------------------------------
# Stated successors (§5.4)
# ---------------------------------------------------------------------------

# Continuation wording only — a mention of both codes is not enough.
SUCCESSOR_RE = re.compile(
    r"continuation of|continues under|previously (?:funded|reflected) (?:under|in)",
    re.IGNORECASE,
)
# Code-shaped tokens: 5+ uppercase alphanumerics with at least one letter and
# one digit. Digits-only codes ('1045') are never matched: in prose they are
# indistinguishable from years, quantities and line numbers.
_CODE_TOKEN_RE = re.compile(r"\b(?=[A-Z0-9]*[A-Z])(?=[A-Z0-9]*[0-9])[A-Z0-9]{5,}\b")
_ACCOUNT_PREFIX_RE = re.compile(r"^[0-9]{4}(?=[A-Z])")
SUCCESSOR_EDITION_DIRS = ("fy2026", "fy2025", "fy2024")


def code_forms(code: str) -> list[tuple[str, str]]:
    """[(token, form)]: the literal code, then — for a code printed with a
    4-digit account prefix ('5600D15603') — the code without it ('D15603'),
    which is how the Army books print it."""
    forms = [(code, "literal")]
    short = _ACCOUNT_PREFIX_RE.sub("", code)
    if short != code and len(short) >= 5:
        forms.append((short, "short"))
    return forms


def successor_xml_files(raw_docs_dir: Path) -> list[Path]:
    """PB2026, then PB2025, then PB2024 XML; inside an edition, a volume's own
    justification book before any master book ('_MJB_' bundles every volume),
    then by path."""
    out: list[Path] = []
    for edition_dir in SUCCESSOR_EDITION_DIRS:
        base = Path(raw_docs_dir) / edition_dir
        if not base.is_dir():
            continue
        out.extend(sorted(
            base.rglob("*.xml"),
            key=lambda p: ("_MJB_" in p.name, p.relative_to(base).as_posix()),
        ))
    return out


def _sentence_bounds(text: str, start: int, end: int) -> tuple[int, int]:
    """The sentence around text[start:end]: bounded by a newline, an XML tag
    edge, or a period followed by a space."""
    lows = [text.rfind("\n", 0, start), text.rfind(">", 0, start)]
    dot = text.rfind(". ", 0, start)
    if dot >= 0:
        lows.append(dot + 1)
    lo = max(lows) + 1
    highs = [p for p in (text.find("\n", end), text.find("<", end)) if p >= 0]
    dot = text.find(". ", end)
    if dot >= 0:
        highs.append(dot + 1)
    hi = min(highs) if highs else len(text)
    return lo, hi


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _pdf_page(pdf: Path, quote: str) -> int | None:
    """1-based page of the PDF whose text contains the quote (whitespace
    ignored), or None."""
    from pypdf import PdfReader

    needle = "".join(quote.split())
    for i, page in enumerate(PdfReader(str(pdf)).pages, start=1):
        if needle in "".join((page.extract_text() or "").split()):
            return i
    return None


def search_successors(
    chains: Sequence[Chain], *, raw_docs_dir: Path, modern: Sequence[ModernLine],
) -> dict[str, dict]:
    """{chain_id: successor} for era-only chains (classes == {'H'}) whose code
    a PB2024–26 J-book XML sentence states continues under one PB2024–26 P-1
    code. Each successor dict has successor_code, successor_account,
    successor_evidence, matched_form, xml, line, quote.

    A sentence qualifies only when it carries continuation wording
    (SUCCESSOR_RE), one of the era code's forms, and exactly one other
    PB2024–26 code (preferring the era chain's own account when the sentence
    names several). The first qualifying sentence in successor_xml_files
    order wins."""
    raw_docs_dir = Path(raw_docs_dir)
    targets = {c.chain_id: c for c in chains if c.classes == frozenset({"H"})}
    if not targets:
        return {}
    era_forms: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for cid, ch in targets.items():
        for token, form in code_forms(ch.line_item_code):
            era_forms[token].append((cid, form))
    modern_by_token: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for m in modern:
        for token, _form in code_forms(m.code):
            modern_by_token[token].add((m.code, m.account))
    found: dict[str, dict] = {}
    for xml in successor_xml_files(raw_docs_dir):
        if len(found) == len(targets):
            break
        text = xml.read_bytes().decode("utf-8", errors="replace")
        for hit in SUCCESSOR_RE.finditer(text):
            lo, hi = _sentence_bounds(text, hit.start(), hit.end())
            sentence = text[lo:hi]
            tokens = set(_CODE_TOKEN_RE.findall(sentence))
            for token in sorted(tokens):
                for cid, form in era_forms.get(token, ()):
                    if cid in found:
                        continue
                    ch = targets[cid]
                    own = {t for t, _f in code_forms(ch.line_item_code)}
                    cands: set[tuple[str, str]] = set()
                    for other in tokens - own:
                        cands |= modern_by_token.get(other, set())
                    same = {c for c in cands if c[1] == ch.account}
                    pick = same or cands
                    if len(pick) != 1:
                        continue
                    code, account = next(iter(pick))
                    rel = xml.relative_to(raw_docs_dir).as_posix()
                    line = text.count("\n", 0, hit.start()) + 1
                    quote = " ".join(sentence.split())
                    parts = [f"xml={rel}:{line}", f"xml_sha256={_sha256_file(xml)}"]
                    if xml.parent.name.endswith("__xml"):
                        pdf = xml.parent.parent / (xml.parent.name[: -len("__xml")] + ".pdf")
                        if pdf.is_file():
                            page = _pdf_page(pdf, quote)
                            parts += [f"pdf={pdf.relative_to(raw_docs_dir).as_posix()}",
                                      f"pdf_sha256={_sha256_file(pdf)}",
                                      f"pdf_page={page if page is not None else ''}"]
                    parts += [f"form={form}", f'quote="{quote}"']
                    found[cid] = {
                        "successor_code": code,
                        "successor_account": account,
                        "successor_evidence": "; ".join(parts),
                        "matched_form": form,
                        "xml": rel,
                        "line": line,
                        "quote": quote,
                    }
    return found


# ---------------------------------------------------------------------------
# Lake inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LakeInputs:
    era: list[EraKey]
    modern: list[ModernLine]
    collision_codes: frozenset[str]
    modern_pages: frozenset[tuple[str, str, str]]


def jbooks_parquet(duckdb_path: Path, name: str) -> Path:
    """data/parquet/jbooks/<name> beside the DuckDB file — the layouts
    export_site._stage_parquet_path probes: {duckdb_dir}/parquet/jbooks/
    (test fixtures), then {duckdb_dir}/../parquet/jbooks/ (data/duckdb +
    data/parquet)."""
    base = Path(duckdb_path).parent
    for cand in (base / "parquet" / "jbooks" / name,
                 base.parent / "parquet" / "jbooks" / name):
        if cand.is_file():
            return cand
    raise FileNotFoundError(
        f"era-map: {name} not found beside {duckdb_path}"
        f" (looked in {base / 'parquet' / 'jbooks'} and"
        f" {base.parent / 'parquet' / 'jbooks'})"
    )


def _sql_path(p: Path) -> str:
    return str(p).replace("'", "''")


def _dec(v) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def _cell_sort_key(cell: str) -> tuple[int, str]:
    m = re.match(r"^([A-Z]+)([0-9]+)$", cell)
    return (int(m.group(2)), m.group(1)) if m else (0, cell)


def _connect(duckdb_path: Path):
    import duckdb

    return duckdb.connect(str(duckdb_path), read_only=True)


def _read_budget_lines(con, duckdb_path: Path) -> list[tuple]:
    bl = jbooks_parquet(duckdb_path, "budget_lines.parquet")
    cols = {r[0] for r in con.execute(
        f"describe select * from read_parquet('{_sql_path(bl)}')").fetchall()}
    if "line_item_code" not in cols:
        raise RuntimeError(
            f"era-map: {bl} has no line_item_code column. The era map reads the"
            " printed budget line code from the lake: apply migration 021 and"
            " run the S1 reload (scripts/era/s1_reload_era_p1.py --apply) and"
            " `govbudget jbooks export-facts` first (plan Tasks 7-8)."
        )
    return con.execute(
        "select cast(fiscal_year as integer), account, organization,"
        " budget_activity, pe_bli, title, line_item_code, source_document_id,"
        " coalesce(source_cells, '')"
        f" from read_parquet('{_sql_path(bl)}')"
        " where exhibit = 'P-1' and cast(fiscal_year as integer) between 2017 and 2026"
    ).fetchall()


def load_era_keys(duckdb_path: Path, *, with_amounts: bool = True) -> list[EraKey]:
    """Every era P-1 key (PB2017–23, pe_bli an era procurement key) with its
    printed code, title, budget activity, workbook sha and cells; amounts
    from fct_decade_series when with_amounts. Raises EraKeyConflict if a key
    prints more than one code, title, budget activity or source document."""
    con = _connect(duckdb_path)
    try:
        rows = _read_budget_lines(con, duckdb_path)
        docs = dict(con.execute(
            "select id, sha256 from read_parquet("
            f"'{_sql_path(jbooks_parquet(duckdb_path, 'documents.parquet'))}')"
        ).fetchall())
        amounts: dict[tuple[str, int, str], Decimal] = {}
        if with_amounts:
            for pe, ed, kind, amt in con.execute(
                "select pe_bli, edition_year, amount_type_kind, amount"
                " from fct_decade_series where edition_year <= 2023"
                " and amount_type_kind in ('actuals', 'enacted')"
            ).fetchall():
                amounts[(pe, int(ed), kind)] = _dec(amt)
    finally:
        con.close()
    acc: dict[tuple[int, str], dict] = {}
    for ed, account, org, ba, pe, title, code, doc_id, cells in rows:
        if ed > 2023 or not is_era_procurement_key(pe):
            continue
        a = acc.setdefault((ed, pe), {"account": set(), "org": set(), "ba": set(),
                                       "title": set(), "code": set(), "doc": set(),
                                       "cells": set()})
        a["account"].add(account)
        a["org"].add(org)
        a["ba"].add(ba)
        a["title"].add(title)
        a["code"].add((code or "").strip())
        a["doc"].add(doc_id)
        a["cells"].update(c for c in cells.split(",") if c)
    era = []
    for (ed, pe), a in sorted(acc.items()):
        for what in ("account", "org", "ba", "title", "code", "doc"):
            if len(a[what]) != 1:
                raise EraKeyConflict(
                    f"era key {pe} (PB{ed}) has {len(a[what])} distinct {what}"
                    f" values: {sorted(map(str, a[what]))}")
        code = next(iter(a["code"]))
        if not code:
            raise RuntimeError(
                f"era-map: era key {pe} (PB{ed}) has a blank line_item_code —"
                " the S1 reload did not fill every era row (plan Task 8)")
        doc = next(iter(a["doc"]))
        if doc not in docs:
            raise RuntimeError(f"era-map: source document {doc} of {pe} (PB{ed})"
                               " is missing from documents.parquet")
        era.append(EraKey(
            edition=ed, account=next(iter(a["account"])),
            organization=next(iter(a["org"])), budget_activity=next(iter(a["ba"])),
            era_key=pe, line_item_code=code, filed_title=next(iter(a["title"])),
            actuals_k=amounts.get((pe, ed, "actuals")),
            source_document_sha256=docs[doc],
            source_cells=tuple(sorted(a["cells"], key=_cell_sort_key)),
            enacted_k=amounts.get((pe, ed, "enacted")),
        ))
    return era


def load_inputs(duckdb_path: Path) -> LakeInputs:
    """The era keys, the PB2024–26 P-1 lines, the PB2026 collision codes and
    the PB2026 page identities, all read-only."""
    era = load_era_keys(duckdb_path)
    con = _connect(duckdb_path)
    try:
        rows = _read_budget_lines(con, duckdb_path)
        grains = con.execute(
            "select pe_bli, account, organization, edition_year, amount_type_kind,"
            " amount from fct_decade_series where edition_year >= 2024"
            " and amount_type_kind in ('actuals', 'enacted')"
        ).fetchall()
        programs = con.execute(
            "select pe_bli, account, org from dim_programs").fetchall()
    finally:
        con.close()
    acct_split = {r[0] for r in grains if r[1] is not None}
    org_split = {r[0] for r in grains if r[2] is not None}
    amounts = {(pe, acct, org, int(ed), kind): _dec(amt)
               for pe, acct, org, ed, kind, amt in grains}
    modern: set[ModernLine] = set()
    for ed, account, org, _ba, pe, title, _code, _doc, _cells in rows:
        if ed < 2024 or pe == "9999999999" or not is_route_safe_code(pe):
            continue
        gk = (pe, account if pe in acct_split else None,
              org if pe in org_split else None, ed)
        modern.add(ModernLine(
            edition=ed, code=pe, account=account, organization=org, title=title,
            actuals_k=amounts.get(gk + ("actuals",)),
            enacted_k=amounts.get(gk + ("enacted",)),
        ))
    axes = require_resolved(programs, caller="era_map.load_inputs")
    return LakeInputs(
        era=era,
        modern=sorted(modern, key=lambda m: (m.edition, m.code, m.account,
                                             m.organization, m.title or "")),
        collision_codes=frozenset(axes),
        modern_pages=frozenset((pe, acct or "", org or "") for pe, acct, org in programs),
    )


# ---------------------------------------------------------------------------
# Seed / CSV I/O
# ---------------------------------------------------------------------------


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def write_csv(path: Path, columns: Sequence[str], rows: Iterable[Mapping]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(columns), lineterminator="\n",
                           extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


def read_seed(seed_path: Path) -> list[dict[str, str]]:
    if not Path(seed_path).is_file():
        return []
    rows = read_csv(seed_path)
    if rows and tuple(rows[0].keys()) != SEED_COLUMNS:
        raise ValueError(f"{seed_path}: header {tuple(rows[0].keys())} != SEED_COLUMNS")
    return rows


def write_seed(seed_path: Path, rows: Iterable[Mapping]) -> None:
    write_csv(Path(seed_path), SEED_COLUMNS, sorted(rows, key=lambda r: r["decision_id"]))


def _ranges_overlap(a: Mapping, b: Mapping) -> bool:
    return (a["line_item_code"], a["account"], a["organization"]) == (
        b["line_item_code"], b["account"], b["organization"]) and not (
        int(a["last_edition"]) < int(b["first_edition"])
        or int(b["last_edition"]) < int(a["first_edition"]))


# ---------------------------------------------------------------------------
# propose (§4.6, §5.2, §5.4)
# ---------------------------------------------------------------------------


def _chain_group(ch: Chain) -> str:
    """The research-pass bucket a chain falls in (mutually exclusive)."""
    if "CR" in ch.classes:
        return "cr"
    if "UNSAFE" in ch.classes:
        return "unsafe"
    if ch.classes == frozenset({"A1"}):
        return "a1_only"
    if ch.classes == frozenset({"H"}):
        return "h_drift_free" if title_drift_free(ch) else "h_drifting"
    if ch.classes & {"R1", "R2", "R3"}:
        return "r_containing"
    if "A2" in ch.classes:
        return "a2_without_r"
    return "other"


def _chain_context(ch: Chain, keys: Sequence[EraKey], ctx: _Context) -> dict:
    ident = ctx.ident(keys[0])
    mi = ctx.idx.get(ident)
    if mi is not None and mi.latest_title is not None:
        modern_title = mi.latest_title[1]
    else:
        modern_title = ""
    jac = [j for j in (ctx.best_jaccard(k) for k in keys) if j is not None]
    passed, total = ctx.continuity(ident)
    return {
        "modern_title": modern_title,
        "title_jaccard": f"{min(jac):.2f}" if jac else "",
        "continuity": f"{passed}/{total}",
        "continuity_ok": total == 0 or passed * 3 >= total * 2,
        "modern_accounts": sorted(ctx.modern_accounts.get(ch.line_item_code, ())),
    }


def _pick_page_by_title(ch: Chain, keys: Sequence[EraKey], ctx: _Context,
                        modern_pages: frozenset[tuple[str, str, str]]) -> tuple[str, str]:
    """For a collision-code chain left to review: the one page of its code
    whose modern title matches the chain's latest filed title, else blanks."""
    latest = normalize_title(keys[-1].filed_title)
    hits = set()
    for code, account, org in modern_pages:
        if code != ch.line_item_code:
            continue
        mi = ctx.idx.get((code, account, org if code in ctx.split else ""))
        if mi is not None and latest in mi.norm_titles:
            hits.add((account, org))
    return next(iter(hits)) if len(hits) == 1 else ("", "")


def _org_editions(
    era: Iterable[EraKey], split: frozenset[str],
) -> dict[str, dict[tuple[str, str], set[int]]]:
    """{code: {(account, era organization): editions holding keys}} for the
    org-split codes."""
    out: dict[str, dict[tuple[str, str], set[int]]] = {}
    for k in era:
        if k.line_item_code in split:
            out.setdefault(k.line_item_code, {}).setdefault(
                (k.account, k.organization), set()).add(k.edition)
    return out


def _org_clash(
    ch: Chain, ctx: _Context, collision_codes: frozenset[str],
    page: tuple[str, str],
    org_editions: Mapping[str, Mapping[tuple[str, str], set[int]]],
) -> tuple[str, dict[str, list[int]]] | None:
    """(page organization, {other era organization: [shared editions]}) when
    an org-split chain's code points at ANOTHER organization's page and that
    organization prints the code in an edition this chain also holds keys
    in. Deciding both same_program would sum two organizations' lines into
    one page grain (fct_program_decade_series keeps organization only for
    the PB2026 collision codes), i.e. put this chain's dollars on the other
    organization's page. None otherwise.

    The page: for a PB2026 collision code, `page` (the (account, org) the
    pre-fill picked; a blank org means no page was picked); for any other
    code, the code's one page, owned by the organizations that print it in
    PB2024-26 (a chain of one of them is the page's own and never clashes).
    Codes '10' and '15' are the live non-collision cases (PB2018 `10`:
    TJS's page, DPAA's line; PB2021-23 `15`: DISA's page, TJS's line)."""
    if not ch.organization:
        return None
    code, own = ch.line_item_code, _modern_org(ch.organization)
    held = {e for e, _key in ch.keys}
    rivals: dict[str, set[int]] = defaultdict(set)
    if code in collision_codes:
        page_account, page_org = page
        if not page_org or page_org == own:
            return None
        for (a, o), eds in org_editions.get(code, {}).items():
            if a == page_account and _modern_org(o) == page_org:
                rivals[o] |= eds
    else:
        owners = sorted({o for c, _a, o in ctx.line_idents if c == code})
        if not owners or own in owners:
            return None
        page_org = "/".join(owners)
        for (_a, o), eds in org_editions.get(code, {}).items():
            if o != ch.organization:
                rivals[o] |= eds
    shared = {o: sorted(eds & held) for o, eds in rivals.items() if eds & held}
    return (page_org, shared) if shared else None


def _prefill(ch: Chain, keys: Sequence[EraKey], ctx: _Context, info: dict,
             collision_codes: frozenset[str],
             modern_pages: frozenset[tuple[str, str, str]],
             org_editions: Mapping[str, Mapping[tuple[str, str], set[int]]],
             ) -> tuple[str, str, str, str]:
    """(proposed_decision, reason, program_account, program_org) — Claude's
    pre-fill for the owner; never a decision."""
    rule = _proposed_rule(ch.classes)
    pa = po = ""
    if ch.line_item_code in collision_codes:
        page = collision_page(ch, modern_pages)
        pa, po = page if page is not None else _pick_page_by_title(
            ch, keys, ctx, modern_pages)
    if ch.classes == frozenset({"H"}):
        return ("history_only",
                f"{rule}: era-only code whose titles drift — confirm one program"
                " (history_only) or split the range (exclude_reused_code)", "", "")
    clash = _org_clash(ch, ctx, collision_codes, (pa, po), org_editions)
    if clash is not None:
        # another organization's page: data only. A collision code pins the
        # chain's own identity so its grain stays apart from the page's.
        page_org, shared = clash
        printed = "; ".join(
            f"code also printed by {o} in {', '.join(f'PB{e}' for e in eds)}"
            for o, eds in sorted(shared.items()))
        if ch.line_item_code in collision_codes:
            page = f"{ch.line_item_code}-{page_org} (title match)"
            pa, po = ch.account, _modern_org(ch.organization)
        else:
            page, pa, po = ch.line_item_code, "", ""
        return ("history_only", f"{rule}: {printed}; page {page} is {page_org}'s",
                pa, po)
    if ch.classes == frozenset({"A1"}):
        # only a collision-code chain with no matching PB2026 page gets here:
        # pin it to its own PB2024-26 line identity, data only
        org = _modern_org(ch.organization)
        lines = sorted((a, o) for c, a, o in ctx.line_idents
                       if c == ch.line_item_code and a == ch.account
                       and (not ch.organization or o == org))
        pa, po = lines[0] if len(lines) == 1 else ("", "")
        return ("history_only",
                f"{rule}: collision code with no PB2026 page for"
                f" {ch.account}{'/' + ch.organization if ch.organization else ''}"
                " — history_only (data only), or name the page it joins", pa, po)
    if ch.classes & {"R2", "R3"}:
        return ("same_program",
                f"{rule}: account/organization move (modern accounts"
                f" {', '.join(info['modern_accounts']) or 'none'})", pa, po)
    if "R1" in ch.classes:
        if info["continuity_ok"]:
            return ("same_program",
                    f"{rule}: renamed, continuity {info['continuity']} holds"
                    f" (title Jaccard {info['title_jaccard'] or 'n/a'})", pa, po)
        return ("",
                f"{rule}: renamed and continuity {info['continuity']} fails —"
                " consider a range split (earlier range exclude_reused_code)", pa, po)
    return ("same_program",
            f"{rule}: renamed within A2 (title Jaccard {info['title_jaccard']},"
            f" continuity {info['continuity']})", pa, po)


def propose(
    *, duckdb_path: Path, raw_docs_dir: Path, out_dir: Path, seed_path: Path,
    decided_on: date,
) -> dict:
    """Classify, chain, apply the class rulings, search successors, write
    keys.csv / chains.csv / review.csv / counts.json under out_dir and the
    class-ruled rows of the seed. Owner batch rows already in the seed
    (ruling not a class ruling) are kept verbatim and their chains are
    neither class-ruled nor re-proposed. Returns the counts dict."""
    inputs = load_inputs(Path(duckdb_path))
    split = org_split_codes(inputs.era)
    if split != ORG_SPLIT_CODES:
        raise RuntimeError(
            f"era-map: org-split codes changed: lake {sorted(split)} !="
            f" ORG_SPLIT_CODES {sorted(ORG_SPLIT_CODES)} — the chain identity"
            " would move; review the change and update the constant and spec §4.3")
    ctx = _Context(inputs.era, inputs.modern)
    classes = {(k.edition, k.era_key): ctx.classify(k, inputs.collision_codes)
               for k in ctx.era}
    chains = build_chains(inputs.era, classes)
    keys_by_chain = group_keys(inputs.era)
    org_editions = _org_editions(inputs.era, split)

    existing = read_seed(Path(seed_path))
    owner_rows = [r for r in existing if r["ruling"] not in CLASS_RULINGS]
    owner_chains = {chain_id(r["line_item_code"], r["account"], r["organization"])
                    for r in owner_rows}
    review_path = Path(out_dir) / "review.csv"
    if review_path.is_file():
        pending = sorted({r["chain_id"] for r in read_csv(review_path)
                          if (r.get("decision") or "").strip()
                          and r["chain_id"] not in owner_chains})
        if pending:
            raise RuntimeError(
                f"era-map propose: {review_path} holds decisions for"
                f" {len(pending)} chain(s) that are not ratified yet"
                f" ({', '.join(pending[:5])}) — run `govbudget era-map ratify`"
                " first, or blank their decision column; nothing was written")
    open_chains = [c for c in chains if c.chain_id not in owner_chains]
    ruled, left = apply_class_rulings(
        open_chains, modern_pages=inputs.modern_pages,
        collision_codes=inputs.collision_codes, decided_on=decided_on)
    successors = search_successors(chains, raw_docs_dir=Path(raw_docs_dir),
                                   modern=inputs.modern)
    info = {c.chain_id: _chain_context(c, keys_by_chain[c.chain_id], ctx)
            for c in chains}

    prior = {r["decision_id"]: r for r in existing if r["ruling"] in CLASS_RULINGS}
    by_id = {c.chain_id: c for c in chains}
    for row in ruled:
        cid = chain_id(row["line_item_code"], row["account"], row["organization"])
        ch, ci = by_id[cid], info[cid]
        row["modern_title"] = ci["modern_title"]
        row["evidence"] = (f"title_jaccard={ci['title_jaccard'] or 'n/a'};"
                           f" continuity={ci['continuity']};"
                           f" actuals_k={_fmt_k(ch.actuals_k)}")
        if row["decision"] == "history_only" and cid in successors:
            for f in ("successor_code", "successor_account", "successor_evidence"):
                row[f] = successors[cid][f]
        old = prior.get(row["decision_id"])
        if old and all(old[f] == row[f] for f in
                       ("keys_sha256", "decision", "ruling", "program_account",
                        "program_org")):
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
        succ = successors.get(ch.chain_id, {})
        review.append({
            "chain_id": ch.chain_id,
            "first_edition": str(ch.first_edition),
            "last_edition": str(ch.last_edition),
            "titles_by_edition": _titles_seen(ch, ch.first_edition, ch.last_edition),
            "modern_title": ci["modern_title"],
            "accounts": (f"era={ch.account}{'/' + ch.organization if ch.organization else ''};"
                         f" modern={','.join(ci['modern_accounts']) or 'none'}"),
            "continuity": ci["continuity"],
            "actuals_k": _fmt_k(ch.actuals_k),
            "proposed_decision": decision,
            "reason": reason,
            "program_account": pa,
            "program_org": po,
            "successor_code": succ.get("successor_code", ""),
            "keys_sha256": ch.keys_sha256,
            "decision": "",
            "note": "",
        })
    review.sort(key=lambda r: (-Decimal(r["actuals_k"] or "0"), r["chain_id"]))

    out_dir = Path(out_dir)
    write_csv(out_dir / "review.csv", REVIEW_COLUMNS, review)
    chain_rows = []
    for ch in chains:
        ci, succ = info[ch.chain_id], successors.get(ch.chain_id, {})
        ruled_row = ruled_ids.get(ch.chain_id)
        chain_rows.append({
            "chain_id": ch.chain_id, "line_item_code": ch.line_item_code,
            "account": ch.account, "organization": ch.organization,
            "first_edition": str(ch.first_edition), "last_edition": str(ch.last_edition),
            "classes": _proposed_rule(ch.classes), "n_keys": str(ch.n_keys),
            "keys_sha256": ch.keys_sha256, "actuals_k": _fmt_k(ch.actuals_k),
            "titles_by_edition": _titles_seen(ch, ch.first_edition, ch.last_edition),
            "modern_title": ci["modern_title"], "title_jaccard": ci["title_jaccard"],
            "continuity": ci["continuity"],
            "ruling": ruled_row["ruling"] if ruled_row else (
                "owner-batch" if ch.chain_id in owner_chains else ""),
            "decision": ruled_row["decision"] if ruled_row else "",
            "left_ruling_reason": left_reason.get(ch.chain_id, ""),
            "successor_code": succ.get("successor_code", ""),
            "successor_account": succ.get("successor_account", ""),
            "successor_evidence": succ.get("successor_evidence", ""),
        })
    write_csv(out_dir / "chains.csv", CHAIN_COLUMNS, chain_rows)
    key_rows = []
    for ch in chains:
        ci = info[ch.chain_id]
        for k in keys_by_chain[ch.chain_id]:
            jac = ctx.best_jaccard(k)
            key_rows.append({
                "edition": str(k.edition), "era_key": k.era_key,
                "account": k.account, "organization": k.organization,
                "budget_activity": k.budget_activity or "",
                "line_number": k.era_key.rsplit("-L", 1)[1],
                "line_item_code": k.line_item_code, "filed_title": k.filed_title or "",
                "chain_id": ch.chain_id, "class": classes[(k.edition, k.era_key)],
                "title_jaccard": "" if jac is None else f"{jac:.2f}",
                "continuity": ci["continuity"],
                "actuals_k": _fmt_k(k.actuals_k), "enacted_k": _fmt_k(k.enacted_k),
                "source_document_sha256": k.source_document_sha256,
                "source_rows": ",".join(str(r) for r in sorted(
                    {_cell_sort_key(c)[0] for c in k.source_cells})),
                "source_cells": ",".join(k.source_cells),
            })
    key_rows.sort(key=lambda r: (int(r["edition"]), r["era_key"]))
    write_csv(out_dir / "keys.csv", KEY_COLUMNS, key_rows)

    groups: dict[str, int] = defaultdict(int)
    for ch in chains:
        groups[_chain_group(ch)] += 1
    key_classes = {c: 0 for c in CLASS_ORDER}
    key_dollars = {c: Decimal(0) for c in CLASS_ORDER}
    for k in inputs.era:
        cls = classes[(k.edition, k.era_key)]
        key_classes[cls] += 1
        key_dollars[cls] += k.actuals_k or Decimal(0)
    rulings: dict[str, int] = {r: 0 for r in CLASS_RULINGS}
    for r in ruled:
        rulings[r["ruling"]] += 1
    by_edition: dict[str, int] = defaultdict(int)
    for k in inputs.era:
        by_edition[str(k.edition)] += 1
    counts = {
        "era_keys": len(inputs.era),
        "era_keys_by_edition": dict(sorted(by_edition.items())),
        "chains": len(chains),
        "chain_groups": dict(sorted(groups.items())),
        "key_classes": key_classes,
        "key_class_actuals_k": {c: _fmt_k(v) for c, v in key_dollars.items()},
        "era_actuals_k": _fmt_k(sum(key_dollars.values(), Decimal(0))),
        "rulings": rulings,
        "ruled_actuals_k": {
            r: _fmt_k(sum((by_id[chain_id(x["line_item_code"], x["account"],
                                          x["organization"])].actuals_k
                           for x in ruled if x["ruling"] == r), Decimal(0)))
            for r in CLASS_RULINGS},
        "left_ruling": len(left_reason),
        "review_rows": len(review),
        "owner_batch_chains": len(owner_chains),
        "org_split_codes": sorted(split),
        "collision_codes": sorted(inputs.collision_codes),
        "successors": {cid: s["successor_code"] for cid, s in sorted(successors.items())},
    }
    (out_dir / "counts.json").write_text(json.dumps(counts, indent=1, sort_keys=True) + "\n")
    return counts
```

- [ ] **Step 5: Run the tests and watch them pass**

Run: `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && GOVBUDGET_TEST_PG_DSN=postgresql://127.0.0.1:55432/postgres uv run --project . pytest tests/jbooks/test_era_map_propose.py tests/jbooks/test_era_map.py -q`

Expected: `67 passed`.

- [ ] **Step 6: Commit the code**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/src/govbudget/jbooks/era_map.py GovBudget/tests/jbooks/era_map_fixtures.py GovBudget/tests/jbooks/test_era_map_propose.py && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "feat(era-map): propose — lake read, research outputs, class-ruled seed rows, stated successors (spec §4.6, §5.2-5.4)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: Confirm the real-data precondition (Tasks 7–9 done)**

Run:
This step opens the live lake (README SAM window, read-only included): if a block prints `WAIT: SAM window …`, nothing ran — wait until :23 and re-run that block.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
uv run --project . python -c "import duckdb; p='/Users/andeslee/Documents/Cursor-Projects/GovBudget/data/parquet/jbooks/budget_lines.parquet'; c=duckdb.connect(); print([r[0] for r in c.execute(f\"describe select * from read_parquet('{p}')\").fetchall()][-1]); print(c.execute(f\"select count(*), count(*) filter (where coalesce(line_item_code,'') = '') from read_parquet('{p}') where exhibit='P-1' and fiscal_year between '2017' and '2023' and pe_bli similar to '[0-9]{{4}}[A-Z]-[A-Z]+-L.*'\").fetchone())"
```
Expected:
```
line_item_code
(57722, 0)
```
If the first line is not `line_item_code` or the second number is not 0, stop: Task 8 (S1 reload +
`jbooks export-facts`) has not finished. (Before Task 8 this prints `source_cells` and then a DuckDB
`Binder Error` naming `line_item_code`.) `propose` raises the same way
(`RuntimeError: era-map: ... has no line_item_code column ... (plan Tasks 7-8)`).

- [ ] **Step 8: Run propose against the live lake**

The lake and DuckDB are only read (DuckDB `read_only=True`); the run writes only
`data/research/era_map/*` and `dbt/seeds/p1_era_code_decisions.csv` in this worktree. It takes
about 50 s (most of it the PB2024–26 XML scan, 1.75 GB). If DuckDB reports a conflicting lock,
another process is building the warehouse: wait and re-run.

Run:
This step opens the live lake (README SAM window, read-only included): if a block prints `WAIT: SAM window …`, nothing ran — wait until :23 and re-run that block.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
GOVBUDGET_DATA=/Users/andeslee/Documents/Cursor-Projects/GovBudget/data uv run --project . python - <<'EOF'
import json
from govbudget import config
from govbudget.jbooks import era_map
c = era_map.propose(
    duckdb_path=config.DUCKDB_PATH, raw_docs_dir=config.RAW_DOCS_DIR,
    out_dir=config.RESEARCH_DIR / "era_map",
    seed_path=config.ROOT / "dbt" / "seeds" / "p1_era_code_decisions.csv",
    decided_on=era_map.CLASS_RULINGS_DECIDED_ON)
print(json.dumps({k: c[k] for k in ("era_keys", "chains", "chain_groups", "key_classes",
      "rulings", "left_ruling", "review_rows", "era_actuals_k", "ruled_actuals_k",
      "successors")}, sort_keys=True))
EOF
```
Expected (exactly):
```
{"chain_groups": {"a1_only": 811, "a2_without_r": 18, "cr": 45, "h_drift_free": 271, "h_drifting": 8, "r_containing": 98, "unsafe": 2}, "chains": 1253, "era_actuals_k": "783756819", "era_keys": 6927, "key_classes": {"A1": 5477, "A2": 64, "CR": 45, "H": 978, "R1": 152, "R2": 133, "R3": 64, "UNSAFE": 14}, "left_ruling": 1, "review_rows": 125, "ruled_actuals_k": {"R-DEC-ERA-EXCLUDE": "5832017", "R-DEC-ERA-HISTORY": "46875952", "R-DEC-ERA-SAME": "651579549"}, "rulings": {"R-DEC-ERA-EXCLUDE": 47, "R-DEC-ERA-HISTORY": 271, "R-DEC-ERA-SAME": 810}, "successors": {"5600D15603|2035A|": "5731D15610"}}
```
and `data/research/era_map/counts.json` equal to:
```json
{
 "chain_groups": {
  "a1_only": 811,
  "a2_without_r": 18,
  "cr": 45,
  "h_drift_free": 271,
  "h_drifting": 8,
  "r_containing": 98,
  "unsafe": 2
 },
 "chains": 1253,
 "collision_codes": [
  "0145",
  "1350",
  "20",
  "2101",
  "2210",
  "2292",
  "30",
  "3010",
  "3050",
  "3215",
  "3302",
  "4217",
  "500"
 ],
 "era_actuals_k": "783756819",
 "era_keys": 6927,
 "era_keys_by_edition": {
  "2017": 969,
  "2018": 1029,
  "2019": 989,
  "2020": 975,
  "2021": 1005,
  "2022": 993,
  "2023": 967
 },
 "key_class_actuals_k": {
  "A1": "681693028",
  "A2": "10697778",
  "CR": "0",
  "H": "48272642",
  "R1": "11952806",
  "R2": "9172777",
  "R3": "16135771",
  "UNSAFE": "5832017"
 },
 "key_classes": {
  "A1": 5477,
  "A2": 64,
  "CR": 45,
  "H": 978,
  "R1": 152,
  "R2": 133,
  "R3": 64,
  "UNSAFE": 14
 },
 "left_ruling": 1,
 "org_split_codes": [
  "10",
  "15",
  "20",
  "30",
  "500"
 ],
 "owner_batch_chains": 0,
 "review_rows": 125,
 "ruled_actuals_k": {
  "R-DEC-ERA-EXCLUDE": "5832017",
  "R-DEC-ERA-HISTORY": "46875952",
  "R-DEC-ERA-SAME": "651579549"
 },
 "rulings": {
  "R-DEC-ERA-EXCLUDE": 47,
  "R-DEC-ERA-HISTORY": 271,
  "R-DEC-ERA-SAME": 810
 },
 "successors": {
  "5600D15603|2035A|": "5731D15610"
 }
}
```

Tolerance: none. These numbers come from the same lake with column I filled from the same
workbooks, and S1's export diff is empty, so every count and dollar figure must match exactly.
Reference points: 6,927 keys and 1,253 chains are the spec's figures; the research pass's
813 / 19 / 95 / 45 / 2 / 271 / 8 differ only by the 3 org-split chains in CONTRACT ISSUE 7.
On any mismatch: stop, do not commit, and never edit code or numbers to make them match.
Investigate in this order: (a) Step 7's precondition; (b) `counts.json` `collision_codes` must be the 13 codes
`0145 1350 20 2101 2210 2292 30 3010 3050 3215 3302 4217 500` and `org_split_codes` must be
`10 15 20 30 500` (a different set means `dim_programs` or the lake changed); (c) compare
`keys.csv` classes against the expected `key_classes` to find which class moved, then read those
keys' `line_item_code`/`filed_title` against the workbook (V1, Task 8); (d) if `era_keys` ≠ 6,927,
the S1/S1b reload changed the key set, which is a Task 8/9 defect. Report the findings to the
controller.

For reference, the planning run's files had these sha256s (same inputs ⇒ same bytes):
```
3ec9807eb30c5df965d680019e5237b505d28886d0b10d35e73bba58f4f0d2e4  dbt/seeds/p1_era_code_decisions.csv
1c98f400196ca42f2e0c6f3803c07605da9bbaef030bb0dc6d8cfefb7e345548  data/research/era_map/chains.csv
ec7bdac6eb27ea1ed065a9d852ac2fb99bd1b07fba516e45789afd9741d1f08e  data/research/era_map/counts.json
282044cf2f109b9d570debac9cae23971821cb9ac3e9f2b29448818c23c20704  data/research/era_map/keys.csv
39db7799cdffa69465a91ccf8679f98bcfa36ffd30a46acc782e23b43c9e8890  data/research/era_map/review.csv
```
Run `cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh && shasum -a 256 dbt/seeds/p1_era_code_decisions.csv data/research/era_map/*`. A sha that differs while
Step 8's counts match exactly is worth a look (most likely a re-exported `documents.parquet`
sha or a changed PB2026 XML file), but it does not block the task.

- [ ] **Step 9: Check the JLTV successor and the F-15 era-only chains**

Run:
```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - <<'EOF'
import csv
rows = {r["decision_id"]: r for r in csv.DictReader(open("dbt/seeds/p1_era_code_decisions.csv"))}
j = rows["5600D15603|2035A||2017-2022"]
print(j["decision"], j["successor_code"], j["successor_account"])
print([p for p in j["successor_evidence"].split("; ") if not p.startswith(("xml_sha256", "quote"))])
for d in ("F015E0|3010F||2020-2022", "F0150P|3010F||2017-2020"):
    print(d, rows[d]["decision"], rows[d]["ruling"], repr(rows[d]["successor_code"]))
print(len(rows), sum(1 for r in rows.values() if r["successor_code"]))
EOF
```
Expected:
```
history_only 5731D15610 2035A
['xml=fy2026/a/Other Procurement - BA1 - Tactical & Support Vehicles__xml/U_PROCUREMENT_JB_2506261600ZZZZ_ARMY_PB_2026.xml:3440', 'pdf=fy2026/a/Other Procurement - BA1 - Tactical & Support Vehicles.pdf', 'pdf_sha256=184228d828aab1d64819d05f7cd66f24de5e7e28fbeccacf89db50fa15078195', 'pdf_page=100', 'form=short']
F015E0|3010F||2020-2022 history_only R-DEC-ERA-HISTORY ''
F0150P|3010F||2017-2020 history_only R-DEC-ERA-HISTORY ''
1128 1
```
(This matches spec §5.4: BA1 book PDF p.100, sha `184228d8…`; F015E0 has no successor.)

Then check the pre-fills for chains that print a code beside another organization's page
(CONTRACT ISSUE 9c):
```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
uv run --project . python - <<'EOF'
import csv
rows = {r["chain_id"]: r for r in csv.DictReader(open("data/research/era_map/review.csv"))}
for cid in ("10|0300D|DPAA", "15|0300D|TJS", "500|0300D|DCMA", "20|0300D|DSS"):
    r = rows[cid]
    print(cid, r["proposed_decision"], repr(r["program_account"]), repr(r["program_org"]))
    print("   ", r["reason"])
print(sum(r["proposed_decision"] == "history_only" for r in rows.values()),
      sum(r["proposed_decision"] == "same_program" for r in rows.values()),
      sum(r["proposed_decision"] == "" for r in rows.values()))
EOF
```
Expected:
```
10|0300D|DPAA history_only '' ''
    R2: code also printed by TJS in PB2018; page 10 is TJS's
15|0300D|TJS history_only '' ''
    R2: code also printed by DISA in PB2021, PB2022, PB2023; page 15 is DISA's
500|0300D|DCMA history_only '0300D' 'DCMA'
    R2: code also printed by DLA in PB2017, PB2018, PB2019, PB2020, PB2021, PB2022; page 500-DLA (title match) is DLA's
20|0300D|DSS same_program '0300D' 'DCSA'
    R2: account/organization move (modern accounts 0300D)
12 108 5
```
(DPAA's PB2018 `10` line, TJS's PB2021–23 `15` line and DCMA's PB2017–22 `500` line sit beside
another organization's class-ruled same_program keys, so `same_program` would sum two
organizations into one page. DSS → DCSA shares no edition with DCSA's chain: a rename.)

- [ ] **Step 10: Check that propose is deterministic and the worktree change is as expected**

Run the Step 8 command again, then:
This step opens the live lake (README SAM window, read-only included): if a block prints `WAIT: SAM window …`, nothing ran — wait until :23 and re-run that block.

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget && source scripts/era/env.sh || exit 1
MIN=$(date +%M); if [ "$MIN" -ge 12 ] && [ "$MIN" -le 22 ]; then echo "WAIT: SAM window (minute $MIN)"; exit 0; fi
shasum -a 256 dbt/seeds/p1_era_code_decisions.csv data/research/era_map/* && git status --short dbt/seeds data/research/era_map
```
Expected: the same five sha256s as after the first run, and
```
?? data/research/era_map/
?? dbt/seeds/p1_era_code_decisions.csv
```

- [ ] **Step 11: Commit the research outputs and the class-ruled seed**

```bash
cd /Users/andeslee/Documents/Cursor-Projects/GovBudget/.claude/worktrees/families/GovBudget/.. && git add GovBudget/data/research/era_map/keys.csv GovBudget/data/research/era_map/chains.csv GovBudget/data/research/era_map/review.csv GovBudget/data/research/era_map/counts.json GovBudget/dbt/seeds/p1_era_code_decisions.csv && git commit --author="Andes Lee <andes.lee444@gmail.com>" -m "data(era-map): propose on the live lake — 6,927 era keys in 1,253 chains; class rulings decide 1,128 (R-DEC-ERA-SAME 810, -EXCLUDE 47, -HISTORY 271); 125 chains for owner review; JLTV successor 5731D15610" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
