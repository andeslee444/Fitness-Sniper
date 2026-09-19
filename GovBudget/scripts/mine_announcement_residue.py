"""Wave 4 — the tail of the announcement LLM-alias pass (ROADMAP findings :118-119).

The 2026-09-01/02 legs matched defense.gov contract announcements to PE
program names two ways: deterministically (a lexicon name a J-book narrative
owns, verbatim) and, for the biggest unmatched records, with an LLM-assisted
alias pass that decoded designators and backronyms (PATRIOT -> PAC-3,
SEPv3 -> M1A2 SEP). That pass stopped at the top 3,840 unmatched records by
announced value and /methodology/ has disclosed the stop ever since.

This script queues the rest. It does NOT reproduce the historical residue
bit-for-bit: the selection code was never committed (grep 'llm_chunks' over
scripts/ src/ tests/ docs/ returns nothing), and every reconstruction of
"16,651 unmatched records" from records.jsonl + lexicon.jsonl comes out a
superset (28,344 under the rule below; 27,736 including 'mentioned' names;
24,118 as the complement of verification_queue.json's 9,369 PIIDs). ROADMAP
:100 records 22,140 parsed records for the same 2,786 digests that parse to
34,542 today, and the parser has one commit — so the raw HTML moved under the
old figures. The rule is therefore restated here, in code, and its own counts
are what /methodology/ publishes (Task 25b). What WAS reproduced: all 3,840
wave-2 LLM records map back to records.jsonl on (article_id, text[:200]), the
cut was amounts[0] descending at $63,206,673, and sum(amounts[0]) over them is
$1.9545e12 — the "$1.96T" on the page.

  queue   : records.jsonl + lexicon.jsonl + the lake -> wave4_queue/ chunks,
            wave4_lexicon/ per-org indexes, residue_manifest.json
  collect : wave4_queue/ + wave4_verdicts/ -> wave4_chunks/ (loader packets)
            + wave4_result.json

Acceptance rule (docs/superpowers/specs/2026-09-11-announcement-wave4-rubric.md):
proposed -> refute lens A -> refute lens B -> survive. Both lenses must return
refuted=false. A missing or unparseable lens verdict counts as REFUTED and is
reported, so a half-finished run can never read as a clean one.

Chunks are ranked by descending announced value and `collect` accepts a PARTIAL
set of verdict files, because the run protocol (ruling A10) adjudicates rounds
of 5 chunks and stops after 3 consecutive rounds return no survivors. A chunk
with no verdict file is neither surviving nor refuted: it was not attempted, and
records_attempted / chunks_attempted in wave4_result.json say exactly what ran.

Usage:
  uv run python scripts/mine_announcement_residue.py queue [--chunk-size 80]
  uv run python scripts/mine_announcement_residue.py collect
"""
import argparse
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "data" / "research" / "announcements"
RECORDS = ANN / "records.jsonl"
PARSE_STATS = ANN / "parse_stats.json"
LEXICON = ROOT / "data" / "research" / "lexicon" / "lexicon.jsonl"
QUEUE_DIR = ANN / "wave4_queue"
LEXICON_DIR = ANN / "wave4_lexicon"
VERDICT_DIR = ANN / "wave4_verdicts"
PACKET_DIR = ANN / "wave4_chunks"      # NB: matched by the link loader's wave*_chunks glob
MANIFEST = ANN / "residue_manifest.json"
QUEUE_MANIFEST = QUEUE_DIR / "queue_manifest.json"
RESULT = ANN / "wave4_result.json"
RUBRIC = "docs/superpowers/specs/2026-09-11-announcement-wave4-rubric.md"

#: defense.gov service headings -> the J-book org dim_programs uses. Mechanical,
#: not curated: a service with no loaded book (DEFENSE HEALTH AGENCY,
#: U.S. TRANSPORTATION COMMAND, DFAS) has no PEs to link to, so its records are
#: not queued at all rather than sent to an agent that can only answer "none".
SERVICE_ORG = {
    "ARMY": "A", "NAVY": "N", "MARINE CORPS": "N",
    "AIR FORCE": "F", "SPACE FORCE": "F",
    "MISSILE DEFENSE AGENCY": "MDA",
    "DEFENSE ADVANCED RESEARCH PROJECTS AGENCY": "DARPA",
    "U.S. SPECIAL OPERATIONS COMMAND": "SOCOM",
    "DEFENSE INFORMATION SYSTEMS AGENCY": "DISA",
    "DEFENSE THREAT REDUCTION AGENCY": "DTRA",
    "DEFENSE LOGISTICS AGENCY": "DLA",
    "WASHINGTON HEADQUARTERS SERVICES": "WHS",
    "DEFENSE COUNTERINTELLIGENCE AND SECURITY AGENCY": "DCSA",
    "DEFENSE SECURITY COOPERATION AGENCY": "DSCA",
    "DEFENSE HUMAN RESOURCES ACTIVITY": "DHRA",
    "U.S. CYBER COMMAND": "CYBERCOM",
    "THE JOINT STAFF": "TJS",
    "DEFENSE CONTRACT MANAGEMENT AGENCY": "DCMA",
}

