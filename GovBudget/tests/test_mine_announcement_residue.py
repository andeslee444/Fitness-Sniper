"""Unit tests for the wave-4 announcement residue miner.

The wave-4 queue is the tail of the LLM-alias pass the 2026-09-01/02 legs
stopped short of (ROADMAP findings log :118-119: "12,811 records/$278B not").
The script that produced the wave-2 input chunks was never committed — grep for
'llm_chunks' over scripts/ src/ tests/ docs/ returns nothing at 5dd7fb04 — so
these tests pin the rule this one uses, and in particular the two shapes that
would break the downstream loader:

  * wave4_chunks/chunk_*.json must be a bare LIST (load_announcement_links.py
    iterates it directly and subscripts each member with ["piid"]);
  * every emitted packet must carry a match_basis from the closed vocabulary
    and a lexicon_doc, because the citation card words the first and a shared
    BLI code cannot be resolved without the second.
"""
import json

import pytest

import mine_announcement_residue as mar
from mine_announcement_residue import (  # scripts/ on sys.path via tests/conftest.py:22
    BASIS_VOCAB,
    SERVICE_ORG,
    announced_value,
    build_name_index,
    chunk_records,
    cmd_collect,
    collect_verdicts,
    has_deterministic_match,
    lexicon_index_lines,
    normalize_service,
    read_index_rows,
    record_key,
    select_residue,
)

LEXICON = [
    {"name": "Binocular Night Vision Devices (BNVD)", "pe_bli": "842990",
     "ownership": "own", "kind": "system", "doc_id": "411", "quote": "…BNVD…"},
    {"name": "STORM", "pe_bli": "2876", "ownership": "own", "kind": "system",
     "doc_id": "333", "quote": "…STORM…", "weak_name": True},
    {"name": "Triton", "pe_bli": "0305220N", "ownership": "mentioned",
     "kind": "system", "doc_id": "601", "quote": "…Triton…"},
]


def _rec(article_id, text, piids, amounts, service="NAVY"):
    return {
        "article_id": article_id, "date": "2020-04-30", "service": service,
        "contractor": "Acme Corp.", "amounts": amounts,
        "contract_numbers": [{"raw": p, "piid": p, "role": "award"} for p in piids],
        "text": text,
    }


def test_normalize_service_strips_the_nbsp_and_punctuation_noise():
    # The parser keeps the raw heading: 870 of the 34,542 records carry a
    # literal '&NBSP;' (with or without a leading space), and a heading may end
    # in '.' or '*'.
    assert normalize_service("NAVY &NBSP;") == "NAVY"
    assert normalize_service("ARMY&NBSP;") == "ARMY"
    assert normalize_service("ARMY.") == "ARMY"
    assert normalize_service(None) == ""
    assert SERVICE_ORG["MARINE CORPS"] == "N"


def test_deterministic_match_uses_own_strong_names_only():
    index = build_name_index(LEXICON)
    # 'own', not weak -> matched, so NOT residue
    assert has_deterministic_match(
        "…contract for binocular night vision devices (BNVD) …", index) is True
    # weak_name -> never a deterministic match on its own
    assert has_deterministic_match("…hurricane and storm damage …", index) is False
    # ownership='mentioned' -> not an 'own' claim, so not a deterministic match
    assert has_deterministic_match("…support for Triton aircraft …", index) is False


def test_announced_value_is_the_first_amount_not_the_max():
    # The 2026-09-02 cut was by amounts[0]: the 3,840 attempted records are
    # exactly sorted by amounts[0] descending, the cut sits at $63,206,673, and
    # their amounts[0] sum to $1.9545e12 — the '$1.96T' on /methodology/.
    assert announced_value({"amounts": [4_941_105_246, 62_000_000_000]}) == 4_941_105_246
    assert announced_value({"amounts": []}) == 0


def test_select_residue_returns_the_residue_and_the_queued_subset():
    lake = {"N0001912G0006", "W56KGY17C0001"}
    attempted = {("111", "already attempted paragraph"[:200])}
    recs = [
        _rec("111", "already attempted paragraph", ["N0001912G0006"], [10]),
        _rec("222", "…binocular night vision devices (BNVD)…", ["N0001912G0006"], [20]),
        _rec("333", "…generic support services…", ["NOTINLAKE"], [30]),
        _rec("444", "…generic support services…", ["W56KGY17C0001"], [40], "ARMY"),
        _rec("555", "…generic support services…", ["N0001912G0006"], [50],
             "DEFENSE HEALTH AGENCY"),
    ]
    residue, kept = select_residue(
        recs, lake=lake, name_index=build_name_index(LEXICON),
        attempted=attempted, orgs_with_lexicon={"N", "A"})
    # rule 1 drops 333 (no lake PIID); rule 2 drops 222 (owned name in text)
    assert [r["article_id"] for r in residue] == ["111", "444", "555"]
    assert residue[0]["lake_piids"] == ["N0001912G0006"]
    # rule 3 drops 111 (already attempted); rule 4 drops 555 (no J-book org)
    assert [r["article_id"] for r in kept] == ["444"]
    assert kept[0]["org"] == "A"
    assert kept[0]["lake_piids"] == ["W56KGY17C0001"]


