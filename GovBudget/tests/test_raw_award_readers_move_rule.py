"""R-DEC-133c (fix-round-3 ruling, 2026-09-26): "The four remaining raw-archive
summers (crosswalk.py, load_announcement_links.py, derive_ap_links.py,
precision_study.py) read through src/govbudget/award_moves.py." — ROADMAP #133
end to end.

Each of the four sums federal_action_obligation over the RAW contracts archive
(data/parquet/contracts/fy=*/*.parquet). A USAspending source correction that
MOVES a transaction into another fiscal year's archive leaves the stale copy in
the old year's file; dbt staging drops that retired copy, so a reader that sums
the raw files itself counts the moved transaction twice. These tests build that
lake and prove each caller counts the moved key once — the corrected copy, as
the warehouse does — and that an ambiguous duplicate stops the caller before
it computes anything (govbudget.award_moves raises; nothing is half-read).

THE LAKE (one PIID, N0002425C9001, funded from 097-0400, DARPA, AP code 123):
  fy=2025  MOVED001  action 2025-03-01  obligation 100  modified 2025-04-01
  fy=2026  MOVED001  action 2025-10-02  obligation 120  modified 2026-08-02  (kept)
  fy=2026  STAYS001  action 2025-10-03  obligation   5  modified 2026-08-02
The warehouse counts 120 + 5 = 125; the raw files sum to 225.

The crosswalk tests live in tests/jbooks/test_crosswalk.py (they need its
Postgres seeds); the other three are here.
"""
from pathlib import Path

import duckdb
import pytest

from govbudget.award_moves import AmbiguousAwardDuplicateError

#: The columns the four readers select, plus the two the move rule needs
#: (the hive partition `fy` comes from the directory).
COLS = (
    "contract_transaction_unique_key, award_id_piid, federal_action_obligation,"
    " federal_accounts_funding_this_award, recipient_name, recipient_uei,"
    " dod_acquisition_program_code, dod_acquisition_program_description,"
    " transaction_description, prime_award_base_transaction_description,"
    " awarding_sub_agency_name, awarding_office_name, naics_description,"
    " product_or_service_code_description, period_of_performance_start_date,"
    " period_of_performance_current_end_date, action_date, last_modified_date"
)
PIID = "N0002425C9001"
DARPA = "Defense Advanced Research Projects Agency"


def contract_row(key, obligation, action_date, modified, *, description="WORK"):
    """One raw contracts row in COLS order."""
    return (key, PIID, obligation, "097-0400", "MOVER INC", "UEI9", "123",
            "MOVER PROGRAM", description, "BASE", DARPA, "DARPA CMO",
            "R&D", "R&D SERVICES", "2024-10-01", "2027-09-30", action_date,
            modified)


def write_contracts(root: Path, fy: int, rows, part="part") -> None:
    d = root / "contracts" / f"fy={fy}"
    d.mkdir(parents=True, exist_ok=True)
    values = ", ".join(
        "(" + ", ".join("'" + str(v).replace("'", "''") + "'" for v in r) + ")"
        for r in rows)
    duckdb.sql(f"copy (select * from (values {values}) t({COLS}))"
               f" to '{d}/{part}.parquet' (format parquet)")


def moved_lake(root: Path) -> str:
    """The lake in the module docstring; returns the readers' glob."""
    write_contracts(root, 2025, [
        contract_row("MOVED001", "100", "2025-03-01", "2025-04-01 00:00:00+00"),
    ])
    write_contracts(root, 2026, [
        contract_row("MOVED001", "120", "2025-10-02", "2026-08-02 00:00:00+00"),
        contract_row("STAYS001", "5", "2025-10-03", "2026-08-02 00:00:00+00"),
    ])
    return str(root / "contracts" / "fy=*" / "*.parquet")


