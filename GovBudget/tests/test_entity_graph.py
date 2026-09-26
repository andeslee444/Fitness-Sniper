from pathlib import Path

import duckdb
import pytest

from govbudget.entity_graph import (
    DEFAULT_PARENT_EXCLUSIONS,
    ParentExclusion,
    ParentExclusionError,
    build_entity_xwalk,
    load_parent_exclusions,
)

AWARD_COLS = (
    "recipient_uei, recipient_name, recipient_parent_uei, recipient_parent_name,"
    " federal_action_obligation"
)


def make_lake(tmp_path: Path) -> Path:
    out = tmp_path / "contracts" / "fy=2024"
    out.mkdir(parents=True)
    duckdb.sql(
        f"""
        copy (select * from (values
          ('U1','BOEING DEFENSE SPACE','P1','THE BOEING COMPANY','100'),
          ('U2','BOEING AEROSPACE OPS','P2','BOEING COMPANY, THE (INC)','50'),
          ('U3','HII MISSION TECH','P3','HUNTINGTON INGALLS INDUSTRIES, INC','75'),
          ('U4','SOLO RESEARCH LLC',NULL,NULL,'10')
        ) t({AWARD_COLS})) to '{out}/part.parquet' (format parquet)
        """
    )
    return tmp_path


def test_confidence_tiers(tmp_path):
    """Cross-parent-UEI name merges must carry 'medium' confidence; single-parent 'high'."""
    lake = make_lake(tmp_path)
    out = build_entity_xwalk(
        award_glob=str(lake / "contracts" / "*" / "*.parquet"),
        out_path=tmp_path / "entity_xwalk_conf.parquet",
        parent_exclusions=(),
    )
    rows = duckdb.sql(f"select * from read_parquet('{out}')").fetchall()
    cols = [d[0] for d in duckdb.sql(f"describe select * from read_parquet('{out}')").fetchall()]
    by_uei = {r[cols.index("recipient_uei")]: r for r in rows}
    conf = cols.index("confidence")
    # U1 (parent P1) and U2 (parent P2) share family 'BOEING' via name merge
    # -> cross-parent merge -> both must be 'medium'
    assert by_uei["U1"][conf] == "medium", f"Expected medium, got {by_uei['U1'][conf]!r}"
    assert by_uei["U2"][conf] == "medium", f"Expected medium, got {by_uei['U2'][conf]!r}"
    # U3 has a single parent UEI (P3) -> single-parent family -> stays 'high'
    assert by_uei["U3"][conf] == "high", f"Expected high, got {by_uei['U3'][conf]!r}"
    # U4 has no parent (recipient_name method) -> 'medium' (unchanged)
    assert by_uei["U4"][conf] == "medium"


def test_build_entity_xwalk_merges_families(tmp_path):
    lake = make_lake(tmp_path)
    out = build_entity_xwalk(
        award_glob=str(lake / "contracts" / "*" / "*.parquet"),
        out_path=tmp_path / "entity_xwalk.parquet",
        parent_exclusions=(),
    )
    rows = duckdb.sql(f"select * from read_parquet('{out}')").fetchall()
    cols = [d[0] for d in duckdb.sql(f"describe select * from read_parquet('{out}')").fetchall()]
    by_uei = {r[cols.index("recipient_uei")]: r for r in rows}
    fam = cols.index("family_key")
    # P1 and P2 normalize to the same family name -> same canonical key
    assert by_uei["U1"][fam] == by_uei["U2"][fam] == "BOEING"
    assert by_uei["U3"][fam] == "HUNTINGTON INGALLS INDUSTRIES"
    assert by_uei["U4"][fam] == "SOLO RESEARCH"
    method = cols.index("method")
    assert by_uei["U1"][method] == "parent_name"
    assert by_uei["U4"][method] == "recipient_name"


def _read(out) -> tuple[dict, list[str]]:
    rows = duckdb.sql(f"select * from read_parquet('{out}')").fetchall()
    cols = [d[0] for d in duckdb.sql(f"describe select * from read_parquet('{out}')").fetchall()]
    return {r[cols.index("recipient_uei")]: r for r in rows}, cols