#: The closed match_basis vocabulary an ANNOUNCEMENT link may carry. These five
#: are already in award_link_sources; 'subaward-description-exact' is
#: deliberately absent, because load_announcement_links.py:363-366 branches on
#: it to publish at subaward+lexicon/medium and skip the money-colour guard.
BASIS_VOCAB = frozenset({
    "exact-name", "designator-normalized", "llm-alias",
    "llm-designator-variant", "llm-description",
})

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9./&-]*")
_ENTITY = re.compile(r"&NBSP;|&AMP;", re.I)


def normalize_service(service: str | None) -> str:
    """'NAVY &NBSP;' -> 'NAVY'. The parser keeps the raw heading, entities and
    all; 870 of the 34,542 records carry '&NBSP;' (some without a leading
    space) and a heading may end in '*' or '.'."""
    s = _ENTITY.sub(" ", (service or "").upper())
    return re.sub(r"\s+", " ", s).strip(" .*")


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text or "")]


def build_name_index(entries) -> dict[int, set[tuple[str, ...]]]:
    """{token-count: {name token tuple}} for the names a PE's narrative OWNS.

    'mentioned' entries are excluded because the whole evidence chain is "the
    PE's own narrative owns this name"; weak_name entries are excluded because
    the waves excluded them (a record naming only a weak generic name is not a
    deterministic match and belongs in the residue, where an agent can judge
    it). 7,300 of lexicon.jsonl's 10,464 rows qualify, carrying 6,396 distinct
    names."""
    index: dict[int, set[tuple[str, ...]]] = defaultdict(set)
    for e in entries:
        if e.get("ownership") != "own" or e.get("weak_name"):
            continue
        name = e.get("name") or ""
        if len(name) < 3:
            continue
        toks = tuple(_tokens(name))
        if toks:
            index[len(toks)].add(toks)
    return dict(index)


def has_deterministic_match(text: str, name_index) -> bool:
    """True when some owned lexicon name appears in the text as a contiguous
    token n-gram (case-insensitive). This is the 'already covered' test; a
    record it returns True for was never LLM-pass material."""
    toks = _tokens(text)
    for length, names in name_index.items():
        for i in range(0, len(toks) - length + 1):
            if tuple(toks[i:i + length]) in names:
                return True
    return False


def record_key(rec: dict) -> tuple[str, str]:
    """The stable identity of a parsed RECORD: (article_id, text[:200]).
    Verified against the wave-2 input: all 3,840 llm_chunks entries resolve to
    a re-parsed record on this key (3,832 distinct; 8 duplicate paragraphs).
    Not defined for a loader PACKET, which carries announcement_excerpt."""
    return (str(rec.get("article_id")), (rec.get("text") or "")[:200])


INDEX_HEADER = "name\tpe_bli\tlexicon_doc\tprogram_title"


def reads_as_absent(value) -> bool:
    """True when a field would read as ABSENT to the loader's `_packet_value`
    (load_announcement_links.py:112-122): None, blank, or the literal strings
    'None'/'null' that an f-string leaves behind when it interpolates one."""
    s = str(value if value is not None else "").strip()
    return not s or s.lower() in {"none", "null"}


def lexicon_index_lines(owned, org, pe_orgs, pe_title) -> list[str]:
    """One org's index TSV — the file lens P proposes out of — header first.

    A lexicon row with no `doc_id` is OMITTED. Ruling A7 makes a proposal with
    no `lexicon_doc` unpublishable and the rubric tells the lens to copy this
    column verbatim, so such a row can only produce a packet whose published
    rationale reads "J-book narrative owns it (None)" — and, on an
    account-split key, a link dropped under skipped['collision_unresolved'].
    314 of the first build's 6,409 rows were that string."""
    lines = [INDEX_HEADER]
    for e in owned:
        if org not in pe_orgs.get(e["pe_bli"], ()):
            continue
        if reads_as_absent(e.get("doc_id")):
            continue
        lines.append(f"{e['name']}\t{e['pe_bli']}\t{e['doc_id']}\t"
                     f"{(pe_title.get(e['pe_bli']) or '')[:60]}")
    return lines


def index_key(name, pe_bli, lexicon_doc) -> tuple[str, str, str]:
    """The identity a proposal's (program_name, pe_bli, lexicon_doc) is checked
    by. The name compares case-insensitively — a lens that lowercased a copied
    name is not a hallucination — the code and the doc id do not."""
    return (str(name or "").strip().casefold(), str(pe_bli or "").strip(),
            str(lexicon_doc or "").strip())


def read_index_rows(text: str) -> set[tuple[str, str, str]]:
    """{(name, pe_bli, lexicon_doc)} of one org's index TSV. Mirrors
    lexicon_index_lines: the collector validates against exactly the file the
    lens read."""
    rows = set()
    for line in text.splitlines()[1:]:
        cols = line.split("\t")
        if len(cols) >= 3 and line.strip():
            rows.add(index_key(cols[0], cols[1], cols[2]))
    return rows


