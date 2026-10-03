"""scripts/era/review_batch_page.py — owner review batches (Task 15, spec §5.3)."""
import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from era.review_batch_page import (  # scripts/ is on sys.path via conftest
    BATCH_SIZE,
    ReviewError,
    apply_answers,
    fmt_usd_k,
    main,
    next_batch,
    read_collision_codes,
    render_page,
)
from govbudget.jbooks import era_map
from govbudget.jbooks.era_map import CHAIN_COLUMNS, REVIEW_COLUMNS, SEED_COLUMNS, write_csv
from jbooks.era_map_fixtures import make_lake, make_raw_docs


def cid(i):
    return f"C{i:03d}|3010F|"


def row(i, actuals="1000", **changes):
    """One review.csv row exactly as `era-map propose` writes it (era_map.REVIEW_COLUMNS)."""
    base = dict.fromkeys(REVIEW_COLUMNS, "")
    base.update(
        chain_id=cid(i), first_edition="2017", last_edition="2023",
        titles_by_edition="2017: OLD TITLE; 2018: OLD TITLE | OLD TITLE (AP); 2023: NEW TITLE",
        modern_title="NEW TITLE", accounts="era=3010F; modern=3010F", continuity="3/3",
        actuals_k=actuals, proposed_decision="same_program",
        reason="R1: renamed, continuity 3/3 holds (title Jaccard 0.50)", keys_sha256="ab" * 32,
    )
    base.update(changes)
    return base


def chains_for(rows, **changes):
    return {r["chain_id"]: {"n_keys": "7", "classes": "A1+R1", "successor_account": "",
                            "successor_evidence": "", **changes} for r in rows}


def test_batch_is_the_25_largest_open_chains():
    rows = [row(i, actuals=str(i * 10)) for i in range(30)]
    rows[29]["decision"] = "same_program"          # answered, not yet ratified
    batch, open_count = next_batch(rows, {cid(28)})  # C028 already in the seed
    assert BATCH_SIZE == 25
    assert open_count == 28
    assert [r["chain_id"] for r in batch] == [cid(i) for i in range(27, 2, -1)]


def test_equal_dollars_break_ties_on_chain_id():
    batch, _ = next_batch([row(2, actuals="5"), row(1, actuals="5"), row(3, actuals="9")], set())
    assert [r["chain_id"] for r in batch] == [cid(3), cid(1), cid(2)]


def test_dollars_print_in_the_scale_the_owner_reads():
    assert fmt_usd_k(Decimal("1234567")) == "$1.23B"
    assert fmt_usd_k(Decimal("4500")) == "$4.50M"
    assert fmt_usd_k(Decimal("12")) == "$12.00K"
    assert fmt_usd_k(Decimal("0")) == "$0"


def test_page_escapes_every_source_string():
    hostile = row(1, titles_by_edition='2017: <script>alert(1)</script> & "Co"',
                  reason="<b>bold</b>", modern_title="A&B")
    page = render_page("B1", [hostile], 0, chains_for([hostile], successor_evidence="<i>x</i>"))
    assert "<script>alert" not in page and "<b>bold</b>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; &quot;Co&quot;" in page
    assert "&lt;b&gt;bold&lt;/b&gt;" in page and "A&amp;B" in page


def test_page_is_an_artifact_fragment_numbered_in_batch_order():
    rows = [row(i, actuals=str(100 - i)) for i in range(3)]
    page = render_page("B3", rows, 40, chains_for(rows))
    assert page.startswith("<title>Era map review B3</title>")
    assert "<html" not in page and "<body" not in page and "<!doctype" not in page.lower()
    assert ':root:not([data-theme="light"])' in page and ':root[data-theme="dark"]' in page
    assert "body{background:var(--paper)" in page
    assert page.count('<li class="chain"') == 3
    assert page.index('id="row-1"') < page.index("C000|3010F||2017-2023") < page.index('id="row-2"')
    assert "7 era lines · class A1+R1" in page
    assert "2017: OLD TITLE\n2018: OLD TITLE | OLD TITLE (AP)\n2023: NEW TITLE" in page
    assert "era=3010F; modern=3010F" in page and "3/3" in page
    assert "40 undecided chains will remain after this batch" in page