def test_chunk_records_groups_by_org_and_numbers_by_descending_value():
    recs = ([dict(_rec(str(i), "t", ["P"], [100 - i]), org="N", lake_piids=["P"])
             for i in range(3)]
            + [dict(_rec("9", "t", ["P"], [1000]), org="A", lake_piids=["P"])])
    chunks = chunk_records(recs, size=2)
    assert [c["file"] for c in chunks] == [
        "chunk_000_A.json", "chunk_001_N.json", "chunk_002_N.json"]
    assert chunks[0]["announced_value"] == 1000
    assert [len(c["records"]) for c in chunks] == [1, 2, 1]


def test_chunk_records_stamps_the_rank_the_run_protocol_orders_by():
    """Ruling A10 resolved to loop-until-dry in rounds of 5 chunks, so the
    controller has to be able to say WHICH chunks a round covers without
    re-deriving the order. `rank` is that number, and it is the same integer
    the file name carries."""
    recs = ([dict(_rec(str(i), "t", ["P"], [100 - i]), org="N", lake_piids=["P"])
             for i in range(3)]
            + [dict(_rec("9", "t", ["P"], [1000]), org="A", lake_piids=["P"])])
    chunks = chunk_records(recs, size=2)
    assert [c["rank"] for c in chunks] == [0, 1, 2]
    assert [c["announced_value"] for c in chunks] == [1000, 199, 98]
    # The order is by the chunk's TOP record, not by its sum — that is what
    # "stop anywhere and what you skipped is the cheapest tail" means, and on
    # the real queue 83 of the 305 adjacent pairs have a larger SUM below a
    # smaller one. Ranking by the top record is the property to pin.
    tops = [max(announced_value(r) for r in c["records"]) for c in chunks]
    assert tops == [1000, 100, 98]
    assert all(a >= b for a, b in zip(tops, tops[1:]))


def test_collect_requires_both_refute_lenses_to_clear():
    queue = [{"file": "chunk_000_N.json", "org": "N", "announced_value": 300,
              "records": [
                  dict(_rec("1", "t", ["P1"], [100]), org="N", lake_piids=["P1"]),
                  dict(_rec("2", "t", ["P2"], [100]), org="N", lake_piids=["P2"]),
                  dict(_rec("3", "t", ["P3"], [100]), org="N", lake_piids=["P3"]),
              ]}]
    verdicts = {"chunk_000_N.json": {"proposals": [
        {"article_id": "1", "piid": "P1", "pe_bli": "0305220N", "verdict": "link",
         "match_basis": "llm-alias", "program_name": "Triton", "lexicon_doc": "601",
         "announcement_evidence": "MQ-4C", "rationale": "…",
         "refute_a": {"refuted": False, "reason": "holds"},
         "refute_b": {"refuted": False, "reason": "holds"}},
        {"article_id": "2", "piid": "P2", "pe_bli": "0305220N", "verdict": "link",
         "match_basis": "llm-alias", "program_name": "Triton", "lexicon_doc": "601",
         "announcement_evidence": "…", "rationale": "…",
         "refute_a": {"refuted": False, "reason": "holds"},
         "refute_b": {"refuted": True, "reason": "O&M-only support award"}},
        {"article_id": "3", "piid": "P3", "pe_bli": "0305220N", "verdict": "link",
         "match_basis": "llm-alias", "program_name": "Triton", "lexicon_doc": "601",
         "announcement_evidence": "…", "rationale": "…",
         "refute_a": {"refuted": False, "reason": "holds"}},   # lens B never ran
    ]}}
    packets, result = collect_verdicts(queue, verdicts)
    assert [p["piid"] for p in packets] == ["P1"]
    assert result["surviving"] == [
        {"piid": "P1", "pe_bli": "0305220N", "reason": "holds"}]
    assert result["proposed"] == 3
    assert result["refuted_a"] == 0 and result["refuted_b"] == 1
    assert result["missing_lens"] == 1
    assert result["records_attempted"] == 3
    assert result["chunks_attempted"] == ["chunk_000_N.json"]


