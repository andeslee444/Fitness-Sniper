"""#110 (record half): the announcement path's recorded review outcomes are
backfilled into announcement_link_reviews (migration 018) — decided 2026-09-25
under the owner's delegation ("unrecorded review is not evidence") and refined
by the stage-1 follow-up ruling R-DEC-110 (2026-09-26): a wave 1-3 `surviving`
entry IS a recorded review (record_kind 'survivor_list', reviewer 'link',
adversarial 'upheld'); wave-4 proposals are 'verdict_pair' rows, INCLUDING the
reviewer's 'weak' / 'wrong' rejections (adversarial 'not_run'); wave 1-2
refutations_sample entries are 'refutation_sample' rows (adversarial 'refuted').

Fixtures only: the verdict and result files are written to tmp_path in the
shapes the wave collectors write, and the DB tests run inside a transaction
that is rolled back.
"""
import json

import psycopg
import pytest

import backfill_announcement_link_reviews as bf  # scripts/ on sys.path

VERDICT_SRC = "data/research/announcements/wave4_verdicts/chunk_000_A.json"


def _prop(piid="P1", pe="PE1", article="A1", index=0, verdict="link",
          a=False, b=False):
    p = {"piid": piid, "pe_bli": pe, "article_id": article,
         "record_index": index, "verdict": verdict}
    if a is not None:
        p["refute_a"] = {"refuted": a, "reason": "lens a"}
    if b is not None:
        p["refute_b"] = {"refuted": b, "reason": "lens b"}
    return p


def _verdicts(tmp_path, files: dict):
    root = tmp_path
    d = root / "data" / "research" / "announcements" / "wave4_verdicts"
    d.mkdir(parents=True)
    for name, body in files.items():
        (d / name).write_text(json.dumps(body))
    return root, d


def _wave(tmp_path, n, *, surviving, packets, refutations=None):
    """wave<n>_result.json + wave<n>_chunks/chunk_000.json under the
    announcements dir the loader and the backfill both read."""
    ann = tmp_path / "data" / "research" / "announcements"
    (ann / f"wave{n}_chunks").mkdir(parents=True, exist_ok=True)
    body = {"triaged": len(packets), "verdict_counts": {"link": len(surviving)},
            "proposed": len(surviving), "surviving": surviving}
    if refutations is not None:
        body["refutations_sample"] = refutations
    (ann / f"wave{n}_result.json").write_text(json.dumps(body))
    (ann / f"wave{n}_chunks" / "chunk_000.json").write_text(json.dumps(packets))
    return ann


# ── what a verdict file records ─────────────────────────────────────────────

@pytest.mark.parametrize(("a", "b", "expected"), [
    (False, False, ("upheld", 2)),
    (True, False, ("refuted", 1)),
    (False, True, ("refuted", 1)),
    (True, True, ("refuted", 0)),
    (False, None, ("incomplete", 1)),   # neither an uphold nor a refutation (R-DEC-INCOMPLETE)
    (None, True, ("refuted", 0)),
    ("false", False, ("incomplete", 1)),  # not a JSON boolean: cleared nothing
])
def test_lens_outcome(a, b, expected):
    lens_a = None if a is None else {"refuted": a}
    lens_b = None if b is None else {"refuted": b}
    assert bf.lens_outcome(lens_a, lens_b) == expected


def test_no_lens_at_all_is_no_adversarial_record():
    assert bf.lens_outcome(None, None) is None
    assert bf.lens_outcome({}, {"reason": "no verdict key"}) is None