def make_chimera_lake(tmp_path: Path) -> Path:
    """A UEI whose parent changed over time — the shape that shatters families.

    U9 filed 2 transactions under parent ('P9', 'LOCKHEED MARTIN CORP') worth
    $1,000 and 1 transaction under a different, tiny parent ('P1', 'SIKORSKY
    SUPPORT SERVICES INC') worth $10.  Aggregating the two parent columns with
    INDEPENDENT max() takes the uei from one pair and the name from the other:
    ('P9', 'SIKORSKY SUPPORT SERVICES INC') — a pair that appears on no
    transaction anywhere.  That is the real FY2017-2026 defect: it moved
    $210B of Lockheed Martin into a family named after a support subsidiary.
    """
    out = tmp_path / "contracts" / "fy=2024"
    out.mkdir(parents=True)
    duckdb.sql(
        f"""
        copy (select * from (values
          ('U9','LOCKHEED MARTIN CORPORATION','P9','LOCKHEED MARTIN CORP','600'),
          ('U9','LOCKHEED MARTIN CORPORATION','P9','LOCKHEED MARTIN CORP','400'),
          ('U9','LOCKHEED MARTIN CORP','P1','SIKORSKY SUPPORT SERVICES INC','10')
        ) t({AWARD_COLS})) to '{out}/part.parquet' (format parquet)
        """
    )
    return tmp_path


def test_parent_pair_is_never_a_chimera(tmp_path):
    """The emitted (parent_uei, parent_name) pair must co-occur on a real transaction."""
    lake = make_chimera_lake(tmp_path)
    out = build_entity_xwalk(
        award_glob=str(lake / "contracts" / "*" / "*.parquet"),
        out_path=tmp_path / "xw_chimera.parquet",
        parent_exclusions=(),
    )
    by_uei, cols = _read(out)
    row = by_uei["U9"]
    pair = (row[cols.index("parent_uei")], row[cols.index("parent_name")])
    assert pair in {("P9", "LOCKHEED MARTIN CORP"), ("P1", "SIKORSKY SUPPORT SERVICES INC")}, (
        f"{pair} never co-occurs on any transaction — independent max() over two "
        f"correlated columns invented it"
    )
    # ...and of the two real pairs it must be the one carrying the dollars.
    assert pair == ("P9", "LOCKHEED MARTIN CORP")
    assert row[cols.index("family_key")] == "LOCKHEED MARTIN"


def test_recipient_name_is_the_dominant_one_not_the_last_alphabetically(tmp_path):
    """Display names follow the money, not the alphabet."""
    lake = make_chimera_lake(tmp_path)
    out = build_entity_xwalk(
        award_glob=str(lake / "contracts" / "*" / "*.parquet"),
        out_path=tmp_path / "xw_name.parquet",
        parent_exclusions=(),
    )
    by_uei, cols = _read(out)
    # 'LOCKHEED MARTIN CORPORATION' ($1,000) vs 'LOCKHEED MARTIN CORP' ($10);
    # max() would take neither on merit — it takes 'LOCKHEED MARTIN CORPORATION'
    # here only by luck of the alphabet.  Assert the dollar-weighted choice.
    assert by_uei["U9"][cols.index("recipient_name")] == "LOCKHEED MARTIN CORPORATION"


def test_award_globs_union_contracts_and_assistance(tmp_path):
    """The crosswalk covers the same award universe fct_award_transactions does."""
    lake = make_lake(tmp_path)
    assist = lake / "assistance" / "fy=2024"
    assist.mkdir(parents=True)
    duckdb.sql(
        f"""
        copy (select * from (values
          ('U1','BOEING DEFENSE SPACE','P1','THE BOEING COMPANY','7'),
          ('U8','GRANTEE UNIVERSITY',NULL,NULL,'12')
        ) t({AWARD_COLS})) to '{assist}/part.parquet' (format parquet)
        """
    )
    out = build_entity_xwalk(
        award_glob=[
            str(lake / "contracts" / "*" / "*.parquet"),
            str(lake / "assistance" / "*" / "*.parquet"),
        ],
        out_path=tmp_path / "xw_union.parquet",
        parent_exclusions=(),
    )
    by_uei, cols = _read(out)
    tot = cols.index("total_obligation")
    assert by_uei["U1"][tot] == 107.0, "assistance dollars must land on the same UEI"
    assert "U8" in by_uei, "assistance-only recipients must get a family"
    assert by_uei["U8"][cols.index("family_key")] == "GRANTEE UNIVERSITY"


# ── ROADMAP #135: a curated parent-pair exclusion ───────────────────────────
#
# The shape of the real defect (measured read-only 2026-09-25): SPARTON
# DELEON SPRINGS, LLC (UEI H7KFX5RH75K3) filed five parent registrations
# over the decade, and the dollar-dominant one — EGAVSJTA2D81, registered as
# ROCKWELL COLLINS AUSTRALIA PTY LIMITED, $207.3M in FY2024-FY2025 — put it in
# that family key, which the curated RTX family merges on name-inferred
# evidence. The ruling (owner-delegated, 2026-09-25): that merge's evidence
# covers RC Australia, not Sparton, so the pair is excluded and Sparton's
# family follows its OTHER registry filings.