def test_collect_identifies_the_record_by_article_AND_piid():
    """A daily digest is ONE article with many paragraphs: 1,766 of the 23,824
    queued records (7.4%) share an article_id with another record in the same
    chunk. Keyed on article_id alone the packet would carry the other
    paragraph's date, contractor and excerpt — the citation card would quote a
    different award."""
    queue = [{"file": "chunk_000_N.json", "org": "N", "announced_value": 2,
              "records": [
                  dict(_rec("7", "the first award paragraph", ["P1"], [2]),
                       org="N", lake_piids=["P1"]),
                  dict(_rec("7", "the second award paragraph", ["P2"], [1]),
                       org="N", lake_piids=["P2"])]}]
    verdicts = {"chunk_000_N.json": {"proposals": [
        {"article_id": "7", "piid": "P2", "pe_bli": "0305220N", "verdict": "link",
         "match_basis": "llm-alias", "program_name": "Triton", "lexicon_doc": "601",
         "rationale": "…", "refute_a": {"refuted": False, "reason": "holds"},
         "refute_b": {"refuted": False}}]}}
    packets, _ = collect_verdicts(queue, verdicts)
    assert packets[0]["announcement_excerpt"] == "the second award paragraph"


def test_collect_refuses_an_ambiguous_record_unless_the_index_says_which():
    """17 of the queue's 31,693 (article_id, PIID) keys name two records of the
    same chunk — a modification paragraph citing the vehicle its award
    paragraph announced. Which paragraph the card quotes is then a coin flip,
    so the collector refuses until the proposal says."""
    queue = [{"file": "chunk_000_N.json", "org": "N", "announced_value": 2,
              "records": [
                  dict(_rec("7", "the award paragraph", ["P1"], [2]),
                       org="N", lake_piids=["P1"]),
                  dict(_rec("7", "the modification paragraph", ["P1"], [1]),
                       org="N", lake_piids=["P1"])]}]
    prop = {"article_id": "7", "piid": "P1", "pe_bli": "0305220N",
            "verdict": "link", "match_basis": "llm-alias",
            "program_name": "Triton", "lexicon_doc": "601", "rationale": "…",
            "refute_a": {"refuted": False, "reason": "holds"},
            "refute_b": {"refuted": False}}
    with pytest.raises(ValueError, match="record_index"):
        collect_verdicts(queue, {"chunk_000_N.json": {"proposals": [prop]}})
    packets, _ = collect_verdicts(
        queue, {"chunk_000_N.json": {"proposals": [{**prop, "record_index": 1}]}})
    assert packets[0]["announcement_excerpt"] == "the modification paragraph"
    with pytest.raises(ValueError, match="record_index"):
        collect_verdicts(
            queue, {"chunk_000_N.json": {"proposals": [{**prop, "record_index": 9}]}})


def test_collect_refuses_a_packet_with_no_match_basis():
    queue = [{"file": "chunk_000_N.json", "org": "N", "announced_value": 1,
              "records": [dict(_rec("1", "t", ["P1"], [1]), org="N", lake_piids=["P1"])]}]
    verdicts = {"chunk_000_N.json": {"proposals": [
        {"article_id": "1", "piid": "P1", "pe_bli": "0305220N", "verdict": "link",
         "program_name": "Triton", "lexicon_doc": "601", "rationale": "…",
         "refute_a": {"refuted": False}, "refute_b": {"refuted": False}}]}}
    with pytest.raises(ValueError, match="match_basis"):
        collect_verdicts(queue, verdicts)
    assert "llm-alias" in BASIS_VOCAB
    # subaward-description-exact makes the loader publish at subaward+lexicon /
    # medium and skip the money-colour guard (load_announcement_links.py:363-366),
    # which is not what an announcement link is.
    assert "subaward-description-exact" not in BASIS_VOCAB


def test_collect_refuses_a_proposal_that_names_no_pe():
    queue = [{"file": "chunk_000_N.json", "org": "N", "announced_value": 1,
              "records": [dict(_rec("1", "t", ["P1"], [1]), org="N", lake_piids=["P1"])]}]
    verdicts = {"chunk_000_N.json": {"proposals": [
        {"article_id": "1", "piid": "P1", "verdict": "link",
         "match_basis": "llm-alias", "lexicon_doc": "601", "rationale": "…",
         "refute_a": {"refuted": False}, "refute_b": {"refuted": False}}]}}
    with pytest.raises(ValueError, match="pe_bli"):
        collect_verdicts(queue, verdicts)


