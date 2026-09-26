"""The packet a published announcement link cites must come from a wave in
which the pair SURVIVED (found 2026-09-25 while backfilling #110's review
record) — and, when the pair survived in several waves, from the one whose
evidence is best (R-DEC-PACKET, fix-round-2 ruling 2026-09-26).

THE DEFECT. load_announcement_links.py built its provenance map by walking
every wave*_chunks directory in name order and keeping the FIRST packet per
(piid, pe_bli). Those directories hold every TRIAGED packet, not only the
survivors, so a pair wave 1 or 2 triaged and dropped but wave 4 upheld on a
different announcement published with the dropped wave's packet: its citation
card links the article the reviewers did not uphold, and its rationale pairs
that article's program name and match basis with wave 4's reason. Measured
read-only 2026-09-25: 10 published links — 9 of the 1,074 high announcement
links (7 from wave-2 packets, 2 from wave-1) and 1 subaward+lexicon link built
from a wave-3 packet for a pair only wave 4 upheld.

R-DEC-PACKET. The 2026-09-25 fix took the EARLIEST surviving wave's packet, so
N0002416C4202/2122 kept citing wave 2's article 655726 — which a wave-4
reviewer later judged 'weak' — although wave 4 upheld the pair, both lenses
passing, on 1197079. The ruling: a pair that survived in several waves cites
the best-evidenced article — a wave-4 verdict pair upheld > a later wave's
survivor packet > an earlier one — never an article a later review rejected or
refuted. When no surviving packet is clean, the earliest surviving packet is
kept (the pre-ruling choice) and the grading demotes the link.
"""
import json

import pytest

import backfill_announcement_link_reviews as bf  # scripts/ on sys.path
import load_announcement_links as lal  # scripts/ on sys.path (tests/conftest.py)


def _write_wave(ann, wave, packets, surviving, refutations=None):
    d = ann / f"{wave}_chunks"
    d.mkdir(parents=True)
    (d / "chunk_000.json").write_text(json.dumps(packets))
    body = {"surviving": [{"piid": p, "pe_bli": b, "reason": "r"} for p, b in surviving]}
    if refutations is not None:
        body["refutations_sample"] = [
            {"piid": p, "pe_bli": b, "refuted": True, "reason": "refuted"}
            for p, b in refutations]
    (ann / f"{wave}_result.json").write_text(json.dumps(body))
    return ann / f"{wave}_result.json"


def _verdicts(ann, proposals=()):
    """wave4_verdicts/chunk_000_N.json in the collector's shape (an empty
    directory when no proposal is given — a wave-4 run that judged nothing)."""
    d = ann / "wave4_verdicts"
    d.mkdir(parents=True, exist_ok=True)
    if proposals:
        (d / "chunk_000_N.json").write_text(json.dumps(
            {"chunk": "chunk_000_N.json", "proposals": list(proposals)}))
    return d


def _prop(piid, pe, article, verdict="link", a=False, b=False, index=0):
    p = {"piid": piid, "pe_bli": pe, "article_id": article,
         "record_index": index, "verdict": verdict}
    if a is not None:
        p["refute_a"] = {"refuted": a, "reason": "lens a"}
    if b is not None:
        p["refute_b"] = {"refuted": b, "reason": "lens b"}
    return p


def _packet(piid, pe, article):
    return {"piid": piid, "pe_bli": pe, "article_id": article,
            "program_name": f"program of {article}", "lexicon_doc": "1"}


def _ann(tmp_path):
    ann = tmp_path / "announcements"
    ann.mkdir()
    return ann


def test_a_pair_dropped_early_and_upheld_later_cites_the_upholding_packet(tmp_path):
    ann = _ann(tmp_path)
    _verdicts(ann)
    w1 = _write_wave(ann, "wave1", [_packet("P1", "PE1", "A-DROPPED")], [])
    w4 = _write_wave(ann, "wave4", [_packet("P1", "PE1", "A-UPHELD")], [("P1", "PE1")])
    prov = lal.provenance_packets(ann, [w1, w4])
    assert prov[("P1", "PE1")]["article_id"] == "A-UPHELD"