def ambiguous_lake(root: Path) -> str:
    """Two copies of one key in ONE fiscal year: not a move, so the rule
    refuses it (dbt fails unique_fct_award_transactions_transaction_key)."""
    write_contracts(root, 2026, [
        contract_row("SAMEFY01", "7", "2025-10-02", "2026-08-02 00:00:00+00"),
    ])
    write_contracts(root, 2026, [
        contract_row("SAMEFY01", "8", "2025-10-05", "2026-08-03 00:00:00+00"),
    ], part="part-2")
    return str(root / "contracts" / "fy=*" / "*.parquet")


def raw_sum(glob: str) -> float:
    """What a reader that ignores the rule sums — the double count."""
    return duckdb.sql(
        f"select sum(try_cast(federal_action_obligation as double))"
        f" from read_parquet('{glob}', union_by_name=true)"
        f" where award_id_piid = '{PIID}'").fetchone()[0]


# ── scripts/load_announcement_links.py ─────────────────────────────────────

def test_the_announcement_loader_counts_a_moved_key_once(tmp_path):
    from load_announcement_links import lake_evidence

    glob = moved_lake(tmp_path)
    assert raw_sum(glob) == 225.0                    # the defect's size
    ev, moves = lake_evidence([PIID, "NOT_IN_LAKE"], contracts_glob=glob)
    rname, ruei, ob, accts = ev[PIID]
    assert ob == 125.0                               # the warehouse's figure
    assert (rname, ruei, accts) == ("MOVER INC", "UEI9", "097-0400")
    assert "NOT_IN_LAKE" not in ev
    assert [(r.transaction_key, r.retired_fiscal_year, r.kept_fiscal_year)
            for r in moves.retired] == [("MOVED001", 2025, 2026)]
    assert moves.summary().startswith(
        "fiscal-year move rule (ROADMAP #133): retired 1 contract")


def test_the_announcement_loader_refuses_an_ambiguous_duplicate(tmp_path):
    from load_announcement_links import lake_evidence

    with pytest.raises(AmbiguousAwardDuplicateError, match="SAMEFY01"):
        lake_evidence([PIID], contracts_glob=ambiguous_lake(tmp_path))


# ── scripts/derive_ap_links.py ─────────────────────────────────────────────

def test_the_ap_deriver_counts_a_moved_key_once(tmp_path):
    from derive_ap_links import ap_awards

    glob = moved_lake(tmp_path)
    awards, moves = ap_awards(["123", "999"], contracts_glob=glob)
    assert awards == [("123", PIID, "MOVER INC", "UEI9", "097-0400", 125.0)]
    assert moves.count("contract") == 1


def test_the_ap_deriver_refuses_an_ambiguous_duplicate(tmp_path):
    from derive_ap_links import ap_awards

    with pytest.raises(AmbiguousAwardDuplicateError, match="SAMEFY01"):
        ap_awards(["123"], contracts_glob=ambiguous_lake(tmp_path))


# ── scripts/precision_study.py ─────────────────────────────────────────────

def _packet():
    return [{"method": "announcement+lexicon", "rubric": "attribution",
             "question": "q", "piid": PIID, "pe_bli": "MOVE0601E",
             "recipient": "MOVER INC", "rationale": "r"}]


def test_the_precision_packets_count_a_moved_key_once(pg_dsn, tmp_path):
    from precision_study import enrich_packets

    glob = moved_lake(tmp_path)
    out = enrich_packets(_packet(), pg_dsn, contracts_glob=glob,
                         lexicon_path=tmp_path / "no-lexicon.jsonl")
    award = out[0]["award"]
    assert award["obligation"] == 125.0
    # the retired copy's fiscal year is not evidence about the award any more
    assert award["fiscal_years"] == [2026]
    assert "lake" not in award


def test_the_precision_packets_refuse_an_ambiguous_duplicate(pg_dsn, tmp_path):
    """Never folded into the packet's 'no contracts parquet readable' note:
    that note would be false (the parquet is readable) and the adjudicator
    would judge the link with its award evidence silently missing."""
    from precision_study import enrich_packets

    with pytest.raises(AmbiguousAwardDuplicateError, match="SAMEFY01"):
        enrich_packets(_packet(), pg_dsn, contracts_glob=ambiguous_lake(tmp_path),
                       lexicon_path=tmp_path / "no-lexicon.jsonl")