def make_split_lake(tmp_path: Path) -> Path:
    out = tmp_path / "contracts" / "fy=2025"
    out.mkdir(parents=True)
    duckdb.sql(
        f"""
        copy (select * from (values
          ('US1','SPARTON DELEON SPRINGS, LLC','PRCA','ROCKWELL COLLINS AUSTRALIA PTY LIMITED','300'),
          ('US1','SPARTON DELEON SPRINGS, LLC','PELB','ELBIT SYSTEMS LTD','200'),
          ('US1','SPARTON DELEON SPRINGS, LLC','PRTX','RTX CORP','150'),
          ('UI1','INTERTRADE LIMITED','PRCA','ROCKWELL COLLINS AUSTRALIA PTY LIMITED','50')
        ) t({AWARD_COLS})) to '{out}/part.parquet' (format parquet)
        """
    )
    return tmp_path


def _excl(**kw) -> ParentExclusion:
    base = dict(
        recipient_uei="US1",
        recipient_name="SPARTON DELEON SPRINGS, LLC",
        excluded_parent_uei="PRCA",
        excluded_parent_name="ROCKWELL COLLINS AUSTRALIA PTY LIMITED",
        decided="2026-09-25",
        roadmap="#135",
        note="test",
    )
    base.update(kw)
    return ParentExclusion(**base)


def _build(tmp_path, exclusions, name="xw.parquet"):
    lake = make_split_lake(tmp_path)
    return build_entity_xwalk(
        award_glob=str(lake / "contracts" / "*" / "*.parquet"),
        out_path=tmp_path / name,
        parent_exclusions=exclusions,
    )


def test_without_an_exclusion_the_dollar_dominant_pair_wins(tmp_path):
    """The control: the unmodified rule puts both recipients in the RC key."""
    by_uei, cols = _read(_build(tmp_path, ()))
    fam = cols.index("family_key")
    assert by_uei["US1"][fam] == "ROCKWELL COLLINS AUSTRALIA"
    assert by_uei["UI1"][fam] == "ROCKWELL COLLINS AUSTRALIA"


def test_an_excluded_pair_hands_the_recipient_to_its_next_registry_parent(tmp_path):
    by_uei, cols = _read(_build(tmp_path, (_excl(),)))
    fam, puei, pname = (cols.index(c) for c in ("family_key", "parent_uei", "parent_name"))
    # Sparton leaves the key; its next registry filing by dollars decides.
    assert by_uei["US1"][fam] == "ELBIT SYSTEMS"
    assert (by_uei["US1"][puei], by_uei["US1"][pname]) == ("PELB", "ELBIT SYSTEMS LTD")
    assert by_uei["US1"][cols.index("method")] == "parent_name"
    # The key keeps its own members.
    assert by_uei["UI1"][fam] == "ROCKWELL COLLINS AUSTRALIA"
    # A UEI's dollars stay whole: the exclusion moves the FAMILY, never money.
    assert by_uei["US1"][cols.index("total_obligation")] == 650.0


def test_the_build_log_names_what_the_exclusion_moved(tmp_path, capsys):
    _build(tmp_path, (_excl(),))
    out = capsys.readouterr().out
    assert "US1" in out and "PRCA" in out
    assert "ELBIT SYSTEMS" in out          # where it went
    assert "RTX CORP" in out               # the runner-up, so a near tie is visible


def test_an_exclusion_that_matches_nothing_fails_loudly(tmp_path):
    """A typo or a stale row would leave the defect in place without a word."""
    with pytest.raises(ParentExclusionError, match="no transaction"):
        _build(tmp_path, (_excl(excluded_parent_uei="PNOPE"),))
    with pytest.raises(ParentExclusionError, match="no transaction"):
        _build(tmp_path / "second", (_excl(recipient_uei="UNOPE"),))


def test_an_exclusion_whose_registration_changed_name_fails_loudly(tmp_path):
    """The curation reviewed ONE registration; a renamed one needs a new look."""
    with pytest.raises(ParentExclusionError, match="registration"):
        _build(tmp_path, (_excl(excluded_parent_name="SOMEONE ELSE PTY LIMITED"),))


def test_an_exclusion_names_the_recipient_it_was_written_for(tmp_path):
    with pytest.raises(ParentExclusionError, match="recipient"):
        _build(tmp_path, (_excl(recipient_name="INTERTRADE LIMITED"),))


def test_the_real_seed_is_the_135_split(tmp_path):
    rows = load_parent_exclusions(DEFAULT_PARENT_EXCLUSIONS)
    assert [(r.recipient_uei, r.excluded_parent_uei) for r in rows] == [
        ("H7KFX5RH75K3", "EGAVSJTA2D81")
    ]
    assert rows[0].roadmap == "#135" and rows[0].decided == "2026-09-25"