def test_n0002416c4202_shape_cites_the_article_wave4_upheld(tmp_path):
    """R-DEC-PACKET's named case: wave 2 survived the pair on 655726, wave 4
    rejected 655726 ('weak') and upheld the pair, both lenses passing, on
    1197079 (its own packet) and 2641085. The card cites 1197079, and the
    link carries no binding rejection any more (it stays high)."""
    ann = _ann(tmp_path)
    _verdicts(ann, [
        _prop("N0002416C4202", "2122", "655726", verdict="weak", a=None, b=None),
        _prop("N0002416C4202", "2122", "1197079", index=1),
        _prop("N0002416C4202", "2122", "2641085", index=2),
    ])
    pair = ("N0002416C4202", "2122")
    w2 = _write_wave(ann, "wave2", [_packet(*pair, "655726")], [pair])
    w4 = _write_wave(ann, "wave4", [_packet(*pair, "1197079")], [pair])
    stats: dict = {}
    prov = lal.provenance_packets(ann, [w2, w4], stats=stats)
    assert prov[pair]["article_id"] == "1197079"
    assert stats["verdict_upheld"] == 1
    assert stats["changed_from_earliest"] == 1
    assert stats["no_clean_article"] == 0

    # what the grading then reads: the wave-2 survivor entry and the two
    # wave-4 upholds hold it high; the 'weak' on 655726 no longer binds
    records = (bf.read_verdict_files(ann / "wave4_verdicts", tmp_path)[0]
               + bf.read_result_files(ann, tmp_path, waves=(2,))[0])
    rows, _ = bf.review_rows(records, {pair: [("P-1", 2026)]},
                             {pair: {prov[pair]["article_id"]}})
    c = bf.classify(rows)
    assert not c["rejected_binding"] and not c["refuted_binding"]
    assert bf.rule_outcome(c) == "stays high"


def test_a_verdict_upheld_article_beats_a_later_survivor_packet_with_none(tmp_path):
    """The first rank is the wave-4 verdict pair upheld — above wave order."""
    ann = _ann(tmp_path)
    _verdicts(ann, [_prop("P1", "PE1", "A-W1")])        # wave 4 upheld wave 1's article
    w1 = _write_wave(ann, "wave1", [_packet("P1", "PE1", "A-W1")], [("P1", "PE1")])
    w3 = _write_wave(ann, "wave3", [_packet("P1", "PE1", "A-W3")], [("P1", "PE1")])
    assert lal.provenance_packets(ann, [w1, w3])[("P1", "PE1")]["article_id"] == "A-W1"


def test_a_later_waves_survivor_packet_beats_an_earlier_one(tmp_path):
    """R-DEC-PACKET reverses the 2026-09-25 tie-break (earliest wave): with no
    verdict pair on either article, the LATER wave's survivor packet is
    cited."""
    ann = _ann(tmp_path)
    _verdicts(ann)
    w1 = _write_wave(ann, "wave1", [_packet("P2", "PE2", "A-W1")], [("P2", "PE2")])
    w2 = _write_wave(ann, "wave2", [_packet("P2", "PE2", "A-W2")], [("P2", "PE2")])
    stats: dict = {}
    prov = lal.provenance_packets(ann, [w1, w2], stats=stats)
    assert prov[("P2", "PE2")]["article_id"] == "A-W2"
    assert stats["later_survivor"] == 1 and stats["changed_from_earliest"] == 1


@pytest.mark.parametrize("contrary", [
    _prop("P3", "PE3", "A-W2", verdict="wrong", a=None, b=None),   # rejected
    _prop("P3", "PE3", "A-W2", a=True),                             # refuted
])
def test_never_an_article_a_later_review_rejected_or_refuted(tmp_path, contrary):
    ann = _ann(tmp_path)
    _verdicts(ann, [contrary])
    w1 = _write_wave(ann, "wave1", [_packet("P3", "PE3", "A-W1")], [("P3", "PE3")])
    w2 = _write_wave(ann, "wave2", [_packet("P3", "PE3", "A-W2")], [("P3", "PE3")])
    assert lal.provenance_packets(ann, [w1, w2])[("P3", "PE3")]["article_id"] == "A-W1"


def test_an_incomplete_read_neither_upholds_nor_excludes(tmp_path):
    """R-DEC-INCOMPLETE: an 'incomplete' adversarial read is neither an
    uphold nor a refutation — so it neither ranks an article first nor rules
    it out; wave order decides."""
    ann = _ann(tmp_path)
    _verdicts(ann, [_prop("P4", "PE4", "A-W1", b=None),      # incomplete on A-W1
                    _prop("P4", "PE4", "A-W2", b=None, index=1)])
    w1 = _write_wave(ann, "wave1", [_packet("P4", "PE4", "A-W1")], [("P4", "PE4")])
    w2 = _write_wave(ann, "wave2", [_packet("P4", "PE4", "A-W2")], [("P4", "PE4")])
    stats: dict = {}
    prov = lal.provenance_packets(ann, [w1, w2], stats=stats)
    assert prov[("P4", "PE4")]["article_id"] == "A-W2"
    assert stats["verdict_upheld"] == 0 and stats["no_clean_article"] == 0


def test_a_same_wave_contrary_rules_the_article_out_too(tmp_path):
    """A wave-4 packet whose article wave 4 ALSO rejected (the pair proposed
    from two paragraphs of one article, one upheld, one 'weak') is not clean:
    the grading would demote a card citing it, so a clean earlier survivor
    packet is cited instead."""
    ann = _ann(tmp_path)
    _verdicts(ann, [_prop("P5", "PE5", "A-W4"),
                    _prop("P5", "PE5", "A-W4", verdict="weak", a=None, b=None, index=1)])
    w2 = _write_wave(ann, "wave2", [_packet("P5", "PE5", "A-W2")], [("P5", "PE5")])
    w4 = _write_wave(ann, "wave4", [_packet("P5", "PE5", "A-W4")], [("P5", "PE5")])
    assert lal.provenance_packets(ann, [w2, w4])[("P5", "PE5")]["article_id"] == "A-W2"