def announced_value(rec: dict) -> int:
    """The FIRST dollar figure in the paragraph — the announced value of the
    action. Not max(): the wave-2 cut was by amounts[0] (sum $1.9545e12, the
    '$1.96T' on /methodology/)."""
    amounts = rec.get("amounts") or []
    return int(amounts[0]) if amounts else 0


def earlier_pass_in_residue(residue, attempted) -> tuple[int, int]:
    """(records, announced value) of the EARLIER pass that are still residue.

    The earlier pass's own entry count is not a subset of today's residue and
    must never be added to one: 8 of its 3,840 entries are duplicate keys, and
    a record it attempted may since have gained a deterministic owned-name
    match, which drops it out of `records_residue` altogether. Both errors run
    the same way — they inflate `records_attempted` / `value_attempted`, which
    /methodology/ publishes as a share OF the residue, and shrink the
    unattempted tail. So: distinct residue keys the earlier pass attempted,
    and their announced value counted once per key.

    A key that appears twice in the residue with two different announced
    values keeps the SMALLER one: the figure is a numerator over the residue's
    value, and the smaller true number is the one that publishes.
    """
    value_by_key: dict[tuple[str, str], int] = {}
    for rec in residue:
        key = record_key(rec)
        value = announced_value(rec)
        value_by_key[key] = min(value_by_key.get(key, value), value)
    shared = set(value_by_key) & set(attempted)
    return len(shared), sum(value_by_key[k] for k in shared)


def select_residue(records, *, lake, name_index, attempted, orgs_with_lexicon):
    """(residue, queued) in ONE pass — see the module docstring for the rules.

    `residue` is rules 1-2 (a lake PIID, no owned-name match), each record
    annotated with its `lake_piids`; `queued` is the subset that also passes
    rules 3-4 (not already attempted, service maps to an org that has a
    lexicon), annotated with `org`. Both are returned because
    residue_manifest.json publishes the first and the queue is the second, and
    the owned-name scan is the expensive half — computing it twice doubles the
    command's runtime for nothing."""
    residue, kept = [], []
    for rec in records:
        piids = sorted({n["piid"] for n in rec.get("contract_numbers", [])
                        if n["piid"] in lake})
        if not piids:
            continue
        if has_deterministic_match(rec.get("text") or "", name_index):
            continue
        annotated = {**rec, "lake_piids": piids}
        residue.append(annotated)
        if record_key(rec) in attempted:
            continue
        org = SERVICE_ORG.get(normalize_service(rec.get("service")))
        if org is None or org not in orgs_with_lexicon:
            continue
        kept.append({**annotated, "org": org})
    return residue, kept


def chunk_records(records, size: int = 80):
    """Chunks grouped by org (one lexicon index per chunk), numbered globally by
    descending max announced value so the controller can stop at any chunk and
    what was skipped is the cheapest tail. 80 per chunk is the house size
    (llm_chunks and mine_lexicon_candidates.py both use it). Grouping by org
    means each org contributes a partial chunk: 23,824 records across 13 orgs
    is 306 chunks, not 298.

    Each chunk carries its `rank` — the same integer as its file name — because
    the run protocol (ruling A10) walks the chunks in rounds of 5 in exactly
    this order and has to be able to name the round it is on."""
    by_org: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_org[rec["org"]].append(rec)
    raw = []
    for org, recs in by_org.items():
        recs.sort(key=announced_value, reverse=True)
        for i in range(0, len(recs), size):
            group = recs[i:i + size]
            raw.append({"org": org, "records": group,
                        "announced_value": sum(announced_value(r) for r in group),
                        "top_value": announced_value(group[0])})
    raw.sort(key=lambda c: (-c["top_value"], c["org"]))
    for n, chunk in enumerate(raw):
        chunk["rank"] = n
        chunk["file"] = f"chunk_{n:03d}_{chunk['org']}.json"
        chunk.pop("top_value")
    return raw