def test_page_flags_a_chain_with_no_proposal_and_shows_pins_and_the_stated_successor():
    rows = [row(1, proposed_decision="", program_account="1611N", program_org="N",
                successor_code="5731D15610")]
    page = render_page("B1", rows, 0, chains_for(rows, successor_account="2035A",
                                                  successor_evidence="FY 2024 P-1 line 5731D15610"))
    assert '<span class="chip chip-other">needs your decision</span>' in page
    assert "joins account 1611N · joins org N" in page
    assert "<code>5731D15610</code> 2035A" in page and "FY 2024 P-1 line 5731D15610" in page


def test_page_needs_every_chain_in_chains_csv():
    with pytest.raises(ReviewError, match="chains.csv has no row"):
        render_page("B1", [row(1)], 0, {})


def test_page_flags_a_collision_code_proposal_without_both_pins():
    # Task 12 ratify refuses same_program/history_only on a PB2026 collision
    # code unless program_account AND program_org are set (e.g. the live
    # 20|0300D|DCAA, proposed same_program with blank pins): the page says so.
    rows = [row(1, chain_id="20|0300D|DCAA", proposed_decision="same_program"),
            row(2, chain_id="500|0300D|DCMA", proposed_decision="history_only",
                program_account="0300D", program_org="DCMA"),
            row(3, chain_id="3010|1611N|", proposed_decision="history_only", program_account="1611N"),
            row(4, chain_id="C004|3010F|", proposed_decision="same_program")]
    page = render_page("B1", rows, 0, chains_for(rows), collision_codes=frozenset({"20", "500", "3010"}))
    items = page.split('<li class="chain"')[1:]
    assert '<span class="chip chip-other">needs your decision</span>' in items[0]
    assert ("PB2026 collision code 20: same_program needs program_account and program_org" in items[0])
    assert "needs your decision" not in items[1] and "joins account 0300D · joins org DCMA" in items[1]
    assert "PB2026 collision code 3010: history_only needs program_org" in items[2]
    assert "needs your decision" not in items[3] and "chip-same" in items[3]


def test_collision_codes_come_from_counts_json(tmp_path):
    counts = tmp_path / "counts.json"
    counts.write_text(json.dumps({"collision_codes": ["20", "3010"], "chain_groups": {}}))
    assert read_collision_codes(counts) == frozenset({"20", "3010"})
    counts.write_text(json.dumps({"chain_groups": {}}))
    with pytest.raises(ReviewError, match="no collision_codes list"):
        read_collision_codes(counts)
    with pytest.raises(ReviewError, match="is missing"):
        read_collision_codes(tmp_path / "absent.json")


SHOWN = [cid(1), cid(2), cid(3)]


def three():
    return [row(1), row(2, proposed_decision="history_only"), row(3)]


def test_approval_takes_each_proposal_and_an_amendment_overrides_it():
    out, counts = apply_answers(three(), SHOWN, {"rows": {
        cid(3): {"decision": "exclude_reused_code", "note": "owner B1 row 3: a different program in PB2017"}}})
    assert [r["decision"] for r in out] == ["same_program", "history_only", "exclude_reused_code"]
    assert out[2]["note"] == "owner B1 row 3: a different program in PB2017"
    assert [r["keys_sha256"] for r in out] == ["ab" * 32] * 3
    assert counts == {"decided": 3, "split_chains": 0, "split_rows": 0, "deferred": 0}


def test_pins_and_successor_are_written_only_when_answered():
    out, _ = apply_answers(three(), SHOWN, {"rows": {cid(1): {"program_account": "3022F"},
                                                      cid(2): {"successor_code": "5731D15610"}}})
    assert (out[0]["program_account"], out[0]["decision"]) == ("3022F", "same_program")
    assert out[1]["successor_code"] == "5731D15610"
    assert out[2]["program_account"] == "" and out[2]["successor_code"] == ""


def test_a_deferred_chain_stays_open_and_leads_the_next_batch():
    out, counts = apply_answers(three(), SHOWN, {"rows": {cid(2): {"defer": True}}})
    assert out[1]["decision"] == "" and counts["deferred"] == 1
    assert [r["chain_id"] for r in next_batch(out, set())[0]] == [cid(2)]