def test_every_wave4_proposal_becomes_a_verdict_pair_record(tmp_path):
    """R-DEC-110: the reviewer's rejections are recorded too — 'weak' and
    'wrong' never reached the lenses, so their adversarial verdict is
    'not_run' (and so is a 'link' no lens answered). A malformed file, a
    non-object and an unknown verdict are counted, never guessed."""
    root, d = _verdicts(tmp_path, {
        "chunk_000_A.json": {"chunk": "chunk_000_A.json", "proposals": [
            _prop("P1", "PE1", "A1", 3),                          # upheld
            _prop("P2", "PE2", "A2", 4, a=True),                  # refuted
            _prop("P3", "PE3", "A3", 5, verdict="weak", a=None, b=None),
            _prop("P4", "PE4", "A4", 6, verdict="wrong", a=None, b=None),
            _prop("P5", "PE5", "A5", 7, a=None, b=None),          # link, no lens
            "not a proposal",
            _prop("P7", "PE7", "A7", 9, verdict="maybe", a=None, b=None),
        ]},
        "chunk_001_F.json": {},                                   # crashed lens: no list
    })
    records, counts = bf.read_verdict_files(d, root)
    got = [(r.piid, r.record_kind, r.reviewer_verdict, r.adversarial_verdict,
            r.lenses_passed, r.article_id, r.article_source, r.record_index,
            r.entry_index, r.reason) for r in records]
    assert got == [
        ("P1", "verdict_pair", "link", "upheld", 2, "A1", "verdict_file", 3, 0, None),
        ("P2", "verdict_pair", "link", "refuted", 1, "A2", "verdict_file", 4, 1, None),
        ("P3", "verdict_pair", "weak", "not_run", None, "A3", "verdict_file", 5, 2, None),
        ("P4", "verdict_pair", "wrong", "not_run", None, "A4", "verdict_file", 6, 3, None),
        ("P5", "verdict_pair", "link", "not_run", None, "A5", "verdict_file", 7, 4, None),
    ]
    assert {r.source_file for r in records} == {VERDICT_SRC}
    assert counts["recorded"] == 5
    assert counts["rejection"] == 2
    assert counts["link_without_lens"] == 1
    assert counts["invalid_verdict"] == 1
    assert counts["malformed_file"] == 1
    assert counts["not_a_proposal"] == 1


def test_pe_bli_is_stripped_like_the_collector_strips_it(tmp_path):
    root, d = _verdicts(tmp_path, {"chunk_000_A.json": {"proposals": [
        _prop("P1", " PE1 ", "A1", 0)]}})
    records, _ = bf.read_verdict_files(d, root)
    assert records[0].pe_bli == "PE1"


def test_a_proposal_without_an_integer_record_index_is_counted_not_guessed(tmp_path):
    root, d = _verdicts(tmp_path, {"chunk_000_A.json": {"proposals": [
        _prop("P1", "PE1", "A1", None), _prop("P2", "PE2", "A2", "7")]}})
    records, counts = bf.read_verdict_files(d, root)
    assert [r.piid for r in records] == ["P2"]      # "7" is the collector's own coercion
    assert records[0].record_index == 7
    assert records[0].entry_index == 1              # its place in the file's list
    assert counts["no_record_index"] == 1


# ── what a wave 1-3 result file records (R-DEC-110) ────────────────────────

def test_surviving_entries_are_survivor_list_records_with_the_waves_packet(tmp_path):
    """A `surviving` entry records the reviewer's 'link' AND survival of the
    refuter: reviewer 'link', adversarial 'upheld', the entry's reason kept.
    The entry names no article; the one packet that wave triaged for the pair
    does (article_source 'wave_packet')."""
    ann = _wave(tmp_path, 1,
                surviving=[{"piid": "P1", "pe_bli": "PE1", "reason": "owns it"},
                           {"piid": "P2", "pe_bli": "PE2", "reason": "r2"}],
                packets=[{"piid": "P1", "pe_bli": "PE1", "article_id": "A1"},
                         {"piid": "P2", "pe_bli": "PE2", "article_id": "A2"},
                         {"piid": "P9", "pe_bli": "PE9", "article_id": "A9"}],
                refutations=[])
    records, counts = bf.read_result_files(ann, tmp_path, waves=(1,))
    got = [(r.piid, r.record_kind, r.reviewer_verdict, r.adversarial_verdict,
            r.lenses_passed, r.article_id, r.article_source, r.record_index,
            r.entry_index, r.reason, r.source_file) for r in records]
    assert got == [
        ("P1", "survivor_list", "link", "upheld", None, "A1", "wave_packet", None, 0,
         "owns it", "data/research/announcements/wave1_result.json"),
        ("P2", "survivor_list", "link", "upheld", None, "A2", "wave_packet", None, 1,
         "r2", "data/research/announcements/wave1_result.json"),
    ]
    assert counts["survivor_list"] == 2