def test_a_missing_or_malformed_seed_fails_loudly(tmp_path):
    with pytest.raises(ParentExclusionError, match="missing"):
        load_parent_exclusions(tmp_path / "absent.csv")
    bad = tmp_path / "bad.csv"
    bad.write_text("recipient_uei,excluded_parent_uei\nUS1,PRCA\n")
    with pytest.raises(ParentExclusionError, match="columns"):
        load_parent_exclusions(bad)
    dup = tmp_path / "dup.csv"
    header = ("recipient_uei,recipient_name,excluded_parent_uei,excluded_parent_name,"
              "decided,roadmap,note\n")
    line = "US1,SPARTON,PRCA,RC AUSTRALIA,2026-09-25,#135,n\n"
    dup.write_text(header + line + line)
    with pytest.raises(ParentExclusionError, match="twice"):
        load_parent_exclusions(dup)
    date = tmp_path / "date.csv"
    date.write_text(header + "US1,SPARTON,PRCA,RC AUSTRALIA,25/09/2026,#135,n\n")
    with pytest.raises(ParentExclusionError, match="decided"):
        load_parent_exclusions(date)


# ── ROADMAP #133 / R-DEC-133b: the fiscal-year move rule ────────────────────
#
# entity-graph sums the RAW award archives, so it applies the same rule dbt
# staging applies (govbudget.award_moves): the retired copy of a proven move
# is not counted, and any other duplicate stops the build before anything is
# written. The fixtures are test_dbt_award_fy_moves' own shapes.

from test_dbt_award_fy_moves import _write_the_moves  # noqa: E402

from govbudget import award_moves  # noqa: E402


def _award_globs(data_dir: Path) -> list[str]:
    return [
        str(data_dir / "parquet" / "contracts" / "*" / "*.parquet"),
        str(data_dir / "parquet" / "assistance" / "*" / "*.parquet"),
    ]


def test_a_moved_transaction_is_counted_once(tmp_path, capsys):
    """The un-reconciled 2026-09-24 shape. Raw archive sums are UEI9 1,211 and
    UEI8 1,350; the warehouse keeps 611 and 650, and so must the crosswalk —
    the totals assert_entity_totals_exclude_retired_award_copies accepts."""
    _write_the_moves(tmp_path)
    out = build_entity_xwalk(
        award_glob=_award_globs(tmp_path),
        out_path=tmp_path / "xw_moves.parquet",
        parent_exclusions=(),
        require_transaction_keys=True,
    )
    by_uei, cols = _read(out)
    tot = cols.index("total_obligation")
    assert by_uei["UEI9"][tot] == 611.0
    assert by_uei["UEI8"][tot] == 650.0
    assert "entity-graph: fiscal-year move rule (ROADMAP #133): retired 2 contract" \
        " and 1 assistance copies" in capsys.readouterr().out


def test_an_ambiguous_duplicate_stops_the_crosswalk_before_it_is_written(tmp_path):
    from test_award_moves import _write_ambiguous

    _write_ambiguous(tmp_path)
    out = tmp_path / "xw_ambiguous.parquet"
    with pytest.raises(award_moves.AmbiguousAwardDuplicateError, match="THREE001"):
        build_entity_xwalk(
            award_glob=[_award_globs(tmp_path)[0]],
            out_path=out,
            parent_exclusions=(),
        )
    assert not out.exists()


def test_the_cli_reads_both_archives_through_the_rule(tmp_path, monkeypatch):
    """cmd_entity_graph is the production caller: both archives, and a glob
    that carries no transaction key is an error there, never a silent pass."""
    from govbudget import cli, config
    from govbudget import entity_graph

    _write_the_moves(tmp_path)
    monkeypatch.setattr(config, "PARQUET_DIR", tmp_path / "parquet")
    seen = {}
    real = entity_graph.build_entity_xwalk

    def spy(**kwargs):
        seen.update(kwargs)
        return real(**{**kwargs, "parent_exclusions": ()})

    monkeypatch.setattr(entity_graph, "build_entity_xwalk", spy)
    cli.cmd_entity_graph(None)
    assert seen["require_transaction_keys"] is True
    assert seen["award_glob"] == _award_globs(tmp_path)
    by_uei, cols = _read(seen["out_path"])
    assert by_uei["UEI9"][cols.index("total_obligation")] == 611.0

    # A key-less archive is refused on the CLI path.
    keyless = tmp_path / "keyless" / "parquet"
    make_lake(keyless)  # contracts/fy=2024 without a transaction key column
    (keyless / "assistance" / "fy=2024").mkdir(parents=True)
    duckdb.sql(
        f"copy (select * from read_parquet('{keyless}/contracts/fy=2024/part.parquet',"
        f" hive_partitioning=false)) to '{keyless}/assistance/fy=2024/part.parquet'"
        " (format parquet)"
    )
    monkeypatch.setattr(config, "PARQUET_DIR", keyless)
    with pytest.raises(award_moves.AwardArchiveError, match="no transaction key column"):
        cli.cmd_entity_graph(None)
