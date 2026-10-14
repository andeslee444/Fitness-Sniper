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