def test_refutations_sample_entries_are_refutation_sample_records(tmp_path):
    ann = _wave(tmp_path, 2,
                surviving=[],
                packets=[{"piid": "P3", "pe_bli": "PE3", "article_id": "A3"}],
                refutations=[
                    {"piid": "P3", "pe_bli": "PE3", "refuted": True, "reason": "O&M"},
                    {"piid": "P4", "pe_bli": "PE4", "refuted": "yes", "reason": "?"},
                ])
    records, counts = bf.read_result_files(ann, tmp_path, waves=(2,))
    assert [(r.piid, r.record_kind, r.reviewer_verdict, r.adversarial_verdict,
             r.article_id, r.article_source, r.entry_index, r.reason)
            for r in records] == [
        ("P3", "refutation_sample", "link", "refuted", "A3", "wave_packet", 0, "O&M"),
    ]
    assert counts["refutation_sample"] == 1
    assert counts["refutation_not_true"] == 1       # never read as a refutation


@pytest.mark.parametrize(("packets", "count_key"), [
    ([], "no_packet"),
    ([{"piid": "P1", "pe_bli": "PE1", "article_id": "None",
       "subaward_number": "S1"}], "packet_without_article"),   # wave-3 subaward packet
    ([{"piid": "P1", "pe_bli": "PE1", "article_id": "A1"},
      {"piid": "P1", "pe_bli": "PE1", "article_id": "A2"}], "ambiguous_packet"),
])
def test_a_survivor_whose_article_is_not_determined_records_none(
    tmp_path, packets, count_key,
):
    ann = _wave(tmp_path, 3, packets=packets,
                surviving=[{"piid": "P1", "pe_bli": "PE1", "reason": "r"}])
    records, counts = bf.read_result_files(ann, tmp_path, waves=(3,))
    assert [(r.article_id, r.article_source) for r in records] == [(None, None)]
    assert counts[count_key] == 1


def test_a_missing_wave_result_or_chunks_dir_is_refused(tmp_path):
    """A wave file that is not there must stop the run, not shrink it: every
    survivor it held would publish at medium as 'unrecorded'."""
    ann = tmp_path / "data" / "research" / "announcements"
    ann.mkdir(parents=True)
    with pytest.raises(SystemExit, match="wave1_result.json"):
        bf.read_result_files(ann, tmp_path, waves=(1,))
    (ann / "wave1_result.json").write_text(json.dumps({"surviving": []}))
    with pytest.raises(SystemExit, match="wave1_chunks"):
        bf.read_result_files(ann, tmp_path, waves=(1,))


# ── attaching records to the pair's links ──────────────────────────────────

def _rec(piid="P1", pe="PE1", kind="verdict_pair", reviewer="link", adv="upheld",
         lenses=2, article="A1", index=0, entry=0, reason=None, src=VERDICT_SRC):
    source = None if article is None else (
        "verdict_file" if kind == "verdict_pair" else "wave_packet")
    return bf.ReviewRecord(piid, pe, kind, reviewer, adv, lenses, article, source,
                           index if kind == "verdict_pair" else None, entry,
                           reason, src)