def collect_verdicts(queue, verdicts, indexes=None):
    """(packets, result) from the queue, the returned adjudications and the
    per-org lexicon indexes the lenses proposed out of (`{org: read_index_rows}`;
    None skips the content check, which only the pure-function tests do).

    Acceptance: verdict == 'link' AND refute_a.refuted is False AND
    refute_b.refuted is False. Anything else — 'weak', 'wrong', a refutation,
    a lens that never ran, a malformed verdict — does not survive, and the
    counts say which. Raises ValueError ONLY on a verdict file naming a chunk
    this queue does not hold (the numbering is derived from the universe, so a
    re-queue renumbers everything; silently ignoring such a file would drop
    real adjudications) — a whole-run, file-level refusal, never a
    per-proposal one.

    EVERY per-proposal validation failure is COUNTED rather than raised,
    because each is content the refute lenses were meant to catch rather than
    a broken protocol, and a raise would block a whole 150-chunk collection on
    one bad row — which is exactly what happened live: the real run aborted on
    chunk_090_N.json, which swaps articles 1330165/962429 between records 31
    and 33 for N0017417C0022/N0003017C0002 (2 of the run's 1,086 `link`
    proposals; every other link resolved). Each failure records an example
    alongside its count — `<counter>_examples`, a list of
    `{chunk, piid, pe_bli, ...detail}` — because a basis, an index or a program
    name a citation card cannot word is the exact failure Task 25b's report
    discloses:

      invalid_verdict      — `verdict` is not one of 'link'/'weak'/'wrong'.
      invalid_record_index — `record_index` is not among the records of that
                              chunk holding the proposal's (article_id, PIID)
                              pair — the chunk_090 shape: the index names a
                              record of the chunk, just not the right one.
      unknown_article_piid — the (article_id, PIID) pair is not a lake PIID of
                              any record in that chunk.
      ambiguous_record     — the pair names more than one record of the chunk
                              (a modification paragraph citing the vehicle its
                              award paragraph announced) and the proposal
                              carries no usable `record_index` to say which.
      missing_pe_bli       — `pe_bli` is missing or blank; there is nothing to
                              link the award to. Distinct from `invalid_pe_bli`
                              below, which is a PRESENT but wrong code.
      invalid_match_basis  — a `link` proposal whose `match_basis` is missing
                              or outside BASIS_VOCAB (the proposer only records
                              a basis for `link` verdicts, so `weak`/`wrong`
                              proposals are never checked for one at all).
      missing_lexicon_doc  — `lexicon_doc` is absent or reads as absent to the
                              loader's `_packet_value` (''/'none'/'null', any
                              case, or whitespace-only); a shared BLI code
                              cannot be resolved without it.
      missing_program_name — `program_name` is absent or reads as absent; the
                              published rationale words it ("program 'None'
                              named for this award").
      invalid_pe_bli       — a (program_name, pe_bli, lexicon_doc) triple that
                              is not a row of that org's index: an invented
                              code, another org's code, an invented doc id or a
                              name that PE does not own. load_announcement_
                              links.py:289 drops them anyway, so the harm is to
                              the 'surviving' count Task 25b publishes.
      malformed_file        — a verdict file carrying no `proposals` LIST; the
                              chunk is NOT attempted, so a crashed lens cannot
                              read as an adjudicated dry chunk.

    A skipped proposal — any counter above — is dropped from `packets` and
    from `surviving`, exactly like a refuted one; the printed summary and
    wave4_result.json's counts say how many and why.

    A chunk with no verdict file is skipped, not failed: the run protocol stops
    when three consecutive rounds return nothing, and `records_attempted` /
    `chunks_attempted` describe what actually came back."""
    by_file = {chunk["file"]: chunk for chunk in queue}
    unknown = sorted(set(verdicts) - set(by_file))
    if unknown:
        raise ValueError(
            f"verdict file(s) {unknown} name chunks the queue does not hold; "
            f"re-run `queue` only when no verdicts are outstanding, because the "
            f"chunk numbering is derived from the universe")
    counts = {"link": 0, "weak": 0, "wrong": 0}
    refuted_a = refuted_b = missing_lens = malformed_lens = duplicate_pairs = 0
    invalid_pe_bli = malformed_file = invalid_match_basis = 0
    invalid_verdict = invalid_record_index = unknown_article_piid = 0
    ambiguous_record = missing_pe_bli = missing_lexicon_doc = 0
    missing_program_name = 0
    packets, surviving, attempted_files = [], [], []
    invalid_match_basis_examples = []
    invalid_verdict_examples = []
    invalid_record_index_examples = []
    unknown_article_piid_examples = []
    ambiguous_record_examples = []
    missing_pe_bli_examples = []
    missing_lexicon_doc_examples = []
    missing_program_name_examples = []
    records_attempted = 0
    seen_pairs: set[tuple[str, str]] = set()
    for chunk in queue:
        returned = verdicts.get(chunk["file"])
        if returned is None:
            continue
        if not isinstance(returned.get("proposals"), list):
            # a crashed lens leaves {} behind; counting that as an adjudicated
            # dry chunk would both advance the run protocol's dry-round counter
            # and overstate records_attempted
            malformed_file += 1
            continue
        attempted_files.append(chunk["file"])
        records = chunk["records"]
        records_attempted += len(records)
        # A record is identified by (article_id, PIID), not by article_id: a
        # daily digest is one article with many paragraphs, and 1,766 of the
        # 23,824 queued records (7.4%) share an article_id with another record
        # in the same chunk. Keying on article_id alone would hand the packet
        # the WRONG paragraph's date, contractor and excerpt — the citation
        # card would quote a different award.
        by_pair: dict[tuple[str, str], list[int]] = defaultdict(list)
        for i, r in enumerate(records):
            for piid in r["lake_piids"]:
                by_pair[(str(r["article_id"]), piid)].append(i)
        for prop in returned.get("proposals", []):
            if not isinstance(prop, dict):
                # a malformed list entry ([null], ["text"]) used to raise a
                # bare AttributeError on prop.get(...); counted alongside the
                # other malformed-content failures instead
                malformed_lens += 1
                continue
            verdict = prop.get("verdict")
            if verdict not in counts:
                # an unrecognized verdict is content a broken lens produced,
                # not a protocol violation — counted and skipped rather than
                # aborting a 150-chunk collection over one bad row
                invalid_verdict += 1
                invalid_verdict_examples.append({
                    "chunk": chunk["file"], "piid": prop.get("piid"),
                    "pe_bli": prop.get("pe_bli"), "verdict": verdict,
                })
                continue
            counts[verdict] += 1
            if verdict != "link":
                continue
            aid, piid = str(prop.get("article_id")), prop.get("piid")
            found = by_pair.get((aid, piid), [])
            index = prop.get("record_index")
            if isinstance(index, str):
                stripped_index = index.strip()
                if stripped_index.isdigit():
                    # the most plausible lens slip: JSON "12" instead of 12
                    index = int(stripped_index)
                else:
                    # a non-numeric string is content the refute lenses were
                    # meant to catch, not a protocol violation worth aborting
                    # a 150-chunk collection over
                    malformed_lens += 1
                    continue
            if index is not None:
                if not isinstance(index, int) or index not in found:
                    # the chunk_090_N.json shape: record_index names a record
                    # of this chunk, just not one holding this (article_id,
                    # PIID) pair — counted, never raised, so one swapped index
                    # cannot abort the whole 150-chunk collection
                    invalid_record_index += 1
                    invalid_record_index_examples.append({
                        "chunk": chunk["file"], "piid": piid,
                        "pe_bli": prop.get("pe_bli"), "article_id": aid,
                        "record_index": index, "candidates": found,
                    })
                    continue
            elif not found:
                # the pair names no record of this chunk at all
                unknown_article_piid += 1
                unknown_article_piid_examples.append({
                    "chunk": chunk["file"], "piid": piid,
                    "pe_bli": prop.get("pe_bli"), "article_id": aid,
                })
                continue
            elif len(found) > 1:
                # 17 of the queue's 31,693 (article_id, PIID) keys, across 16
                # chunks: a modification paragraph naming the same vehicle as
                # its award paragraph. The excerpt would be a coin flip
                # without a record_index to say which paragraph it read.
                ambiguous_record += 1
                ambiguous_record_examples.append({
                    "chunk": chunk["file"], "piid": piid,
                    "pe_bli": prop.get("pe_bli"), "article_id": aid,
                    "candidates": found,
                })
                continue
            else:
                index = found[0]
            rec = records[index]
            # compared AND stored stripped everywhere below: a padded
            # " 0305220N " must not validate as a different key from the
            # index's "0305220N", nor survive and publish padded while the
            # loader (which keys on the raw string) drops it
            pe_bli = str(prop.get("pe_bli") or "").strip()
            if not pe_bli:
                # missing/blank, not a wrong-but-present code (invalid_pe_bli
                # below): there is nothing to link the award to
                missing_pe_bli += 1
                missing_pe_bli_examples.append({
                    "chunk": chunk["file"], "piid": piid,
                    "pe_bli": prop.get("pe_bli"), "article_id": aid,
                })
                continue
            basis = prop.get("match_basis")
            if basis not in BASIS_VOCAB:
                # content the refute lenses were meant to catch, not a broken
                # protocol — counted and skipped, never raised, so one bad
                # basis cannot abort a 150-chunk collection (see docstring)
                invalid_match_basis += 1
                invalid_match_basis_examples.append({
                    "chunk": chunk["file"], "piid": prop.get("piid"),
                    "pe_bli": pe_bli, "basis": basis,
                })
                continue
            if reads_as_absent(prop.get("lexicon_doc")):
                # the loader's _packet_value reads this as no lexicon_doc; a
                # shared BLI code cannot be resolved without it, and the
                # citation card would name no document
                missing_lexicon_doc += 1
                missing_lexicon_doc_examples.append({
                    "chunk": chunk["file"], "piid": piid, "pe_bli": pe_bli,
                    "lexicon_doc": prop.get("lexicon_doc"),
                })
                continue
            if reads_as_absent(prop.get("program_name")):
                # the published rationale words it ("program 'None' named for
                # this award")
                missing_program_name += 1
                missing_program_name_examples.append({
                    "chunk": chunk["file"], "piid": piid, "pe_bli": pe_bli,
                    "program_name": prop.get("program_name"),
                })
                continue
            if indexes is not None and index_key(
                    prop["program_name"], pe_bli, prop["lexicon_doc"]
            ) not in indexes.get(chunk["org"], set()):
                # counted as refuted, not raised — see the docstring
                invalid_pe_bli += 1
                continue
            a, b = prop.get("refute_a"), prop.get("refute_b")
            if any(x is not None and not isinstance(x, dict) for x in (a, b)):
                # a lens that answered something other than an object cleared
                # nothing; naming the chunk beats a bare AttributeError
                malformed_lens += 1
                continue
            a, b = a or {}, b or {}
            a_ok = a.get("refuted") is False
            b_ok = b.get("refuted") is False
            if a.get("refuted") is True:
                refuted_a += 1
            if b.get("refuted") is True:
                refuted_b += 1
            if "refuted" not in a or "refuted" not in b:
                missing_lens += 1
            elif not isinstance(a.get("refuted"), bool) or not isinstance(
                    b.get("refuted"), bool):
                # fail-closed: a lens that answered something other than a JSON
                # boolean has not cleared the proposal, and the count says so
                malformed_lens += 1
            if not (a_ok and b_ok):
                continue
            pair = (prop["piid"], pe_bli)
            if pair in seen_pairs:
                # the same PIID can carry several announcement paragraphs; the
                # loader keeps the first packet per pair anyway (:270-273), so
                # the duplicate is resolved here instead of shipped
                duplicate_pairs += 1
                continue
            seen_pairs.add(pair)
            packets.append({
                "piid": prop["piid"],
                "pe_bli": pe_bli,
                "program_name": prop.get("program_name"),
                "match_basis": basis,
                "date": rec.get("date"),
                "contractor": rec.get("contractor"),
                "service": rec.get("service"),
                "article_id": str(rec["article_id"]),
                "announcement_excerpt": (rec.get("text") or "")[:700],
                "lexicon_doc": str(prop["lexicon_doc"]),
                "llm_rationale": prop.get("rationale"),
            })
            # the reason is interpolated into the published rationale
            # ("triage+adversarial refute survived — …"); an empty one printed a
            # bare semicolon, and a lens writing it as a number or list used to
            # raise AttributeError on a bare .strip()
            reason = str(a.get("reason") or b.get("reason") or "").strip()[:200]
            surviving.append({"piid": prop["piid"], "pe_bli": pe_bli,
                              "reason": reason or "(no reason given)"})
    result = {
        "triaged": records_attempted,
        "verdict_counts": counts,
        "proposed": counts["link"],
        "surviving": surviving,
        "refuted_a": refuted_a,
        "refuted_b": refuted_b,
        "missing_lens": missing_lens,
        "malformed_lens": malformed_lens,
        "invalid_verdict": invalid_verdict,
        "invalid_verdict_examples": invalid_verdict_examples,
        "invalid_record_index": invalid_record_index,
        "invalid_record_index_examples": invalid_record_index_examples,
        "unknown_article_piid": unknown_article_piid,
        "unknown_article_piid_examples": unknown_article_piid_examples,
        "ambiguous_record": ambiguous_record,
        "ambiguous_record_examples": ambiguous_record_examples,
        "missing_pe_bli": missing_pe_bli,
        "missing_pe_bli_examples": missing_pe_bli_examples,
        "invalid_match_basis": invalid_match_basis,
        "invalid_match_basis_examples": invalid_match_basis_examples,
        "missing_lexicon_doc": missing_lexicon_doc,
        "missing_lexicon_doc_examples": missing_lexicon_doc_examples,
        "missing_program_name": missing_program_name,
        "missing_program_name_examples": missing_program_name_examples,
        "invalid_pe_bli": invalid_pe_bli,
        "malformed_file": malformed_file,
        "duplicate_pairs": duplicate_pairs,
        "records_attempted": records_attempted,
        "chunks_attempted": attempted_files,
        "chunks_queued": len(queue),
    }
    return packets, result