def test_collect_refuses_a_packet_with_no_lexicon_doc():
    """collision_account_for (load_announcement_links.py:126-146) returns None
    without one, and the link is dropped under skipped['collision_unresolved'];
    for every other key it is the evidence chain the rationale prints."""
    queue = [{"file": "chunk_000_N.json", "org": "N", "announced_value": 1,
              "records": [dict(_rec("1", "t", ["P1"], [1]), org="N", lake_piids=["P1"])]}]
    verdicts = {"chunk_000_N.json": {"proposals": [
        {"article_id": "1", "piid": "P1", "pe_bli": "0305220N", "verdict": "link",
         "match_basis": "llm-alias", "program_name": "Triton", "lexicon_doc": "  ",
         "rationale": "…", "refute_a": {"refuted": False},
         "refute_b": {"refuted": False}}]}}
    with pytest.raises(ValueError, match="lexicon_doc"):
        collect_verdicts(queue, verdicts)


def test_collect_accepts_a_partial_run_and_says_exactly_what_ran():
    """Ruling A10: the controller adjudicates rounds of 5 chunks and stops when
    three consecutive rounds return nothing. An unattempted chunk is neither
    surviving nor refuted — records_attempted/chunks_attempted are the scope
    figures Task 25b publishes, so they must describe the verdicts that came
    back, never the queue that was built."""
    def _chunk(file, org, article, piid):
        return {"file": file, "org": org, "announced_value": 1,
                "records": [dict(_rec(article, "t", [piid], [1]), org=org,
                                 lake_piids=[piid])]}
    queue = [_chunk("chunk_000_A.json", "A", "1", "P1"),
             _chunk("chunk_001_N.json", "N", "2", "P2"),
             _chunk("chunk_002_N.json", "N", "3", "P3")]
    verdicts = {"chunk_000_A.json": {"proposals": [
        {"article_id": "1", "piid": "P1", "pe_bli": "0305220N", "verdict": "link",
         "match_basis": "llm-alias", "program_name": "Triton", "lexicon_doc": "601",
         "rationale": "…", "refute_a": {"refuted": False, "reason": "holds"},
         "refute_b": {"refuted": False, "reason": "holds"}}]},
        "chunk_002_N.json": {"proposals": [
            {"article_id": "3", "piid": "P3", "pe_bli": "0305220N",
             "verdict": "wrong"}]}}
    packets, result = collect_verdicts(queue, verdicts)
    assert [p["piid"] for p in packets] == ["P1"]
    assert result["chunks_attempted"] == ["chunk_000_A.json", "chunk_002_N.json"]
    assert result["records_attempted"] == 2          # not 3 — chunk_001 never ran
    assert result["verdict_counts"] == {"link": 1, "weak": 0, "wrong": 1}


def test_collect_refuses_a_verdict_for_a_chunk_the_queue_does_not_hold():
    """A verdict file naming an unknown chunk means the queue was rebuilt under
    the adjudicators (the numbering is derived from the universe, so a re-run
    after new data renumbers everything). Silently ignoring it would drop real
    adjudications on the floor."""
    queue = [{"file": "chunk_000_N.json", "org": "N", "announced_value": 1,
              "records": [dict(_rec("1", "t", ["P1"], [1]), org="N", lake_piids=["P1"])]}]
    with pytest.raises(ValueError, match="chunk_007_N.json"):
        collect_verdicts(queue, {"chunk_007_N.json": {"proposals": []}})


def test_collect_counts_a_malformed_lens_verdict_as_refuted():
    """A8's fail-closed default: anything that is not the boolean false does not
    survive, and the count is printed so a mangled run cannot read as a clean
    one."""
    queue = [{"file": "chunk_000_N.json", "org": "N", "announced_value": 2,
              "records": [
                  dict(_rec("1", "t", ["P1"], [1]), org="N", lake_piids=["P1"]),
                  dict(_rec("2", "t", ["P2"], [1]), org="N", lake_piids=["P2"])]}]
    base = {"pe_bli": "0305220N", "verdict": "link", "match_basis": "llm-alias",
            "program_name": "Triton", "lexicon_doc": "601", "rationale": "…"}
    verdicts = {"chunk_000_N.json": {"proposals": [
        {**base, "article_id": "1", "piid": "P1",
         "refute_a": {"refuted": "no"}, "refute_b": {"refuted": False}},
        {**base, "article_id": "2", "piid": "P2",
         "refute_a": {"refuted": False}, "refute_b": {"refuted": False}}]}}
    packets, result = collect_verdicts(queue, verdicts)
    assert [p["piid"] for p in packets] == ["P2"]
    assert result["malformed_lens"] == 1
    assert result["missing_lens"] == 0