def test_records_attach_to_every_row_of_the_pair():
    links = {("P1", "PE1"): [("P-1", 2026), ("R-1", 2025)]}
    cited = {("P1", "PE1"): {"A1"}}
    rows, counts = bf.review_rows(
        [_rec(), _rec(article="A9", index=4, entry=1, adv="refuted", lenses=1),
         _rec(piid="P2")], links, cited)
    assert rows == [
        ("P1", "PE1", "P-1", 2026, "verdict_pair", "link", "upheld", 2, True,
         "A1", "verdict_file", 0, 0, True, None, None, VERDICT_SRC),
        ("P1", "PE1", "R-1", 2025, "verdict_pair", "link", "upheld", 2, True,
         "A1", "verdict_file", 0, 0, True, None, None, VERDICT_SRC),
        ("P1", "PE1", "P-1", 2026, "verdict_pair", "link", "refuted", 1, False,
         "A9", "verdict_file", 4, 1, False, None, None, VERDICT_SRC),
        ("P1", "PE1", "R-1", 2025, "verdict_pair", "link", "refuted", 1, False,
         "A9", "verdict_file", 4, 1, False, None, None, VERDICT_SRC),
    ]
    assert counts["no_link"] == 1
    assert tuple(bf.COLUMNS[:4]) == ("award_piid", "pe_bli", "exhibit", "fiscal_year")


def test_a_record_with_no_article_has_no_cites_verdict():
    rows, _ = bf.review_rows(
        [_rec(kind="survivor_list", lenses=None, article=None, reason="r",
              src="data/research/announcements/wave3_result.json")],
        {("P1", "PE1"): [("R-1", 2026)]}, {("P1", "PE1"): {"A1"}})
    row = dict(zip(bf.COLUMNS, rows[0]))
    assert (row["article_id"], row["article_source"],
            row["cites_reviewed_article"]) == (None, None, None)


def test_coverage_splits_the_links_by_upholding_kind_and_cited_rejection():
    W1 = "data/research/announcements/wave1_result.json"
    records = [
        _rec("P1"),                                                  # pair only
        _rec("P2", kind="survivor_list", lenses=None, src=W1),       # list only
        _rec("P3"), _rec("P3", kind="survivor_list", lenses=None, src=W1),  # both
        _rec("P4"), _rec("P4", reviewer="weak", adv="not_run", lenses=None,
                         entry=1),                                   # rejected, cited
        _rec("P5"), _rec("P5", adv="refuted", lenses=1, article="A5", entry=1),
        _rec("P6", adv="refuted", lenses=0, article="A9"),           # refuted elsewhere
        _rec("P7", reviewer="wrong", adv="not_run", lenses=None),    # rejected, cited
        _rec("P8", adv="not_run", lenses=None),                      # link, no lens
        _rec("P10", adv="incomplete", lenses=1),                     # incomplete, cited
        _rec("P11"), _rec("P11", adv="incomplete", lenses=1, entry=1),  # upheld + incomplete
    ]
    ids = [f"P{i}" for i in range(1, 12)]
    links = {(p, "PE1"): [("R-1", 2026)] for p in ids}
    cited = {(p, "PE1"): {"A1"} for p in ids}
    cited[("P5", "PE1")] = {"A5"}
    rows, _ = bf.review_rows(records, links, cited)
    published = [(p, "PE1", "R-1", 2026) for p in ids]
    assert bf.coverage(rows, published) == {
        "total": 11,
        "upheld: verdict_pair only": 4,      # P1, P4, P5, P11
        "upheld: survivor_list only": 1,     # P2
        "upheld: both kinds": 1,             # P3
        "no upholding record": 5,            # P6, P7, P8, P9, P10
        "refuted on the cited article": 1,   # P5 (the card cites A5); never P10/P11
        "rejected on the cited article": 2,  # P4, P7
        "contrary record naming no article": 0,
        "no record at all": 1,               # P9
        "rule: stays high": 4,               # P1, P2, P3, P11 (incomplete never binds)
        "rule: review_refuted": 2,           # P5 (cited), P6 (no uphold, refuted)
        "rule: reviewer_rejected": 2,        # P4 (cited), P7
        "rule: review_incomplete": 2,        # P8 (lenses never ran), P10 (incomplete)
        "rule: review_unrecorded": 1,        # P9: no record at all
    }


