"""The packet a published announcement link cites must come from the wave in
which the pair SURVIVED (found 2026-09-25 while backfilling #110's review
record).

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
"""
import json

import load_announcement_links as lal  # scripts/ on sys.path (tests/conftest.py)


def _write_wave(ann, wave, packets, surviving):
    d = ann / f"{wave}_chunks"
    d.mkdir(parents=True)
    (d / "chunk_000.json").write_text(json.dumps(packets))
    (ann / f"{wave}_result.json").write_text(json.dumps(
        {"surviving": [{"piid": p, "pe_bli": b, "reason": "r"} for p, b in surviving]}))
    return ann / f"{wave}_result.json"


def _packet(piid, pe, article):
    return {"piid": piid, "pe_bli": pe, "article_id": article,
            "program_name": f"program of {article}", "lexicon_doc": "1"}


def test_a_pair_dropped_early_and_upheld_later_cites_the_upholding_packet(tmp_path):
    ann = tmp_path / "announcements"
    w1 = _write_wave(ann, "wave1", [_packet("P1", "PE1", "A-DROPPED")], [])
    w4 = _write_wave(ann, "wave4", [_packet("P1", "PE1", "A-UPHELD")], [("P1", "PE1")])
    prov = lal.provenance_packets(ann, [w1, w4])
    assert prov[("P1", "PE1")]["article_id"] == "A-UPHELD"


def test_a_pair_two_waves_both_upheld_keeps_the_earliest_survivor(tmp_path):
    """The pre-existing choice for a pair more than one wave produced is
    unchanged: the earliest wave's packet."""
    ann = tmp_path / "announcements"
    w1 = _write_wave(ann, "wave1", [_packet("P2", "PE2", "A-W1")], [("P2", "PE2")])
    w4 = _write_wave(ann, "wave4", [_packet("P2", "PE2", "A-W4")], [("P2", "PE2")])
    assert lal.provenance_packets(ann, [w1, w4])[("P2", "PE2")]["article_id"] == "A-W1"


def test_a_survivor_with_no_packet_in_its_own_wave_gets_none(tmp_path):
    """Never borrow a triaged-and-dropped packet from another wave: a link
    with no surviving packet publishes with no article (and so no
    announcement source row), exactly as a packet-less link always has."""
    ann = tmp_path / "announcements"
    w1 = _write_wave(ann, "wave1", [_packet("P3", "PE3", "A-DROPPED")], [])
    w2 = _write_wave(ann, "wave2", [], [("P3", "PE3")])
    assert ("P3", "PE3") not in lal.provenance_packets(ann, [w1, w2])


def test_only_the_waves_on_the_command_line_count_as_survivors(tmp_path):
    ann = tmp_path / "announcements"
    _write_wave(ann, "wave1", [_packet("P4", "PE4", "A-W1")], [("P4", "PE4")])
    w4 = _write_wave(ann, "wave4", [_packet("P4", "PE4", "A-W4")], [("P4", "PE4")])
    assert lal.provenance_packets(ann, [w4])[("P4", "PE4")]["article_id"] == "A-W4"


def test_a_result_file_with_no_chunk_directory_is_refused(tmp_path):
    """wave<N>_result.json is paired with wave<N>_chunks by name; a result
    file whose packets cannot be found must not publish packet-less links
    silently."""
    import pytest

    ann = tmp_path / "announcements"
    ann.mkdir()
    orphan = ann / "wave9_result.json"
    orphan.write_text(json.dumps({"surviving": [{"piid": "P", "pe_bli": "B"}]}))
    with pytest.raises(SystemExit, match="wave9_chunks"):
        lal.provenance_packets(ann, [orphan])