def test_collect_emits_one_packet_per_pair_even_when_two_records_propose_it():
    """The same PIID can appear in several announcements (a modification is its
    own paragraph). load_announcement_links.py:273 keeps the FIRST packet per
    (piid, pe_bli) anyway, so the collector resolves the duplicate here — in
    queue order (chunks descending by announced value, then the order the lens
    wrote its proposals) — and counts it."""
    queue = [{"file": "chunk_000_N.json", "org": "N", "announced_value": 2,
              "records": [
                  dict(_rec("1", "first paragraph", ["P1"], [2]), org="N",
                       lake_piids=["P1"]),
                  dict(_rec("2", "second paragraph", ["P1"], [1]), org="N",
                       lake_piids=["P1"])]}]
    base = {"piid": "P1", "pe_bli": "0305220N", "verdict": "link",
            "match_basis": "llm-alias", "program_name": "Triton",
            "lexicon_doc": "601", "rationale": "…",
            "refute_a": {"refuted": False, "reason": "holds"},
            "refute_b": {"refuted": False, "reason": "holds"}}
    verdicts = {"chunk_000_N.json": {"proposals": [
        {**base, "article_id": "1"}, {**base, "article_id": "2"}]}}
    packets, result = collect_verdicts(queue, verdicts)
    assert [p["announcement_excerpt"] for p in packets] == ["first paragraph"]
    assert result["duplicate_pairs"] == 1
    assert result["surviving"] == [
        {"piid": "P1", "pe_bli": "0305220N", "reason": "holds"}]


def test_collected_packets_are_a_bare_list_the_link_loader_can_iterate(tmp_path):
    """load_announcement_links.py globs wave*_chunks and does
    `for p in json.load(open(f)): prov.setdefault((p["piid"], p["pe_bli"]), p)`,
    then reads p['article_id'], p['date'], p['program_name'], p['match_basis']
    and p['lexicon_doc'] off the packet (:270-273, :347-352, :189-206).
    A dict here iterates keys and raises TypeError on p["piid"]."""
    queue = [{"file": "chunk_000_N.json", "org": "N", "announced_value": 1,
              "records": [dict(_rec("1", "t", ["P1"], [1]), org="N", lake_piids=["P1"])]}]
    verdicts = {"chunk_000_N.json": {"proposals": [
        {"article_id": "1", "piid": "P1", "pe_bli": "0305220N", "verdict": "link",
         "match_basis": "llm-alias", "program_name": "Triton", "lexicon_doc": "601",
         "announcement_evidence": "MQ-4C", "rationale": "…",
         "refute_a": {"refuted": False}, "refute_b": {"refuted": False}}]}}
    packets, _ = collect_verdicts(queue, verdicts)
    path = tmp_path / "chunk_000.json"
    path.write_text(json.dumps(packets))
    loaded = json.load(open(path))
    assert isinstance(loaded, list)
    for p in loaded:                      # exactly the loader's loop
        assert (p["piid"], p["pe_bli"]) == ("P1", "0305220N")
    assert loaded[0]["article_id"] == "1"
    assert loaded[0]["date"] == "2020-04-30"
    assert loaded[0]["program_name"] == "Triton"
    assert loaded[0]["match_basis"] == "llm-alias"
    assert loaded[0]["lexicon_doc"] == "601"
    assert loaded[0]["announcement_excerpt"] == "t"
    # record_key is the identity of a parsed RECORD, not of a packet — a packet
    # carries announcement_excerpt, never `text`.
    assert record_key({"article_id": "1", "text": "t"}) == ("1", "t")
    assert "text" not in loaded[0]


# --- fix round 1: the index the lens copies from, and the collector's content
# --- checks against it (rulings R-25-1, R-25-3).

INDEX_N = "\n".join([
    "name\tpe_bli\tlexicon_doc\tprogram_title",
    "Triton\t0305220N\t601\tTRITON UAS",
    "MQ-4C\t0305220N\t601\tTRITON UAS",
]) + "\n"


def _link(article_id, piid, **over):
    """A proposal lens P + A + B would write for a record of _one_chunk()."""
    prop = {"article_id": article_id, "piid": piid, "pe_bli": "0305220N",
            "verdict": "link", "match_basis": "llm-alias", "program_name": "Triton",
            "lexicon_doc": "601", "rationale": "…",
            "refute_a": {"refuted": False, "reason": "holds"},
            "refute_b": {"refuted": False, "reason": "holds"}}
    prop.update(over)
    return prop


def _one_chunk(file="chunk_000_N.json", org="N", pairs=(("1", "P1"),)):
    return {"file": file, "org": org, "announced_value": len(pairs),
            "records": [dict(_rec(a, "t", [p], [1]), org=org, lake_piids=[p])
                        for a, p in pairs]}