# ── R-DEC-INCOMPLETE: one rule, the mart's ─────────────────────────────────

def _outcome(records, cited=frozenset({"A1"})):
    rows, _ = bf.review_rows(records, {("P1", "PE1"): [("R-1", 2026)]},
                             {("P1", "PE1"): set(cited)})
    return bf.rule_outcome(bf.classify(rows))


@pytest.mark.parametrize(("records", "expected"), [
    # an 'incomplete' read of the CITED article never binds as a refutation
    ([_rec(), _rec(adv="incomplete", lenses=1, entry=1)], "stays high"),
    ([_rec(kind="survivor_list", lenses=None,
           src="data/research/announcements/wave1_result.json"),
      _rec(adv="incomplete", lenses=0, entry=1)], "stays high"),
    # alone it demotes, with its own reason — never 'refuted'
    ([_rec(adv="incomplete", lenses=1)], "review_incomplete"),
    ([_rec(adv="incomplete", lenses=1), _rec(adv="not_run", lenses=None,
                                             entry=1)], "review_incomplete"),
    # a 'link' no lens answered decides nothing either
    ([_rec(adv="not_run", lenses=None)], "review_incomplete"),
    # no record at all is the only 'unrecorded'
    ([], "review_unrecorded"),
    # with no uphold, a real refutation / rejection anywhere still decides
    ([_rec(adv="incomplete", lenses=1),
      _rec(adv="refuted", lenses=0, article="A9", entry=1)], "review_refuted"),
    ([_rec(adv="incomplete", lenses=1),
      _rec(reviewer="weak", adv="not_run", lenses=None, article="A9",
           entry=1)], "reviewer_rejected"),
    # and an upheld link with a real refutation of its cited article demotes
    ([_rec(), _rec(adv="incomplete", lenses=1, entry=1),
      _rec(adv="refuted", lenses=1, entry=2)], "review_refuted"),
])
def test_incomplete_is_neither_an_uphold_nor_a_refutation(records, expected):
    """R-DEC-INCOMPLETE (fix-round ruling, 2026-09-26): an 'incomplete'
    adversarial record is neither an uphold nor a refutation; alone it demotes
    with 'announcement_review_incomplete'; it never binds as a refutation of a
    cited article. classify() follows the mart (audit_link_grading)."""
    assert _outcome(records) == expected


def test_a_contrary_record_naming_no_article_binds_to_the_pair():
    """The mart binds a rejection / refutation that names no article to the
    pair ('read against the card, never wider'); classify() does the same."""
    W1 = "data/research/announcements/wave1_result.json"
    records = [_rec(), _rec(kind="refutation_sample", adv="refuted", lenses=None,
                            article=None, reason="O&M", entry=1, src=W1)]
    assert _outcome(records) == "review_refuted"
    rows, _ = bf.review_rows(records, {("P1", "PE1"): [("R-1", 2026)]},
                             {("P1", "PE1"): {"A1"}})
    got = bf.coverage(rows, [("P1", "PE1", "R-1", 2026)])
    assert got["refuted on the cited article"] == 0
    assert got["contrary record naming no article"] == 1
    assert got["rule: review_refuted"] == 1


_MODEL = (bf.ROOT / "dbt" / "models" / "audit" / "audit_link_grading.sql")