def _load_records() -> list[dict]:
    if not RECORDS.exists():
        raise SystemExit(
            f"{RECORDS} is missing. It is gitignored and regenerable (the parse "
            f"is deterministic):\n  uv run python scripts/parse_contract_announcements.py")
    records = [json.loads(line) for line in RECORDS.read_text().splitlines() if line.strip()]
    stats = json.loads(PARSE_STATS.read_text())
    if len(records) != stats["records"]:
        raise SystemExit(
            f"records.jsonl holds {len(records)} rows but parse_stats.json says "
            f"{stats['records']}; re-run scripts/parse_contract_announcements.py")
    return records


def cmd_queue(chunk_size: int) -> int:
    records = _load_records()
    lexicon = [json.loads(l) for l in LEXICON.read_text().splitlines() if l.strip()]
    name_index = build_name_index(lexicon)

    # A pe_bli maps to a SET of orgs, not one: the three shared BLI codes
    # ('20' DCSA/DTRA, '30' DMACT/DTRA/OSD, '500' DHRA/DLA) are filed under
    # several. any_value() would pick one of them differently between runs and
    # silently move those names out of one org's index — and the chunk
    # numbering the verdict files are keyed by is derived from this. So every
    # aggregate here is deterministic, and a name a shared code owns appears in
    # the index of every org that files it.
    con = duckdb.connect(str(ROOT / "data/duckdb/govbudget.duckdb"), read_only=True)
    pe_orgs: dict[str, set[str]] = defaultdict(set)
    for pe, org in con.execute(
            "select distinct pe_bli, org from dim_programs where org is not null"
            " order by 1, 2").fetchall():
        pe_orgs[pe].add(org)
    pe_title = dict(con.execute(
        "select pe_bli, min(title) from dim_programs group by 1 order by 1").fetchall())
    con.close()

    piids = sorted({n["piid"] for r in records for n in r.get("contract_numbers", [])})
    lakecon = duckdb.connect()
    lakecon.execute("create temp table want(piid varchar)")
    lakecon.executemany("insert into want values (?)", [(p,) for p in piids])
    lake = {r[0] for r in lakecon.execute(f"""
        select distinct award_id_piid
        from read_parquet('{ROOT}/data/parquet/contracts/fy=*/*.parquet',
                          union_by_name=true)
        where award_id_piid in (select piid from want)""").fetchall()}
    lakecon.close()

    # 3,840 entries carrying 3,832 distinct keys — 8 paragraphs are exact
    # duplicates across articles. `attempted_entries` / `attempted_value` are
    # what the wave-2 pass was HANDED (the denominator of its $1.9545e12); the
    # set is what rule 3 excludes by, and — intersected with today's residue
    # below — what /methodology/ may add to wave 4's count.
    attempted = set()
    attempted_entries = 0
    attempted_value = 0
    for f in sorted((ANN / "llm_chunks").glob("chunk_*.json")):
        for rec in json.load(open(f)):
            attempted.add(record_key(rec))
            attempted_entries += 1
            attempted_value += announced_value(rec)

    owned = [e for e in lexicon if e.get("ownership") == "own" and not e.get("weak_name")]
    orgs_with_lexicon = {o for e in owned for o in pe_orgs.get(e["pe_bli"], ())}

    with_lake = sum(1 for r in records
                    if any(n["piid"] in lake for n in r.get("contract_numbers", [])))
    residue_all, queued = select_residue(
        records, lake=lake, name_index=name_index,
        attempted=attempted, orgs_with_lexicon=orgs_with_lexicon)
    # Fix round 1, item 1: the two figures the scope loader is allowed to add
    # to wave 4's, because they are a subset of records_residue / value_residue
    # by construction. The pass's own totals are kept beside them, unchanged,
    # as the record of what it was handed.
    earlier_records, earlier_value = earlier_pass_in_residue(residue_all, attempted)
    chunks = chunk_records(queued, size=chunk_size)

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    for old in QUEUE_DIR.glob("chunk_*.json"):    # prune-before-emit: a shrinking
        old.unlink()                              # universe must not leave stale chunks
    for chunk in chunks:
        payload = {
            "chunk": chunk["file"],
            "rank": chunk["rank"],
            "org": chunk["org"],
            "announced_value_total": chunk["announced_value"],
            "lexicon_index": f"data/research/announcements/wave4_lexicon/{chunk['org']}.tsv",
            "rubric": RUBRIC,
            "records": [
                {"record_index": i,
                 "article_id": r["article_id"], "date": r["date"], "service": r["service"],
                 "contractor": r["contractor"], "amounts": r["amounts"],
                 "lake_piids": r["lake_piids"], "text": (r["text"] or "")[:700]}
                for i, r in enumerate(chunk["records"])],
        }
        (QUEUE_DIR / chunk["file"]).write_text(json.dumps(payload, indent=0))

    LEXICON_DIR.mkdir(parents=True, exist_ok=True)
    for old in LEXICON_DIR.glob("*.tsv"):
        old.unlink()
    for org in sorted({c["org"] for c in chunks}):
        (LEXICON_DIR / f"{org}.tsv").write_text(
            "\n".join(lexicon_index_lines(owned, org, pe_orgs, pe_title)) + "\n")

    chunk_rows = [{"rank": c["rank"], "file": c["file"], "org": c["org"],
                   "records": len(c["records"]),
                   "announced_value": c["announced_value"]} for c in chunks]
    # The run order, beside the chunks it orders: the adjudication walks this
    # list top-down in rounds of 5 (ruling A10). Regenerable, so gitignored with
    # the rest of wave4_queue/; residue_manifest.json is the committed copy.
    QUEUE_MANIFEST.write_text(json.dumps({
        "generated_at": date.today().isoformat(),
        "rubric": RUBRIC,
        "order": "descending announced value; rank == the chunk file's number",
        "chunk_size": chunk_size,
        "records_queued": len(queued),
        "value_queued": sum(announced_value(r) for r in queued),
        "chunks": chunk_rows,
    }, indent=1))

    manifest = {
        "generated_at": date.today().isoformat(),
        "records_total": len(records),
        "records_with_lake_piid": with_lake,
        "records_deterministic": with_lake - len(residue_all),
        "records_residue": len(residue_all),
        "value_residue": sum(announced_value(r) for r in residue_all),
        "earlier_pass": {"name": "wave2-llm-alias", "records": attempted_entries,
                         "distinct_records": len(attempted),
                         "value": attempted_value,
                         "records_in_residue": earlier_records,
                         "value_in_residue": earlier_value},
        "records_queued": len(queued),
        "value_queued": sum(announced_value(r) for r in queued),
        "chunk_size": chunk_size,
        "chunks": chunk_rows,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1))
    print(f"records {len(records):,}; with lake PIID {with_lake:,}; "
          f"deterministic {manifest['records_deterministic']:,}; "
          f"residue {len(residue_all):,} (${manifest['value_residue']/1e12:.4f}T); "
          f"already attempted {attempted_entries:,} ({len(attempted):,} distinct, "
          f"{earlier_records:,} still in the residue "
          f"(${earlier_value/1e12:.4f}T)); "
          f"queued {len(queued):,} in "
          f"{len(chunks)} chunks -> {QUEUE_DIR}")
    return 0