def test_lexicon_index_omits_a_row_whose_lexicon_entry_has_no_doc_id():
    """Ruling A7 makes a proposal with no lexicon_doc unpublishable, and the
    rubric tells the lens to copy this column verbatim — so a row written as the
    literal 'None' can only produce a packet whose published rationale reads
    "J-book narrative owns it (None)". 314 of the first build's 6,409 rows were
    that string (A 192 · N 83 · F 35 · DTRA 3 · DLA 1)."""
    owned = [
        {"name": "Triton", "pe_bli": "0305220N", "doc_id": "601"},
        {"name": "Poseidon", "pe_bli": "0305220N", "doc_id": None},
        {"name": "Sea Hunter", "pe_bli": "0604373N", "doc_id": ""},
        {"name": "Reaper", "pe_bli": "0305205F", "doc_id": "712"},
    ]
    pe_orgs = {"0305220N": {"N"}, "0604373N": {"N"}, "0305205F": {"F"}}
    lines = lexicon_index_lines(owned, "N", pe_orgs, {"0305220N": "TRITON UAS"})
    assert lines[0] == "name\tpe_bli\tlexicon_doc\tprogram_title"
    assert [l.split("\t")[0] for l in lines[1:]] == ["Triton"]
    assert "None" not in "\n".join(lines)


def test_read_index_rows_round_trips_what_the_queue_writes():
    """The collector validates a proposal's (program_name, pe_bli, lexicon_doc)
    against exactly the file the lens read, so the reader has to mirror the
    writer. Names compare case-insensitively; the pe_bli and the doc id do not."""
    owned = [{"name": "Triton", "pe_bli": "0305220N", "doc_id": "601"}]
    lines = lexicon_index_lines(owned, "N", {"0305220N": {"N"}}, {"0305220N": "TRITON UAS"})
    assert read_index_rows("\n".join(lines) + "\n") == {("triton", "0305220N", "601")}


def test_chunk_records_ranks_by_top_record_even_when_another_chunk_sums_higher():
    """Discriminates the rank rule: ranking by chunk SUM would invert these two.
    On the real queue 83 of the 305 adjacent pairs carry a larger sum below a
    smaller one, and the run protocol walks this order in rounds of 5."""
    recs = [dict(_rec("A1", "t", ["P"], [150]), org="A", lake_piids=["P"]),
            dict(_rec("N1", "t", ["P"], [100]), org="N", lake_piids=["P"]),
            dict(_rec("N2", "t", ["P"], [99]), org="N", lake_piids=["P"])]
    chunks = chunk_records(recs, size=2)
    assert [c["file"] for c in chunks] == ["chunk_000_A.json", "chunk_001_N.json"]
    # the sums are NOT monotonic — that is the point
    assert [c["announced_value"] for c in chunks] == [150, 199]


def test_collect_refuses_a_lexicon_doc_that_reads_as_absent_to_the_loader():
    """load_announcement_links._packet_value (:112-122) maps '' and the literal
    'None' back to absent, so accepting either here publishes a card whose
    evidence chain names no document — and drops the link outright on an
    account-split key (skipped['collision_unresolved'])."""
    queue = [_one_chunk()]
    for bad in ("None", "none", "null", "  "):
        with pytest.raises(ValueError, match="lexicon_doc"):
            collect_verdicts(queue, {"chunk_000_N.json": {"proposals": [
                _link("1", "P1", lexicon_doc=bad)]}})


def test_collect_refuses_a_proposal_with_no_program_name():
    """load_announcement_links.py:348 interpolates it into the published
    rationale — without one the card reads "program 'None' named for this
    award"."""
    queue = [_one_chunk()]
    for bad in (None, "", "None"):
        with pytest.raises(ValueError, match="program_name"):
            collect_verdicts(queue, {"chunk_000_N.json": {"proposals": [
                _link("1", "P1", program_name=bad)]}})


def test_collect_counts_an_invented_or_foreign_pe_as_refuted_and_never_raises():
    """A hallucinated code, a code borrowed from another org's index, an
    invented doc id and a name that PE does not own are CONTENT failures the
    refute lenses were meant to catch — they are counted, not raised, because a
    raise would block a 150-chunk collection on one bad row. None survives:
    load_announcement_links.py:289 would drop them anyway, so the damage they do
    is to wave4_result.json's 'surviving', which is the number Task 25b
    publishes."""
    queue = [_one_chunk(pairs=(("1", "P1"), ("2", "P2"), ("3", "P3"),
                               ("4", "P4"), ("5", "P5")))]
    verdicts = {"chunk_000_N.json": {"proposals": [
        _link("1", "P1"),                                        # a real index row
        _link("2", "P2", pe_bli="ZZZ9999"),                      # invented
        _link("3", "P3", pe_bli="0305205F"),                     # another org's index
        _link("4", "P4", lexicon_doc="999"),                     # invented doc id
        _link("5", "P5", program_name="Poseidon"),               # not a name of this PE
    ]}}
    packets, result = collect_verdicts(queue, verdicts,
                                       indexes={"N": read_index_rows(INDEX_N)})
    assert [p["piid"] for p in packets] == ["P1"]
    assert result["invalid_pe_bli"] == 4
    assert result["proposed"] == 5            # every proposal is still counted
    assert len(result["surviving"]) == 1
    # an alias the index carries under the same PE is fine
    packets, _ = collect_verdicts(
        queue, {"chunk_000_N.json": {"proposals": [_link("1", "P1", program_name="mq-4c")]}},
        indexes={"N": read_index_rows(INDEX_N)})
    assert [p["program_name"] for p in packets] == ["mq-4c"]