def _mart_reasons(rows, piids):
    """Run the COMMITTED audit_link_grading.sql over `rows` exactly as
    `jbooks export-facts` exports them (every column varchar; None -> NULL,
    else str()) and return piid -> demotion_reason for unadjudicated
    announcement+lexicon/high links (R-1, FY2026, PE1)."""
    duckdb = pytest.importorskip("duckdb")
    sql = _MODEL.read_text()
    for src, table in {
        "{{ source('lake', 'jbook_awards') }}": "awards",
        "{{ source('lake', 'jbook_award_adjudications') }}": "adjudications",
        "{{ source('lake', 'jbook_announcement_link_reviews') }}": "reviews",
    }.items():
        sql = sql.replace(src, table)
    assert "{{" not in sql
    con = duckdb.connect()
    try:
        con.execute(
            "create table awards (pe_bli varchar, exhibit varchar,"
            " fiscal_year varchar, organization varchar, award_piid varchar,"
            " recipient_name varchar, recipient_uei varchar, method varchar,"
            " account varchar, confidence varchar)")
        con.execute(
            "create table adjudications (award_piid varchar, pe_bli varchar,"
            " adjudicated_confidence varchar, award_verdict varchar,"
            " pair_reason varchar, basis varchar, refuter_lenses_passed varchar)")
        con.execute("create table reviews ("
                    + ", ".join(f"{c} varchar" for c in bf.COLUMNS) + ")")
        for piid in piids:
            con.execute(
                "insert into awards values ('PE1', 'R-1', '2026', 'N', ?, 'X',"
                " 'U', 'announcement+lexicon', '1810', 'high')", [piid])
        for row in rows:
            con.execute(
                f"insert into reviews values ({', '.join(['?'] * len(bf.COLUMNS))})",
                [None if v is None else str(v) for v in row])
        got = dict(con.execute(
            f"select award_piid, demotion_reason from ({sql})").fetchall())
    finally:
        con.close()
    assert set(got) == set(piids)
    return got


def test_classify_matches_the_mart_on_every_record_shape():
    """Parity (R-DEC-INCOMPLETE: "one rule, stated once"): for every shape a
    link's records can take, the backfill's measurement and the committed
    mart give the same outcome and the same reason."""
    W1 = "data/research/announcements/wave1_result.json"
    ups = dict(kind="survivor_list", lenses=None, src=W1)
    cases = {
        "UP_PAIR": [_rec("UP_PAIR")],
        "UP_LIST": [_rec("UP_LIST", **ups)],
        "UP_INCOMPLETE_CITED": [_rec("UP_INCOMPLETE_CITED"),
                                _rec("UP_INCOMPLETE_CITED", adv="incomplete",
                                     lenses=1, entry=1)],
        "INCOMPLETE": [_rec("INCOMPLETE", adv="incomplete", lenses=0)],
        "NOT_RUN": [_rec("NOT_RUN", adv="not_run", lenses=None)],
        "NONE": [],
        "UP_REFUTED_CITED": [_rec("UP_REFUTED_CITED"),
                             _rec("UP_REFUTED_CITED", adv="refuted", lenses=1,
                                  entry=1)],
        "UP_WEAK_CITED": [_rec("UP_WEAK_CITED", **ups),
                          _rec("UP_WEAK_CITED", reviewer="weak", adv="not_run",
                               lenses=None)],
        "UP_REFUTED_OTHER": [_rec("UP_REFUTED_OTHER"),
                             _rec("UP_REFUTED_OTHER", adv="refuted", lenses=0,
                                  article="A9", entry=1)],
        "UP_WRONG_OTHER": [_rec("UP_WRONG_OTHER"),
                           _rec("UP_WRONG_OTHER", reviewer="wrong",
                                adv="not_run", lenses=None, article="A9",
                                entry=1)],
        "REFUTED_OTHER": [_rec("REFUTED_OTHER", adv="refuted", lenses=1,
                               article="A9")],
        "WEAK_OTHER_INCOMPLETE": [
            _rec("WEAK_OTHER_INCOMPLETE", reviewer="weak", adv="not_run",
                 lenses=None, article="A9"),
            _rec("WEAK_OTHER_INCOMPLETE", adv="incomplete", lenses=1, entry=1)],
        "UP_SAMPLE_NO_ARTICLE": [
            _rec("UP_SAMPLE_NO_ARTICLE"),
            _rec("UP_SAMPLE_NO_ARTICLE", kind="refutation_sample", adv="refuted",
                 lenses=None, article=None, entry=1, src=W1)],
        "UP_LIST_NO_ARTICLE": [_rec("UP_LIST_NO_ARTICLE", article=None, **ups)],
        "REFUTED_AND_WEAK_CITED": [
            _rec("REFUTED_AND_WEAK_CITED", adv="refuted", lenses=1),
            _rec("REFUTED_AND_WEAK_CITED", reviewer="wrong", adv="not_run",
                 lenses=None, entry=1)],
    }
    records = [r for recs in cases.values() for r in recs]
    links = {(p, "PE1"): [("R-1", 2026)] for p in cases}
    cited = {(p, "PE1"): {"A1"} for p in cases}
    rows, _ = bf.review_rows(records, links, cited)
    mart = _mart_reasons(rows, list(cases))
    by_link: dict = {}
    for row in rows:
        by_link.setdefault(row[0], []).append(row)
    ours = {}
    for piid in cases:
        outcome = bf.rule_outcome(bf.classify(by_link.get(piid, [])))
        ours[piid] = None if outcome == "stays high" else f"announcement_{outcome}"
    assert ours == mart
    # the shapes the ruling names, spelled out
    assert mart["UP_INCOMPLETE_CITED"] is None
    assert mart["INCOMPLETE"] == "announcement_review_incomplete"
    assert mart["NONE"] == "announcement_review_unrecorded"