@pytest.mark.parametrize("answers, message", [
    ({"rows": {cid(9): {"decision": "same_program"}}}, "did not show"),
    ({"rows": {cid(1): {"decision": "maybe"}}}, "is not a decision"),
    ({"rows": {cid(1): {"verdict": "same_program"}}}, "unknown answer field"),
    ({"rows": {cid(1): {"defer": True, "note": "x"}}}, "takes no other answer"),
    ({"rows": {cid(1): {"split": [{"last_edition": 2019, "decision": "history_only"},
                                  {"decision": "same_program"}], "note": "x"}}}, "inside each range"),
    ({"rows": {cid(1): {"successor_code": "5731D15610"}}}, "successor only on history_only"),
    ({"rows": {cid(1): {"decision": "exclude_reused_code", "program_account": "3022F"}}},
     "an exclusion carries no program pin"),
    ({"row": {}}, 'answers need a "rows" object'),
])
def test_unusable_answers_are_refused(answers, message):
    with pytest.raises(ReviewError, match=message):
        apply_answers(three(), SHOWN, answers)


def test_a_proposal_that_is_not_a_decision_needs_the_owners_explicit_answer():
    rows = three()
    rows[0]["proposed_decision"] = ""
    with pytest.raises(ReviewError, match="is not a decision"):
        apply_answers(rows, SHOWN, {"rows": {}})
    out, _ = apply_answers(rows, SHOWN, {"rows": {cid(1): {"decision": "history_only"}}})
    assert out[0]["decision"] == "history_only"


def test_an_answered_chain_cannot_be_answered_twice():
    rows = three()
    rows[1]["decision"] = "history_only"
    with pytest.raises(ReviewError, match="already has a decision"):
        apply_answers(rows, SHOWN, {"rows": {}})


def test_a_shown_chain_must_have_exactly_one_review_row():
    rows = three() + [row(1, first_edition="2020")]
    with pytest.raises(ReviewError, match="2 review.csv row"):
        apply_answers(rows, SHOWN, {"rows": {}})


def test_a_split_duplicates_the_row_and_changes_only_its_edition_range():
    out, counts = apply_answers(three(), SHOWN, {"rows": {cid(1): {"split": [
        {"last_edition": 2019, "decision": "exclude_reused_code", "note": "owner B1 row 1: earlier program"},
        {"decision": "same_program"}]}}})
    first, second = out[0], out[1]
    assert (first["first_edition"], first["last_edition"]) == ("2017", "2019")
    assert (second["first_edition"], second["last_edition"]) == ("2020", "2023")
    assert {first["chain_id"], second["chain_id"]} == {cid(1)}
    assert first["keys_sha256"] == second["keys_sha256"] == "ab" * 32
    unchanged = set(REVIEW_COLUMNS) - {"first_edition", "last_edition", "decision", "note"}
    assert all(first[c] == second[c] == row(1)[c] for c in unchanged)
    assert [r["decision"] for r in out] == ["exclude_reused_code", "same_program", "history_only", "same_program"]
    assert first["note"] == "owner B1 row 1: earlier program" and second["note"] == ""
    assert counts == {"decided": 2, "split_chains": 1, "split_rows": 2, "deferred": 0}


@pytest.mark.parametrize("ranges, message", [
    ([{"decision": "same_program"}], "at least two ranges"),
    ([{"decision": "history_only"}, {"decision": "same_program"}], "names its last_edition"),
    ([{"last_edition": 2019, "decision": "history_only"},
      {"last_edition": 2022, "decision": "same_program"}], "must end at PB2023"),
    ([{"last_edition": 2016, "decision": "history_only"}, {"decision": "same_program"}], "does not fit"),
    ([{"last_edition": 2023, "decision": "history_only"}, {"decision": "same_program"}], "does not fit"),
    ([{"last_edition": 2019, "decision": "history_only"},
      {"last_edition": 2018, "decision": "history_only"}, {"decision": "same_program"}], "does not fit"),
    ([{"last_edition": 2019}, {"decision": "same_program"}], "needs an explicit decision"),
    ([{"first_edition": 2017, "last_edition": 2019, "decision": "history_only"},
      {"decision": "same_program"}], "unknown answer field"),
])
def test_a_split_must_cover_the_chain_in_contiguous_decided_ranges(ranges, message):
    with pytest.raises(ReviewError, match=message):
        apply_answers(three(), SHOWN, {"rows": {cid(1): {"split": ranges}}})