def cmd_collect() -> int:
    queue = []
    for f in sorted(QUEUE_DIR.glob("chunk_*.json")):
        payload = json.load(open(f))
        queue.append({"file": payload["chunk"], "org": payload["org"],
                      "announced_value": sum(announced_value(r) for r in payload["records"]),
                      "records": payload["records"]})
    if not queue:
        raise SystemExit(
            f"{QUEUE_DIR} is empty — run `queue` first (it is gitignored and "
            f"regenerated deterministically from records.jsonl + lexicon.jsonl)")
    verdicts = {}
    for f in sorted(VERDICT_DIR.glob("chunk_*.json")):
        try:
            payload = json.load(open(f))
        except json.JSONDecodeError as e:
            # fail closed and loudly: an unreadable verdict file is an
            # adjudicated chunk whose result would otherwise vanish
            raise SystemExit(f"{f} is not readable JSON ({e}); fix or remove it")
        if payload.get("chunk") != f.name:
            # keyed by the declared name, two files declaring one chunk would
            # silently overwrite each other in this dict
            raise SystemExit(
                f"{f} declares chunk {payload.get('chunk')!r}; a verdict file "
                f"must be named for the chunk it adjudicates")
        verdicts[f.name] = payload
    indexes = {}
    for org in sorted({c["org"] for c in queue}):
        index = LEXICON_DIR / f"{org}.tsv"
        if not index.exists():
            # without it every proposal would count invalid_pe_bli and the run
            # would read as uniformly hallucinated
            raise SystemExit(
                f"{index} is missing; it is written by `queue` beside the chunks "
                f"and is what every proposal's (program_name, pe_bli, "
                f"lexicon_doc) is validated against")
        indexes[org] = read_index_rows(index.read_text())
    packets, result = collect_verdicts(queue, verdicts, indexes)

    PACKET_DIR.mkdir(parents=True, exist_ok=True)
    for old in PACKET_DIR.glob("chunk_*.json"):
        old.unlink()
    for i in range(0, len(packets), 200):
        # a bare LIST: load_announcement_links.py iterates this file directly
        (PACKET_DIR / f"chunk_{i//200:03d}.json").write_text(
            json.dumps(packets[i:i + 200], indent=0))
    RESULT.write_text(json.dumps(result, indent=1))
    print(f"chunks adjudicated {len(result['chunks_attempted'])} of {len(queue)}; "
          f"records {result['records_attempted']:,}; "
          f"proposed {result['proposed']:,} "
          f"(weak {result['verdict_counts']['weak']:,}, "
          f"wrong {result['verdict_counts']['wrong']:,}); "
          f"refuted A {result['refuted_a']:,} / B {result['refuted_b']:,}; "
          f"missing a lens {result['missing_lens']:,}; "
          f"malformed a lens {result['malformed_lens']:,}; "
          f"invalid verdict {result['invalid_verdict']:,}; "
          f"invalid record_index {result['invalid_record_index']:,}; "
          f"unknown article/PIID {result['unknown_article_piid']:,}; "
          f"ambiguous record {result['ambiguous_record']:,}; "
          f"missing pe_bli {result['missing_pe_bli']:,}; "
          f"invalid match_basis {result['invalid_match_basis']:,}; "
          f"missing lexicon_doc {result['missing_lexicon_doc']:,}; "
          f"missing program_name {result['missing_program_name']:,}; "
          f"not in the org index {result['invalid_pe_bli']:,}; "
          f"malformed verdict files {result['malformed_file']:,}; "
          f"duplicate pairs {result['duplicate_pairs']:,}; "
          f"surviving {len(result['surviving']):,} -> {RESULT}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("queue", help="build the wave-4 adjudication queue")
    q.add_argument("--chunk-size", type=int, default=80)
    sub.add_parser("collect", help="turn returned verdicts into loader packets")
    args = ap.parse_args()
    return cmd_queue(args.chunk_size) if args.cmd == "queue" else cmd_collect()


if __name__ == "__main__":
    raise SystemExit(main())