# ── the table ───────────────────────────────────────────────────────────────

@pytest.fixture()
def con(pg_dsn):
    with psycopg.connect(pg_dsn) as c:
        yield c
        c.rollback()


def _rows(records, links=None, cited=None):
    return bf.review_rows(records, links or {("P1", "PE1"): [("R-1", 2026)]},
                          cited or {("P1", "PE1"): {"A1"}})[0]


def test_write_reviews_rebuilds_the_table(con):
    W1 = "data/research/announcements/wave1_result.json"
    rows = _rows([_rec(), _rec(article="A2", index=1, entry=1, adv="refuted", lenses=1),
                  _rec(reviewer="weak", adv="not_run", lenses=None, entry=2),
                  _rec(kind="survivor_list", lenses=None, reason="r", src=W1),
                  _rec(kind="refutation_sample", adv="refuted", lenses=None,
                       article=None, reason="O&M", src=W1)])
    cur = con.cursor()
    assert bf.write_reviews(cur, rows) == (0, 5)
    assert bf.write_reviews(cur, rows[:1]) == (5, 1)       # a re-run replaces
    got = con.execute(
        f"select {', '.join(bf.COLUMNS)} from announcement_link_reviews").fetchall()
    assert got == [rows[0]]


@pytest.mark.parametrize("change", [
    {"upholds": True, "adversarial_verdict": "refuted",
     "adversarial_lenses_passed": 1},                       # upholds, but refuted
    {"reviewer_verdict": "weak", "upholds": False},         # a rejection that "ran" lenses
    {"record_kind": "survivor_list", "adversarial_verdict": "refuted",
     "upholds": False, "adversarial_lenses_passed": None,
     "record_index": None, "article_source": "wave_packet"},  # a survivor that was refuted
    {"article_source": None},                               # an article with no source
    {"adversarial_lenses_passed": None},                    # lenses ran but no count
    {"adversarial_verdict": "maybe", "upholds": False},     # outside the vocabulary
])
def test_the_table_refuses_a_row_that_contradicts_its_own_record(con, change):
    row = dict(zip(bf.COLUMNS, _rows([_rec()])[0]))
    row.update(change)
    with pytest.raises(psycopg.errors.CheckViolation):
        with con.transaction():
            bf.write_reviews(con.cursor(), [tuple(row[c] for c in bf.COLUMNS)])