def write_world(tmp_path, rows, collision_codes=()):
    review = tmp_path / "research" / "review.csv"
    write_csv(review, REVIEW_COLUMNS, rows)
    write_csv(review.with_name("chains.csv"), CHAIN_COLUMNS,
              [{"chain_id": r["chain_id"], "n_keys": "7", "classes": "A1+R1"} for r in rows])
    review.with_name("counts.json").write_text(json.dumps({"collision_codes": sorted(collision_codes)}))
    return review


def answers_file(tmp_path, label, rows, **extra):
    path = tmp_path / f"{label}.answers.json"
    path.write_text(json.dumps({"batch": label, "decided_on": "2026-10-05",
                                "owner_reply": "approved, except 3: history_only", "rows": rows, **extra}))
    return path


def test_render_then_answer_round_trip_through_the_cli(tmp_path, capsys):
    review, out = write_world(tmp_path, [row(1, actuals="10"), row(2, actuals="30"), row(3, actuals="20")]), tmp_path / "out"
    assert main(["render", "--batch", "2", "--review", str(review),
                 "--seed", str(tmp_path / "absent.csv"), "--out-dir", str(out)]) == 0
    manifest = json.loads((out / "B2.json").read_text())
    assert manifest["chain_ids"] == [cid(2), cid(3), cid(1)]
    assert manifest["labels"][0] == "C002|3010F||2017-2023"
    assert (out / "B2.html").read_text().startswith("<title>Era map review B2</title>")
    answers = answers_file(tmp_path, "B2", {cid(1): {"decision": "history_only"}},
                           owner_acknowledgements={"R-DEC-ERA-EXCLUDE actuals correction": "noted"})
    capsys.readouterr()
    assert main(["answer", "--batch", "2", "--review", str(review), "--out-dir", str(out),
                 "--answers", str(answers)]) == 0
    assert capsys.readouterr().out.strip().endswith(
        "ratify writes 3 seed row(s): era-map ratify --batch B2 --decided-on 2026-10-05")
    with review.open(newline="") as f:
        reader = csv.DictReader(f)
        assert tuple(reader.fieldnames) == REVIEW_COLUMNS
        decided = {r["chain_id"]: r["decision"] for r in reader}
    assert decided == {cid(1): "history_only", cid(2): "same_program", cid(3): "same_program"}
    assert main(["answer", "--batch", "2", "--review", str(review), "--out-dir", str(out),
                 "--answers", str(answers)]) == 2
    assert "already has a decision" in capsys.readouterr().err


@pytest.mark.parametrize("extra, message", [
    ({"batch": "B3"}, "is batch 'B3', not B2"),
    ({"owner_reply": " "}, "owner_reply"),
    ({"decided_on": "Oct 5"}, "not an ISO date"),
    ({"rws": {}}, "unknown top-level key"),
])
def test_the_cli_refuses_an_unusable_answers_file(tmp_path, capsys, extra, message):
    review, out = write_world(tmp_path, [row(1)]), tmp_path / "out"
    assert main(["render", "--batch", "2", "--review", str(review),
                 "--seed", str(tmp_path / "absent.csv"), "--out-dir", str(out)]) == 0
    before = review.read_bytes()
    answers = answers_file(tmp_path, "B2", {}, **extra)
    assert main(["answer", "--batch", "2", "--review", str(review), "--out-dir", str(out),
                 "--answers", str(answers)]) == 2
    assert message in capsys.readouterr().err
    assert review.read_bytes() == before


def test_the_cli_refuses_a_review_file_with_another_header(tmp_path, capsys):
    review = tmp_path / "review.csv"
    review.write_text("decision_id,decision\nX|3010F||2017-2023,\n")
    assert main(["render", "--batch", "1", "--review", str(review), "--out-dir", str(tmp_path)]) == 2
    assert "is not era_map.REVIEW_COLUMNS" in capsys.readouterr().err