def test_collect_does_not_attempt_a_verdict_file_with_no_proposals_list():
    """`{}` from a crashed lens must not read as an adjudicated dry chunk: it
    would both advance the run protocol's dry-round counter and overstate
    records_attempted, the scope figure Task 25b publishes."""
    queue = [_one_chunk("chunk_000_N.json"),
             _one_chunk("chunk_001_N.json", pairs=(("2", "P2"),)),
             _one_chunk("chunk_002_N.json", pairs=(("3", "P3"),))]
    verdicts = {"chunk_000_N.json": {},
                "chunk_001_N.json": {"proposals": "none of them"},
                "chunk_002_N.json": {"proposals": [_link("3", "P3")]}}
    packets, result = collect_verdicts(queue, verdicts,
                                       indexes={"N": read_index_rows(INDEX_N)})
    assert result["malformed_file"] == 2
    assert result["chunks_attempted"] == ["chunk_002_N.json"]
    assert result["records_attempted"] == 1
    assert [p["piid"] for p in packets] == ["P3"]


def test_collect_counts_a_non_dict_lens_as_malformed_rather_than_crashing():
    """A lens that answered a bare string used to raise AttributeError naming
    neither the chunk nor the pair."""
    queue = [_one_chunk(pairs=(("1", "P1"), ("2", "P2")))]
    verdicts = {"chunk_000_N.json": {"proposals": [
        _link("1", "P1", refute_a="not refuted"),
        _link("2", "P2", refute_b=["no"]),
    ]}}
    packets, result = collect_verdicts(queue, verdicts,
                                       indexes={"N": read_index_rows(INDEX_N)})
    assert packets == []
    assert result["malformed_lens"] == 2
    assert result["missing_lens"] == 0


def test_a_survivor_with_no_reason_says_so():
    """The reason is interpolated into the published rationale
    ("triage+adversarial refute survived — {reason}"); an empty one printed a
    bare semicolon."""
    queue = [_one_chunk()]
    verdicts = {"chunk_000_N.json": {"proposals": [_link(
        "1", "P1", refute_a={"refuted": False}, refute_b={"refuted": False})]}}
    _, result = collect_verdicts(queue, verdicts,
                                 indexes={"N": read_index_rows(INDEX_N)})
    assert result["surviving"] == [
        {"piid": "P1", "pe_bli": "0305220N", "reason": "(no reason given)"}]


# --- Task 25b riders (fix-round re-review, approved before running `collect`
# --- on the real wave4_verdicts/): five hardening fixes, each with its own
# --- red-first test below.

def test_collect_counts_a_non_dict_proposal_as_malformed_rather_than_crashing():
    """Rider 1: a malformed `proposals` LIST entry ([null], ["text"]) used to
    raise a bare AttributeError on `prop.get(...)` — aborting the whole
    collection over one bad row in one chunk, the same failure mode already
    fixed for a non-dict refute lens."""
    queue = [_one_chunk(pairs=(("1", "P1"), ("2", "P2")))]
    verdicts = {"chunk_000_N.json": {"proposals": [
        None, "not a proposal", _link("2", "P2"),
    ]}}
    packets, result = collect_verdicts(queue, verdicts,
                                       indexes={"N": read_index_rows(INDEX_N)})
    assert [p["piid"] for p in packets] == ["P2"]
    assert result["malformed_lens"] == 2
    assert result["proposed"] == 1            # only the real proposal counts


def test_a_non_string_reason_is_stringified_not_crashed_on():
    """Rider 2: `reason` is only ever interpolated into the published
    rationale, so a lens writing it as a number or list must be coerced with
    str(...) instead of raising AttributeError on a bare `.strip()`."""
    queue = [_one_chunk()]
    verdicts = {"chunk_000_N.json": {"proposals": [_link(
        "1", "P1", refute_a={"refuted": False, "reason": 12345},
        refute_b={"refuted": False})]}}
    _, result = collect_verdicts(queue, verdicts,
                                 indexes={"N": read_index_rows(INDEX_N)})
    assert result["surviving"] == [
        {"piid": "P1", "pe_bli": "0305220N", "reason": "12345"}]