def test_with_no_clean_article_the_old_choice_stands_and_the_grading_demotes(tmp_path):
    """The only surviving packet (wave 1's) was later rejected by a wave-4
    reviewer, and wave 4 upheld nothing for the pair: there is no clean
    article to cite. The loader keeps the pre-ruling choice (the earliest
    surviving packet — it never invents or borrows one), counts it, and the
    grading demotes the link: the rejection names the article its card
    cites, so it binds — 'reviewer_rejected', published at medium."""
    ann = _ann(tmp_path)
    _verdicts(ann, [_prop("P6", "PE6", "A-W1", verdict="weak", a=None, b=None)])
    w1 = _write_wave(ann, "wave1", [_packet("P6", "PE6", "A-W1")], [("P6", "PE6")])
    stats: dict = {}
    prov = lal.provenance_packets(ann, [w1], stats=stats)
    assert prov[("P6", "PE6")]["article_id"] == "A-W1"
    assert stats["no_clean_article"] == 1
    assert stats["no_clean_article_pairs"] == [("P6", "PE6")]

    pair = ("P6", "PE6")
    records = (bf.read_verdict_files(ann / "wave4_verdicts", tmp_path)[0]
               + bf.read_result_files(ann, tmp_path, waves=(1,))[0])
    rows, _ = bf.review_rows(records, {pair: [("P-1", 2026)]}, {pair: {"A-W1"}})
    assert bf.rule_outcome(bf.classify(rows)) == "reviewer_rejected"


def test_a_later_refutation_sample_counts_as_a_refutation(tmp_path):
    """A wave 1-2 `refutations_sample` entry is a recorded refutation of the
    article its wave's one packet names (the backfill's reading): wave 2
    refuted the article wave 1 survived the pair on, so it is not clean."""
    ann = _ann(tmp_path)
    _verdicts(ann)
    pair = ("P7", "PE7")
    w1 = _write_wave(ann, "wave1", [_packet(*pair, "A-W1")], [pair])
    w2 = _write_wave(ann, "wave2", [_packet(*pair, "A-W1")], [], refutations=[pair])
    stats: dict = {}
    prov = lal.provenance_packets(ann, [w1, w2], stats=stats)
    assert prov[pair]["article_id"] == "A-W1"      # nothing clean: the old choice
    assert stats["no_clean_article"] == 1


def test_a_survivor_with_no_packet_in_its_own_wave_gets_none(tmp_path):
    """Never borrow a triaged-and-dropped packet from another wave: a link
    with no surviving packet publishes with no article (and so no
    announcement source row), exactly as a packet-less link always has."""
    ann = _ann(tmp_path)
    _verdicts(ann)
    w1 = _write_wave(ann, "wave1", [_packet("P3", "PE3", "A-DROPPED")], [])
    w2 = _write_wave(ann, "wave2", [], [("P3", "PE3")])
    assert ("P3", "PE3") not in lal.provenance_packets(ann, [w1, w2])


def test_only_the_waves_on_the_command_line_count_as_survivors(tmp_path):
    ann = _ann(tmp_path)
    _verdicts(ann)
    _write_wave(ann, "wave1", [_packet("P4", "PE4", "A-W1")], [("P4", "PE4")])
    w4 = _write_wave(ann, "wave4", [_packet("P4", "PE4", "A-W4")], [("P4", "PE4")])
    assert lal.provenance_packets(ann, [w4])[("P4", "PE4")]["article_id"] == "A-W4"


def test_a_result_file_with_no_chunk_directory_is_refused(tmp_path):
    """wave<N>_result.json is paired with wave<N>_chunks by name; a result
    file whose packets cannot be found must not publish packet-less links
    silently."""
    ann = _ann(tmp_path)
    _verdicts(ann)
    orphan = ann / "wave9_result.json"
    orphan.write_text(json.dumps({"surviving": [{"piid": "P", "pe_bli": "B"}]}))
    with pytest.raises(SystemExit, match="wave9_chunks"):
        lal.provenance_packets(ann, [orphan])


def test_a_missing_verdict_directory_is_refused(tmp_path):
    """Without wave4_verdicts/ the choice cannot see which articles wave 4
    upheld or rejected — it would cite a rejected article silently."""
    ann = _ann(tmp_path)
    w1 = _write_wave(ann, "wave1", [_packet("P1", "PE1", "A-W1")], [("P1", "PE1")])
    with pytest.raises(SystemExit, match="wave4_verdicts"):
        lal.provenance_packets(ann, [w1])