def test_render_reads_the_collision_codes_beside_review_csv(tmp_path):
    review = write_world(tmp_path, [row(1, chain_id="20|0300D|DCAA")], collision_codes={"20"})
    assert main(["render", "--batch", "1", "--review", str(review),
                 "--seed", str(tmp_path / "absent.csv"), "--out-dir", str(tmp_path / "out")]) == 0
    assert "PB2026 collision code 20: same_program needs program_account and program_org" in (
        (tmp_path / "out" / "B1.html").read_text())


def test_render_skips_chains_the_seed_already_covers(tmp_path, capsys):
    review = write_world(tmp_path, [row(1), row(2)])
    seed = tmp_path / "seed.csv"
    write_csv(seed, SEED_COLUMNS, [{"decision_id": "C001|3010F||2017-2023", "line_item_code": "C001",
                                    "account": "3010F", "organization": "", "first_edition": "2017",
                                    "last_edition": "2023"}])
    assert main(["render", "--batch", "1", "--review", str(review), "--seed", str(seed),
                 "--out-dir", str(tmp_path / "out")]) == 0
    assert json.loads((tmp_path / "out" / "B1.json").read_text())["chain_ids"] == [cid(2)]


def test_what_this_tool_writes_is_what_ratify_accepts(tmp_path, monkeypatch):
    """End to end on era_map's miniature lake: propose -> render -> answer
    (one approval with a note, one range split, two approved proposals with
    their pre-filled pins) -> ratify -> check -> propose."""
    monkeypatch.setattr(era_map, "ORG_SPLIT_CODES", frozenset({"20"}))
    db = make_lake(tmp_path / "lake")
    raw = make_raw_docs(tmp_path)
    out = tmp_path / "research" / "era_map"
    seed = tmp_path / "seeds" / "p1_era_code_decisions.csv"
    era_map.propose(duckdb_path=db, raw_docs_dir=raw, out_dir=out, seed_path=seed, decided_on=date(2026, 10, 2))
    review, pages = out / "review.csv", tmp_path / "pages"
    assert main(["render", "--batch", "1", "--review", str(review), "--seed", str(seed),
                 "--out-dir", str(pages)]) == 0
    shown = json.loads((pages / "B1.json").read_text())["chain_ids"]
    assert sorted(shown) == ["1045|1612N|", "20|0300D|DHRA", "20|0300D|DSS", "50|0300D|"]
    answers = answers_file(tmp_path, "B1", {
        "1045|1612N|": {"decision": "same_program", "note": "OHIO Replacement = COLUMBIA"},
        "50|0300D|": {"split": [{"last_edition": 2022, "decision": "exclude_reused_code"},
                                {"decision": "history_only"}]}})
    assert main(["answer", "--batch", "1", "--review", str(review), "--out-dir", str(pages),
                 "--answers", str(answers)]) == 0
    assert era_map.ratify(review_csv=review, seed_path=seed, batch="B1",
                          decided_on=date(2026, 10, 5), duckdb_path=db) == 5
    b1 = {r["decision_id"]: r for r in era_map.read_seed(seed) if r["ruling"] == "R-DEC-ERA-B1"}
    assert set(b1) == {"1045|1612N||2022-2022", "20|0300D|DSS|2022-2022", "50|0300D||2022-2022",
                       "50|0300D||2023-2023", "20|0300D|DHRA|2023-2023"}
    assert b1["1045|1612N||2022-2022"]["note"] == "OHIO Replacement = COLUMBIA"
    assert era_map.check(duckdb_path=db, seed_path=seed) == {"undecided": [], "stale": []}
    era_map.propose(duckdb_path=db, raw_docs_dir=raw, out_dir=out, seed_path=seed, decided_on=date(2026, 10, 2))
    assert era_map.read_csv(review) == []
    assert main(["render", "--batch", "2", "--review", str(review), "--seed", str(seed),
                 "--out-dir", str(pages)]) == 0
    assert not (pages / "B2.json").exists()
