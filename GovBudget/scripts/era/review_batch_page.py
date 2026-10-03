#!/usr/bin/env python3
"""Owner review batches for the PB2017-23 era map (spec §5.3; R-DEC-FAM-REVIEW).

render  The next BATCH_SIZE open chains of review.csv, largest recorded era
        actuals first, as one self-contained page fragment. The page is
        published as a private Artifact; the owner reads it (on a phone) and
        answers in chat. A JSON manifest beside it records exactly which
        chains it showed, in the order the owner's row numbers refer to.
answer  Writes the owner's answers for exactly those chains into review.csv
        (decision, note, program pins, successor, range splits), ready for
        `govbudget era-map ratify --batch B<n> --decided-on DATE`.

review.csv is `era-map propose`'s file: era_map.REVIEW_COLUMNS, one row per
chain, keyed by chain_id. chains.csv beside it supplies what the page shows
and review.csv lacks (n_keys, classes, the book-stated successor's account
and evidence). A chain is open while its review.csv `decision` is blank and
no seed row covers it; after ratify, `era-map propose` rewrites review.csv
with only the chains still open (deferred ones come back blank).

A range split duplicates the chain's row and changes only first_edition and
last_edition: every range keeps the chain's keys_sha256, which ratify
compares with the whole chain in the lake before it hashes each range
itself. The ranges are contiguous and cover the chain by construction.

Nothing here decides anything: `answer` copies a proposal only when the
owner's reply approves it, refuses a proposal that is not a decision, and
leaves every check against the lake to ratify.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from govbudget.jbooks.era_map import (
    DECISIONS,
    REVIEW_COLUMNS,
    chain_id,
    parse_chain_id,
    read_csv,
    read_seed,
    write_csv,
)

BATCH_SIZE = 25
ANSWER_FIELDS = frozenset({"decision", "note", "program_account", "program_org", "successor_code"})
CHAIN_FIELDS = ("n_keys", "classes", "successor_account", "successor_evidence")
ANSWERS_KEYS = frozenset({"batch", "decided_on", "owner_reply", "owner_acknowledgements", "rows"})
FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500"
         "&family=IBM+Plex+Sans:wght@400;500;600&display=swap")
PAGE_CSS = """
:root{--paper:#f4f6f9;--sheet:#ffffff;--ink:#16202c;--muted:#556173;--rule:#d3dae3;--accent:#21507f;--same:#1d6a45;--same-bg:#e1f0e7;--hist:#7a520c;--hist-bg:#f5ead3;--excl:#8e2b22;--excl-bg:#f6e0dc;--other:#3b4553;--other-bg:#e6e9ee}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;--paper:#0e131a;--sheet:#151c25;--ink:#e2e7ee;--muted:#9ba7b7;--rule:#2a3441;--accent:#8fb6e4;--same:#8fd2ac;--same-bg:#16321f;--hist:#e5c27f;--hist-bg:#382b11;--excl:#f0a69d;--excl-bg:#3b1b18;--other:#c2cad5;--other-bg:#242c37}}
:root[data-theme="dark"]{color-scheme:dark;--paper:#0e131a;--sheet:#151c25;--ink:#e2e7ee;--muted:#9ba7b7;--rule:#2a3441;--accent:#8fb6e4;--same:#8fd2ac;--same-bg:#16321f;--hist:#e5c27f;--hist-bg:#382b11;--excl:#f0a69d;--excl-bg:#3b1b18;--other:#c2cad5;--other-bg:#242c37}
body{background:var(--paper);color:var(--ink);font:15px/1.55 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif}
.page{max-width:880px;margin:0 auto;padding-inline:16px;padding-block:28px 64px}
.eyebrow,.label{margin:0;font:500 12px/1.4 "IBM Plex Mono",ui-monospace,Menlo,monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
h1{margin:6px 0 10px;font-size:26px;line-height:1.2;font-weight:600;text-wrap:balance}
.lede,.how{margin:0 0 10px;max-width:68ch}
.how{color:var(--muted)}.how b{color:var(--ink)}
.legend{display:grid;gap:6px;margin:14px 0 0;padding-block:12px;border-block:1px solid var(--rule)}
.legend div{display:grid;grid-template-columns:minmax(0,max-content) 1fr;gap:10px;align-items:baseline}
.legend dd{margin:0;color:var(--muted)}
.chains{list-style:none;margin:8px 0 0;padding:0}
.chain{padding-block:18px;border-bottom:1px solid var(--rule)}
.chain-head{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 12px}
.num{font:500 13px/1 "IBM Plex Mono",ui-monospace,Menlo,monospace;color:var(--muted);min-width:2ch}
.chain h2{margin:0;flex:1 1 auto;display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline;font-size:18px;line-height:1.3;font-weight:600}
code,.usd,.acct,.org,.cid{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace}
.acct,.org{font-size:14px;font-weight:400;color:var(--muted)}
.usd{font-size:16px;font-weight:500;font-variant-numeric:tabular-nums}
.span{margin:4px 0 10px;color:var(--muted);font-size:14px}
.cid{font-size:12px;overflow-wrap:anywhere}
dl{margin:0}.chain dl{display:grid;gap:8px}
.chain dl div{display:grid;grid-template-columns:150px minmax(0,1fr);gap:4px 14px}
dt{font-size:13px;color:var(--muted)}
dd{margin:0;min-width:0;overflow-wrap:anywhere}
.pre{display:block;white-space:pre-wrap}
.proposal{display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 10px;margin:12px 0 0;padding:10px 12px;background:var(--sheet);border:1px solid var(--rule);border-radius:4px}
.chip{display:inline-block;padding:2px 8px;border-radius:3px;font:500 13px/1.5 "IBM Plex Mono",ui-monospace,Menlo,monospace}
.chip-same{color:var(--same);background:var(--same-bg)}.chip-hist{color:var(--hist);background:var(--hist-bg)}
.chip-excl{color:var(--excl);background:var(--excl-bg)}.chip-other{color:var(--other);background:var(--other-bg)}
.pins{font-size:14px;color:var(--accent)}
.reason{flex:1 1 100%}
@media (max-width:560px){.chain dl div{grid-template-columns:1fr}h1{font-size:22px}}
""".strip()
_EDITION_BREAK = re.compile(r"; (?=\d{4}: )")


class ReviewError(ValueError):
    """A review input that cannot be applied safely."""


def read_review(path: Path) -> list[dict]:
    """review.csv rows; refuses any header but era_map.REVIEW_COLUMNS."""
    with Path(path).open(newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh), [])
    if tuple(header) != REVIEW_COLUMNS:
        raise ReviewError(f"{path}: header {header} is not era_map.REVIEW_COLUMNS {list(REVIEW_COLUMNS)}")
    return read_csv(Path(path))


def read_chains(path: Path) -> dict[str, dict]:
    """chains.csv (beside review.csv): chain_id -> the fields the page reads from it."""
    path = Path(path)
    if not path.is_file():
        raise ReviewError(f"{path} is missing (era-map propose writes it beside review.csv)")
    rows = read_csv(path)
    missing = [c for c in ("chain_id",) + CHAIN_FIELDS if rows and c not in rows[0]]
    if missing:
        raise ReviewError(f"{path} lacks column(s): {', '.join(missing)}")
    return {r["chain_id"]: {f: r[f] for f in CHAIN_FIELDS} for r in rows}


def seed_chain_ids(seed_path: Path) -> set[str]:
    """Every chain at least one seed row already covers."""
    return {chain_id(r["line_item_code"], r["account"], r["organization"])
            for r in read_seed(Path(seed_path))}


def label(row: dict) -> str:
    """What the page prints for a row: '{chain_id}|{first}-{last}'."""
    return f"{row['chain_id']}|{row['first_edition']}-{row['last_edition']}"


def actuals_k(row: dict) -> Decimal:
    try:
        return Decimal(row["actuals_k"] or "0")
    except InvalidOperation as exc:
        raise ReviewError(f"{row['chain_id']}: actuals_k {row['actuals_k']!r} is not a number") from exc


def next_batch(rows: list[dict], decided: set[str], size: int = BATCH_SIZE) -> tuple[list[dict], int]:
    """The `size` largest open chains, and how many chains were open."""
    open_rows = [r for r in rows if not r["decision"].strip() and r["chain_id"] not in decided]
    open_rows.sort(key=lambda r: (-actuals_k(r), r["chain_id"]))
    return open_rows[:size], len(open_rows)


def fmt_usd_k(value: Decimal) -> str:
    """USD thousands as a short dollar figure: Decimal('1234567') -> '$1.23B'."""
    dollars = Decimal(value) * 1000
    for suffix, scale in (("B", Decimal(10) ** 9), ("M", Decimal(10) ** 6), ("K", Decimal(10) ** 3)):
        if abs(dollars) >= scale:
            return f"${dollars / scale:,.2f}{suffix}"
    return f"${dollars:,.0f}"


def _e(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _tone(decision: str) -> str:
    if decision == "same_program":
        return "same"
    if decision == "history_only":
        return "hist"
    if decision.startswith("exclude_"):
        return "excl"
    return "other"


def _editions(row: dict) -> str:
    first, last = row["first_edition"], row["last_edition"]
    return f"PB{first}" if first == last else f"PB{first}–PB{last}"


def read_collision_codes(path: Path) -> frozenset[str]:
    """counts.json (beside review.csv): the PB2026 collision codes `propose` found."""
    path = Path(path)
    if not path.is_file():
        raise ReviewError(f"{path} is missing (era-map propose writes it beside review.csv)")
    codes = json.loads(path.read_text(encoding="utf-8")).get("collision_codes")
    if not isinstance(codes, list):
        raise ReviewError(f"{path} has no collision_codes list")
    return frozenset(str(c) for c in codes)


def collision_pins_missing(row: dict, collision_codes: frozenset[str]) -> list[str]:
    """The pins ratify requires that this row's proposal leaves blank.

    On a PB2026 collision code, same_program and history_only need BOTH
    program_account and program_org (Task 12 ratify refuses either blank), so
    approving such a proposal as it stands could not be ratified."""
    code, _account, _org = parse_chain_id(row["chain_id"])
    if code not in collision_codes or row["proposed_decision"] not in ("same_program", "history_only"):
        return []
    return [f for f in ("program_account", "program_org") if not row[f].strip()]


def _row_html(n: int, row: dict, chain: dict, collision_codes: frozenset[str] = frozenset()) -> str:
    code, account, org = parse_chain_id(row["chain_id"])
    org_html = f'<span class="org">org {_e(org)}</span>' if org else ""
    pins = [f"{text} {_e(row[field])}" for field, text in
            (("program_account", "joins account"), ("program_org", "joins org")) if row[field]]
    pin_html = f'<span class="pins">{" · ".join(pins)}</span>' if pins else ""
    successor = ""
    if row["successor_code"]:
        successor = (f'<div><dt>Stated successor</dt><dd><code>{_e(row["successor_code"])}</code> '
                     f'{_e(chain["successor_account"])}<span class="pre">{_e(chain["successor_evidence"])}</span></dd></div>\n')
    missing = collision_pins_missing(row, collision_codes)
    usable = row["proposed_decision"] and not missing
    proposed = row["proposed_decision"] if usable else "needs your decision"
    tone = _tone(row["proposed_decision"]) if usable else "other"
    need_html = ""
    if missing:
        need_html = (f'<span class="pins">PB2026 collision code {_e(code)}: {_e(row["proposed_decision"])} '
                     f'needs {" and ".join(missing)} (ratify refuses it without them); answer the '
                     f"pin(s) or another decision</span>")
    titles = _EDITION_BREAK.sub("\n", row["titles_by_edition"])
    return (
        f'<li class="chain" id="row-{n}">\n'
        f'<div class="chain-head"><span class="num">{n}</span><h2><code>{_e(code)}</code>'
        f'<span class="acct">{_e(account)}</span>{org_html}</h2>'
        f'<span class="usd">{_e(fmt_usd_k(actuals_k(row)))}</span></div>\n'
        f'<p class="span">{_e(_editions(row))} · {_e(chain["n_keys"])} era lines · '
        f'class {_e(chain["classes"]) or "—"}<br><span class="cid">{_e(label(row))}</span></p>\n'
        f"<dl>\n"
        f'<div><dt>Titles by edition</dt><dd class="pre">{_e(titles)}</dd></div>\n'
        f'<div><dt>PB2024–26 title</dt><dd>{_e(row["modern_title"]) or "—"}</dd></div>\n'
        f'<div><dt>Accounts</dt><dd>{_e(row["accounts"])}</dd></div>\n'
        f'<div><dt>Continuity</dt><dd>{_e(row["continuity"]) or "—"}</dd></div>\n'
        f"{successor}</dl>\n"
        f'<p class="proposal"><span class="label">Proposed</span>'
        f'<span class="chip chip-{tone}">{_e(proposed)}</span>{pin_html}{need_html}'
        f'<span class="reason">{_e(row["reason"])}</span></p>\n'
        f"</li>"
    )


def render_page(batch: str, rows: list[dict], remaining: int, chains: dict[str, dict],
                collision_codes: frozenset[str] = frozenset()) -> str:
    """One Artifact page fragment (the publish skeleton adds <html>/<head>/<body>).

    A row is marked "needs your decision" when it has no proposal, or when its
    proposal is same_program/history_only on a PB2026 collision code with a
    blank pin (collision_pins_missing): the page names the missing pin(s)."""
    for row in rows:
        if row["chain_id"] not in chains:
            raise ReviewError(f"chains.csv has no row for {row['chain_id']}")
    total = sum((actuals_k(r) for r in rows), Decimal(0))
    items = "\n".join(_row_html(n, row, chains[row["chain_id"]], collision_codes)
                      for n, row in enumerate(rows, 1))
    plural = "" if remaining == 1 else "s"
    return (
        f"<title>Era map review {_e(batch)}</title>\n"
        f'<link rel="stylesheet" href="{_e(FONTS)}">\n'
        f"<style>\n{PAGE_CSS}\n</style>\n"
        f'<main class="page">\n<header class="intro">\n'
        f'<p class="eyebrow">Fiscal Receipts · procurement history before FY2024</p>\n'
        f"<h1>Era map review, batch {_e(batch)}</h1>\n"
        f'<p class="lede">{len(rows)} budget-line chains from the PB2017–PB2023 P-1 workbooks, '
        f"ordered by their recorded era actuals ({_e(fmt_usd_k(total))} across this batch). "
        f"Each chain needs one decision before its points can join a program page.</p>\n"
        f'<p class="how">Reply in chat with <b>approved</b> to accept every proposal, or give a row '
        f"number and its change, for example “7: history_only”, “12: split at PB2020, earlier "
        f"range exclude_reused_code” or “3: defer”. A row marked <b>needs your decision</b> has no "
        f"usable proposal (none, or a collision-code proposal missing a pin) and needs an explicit "
        f"answer. {remaining} undecided chain{plural} will remain after this batch.</p>\n"
        f'<dl class="legend">\n'
        f'<div><dt><span class="chip chip-same">same_program</span></dt><dd>The era code is the program on '
        f"today’s page; its PB2017–PB2023 points join that page.</dd></div>\n"
        f'<div><dt><span class="chip chip-hist">history_only</span></dt><dd>Kept in the map and the program '
        f"table; no page gains points.</dd></div>\n"
        f'<div><dt><span class="chip chip-excl">exclude_reused_code</span></dt><dd>The code meant a different '
        f"program in these editions; nothing joins.</dd></div>\n"
        f"</dl>\n</header>\n"
        f'<ol class="chains">\n{items}\n</ol>\n</main>\n'
    )


def _checked(lbl: str, new: dict) -> dict:
    """The two rules ratify would refuse that this tool can see without the lake."""
    if new["successor_code"].strip() and new["decision"] != "history_only":
        raise ReviewError(f"{lbl}: successor_code {new['successor_code']!r} is set but the decision is "
                          f"{new['decision']}; ratify takes a successor only on history_only — answer "
                          f'"successor_code": "" or decision history_only')
    if new["decision"].startswith("exclude_") and (new["program_account"] or new["program_org"]):
        raise ReviewError(f'{lbl}: an exclusion carries no program pin — answer "program_account": "" '
                          f'and "program_org": ""')
    return new


def _decide(row: dict, change: dict) -> dict:
    new = dict(row)
    new.update({f: "" if change[f] is None else str(change[f]) for f in ANSWER_FIELDS if f in change})
    decision = change.get("decision", row["proposed_decision"])
    if decision not in DECISIONS:
        raise ReviewError(
            f"{label(new)}: {decision!r} is not a decision ({', '.join(DECISIONS)}); "
            "the owner's answer must name one, or a split")
    new["decision"] = decision
    return _checked(label(new), new)


def _split(row: dict, ranges) -> list[dict]:
    """One copy of the row per edition range; only first/last_edition and the answers change."""
    lbl = label(row)
    if not isinstance(ranges, list) or len(ranges) < 2:
        raise ReviewError(f"{lbl}: a split needs at least two ranges")
    first, last = int(row["first_edition"]), int(row["last_edition"])
    out, start = [], first
    for i, part in enumerate(ranges):
        unknown = set(part) - ANSWER_FIELDS - {"last_edition"}
        if unknown:
            raise ReviewError(f"{lbl}: unknown answer field(s) {sorted(unknown)} in a split range")
        is_last = i == len(ranges) - 1
        if not is_last and "last_edition" not in part:
            raise ReviewError(f"{lbl}: every split range but the last names its last_edition")
        end = int(part.get("last_edition", last))
        if is_last and end != last:
            raise ReviewError(f"{lbl}: the last range must end at PB{last}, the chain's last edition")
        if end < start or (not is_last and end >= last):
            raise ReviewError(f"{lbl}: range PB{start}-PB{end} does not fit inside PB{first}-PB{last}")
        if "decision" not in part:
            raise ReviewError(f"{lbl}: split range PB{start}-PB{end} needs an explicit decision")
        new = _decide({**row, "first_edition": str(start), "last_edition": str(end)}, part)
        out.append(new)
        start = end + 1
    return out


def apply_answers(rows: list[dict], shown: list[str], answers: dict) -> tuple[list[dict], dict]:
    """Apply the owner's answers to exactly the chains one batch page showed.

    answers["rows"] maps chain_id -> amendment. A shown chain absent from it
    takes its proposal (the owner approved the batch); {"defer": true} leaves
    it open for a later batch; {"split": [...]} replaces it with one row per
    edition range. Returns (rows, counts); rows keep their original order.
    """
    amendments = answers.get("rows")
    if not isinstance(amendments, dict):
        raise ReviewError('answers need a "rows" object (empty when the owner approved every proposal)')
    stray = sorted(set(amendments) - set(shown))
    if stray:
        raise ReviewError(f"answers name chain(s) this batch did not show: {', '.join(stray)}")
    by_id: dict[str, list[dict]] = {}
    for r in rows:
        by_id.setdefault(r["chain_id"], []).append(r)
    for cid in shown:
        found = by_id.get(cid, [])
        if len(found) != 1:
            raise ReviewError(f"{cid}: {len(found)} review.csv row(s); want exactly one (re-run era-map propose)")
        if found[0]["decision"].strip():
            raise ReviewError(f"{label(found[0])}: already has a decision")
    replaced: dict[str, list[dict]] = {}
    counts = {"decided": 0, "split_chains": 0, "split_rows": 0, "deferred": 0}
    for cid in shown:
        row, change = by_id[cid][0], amendments.get(cid, {})
        unknown = set(change) - ANSWER_FIELDS - {"defer", "split"}
        if unknown:
            raise ReviewError(f"{label(row)}: unknown answer field(s) {sorted(unknown)}")
        if change.get("defer"):
            if set(change) != {"defer"}:
                raise ReviewError(f"{label(row)}: a deferred chain takes no other answer")
            counts["deferred"] += 1
            continue
        if "split" in change:
            if set(change) != {"split"}:
                raise ReviewError(f"{label(row)}: a split carries its answers inside each range")
            parts = _split(row, change["split"])
            replaced[cid] = parts
            counts["split_chains"] += 1
            counts["split_rows"] += len(parts)
            continue
        replaced[cid] = [_decide(row, change)]
        counts["decided"] += 1
    out: list[dict] = []
    for row in rows:
        out.extend(replaced.get(row["chain_id"], [row]))
    return out, counts


def _load_answers(path: Path, batch: str) -> dict:
    answers = json.loads(Path(path).read_text(encoding="utf-8"))
    unknown = set(answers) - ANSWERS_KEYS
    if unknown:
        raise ReviewError(f"{path}: unknown top-level key(s) {sorted(unknown)}")
    if answers.get("batch") != batch:
        raise ReviewError(f"{path} is batch {answers.get('batch')!r}, not {batch}")
    if not str(answers.get("owner_reply") or "").strip():
        raise ReviewError(f"{path}: owner_reply (the owner's message, verbatim) is empty")
    try:
        date.fromisoformat(str(answers.get("decided_on")))
    except ValueError as exc:
        raise ReviewError(f"{path}: decided_on {answers.get('decided_on')!r} is not an ISO date") from exc
    return answers


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="review_batch_page", description="Era-map owner review batches")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("render", "answer"):
        s = sub.add_parser(name)
        s.add_argument("--batch", type=int, required=True, help="batch number n (label B<n>)")
        s.add_argument("--review", type=Path, default=Path("data/research/era_map/review.csv"))
        s.add_argument("--out-dir", type=Path, default=Path("tmp/era-review"))
    sub.choices["render"].add_argument("--chains", type=Path, default=None,
                                       help="default: chains.csv beside --review")
    sub.choices["render"].add_argument("--counts", type=Path, default=None,
                                       help="default: counts.json beside --review (PB2026 collision codes)")
    sub.choices["render"].add_argument("--seed", type=Path, default=Path("dbt/seeds/p1_era_code_decisions.csv"))
    sub.choices["answer"].add_argument("--answers", type=Path, required=True)
    args = p.parse_args(argv)
    batch = f"B{args.batch}"
    manifest_path = args.out_dir / f"{batch}.json"
    try:
        rows = read_review(args.review)
        if args.cmd == "render":
            chains = read_chains(args.chains or args.review.with_name("chains.csv"))
            collision_codes = read_collision_codes(args.counts or args.review.with_name("counts.json"))
            shown, open_count = next_batch(rows, seed_chain_ids(args.seed))
            if not shown:
                print("no undecided chain left")
                return 0
            args.out_dir.mkdir(parents=True, exist_ok=True)
            page = args.out_dir / f"{batch}.html"
            page.write_text(render_page(batch, shown, open_count - len(shown), chains, collision_codes),
                            encoding="utf-8")
            total = sum((actuals_k(r) for r in shown), Decimal(0))
            manifest_path.write_text(json.dumps({
                "batch": batch, "chain_ids": [r["chain_id"] for r in shown],
                "labels": [label(r) for r in shown], "actuals_k": str(total),
                "undecided_before": open_count,
            }, indent=2) + "\n", encoding="utf-8")
            print(f"{batch}: {len(shown)} chain(s), {fmt_usd_k(total)} of era actuals -> {page} "
                  f"(manifest {manifest_path}); {open_count - len(shown)} undecided after this batch")
            return 0
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("batch") != batch:
            raise ReviewError(f"{manifest_path} is batch {manifest.get('batch')!r}, not {batch}")
        answers = _load_answers(args.answers, batch)
        out, counts = apply_answers(rows, manifest["chain_ids"], answers)
        write_csv(args.review, REVIEW_COLUMNS, out)
        print(f"{batch}: {counts['decided']} decided, {counts['split_chains']} split into "
              f"{counts['split_rows']} ranges, {counts['deferred']} deferred -> {args.review}; "
              f"ratify writes {counts['decided'] + counts['split_rows']} seed row(s): "
              f"era-map ratify --batch {batch} --decided-on {answers['decided_on']}")
        return 0
    except ReviewError as exc:
        print(f"review_batch_page: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