def test_a_padded_pe_bli_is_stripped_everywhere_it_is_stored():
    """Rider 3: index_key() already strips pe_bli for the validity check, but
    the packet, the dedup pair key and the surviving row must publish the
    STRIPPED value too — a padded " 0305220N " otherwise validates, survives,
    and ships padded, so the loader (which keys on the raw string) drops it
    while wave4_result.json's 'surviving' still counts it."""
    queue = [_one_chunk()]
    verdicts = {"chunk_000_N.json": {"proposals": [
        _link("1", "P1", pe_bli=" 0305220N ")]}}
    packets, result = collect_verdicts(queue, verdicts,
                                       indexes={"N": read_index_rows(INDEX_N)})
    assert packets[0]["pe_bli"] == "0305220N"
    assert result["surviving"] == [
        {"piid": "P1", "pe_bli": "0305220N", "reason": "holds"}]


def test_cmd_collect_refuses_a_verdict_file_declaring_the_wrong_chunk_name(
        tmp_path, monkeypatch):
    """Rider 4: cmd_collect keys `verdicts` by the file's name on disk; if the
    file's own declared `chunk` field disagreed, a second such file would
    silently overwrite the first in that dict. The refusal that prevents this
    (mine_announcement_residue.py's cmd_collect) had no test — only
    collect_verdicts's separate 'unknown chunk' check did."""
    queue_dir = tmp_path / "wave4_queue"
    verdict_dir = tmp_path / "wave4_verdicts"
    queue_dir.mkdir()
    verdict_dir.mkdir()
    chunk = _one_chunk()
    (queue_dir / "chunk_000_N.json").write_text(json.dumps(
        {"chunk": chunk["file"], "org": chunk["org"], "records": chunk["records"]}))
    (verdict_dir / "chunk_000_N.json").write_text(json.dumps(
        {"chunk": "chunk_999_N.json", "proposals": []}))
    monkeypatch.setattr(mar, "QUEUE_DIR", queue_dir)
    monkeypatch.setattr(mar, "VERDICT_DIR", verdict_dir)
    monkeypatch.setattr(mar, "LEXICON_DIR", tmp_path / "wave4_lexicon")
    monkeypatch.setattr(mar, "PACKET_DIR", tmp_path / "wave4_chunks")
    monkeypatch.setattr(mar, "RESULT", tmp_path / "wave4_result.json")
    with pytest.raises(SystemExit, match="chunk_999_N.json"):
        cmd_collect()


def test_a_digit_string_record_index_is_coerced_to_int():
    """Rider 5: a lens sometimes writes record_index as the JSON string "1"
    rather than the integer 1 — the most plausible formatting slip a
    disambiguating lens can make. Before this fix it failed
    isinstance(index, int) and raised, aborting the whole collection over one
    string-vs-int slip."""
    queue = [{"file": "chunk_000_N.json", "org": "N", "announced_value": 2,
              "records": [
                  dict(_rec("7", "the award paragraph", ["P1"], [2]),
                       org="N", lake_piids=["P1"]),
                  dict(_rec("7", "the modification paragraph", ["P1"], [1]),
                       org="N", lake_piids=["P1"])]}]
    prop = _link("7", "P1", record_index="1")
    packets, _ = collect_verdicts(
        queue, {"chunk_000_N.json": {"proposals": [prop]}},
        indexes={"N": read_index_rows(INDEX_N)})
    assert packets[0]["announcement_excerpt"] == "the modification paragraph"


def test_a_non_digit_string_record_index_is_counted_not_raised():
    """Rider 5: a record_index that is a string but not a digit-string is
    content the refute lenses were meant to catch, not a protocol violation
    worth aborting a 150-chunk collection over."""
    queue = [{"file": "chunk_000_N.json", "org": "N", "announced_value": 2,
              "records": [
                  dict(_rec("7", "the award paragraph", ["P1"], [2]),
                       org="N", lake_piids=["P1"]),
                  dict(_rec("7", "the modification paragraph", ["P1"], [1]),
                       org="N", lake_piids=["P1"])]}]
    prop = _link("7", "P1", record_index="not-a-number")
    packets, result = collect_verdicts(
        queue, {"chunk_000_N.json": {"proposals": [prop]}},
        indexes={"N": read_index_rows(INDEX_N)})
    assert packets == []
    assert result["malformed_lens"] == 1
