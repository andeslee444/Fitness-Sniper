"""Phase 5H — flow_chart exporter unit tests.

Covers the precomputed sankey payload builder (src/govbudget/flow_chart.py):
Decimal-exact top-N + Other aggregation, conservation inside the payload,
deterministic layout geometry, the honest crosswalk bridge (remainder ==
total − crosswalked EXACTLY), the competition overlay partition, and the
minted derived citations (budget nodes recompute via sum(budget_lines…;
spend nodes recompute via sum(flow_children…).
"""

import json
from decimal import Decimal as D
from pathlib import Path

import duckdb
import pytest

from govbudget.export_site import fact_id_workbook
from govbudget.flow_chart import (
    COMPETED_CLASSES,
    OFFERS_BUCKETS,
    build_flow_chart,
)

FLOW_COLS = (
    "river varchar, fiscal_year integer, level_from varchar, node_from varchar,"
    " node_from_label varchar, level_to varchar, node_to varchar,"
    " node_to_label varchar, competed_class varchar, offers_bucket varchar,"
    " amount double, line_count bigint, units varchar"
)


def _bl_row(org, account, ba, pe, title, amount, amount_type="fy_2026_total"):
    """Build a 16-element bl_rows tuple like export_site's step 2c."""
    sha = "deadbeef" * 8
    fid = fact_id_workbook(sha, "R-1", 2026, account, org, ba, pe, amount_type)
    return (
        fid, "R-1", 2026, account, f"title of {account}", org, ba,
        f"BA {ba}", pe, title, amount_type, float(amount),
        "USD thousands", sha, "Sheet1", "A1",
    )


@pytest.fixture()
def flow_db(tmp_path: Path) -> Path:
    db = tmp_path / "flow.duckdb"
    con = duckdb.connect(str(db))
    con.execute(f"create table fct_flow_edges ({FLOW_COLS})")

    budget = [
        # total → component (labels for the component level)
        ("budget", 2026, "total", "TOTAL", "FY2026 PB", "component",
         "DARPA", "DARPA", None, None, 400000.0, 2, "USD_thousands"),
        ("budget", 2026, "total", "TOTAL", "FY2026 PB", "component",
         "A", "Army", None, None, 100000.0, 1, "USD_thousands"),
        ("budget", 2026, "total", "TOTAL", "FY2026 PB", "component",
         "CLASSIFIED", "Classified Programs", None, None, 30000.0, 1,
         "USD_thousands"),
        # component → appropriation (labels for the appropriation level)
        ("budget", 2026, "component", "DARPA", "DARPA", "appropriation",
         "DARPA|0400D", "RDT&E Defense-Wide", None, None, 400000.0, 2,
         "USD_thousands"),
        ("budget", 2026, "component", "A", "Army", "appropriation",
         "A|2040A", "RDT&E Army", None, None, 100000.0, 1, "USD_thousands"),
        ("budget", 2026, "component", "CLASSIFIED", "Classified Programs",
         "appropriation", "CLASSIFIED|3080F", "Other Procurement AF",
         None, None, 30000.0, 1, "USD_thousands"),
        # appropriation → budget_activity (labels for the BA level)
        ("budget", 2026, "appropriation", "DARPA|0400D", "RDT&E Defense-Wide",
         "budget_activity", "DARPA|0400D|01", "Basic Research",
         None, None, 400000.0, 2, "USD_thousands"),
        ("budget", 2026, "appropriation", "A|2040A", "RDT&E Army",
         "budget_activity", "A|2040A|02", "Applied Research",
         None, None, 100000.0, 1, "USD_thousands"),
        ("budget", 2026, "appropriation", "CLASSIFIED|3080F",
         "Other Procurement AF", "budget_activity", "CLASSIFIED|3080F|04",
         "BA 04", None, None, 30000.0, 1, "USD_thousands"),
        # budget_activity → program (the leaf grain the builder sums from)
        ("budget", 2026, "budget_activity", "DARPA|0400D|01", "Basic Research",
         "program", "DARPA|0400D|01|0601101E", "DEFENSE RESEARCH",
         None, None, 300000.0, 1, "USD_thousands"),
        ("budget", 2026, "budget_activity", "DARPA|0400D|01", "Basic Research",
         "program", "DARPA|0400D|01|0601102E", "APPLIED RESEARCH",
         None, None, 100000.0, 1, "USD_thousands"),
        ("budget", 2026, "budget_activity", "A|2040A|02", "Applied Research",
         "program", "A|2040A|02|0601104A", "ARMY RESEARCH",
         None, None, 100000.0, 1, "USD_thousands"),
        ("budget", 2026, "budget_activity", "CLASSIFIED|3080F|04", "BA 04",
         "program", "CLASSIFIED|3080F|04|9999999999", "Classified Programs",
         None, None, 30000.0, 1, "USD_thousands"),
    ]
    spend = [
        # office → family leaves (the only spend grain the builder reads)
        ("spend", 2025, "office", "DEPT ARMY|ACC-APG", "ACC-APG", "family",
         "ACME PARENT", "ACME PARENT", "full_and_open", "3-4", 600.25, 3, "USD"),
        ("spend", 2025, "office", "DEPT ARMY|ACC-APG", "ACC-APG", "family",
         "ACME PARENT", "ACME PARENT", "not_competed", "1", 150.5, 1, "USD"),
        ("spend", 2025, "office", "DEPT NAVY|NAVSEA", "NAVSEA", "family",
         "BETA LLC", "BETA LLC", "set_aside", "2", 250.0, 2, "USD"),
        ("spend", 2025, "office", "DEPT NAVY|NAVSEA", "NAVSEA", "family",
         "GAMMA CO", "GAMMA CO", "other_than_full", "unknown", 99.25, 1, "USD"),
        ("spend", 2024, "office", "DEPT ARMY|ACC-APG", "ACC-APG", "family",
         "ACME PARENT", "ACME PARENT", "other_than_full", "unknown",
         100.0, 1, "USD"),
        # net de-obligation: a REAL spend-river case — NAVAIR's net FY2025
        # position with ACME is negative. Values stay negative (honest);
        # geometry renders zero-width bands (see _layout docstring).
        ("spend", 2025, "office", "DEPT NAVY|NAVAIR", "NAVAIR", "family",
         "ACME PARENT", "ACME PARENT", "not_competed", "unknown",
         -50.0, 1, "USD"),
    ]
    con.executemany(
        "insert into fct_flow_edges values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        budget + spend,
    )
    # bridge marts: 0601101E crosswalks high (PIID1) AND medium (PIID3) —
    # PE confidence must be 'high' (an int-max, never a lexicographic
    # varchar max where 'medium' > 'high') and families must come from the
    # high link only. 0601104A is medium-only → confidence 'medium',
    # families [] (medium fan-out excluded by design).
    con.execute(
        "create table fct_budget_to_awards as select * from (values"
        " ('0601101E','PIID1','high'),"
        " ('0601101E','PIID3','medium'),"
        " ('0601104A','PIID2','medium'))"
        " t(pe_bli, award_piid, confidence)"
    )
    con.execute(
        "create table fct_award_transactions as select * from (values"
        " ('PIID1','UEI1',1000.0),"
        " ('PIID2','UEI2',500.0),"
        " ('PIID3','UEI2',250.0))"
        " t(award_id_piid, recipient_uei, obligation)"
    )
    con.execute(
        "create table entity_xwalk as select * from (values"
        " ('UEI1','ACME PARENT'),('UEI2','BETA LLC'))"
        " t(recipient_uei, family_key)"
    )
    con.execute(
        "create table dim_pe_titles as select * from (values"
        " ('0601101E','DEFENSE RESEARCH'),('0601104A','ARMY RESEARCH'))"
        " t(pe_bli, title)"
    )
    con.close()
    return db


@pytest.fixture()
def bl_rows():
    return [
        _bl_row("DARPA", "0400D", "01", "0601101E", "DEFENSE RESEARCH", 300000),
        _bl_row("DARPA", "0400D", "01", "0601102E", "APPLIED RESEARCH", 100000),
        _bl_row("A", "2040A", "02", "0601104A", "ARMY RESEARCH", 100000),
        _bl_row("", "3080F", "04", "9999999999", "Classified Programs", 30000),
        # noise: other amount_type must be ignored by the fid lookup
        _bl_row("DARPA", "0400D", "01", "0601101E", "DEFENSE RESEARCH",
                280494, amount_type="fy_2024_actuals"),
    ]


def _build(flow_db, bl_rows, **kw):
    kw.setdefault("top_n", 2)
    kw.setdefault("default_fy", 2025)
    return build_flow_chart(duckdb_path=flow_db, bl_rows=bl_rows, **kw)


def _cit_index(cit_rows):
    return {r[0]: r for r in cit_rows}


def _node_by_id(river, node_id):
    return next(n for n in river["nodes"] if n["id"] == node_id)


# ---------------------------------------------------------------------------
# Conservation + aggregation
# ---------------------------------------------------------------------------


def test_budget_conservation_and_other_aggregation(flow_db, bl_rows):
    payload, _rows = _build(flow_db, bl_rows)
    b = payload["budget"]
    nodes = b["nodes"]
    edges = b["edges"]

    # every non-terminal node: sum(out) == value; every non-root: sum(in) == value
    by_idx = {i: n for i, n in enumerate(nodes)}
    inflow: dict[int, D] = {}
    outflow: dict[int, D] = {}
    for e in edges:
        outflow[e["s"]] = outflow.get(e["s"], D(0)) + D(str(e["v"]))
        inflow[e["t"]] = inflow.get(e["t"], D(0)) + D(str(e["v"]))
    for i, n in by_idx.items():
        v = D(str(n["value"]))
        if n["level"] != "total":
            assert inflow.get(i, D(0)) == v, f"inflow != value for {n['id']}"
        if n["level"] not in ("bridge",):
            assert outflow.get(i, D(0)) == v, f"outflow != value for {n['id']}"

    # top_n=2 → component level: DARPA + A exported, CLASSIFIED in Other
    comp_ids = [n["id"] for n in nodes if n["level"] == "component"]
    assert "b:c:DARPA" in comp_ids and "b:c:A" in comp_ids
    other = _node_by_id(b, "b:other:component")
    assert other["value"] == 30000.0
    assert other["other"]["count"] == 1
    members = other["other"]["members"]
    assert members[0]["k"] == "CLASSIFIED"
    # members + omitted_value account for 100% of the Other node exactly
    assert (
        sum(D(str(m["v"])) for m in members)
        + D(str(other["other"]["omitted_value"]))
        == D(str(other["value"]))
    )

    # total equals the river mouth
    total = _node_by_id(b, "b:total")
    assert D(str(total["value"])) == D("530000")


def test_spend_conservation_and_competition_partition(flow_db, bl_rows):
    payload, _rows = _build(flow_db, bl_rows)
    s = payload["spend"]
    assert s["competed_classes"] == list(COMPETED_CLASSES)
    assert s["offers_buckets"] == list(OFFERS_BUCKETS)
    assert s["default_fy"] == 2025
    assert s["fys"] == [2024, 2025]

    river = s["by_fy"]["2025"]
    # every edge: competed classes and offers buckets partition the edge value
    for e in river["edges"]:
        v = D(str(e["v"]))
        assert sum(D(str(x)) for x in e["c"]) == v
        assert sum(D(str(x)) for x in e["o"]) == v
    # node conservation
    inflow: dict[int, D] = {}
    outflow: dict[int, D] = {}
    for e in river["edges"]:
        outflow[e["s"]] = outflow.get(e["s"], D(0)) + D(str(e["v"]))
        inflow[e["t"]] = inflow.get(e["t"], D(0)) + D(str(e["v"]))
    for i, n in enumerate(river["nodes"]):
        v = D(str(n["value"]))
        if n["level"] != "total":
            assert inflow.get(i, D(0)) == v
        if n["level"] != "family":
            assert outflow.get(i, D(0)) == v
    # 600.25 + 150.5 + 250 + 99.25 − 50 (net de-obligation stays in the sums)
    assert D(str(river["total"])) == D("1050.00")
    # the negative office survives as an honestly negative Other node
    other_office = next(n for n in river["nodes"] if n["id"] == "s:2025:other:office")
    assert other_office["value"] == -50.0


def test_deterministic_output(flow_db, bl_rows):
    p1, r1 = _build(flow_db, bl_rows)
    p2, r2 = _build(flow_db, bl_rows)
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)
    # rows identical apart from retrieved_at (index 19 — the build timestamp)
    mask = [r[:19] + r[20:] for r in r1]
    assert mask == [r[:19] + r[20:] for r in r2]


# ---------------------------------------------------------------------------
# Layout geometry
# ---------------------------------------------------------------------------


def test_layout_geometry(flow_db, bl_rows):
    payload, _ = _build(flow_db, bl_rows)
    b = payload["budget"]
    total_node = _node_by_id(b, "b:total")
    scale = (total_node["y1"] - total_node["y0"]) / total_node["value"]
    for n in b["nodes"]:
        assert 0 <= n["x0"] < n["x1"] <= b["width"]
        assert 0 <= n["y0"] <= n["y1"] <= b["height"] + 1e-6
        # heights proportional to value (never distorted)
        assert abs((n["y1"] - n["y0"]) - n["value"] * scale) < 0.05, n["id"]
    # levels occupy strictly increasing x columns
    level_x = {}
    for n in b["nodes"]:
        level_x.setdefault(n["level"], n["x0"])
        assert level_x[n["level"]] == n["x0"]
    xs = [level_x[lv] for lv in b["levels"] if lv in level_x]
    assert xs == sorted(xs) and len(set(xs)) == len(xs)
    # edge bands sit inside their nodes and match edge thickness on both ends
    for e in b["edges"]:
        sn, tn = b["nodes"][e["s"]], b["nodes"][e["t"]]
        sy0, sy1, ty0, ty1 = e["g"]
        assert sn["y0"] - 1e-6 <= sy0 <= sy1 <= sn["y1"] + 1e-6
        assert tn["y0"] - 1e-6 <= ty0 <= ty1 <= tn["y1"] + 1e-6
        assert abs((sy1 - sy0) - e["v"] * scale) < 0.05
        assert abs((ty1 - ty0) - e["v"] * scale) < 0.05


def test_negative_flows_geometry(flow_db, bl_rows):
    """Negative flows: honest negative values, zero-width bands, node-side
    compression so positive bands still fit (the documented layout rule)."""
    payload, _ = _build(flow_db, bl_rows)
    river = payload["spend"]["by_fy"]["2025"]
    nodes = river["nodes"]
    total = next(n for n in nodes if n["level"] == "total")
    scale = (total["y1"] - total["y0"]) / total["value"]

    # negative node → zero height
    other_office = next(n for n in nodes if n["id"] == "s:2025:other:office")
    assert other_office["y1"] == other_office["y0"]

    pos_out: dict[int, float] = {}
    pos_in: dict[int, float] = {}
    for e in river["edges"]:
        pos_out[e["s"]] = pos_out.get(e["s"], 0.0) + max(e["v"], 0.0)
        pos_in[e["t"]] = pos_in.get(e["t"], 0.0) + max(e["v"], 0.0)

    def factor(node, pos_sum):
        return min(1.0, max(node["value"], 0.0) / pos_sum) if pos_sum > 0 else 0.0

    saw_negative = False
    for e in river["edges"]:
        sn, tn = nodes[e["s"]], nodes[e["t"]]
        sy0, sy1, ty0, ty1 = e["g"]
        if e["v"] < 0:
            saw_negative = True
            assert sy1 - sy0 == 0 and ty1 - ty0 == 0, "negative flow must be zero-width"
        exp_s = max(e["v"], 0.0) * scale * factor(sn, pos_out.get(e["s"], 0.0))
        exp_t = max(e["v"], 0.0) * scale * factor(tn, pos_in.get(e["t"], 0.0))
        assert abs((sy1 - sy0) - exp_s) < 0.05
        assert abs((ty1 - ty0) - exp_t) < 0.05
        # containment
        assert sn["y0"] - 1e-6 <= sy0 <= sy1 <= sn["y1"] + 1e-6
        assert tn["y0"] - 1e-6 <= ty0 <= ty1 <= tn["y1"] + 1e-6
    assert saw_negative, "fixture must exercise a negative edge"


# ---------------------------------------------------------------------------
# Bridge honesty
# ---------------------------------------------------------------------------


def test_bridge_remainder_exact(flow_db, bl_rows):
    payload, _ = _build(flow_db, bl_rows)
    br = payload["budget"]["bridge"]
    # crosswalked pes: 0601101E (300000) + 0601104A (100000) = 400000
    assert D(br["crosswalked_total_str"]) == D("400000.000")
    assert D(br["budget_total_str"]) == D("530000.000")
    # THE bridge-honesty identity — exact, no tolerance
    assert (
        D(br["budget_total_str"]) - D(br["crosswalked_total_str"])
        == D(br["not_yet_crosswalked_str"])
    )
    assert br["crosswalked_pe_count"] == 2
    assert br["high_confidence_pe_count"] == 1
    # the two band nodes exist and carry the same values
    cw = _node_by_id(payload["budget"], "b:bridge:crosswalked")
    ny = _node_by_id(payload["budget"], "b:bridge:not-crosswalked")
    assert D(str(cw["value"])) == D(br["crosswalked_total_str"])
    assert D(str(ny["value"])) == D(br["not_yet_crosswalked_str"])
    # program detail: families via HIGH-confidence crosswalk links only.
    # 0601101E has a high (→ACME PARENT) and a medium (→BETA LLC) link: the
    # PE is 'high' and BETA LLC must NOT appear (medium fan-out excluded).
    progs = {p["pe_bli"]: p for p in br["programs"]}
    assert progs["0601101E"]["confidence"] == "high"
    assert progs["0601101E"]["families"] == [
        {"family_key": "ACME PARENT", "confidence": "high"}
    ]
    assert progs["0601104A"]["confidence"] == "medium"
    assert progs["0601104A"]["families"] == []
    assert br["crosswalk_universe_pe_count"] == 2
    assert "not yet crosswalked" in br["coverage_note"]


# ---------------------------------------------------------------------------
# Citations
# ---------------------------------------------------------------------------


def test_budget_node_citations_recompute(flow_db, bl_rows):
    payload, rows = _build(flow_db, bl_rows)
    cits = _cit_index(rows)
    bl_amounts = {r[0]: r[11] for r in bl_rows}
    for n in payload["budget"]["nodes"]:
        assert n["fid"], f"budget node {n['id']} lacks a citation"
        row = cits[n["fid"]]
        kind, formula, inputs_raw, recorded = row[1], row[20], row[21], row[23]
        assert kind == "derived"
        assert formula.startswith("sum(budget_lines"), n["id"]
        inputs = json.loads(inputs_raw)
        assert len(inputs) >= 1
        # recompute: the _verify_derived 4c contract
        got = sum(D(str(bl_amounts[f])) for f in inputs)
        assert got == D(recorded), f"{n['id']}: {got} != {recorded}"
        assert D(str(n["value"])) == D(recorded)


def test_budget_edges_cite(flow_db, bl_rows):
    payload, rows = _build(flow_db, bl_rows)
    cits = _cit_index(rows)
    b = payload["budget"]
    for e in b["edges"]:
        assert e["f"] in cits, "budget edge without resolvable citation"
        recorded = cits[e["f"]][23]
        tgt = b["nodes"][e["t"]]
        if not tgt["id"].startswith(("b:other:", "b:bridge:")):
            # tree edge cites its child node fact — identical value
            assert e["f"] == tgt["fid"]
            assert D(str(e["v"])) == D(recorded)


def test_spend_citations_flow_children_recompute(flow_db, bl_rows):
    payload, rows = _build(flow_db, bl_rows)
    cits = _cit_index(rows)
    river = payload["spend"]["by_fy"]["2025"]
    for e in river["edges"]:
        row = cits[e["f"]]
        assert row[1] == "derived"
        assert row[20].startswith("sum(contracts.federal_action_obligation")
        assert row[22] is not None  # query_body
        body = json.loads(row[22])
        assert body["fy"] == 2025
        assert D(row[23]) == D(str(e["v"]))
    for i, n in enumerate(river["nodes"]):
        row = cits[n["fid"]]
        formula, inputs_raw, recorded = row[20], row[21], row[23]
        assert formula.startswith("sum(flow_children"), n["id"]
        inputs = json.loads(inputs_raw)
        got = sum(D(cits[f][23]) for f in inputs)
        assert got == D(recorded), f"{n['id']}: {got} != {recorded}"
        assert D(str(n["value"])) == D(recorded)


def test_missing_mart_returns_none(tmp_path, bl_rows):
    db = tmp_path / "empty.duckdb"
    duckdb.connect(str(db)).close()
    payload, rows = build_flow_chart(duckdb_path=db, bl_rows=bl_rows)
    assert payload is None
    assert rows == []


# ---------------------------------------------------------------------------
# Label layout (F3 — precomputed, collision-free inline labels)
# ---------------------------------------------------------------------------

from govbudget.flow_chart import (  # noqa: E402  (grouped with the section)
    GUTTER_GAP,
    GUTTER_MIN_H,
    LABEL_H,
    MIN_LABEL_H,
    WIDTH,
    _node_label_w,
)


def _label_bbox(node, units):
    """Axis-aligned bbox of a node's exported inline label (None if hidden).

    Recomputed with the SAME estimator the exporter used — the invariant
    under test is the exporter's own geometry model, end to end.
    """
    lbl = node.get("lbl")
    if lbl is None:
        return None
    w = _node_label_w(node["label"], node["value"], units)
    x0 = lbl["x"] if lbl["a"] == "s" else lbl["x"] - w
    return (x0, lbl["y"] - LABEL_H / 2.0, x0 + w, lbl["y"] + LABEL_H / 2.0)


def _bboxes_overlap(a, b):
    return not (
        a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]
    )


def _assert_labels_clean(nodes, units, what):
    """Zero overlapping label bboxes + every label inside the viewBox."""
    boxes = []
    for n in nodes:
        bb = _label_bbox(n, units)
        if bb is None:
            continue
        assert -0.01 <= bb[0] and bb[2] <= WIDTH + 0.01, (
            f"{what}: label for {n['id']} leaves the viewBox horizontally: {bb}"
        )
        assert -LABEL_H <= bb[1] and bb[3] <= 640.0 + LABEL_H, (
            f"{what}: label for {n['id']} leaves the viewBox vertically: {bb}"
        )
        boxes.append((n["id"], bb))
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            assert not _bboxes_overlap(boxes[i][1], boxes[j][1]), (
                f"{what}: labels collide: {boxes[i][0]} × {boxes[j][0]}"
                f" ({boxes[i][1]} ∩ {boxes[j][1]})"
            )


@pytest.fixture()
def collision_db(tmp_path: Path) -> Path:
    """A fixture engineered to force label collisions under naive placement.

    Budget river: long budget-activity labels (start-anchored, extending
    right) sit at the same y as long program labels (end-anchored, extending
    left) — the exact 'BA label overruns program label' judge finding — and a
    TINY high-confidence crosswalked bridge band reproduces the 'Not yet
    crosswalked clips the value above it' finding. Spend river: long office
    labels vs long ALL-CAPS family labels, plus a stack of thin adjacent
    family nodes to exercise gutter stacking + leader lines.
    """
    db = tmp_path / "collide.duckdb"
    con = duckdb.connect(str(db))
    con.execute(f"create table fct_flow_edges ({FLOW_COLS})")

    long_ba = "Advanced Component Development and Prototypes"
    budget = []
    for i, (comp, clabel) in enumerate(
        [("N", "Department of the Navy"), ("F", "Department of the Air Force")]
    ):
        acct = f"{i}400{comp}"
        alabel = f"Research, Development, Test and Evaluation, {clabel}"
        v = 400000.0 - i * 1000.0
        budget += [
            ("budget", 2026, "total", "TOTAL", "FY2026 PB", "component",
             comp, clabel, None, None, v, 1, "USD_thousands"),
            ("budget", 2026, "component", comp, clabel, "appropriation",
             f"{comp}|{acct}", alabel, None, None, v, 1, "USD_thousands"),
            ("budget", 2026, "appropriation", f"{comp}|{acct}", alabel,
             "budget_activity", f"{comp}|{acct}|04", long_ba,
             None, None, v, 1, "USD_thousands"),
            ("budget", 2026, "budget_activity", f"{comp}|{acct}|04", long_ba,
             "program", f"{comp}|{acct}|04|060{i}101X",
             f"Extremely Long Program Title Number {i} For Collisions",
             None, None, v, 1, "USD_thousands"),
        ]
    # a TINY crosswalked program → near-hairline crosswalked bridge band
    budget += [
        ("budget", 2026, "total", "TOTAL", "FY2026 PB", "component",
         "N", "Department of the Navy", None, None, 4000.0, 1,
         "USD_thousands"),
        ("budget", 2026, "component", "N", "Department of the Navy",
         "appropriation", "N|0400N",
         "Research, Development, Test and Evaluation, Department of the Navy",
         None, None, 4000.0, 1, "USD_thousands"),
        ("budget", 2026, "appropriation", "N|0400N",
         "Research, Development, Test and Evaluation, Department of the Navy",
         "budget_activity", "N|0400N|04", long_ba, None, None, 4000.0, 1,
         "USD_thousands"),
        ("budget", 2026, "budget_activity", "N|0400N|04", long_ba,
         "program", "N|0400N|04|0609999X", "Tiny Crosswalked Program",
         None, None, 4000.0, 1, "USD_thousands"),
    ]
    spend = [
        ("spend", 2025, "office", "DEPT ARMY|DHA", "DEFENSE HEALTH AGENCY",
         "family", "HUNTINGTON INGALLS INDUSTRIES",
         "HUNTINGTON INGALLS INDUSTRIES", "full_and_open", "3-4",
         50_000.0, 3, "USD"),
        ("spend", 2025, "office", "DEPT ARMY|DHA", "DEFENSE HEALTH AGENCY",
         "family", "NORTHROP GRUMMAN CORPORATION",
         "NORTHROP GRUMMAN CORPORATION", "not_competed", "1",
         49_000.0, 1, "USD"),
        ("spend", 2025, "office", "DEPT NAVY|NAVAL AIR SYSTEMS COMMAND",
         "NAVAL AIR SYSTEMS COMMAND", "family", "RTX", "RTX",
         "other_than_full", "2", 48_000.0, 2, "USD"),
    ]
    # thin adjacent families → gutter labels must stack with leader lines
    for k in range(6):
        spend.append(
            ("spend", 2025, "office", "DEPT NAVY|NAVAL AIR SYSTEMS COMMAND",
             "NAVAL AIR SYSTEMS COMMAND", "family", f"THIN FAMILY {k}",
             f"THIN FAMILY {k}", "set_aside", "2", 400.0 + k, 1, "USD")
        )
    con.executemany(
        "insert into fct_flow_edges values (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        budget + spend,
    )
    # tiny high-confidence crosswalk → near-hairline crosswalked bridge band
    con.execute(
        "create table fct_budget_to_awards as select * from (values"
        " ('0609999X','PIID1','high')) t(pe_bli, award_piid, confidence)"
    )
    con.execute(
        "create table fct_award_transactions as select * from (values"
        " ('PIID1','UEI1',1000.0)) t(award_id_piid, recipient_uei, obligation)"
    )
    con.execute(
        "create table entity_xwalk as select * from (values"
        " ('UEI1','HUNTINGTON INGALLS INDUSTRIES'))"
        " t(recipient_uei, family_key)"
    )
    con.close()
    return db


@pytest.fixture()
def collision_bl_rows():
    rows = []
    for i, comp in enumerate(["N", "F"]):
        acct = f"{i}400{comp}"
        rows.append(_bl_row(
            comp, acct, "04", f"060{i}101X",
            f"Extremely Long Program Title Number {i} For Collisions",
            400000 - i * 1000,
        ))
    rows.append(_bl_row(
        "N", "0400N", "04", "0609999X", "Tiny Crosswalked Program", 4000,
    ))
    return rows


def _build_collide(collision_db, collision_bl_rows, top_n=12):
    return build_flow_chart(
        duckdb_path=collision_db, bl_rows=collision_bl_rows,
        top_n=top_n, default_fy=2025,
    )


def test_label_bboxes_never_overlap(collision_db, collision_bl_rows):
    """THE F3 invariant: zero intersecting label bboxes, river-wide."""
    payload, _ = _build_collide(collision_db, collision_bl_rows)
    b = payload["budget"]
    _assert_labels_clean(b["nodes"], b["units"], "budget")
    s = payload["spend"]
    for fy, river in s["by_fy"].items():
        _assert_labels_clean(river["nodes"], s["units"], f"spend FY{fy}")


def test_thin_midcolumn_labels_suppressed(flow_db, bl_rows):
    """Mid-column nodes thinner than MIN_LABEL_H export NO inline label —
    their name/value stay reachable via tooltip + aria (client contract)."""
    payload, _ = _build(flow_db, bl_rows)
    for river, units in [
        (payload["budget"], payload["budget"]["units"]),
        (payload["spend"]["by_fy"]["2025"], payload["spend"]["units"]),
    ]:
        last_x1 = max(n["x1"] for n in river["nodes"])
        for n in river["nodes"]:
            if n["x1"] >= last_x1 - 1e-9:
                continue  # last column has its own gutter rules
            if (n["y1"] - n["y0"]) < MIN_LABEL_H:
                assert "lbl" not in n, (
                    f"{n['id']} is {n['y1'] - n['y0']:.2f} tall (<{MIN_LABEL_H})"
                    " but still carries an inline label"
                )
        _assert_labels_clean(river["nodes"], units, "flow_db river")


def test_last_column_gutter_labels_and_leaders(collision_db, collision_bl_rows):
    """Destination-column labels live OUTSIDE the band (right gutter),
    start-anchored, stacked without overlap; displaced labels carry a short
    leader line back to their node."""
    payload, _ = _build_collide(collision_db, collision_bl_rows)

    # budget bridge: BOTH bands labeled — including the near-hairline
    # crosswalked band (the judge's 'clipped bridge label' case)
    b = payload["budget"]
    last_x1 = max(n["x1"] for n in b["nodes"])
    assert last_x1 < WIDTH  # a gutter is actually reserved
    for n in b["nodes"]:
        if n["level"] != "bridge":
            continue
        if (n["y1"] - n["y0"]) >= GUTTER_MIN_H:
            assert n["lbl"]["a"] == "s"
            assert n["lbl"]["x"] >= last_x1 + GUTTER_GAP - 0.01
    cw = _node_by_id(b, "b:bridge:crosswalked")
    assert (cw["y1"] - cw["y0"]) < MIN_LABEL_H  # genuinely thin in this fixture
    assert "lbl" in cw  # ... and still labeled, in the gutter

    # spend family column: thin adjacent nodes stack downward; at least one
    # displaced label carries a leader line [x0, y0, x1, y1]
    river = payload["spend"]["by_fy"]["2025"]
    fam = [n for n in river["nodes"] if n["level"] == "family" and "lbl" in n]
    assert len(fam) >= 8
    ys = [n["lbl"]["y"] for n in sorted(fam, key=lambda n: n["y0"])]
    for a, bb in zip(ys, ys[1:]):
        assert bb - a >= LABEL_H - 0.01, "gutter labels must not stack onto each other"
    leaders = [n for n in fam if "ldr" in n]
    assert leaders, "displaced gutter labels must carry a leader line"
    for n in leaders:
        x0, y0, x1, y1 = n["ldr"]
        assert n["x1"] <= x0 <= x1 <= n["lbl"]["x"]
        assert abs(y0 - (n["y0"] + n["y1"]) / 2) <= LABEL_H
        assert abs(y1 - n["lbl"]["y"]) <= 0.01


def test_label_layout_deterministic(collision_db, collision_bl_rows):
    p1, _ = _build_collide(collision_db, collision_bl_rows)
    p2, _ = _build_collide(collision_db, collision_bl_rows)
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)


REAL_PAYLOAD = Path(__file__).resolve().parents[1] / "data/site/json/flow_chart.json"


@pytest.mark.skipif(not REAL_PAYLOAD.exists(), reason="no exported payload")
def test_real_export_labels_clean():
    """The SHIPPED payload must satisfy the F3 invariant too — this is the
    'verify zero overlapping label bboxes in the payload' acceptance check."""
    payload = json.loads(REAL_PAYLOAD.read_text())
    b = payload["budget"]
    _assert_labels_clean(b["nodes"], b["units"], "real budget")
    # the bridge bands are the judge finding — both must be labeled
    for nid in ("b:bridge:crosswalked", "b:bridge:not-crosswalked"):
        assert "lbl" in _node_by_id(b, nid), f"{nid} lost its label"
    s = payload["spend"]
    for fy, river in s["by_fy"].items():
        _assert_labels_clean(river["nodes"], s["units"], f"real spend FY{fy}")
        last_x1 = max(n["x1"] for n in river["nodes"])
        for n in river["nodes"]:
            if n["level"] == "family" and (n["y1"] - n["y0"]) >= GUTTER_MIN_H:
                assert "lbl" in n and n["lbl"]["x"] >= last_x1, (
                    f"FY{fy} {n['id']}: family labels belong in the right gutter"
                )


# ---------------------------------------------------------------------------
# Payload size (gate 22 leg a's 600KB budget) — serialization, never the budget
# ---------------------------------------------------------------------------
#
# The 2026-09-06 FY2026 refresh took the real flow_chart.json to 615,051 bytes
# against PAYLOAD_BUDGET_BYTES 614,400. The fix is in what the payload carries
# and how its numbers are written; the budget is not raised. The tests below
# pin three things: the budget itself, that the smaller payload changes no
# value any consumer reads, and that every field a consumer reads survives.

import math  # noqa: E402  (grouped with the section)
import re  # noqa: E402

from govbudget.flow_chart import (  # noqa: E402
    PAYLOAD_BUDGET_BYTES,
    _compact_numbers,
)

_REPO = Path(__file__).resolve().parents[1]

# Every field a consumer of flow_chart.json reads or types as required, by
# object kind: site/src/lib/flow.ts (the /flow/ island's payload types and
# what flow-chart.tsx renders), site/src/lib/data.ts (getFlowChartMeta,
# getFlowsOutsideBridgeCount), gate 22 (flowdown.mjs legs a-d), gate 24 leg p
# and the coverage gate. A size fix may drop a field none of them reads and
# flow.ts types optional; it may never drop one of these.
_CONSUMER_FIELDS = {
    "payload": {"schema_version", "budget", "spend"},
    "budget": {"units", "fiscal_year", "label", "levels", "width", "height",
               "nodes", "edges", "bridge"},
    "bridge": {"budget_total", "budget_total_str", "crosswalked_total",
               "crosswalked_total_str", "not_yet_crosswalked",
               "not_yet_crosswalked_str", "crosswalked_pe_count",
               "crosswalk_universe_pe_count", "high_confidence_pe_count",
               "crosswalked_node", "not_crosswalked_node", "coverage_note",
               "programs"},
    "program": {"pe_bli", "value", "confidence", "families"},
    "family": {"family_key", "confidence"},
    "spend": {"units", "source_note", "competed_classes", "offers_buckets",
              "levels", "default_fy", "fys", "width", "height", "by_fy",
              "notes"},
    "spend_notes": {"fy2026_partial", "offers"},
    "spend_fy": {"total", "total_str", "nodes", "edges"},
    "node": {"id", "fid", "label", "level", "value", "x0", "x1", "y0", "y1"},
    "other": {"count", "members", "omitted", "omitted_value"},
    "member": {"k", "l", "v"},
    "lbl": {"x", "y", "a"},
    "budget_edge": {"s", "t", "v", "f", "g"},
    "spend_edge": {"s", "t", "v", "f", "g", "c", "o"},
}


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _assert_consumer_fields(payload) -> int:
    """Walk the payload; every consumer field present with its JSON type."""
    checked = 0

    def need(obj, kind):
        nonlocal checked
        missing = _CONSUMER_FIELDS[kind] - set(obj)
        assert not missing, f"{kind} lost consumer field(s) {sorted(missing)}"
        checked += 1

    need(payload, "payload")
    b = payload["budget"]
    need(b, "budget")
    need(b["bridge"], "bridge")
    for p in b["bridge"]["programs"]:
        need(p, "program")
        assert isinstance(p["pe_bli"], str) and _is_num(p["value"])
        for f in p["families"]:
            need(f, "family")
    s = payload["spend"]
    need(s, "spend")
    need(s["notes"], "spend_notes")
    rivers = [(b, "budget_edge")] + [
        (s["by_fy"][fy], "spend_edge") for fy in s["by_fy"]
    ]
    for fy in s["by_fy"]:
        need(s["by_fy"][fy], "spend_fy")
        assert _is_num(s["by_fy"][fy]["total"])
    for river, edge_kind in rivers:
        for n in river["nodes"]:
            need(n, "node")
            for k in ("value", "x0", "x1", "y0", "y1"):
                assert _is_num(n[k]), (n["id"], k)
            if "other" in n:
                need(n["other"], "other")
                for m in n["other"]["members"]:
                    need(m, "member")
                    assert _is_num(m["v"])
            if "lbl" in n:
                need(n["lbl"], "lbl")
        for e in river["edges"]:
            need(e, edge_kind)
            assert all(_is_num(x) for x in e["g"]) and len(e["g"]) == 4
            if edge_kind == "spend_edge":
                assert len(e["c"]) == len(COMPETED_CLASSES)
                assert len(e["o"]) == len(OFFERS_BUCKETS)
    return checked


def _gate22_payload_legs(payload) -> list[str]:
    """Python port of gate 22's PAYLOAD-INTERNAL legs, run on parsed JSON.

    Mirrors site/scripts/gates/flowdown.mjs checkRiver (leg a: in/out
    conservation, Other drill-down members+omitted, proportional heights,
    band containment and thickness), leg b's exact milli-unit bridge identity
    and program sum, and leg d's class/offers partitions — same tolerances,
    same float arithmetic the gate does on JSON.parse output. The lake legs
    are not here: they compare payload VALUES to the lake, and
    test_compaction_changes_no_value pins that no value moved.
    """
    TOL_INTERNAL, TOL_CITE = 0.005, 0.001
    errors: list[str] = []

    def milli(s: str) -> int:
        m = re.fullmatch(r"(-?)(\d+)(?:\.(\d{1,3}))?", str(s))
        assert m, f"not a canonical decimal string: {s}"
        v = int(m[2]) * 1000 + int((m[3] or "").ljust(3, "0"))
        return -v if m[1] else v

    def check_river(label, river, terminal, root_level="total"):
        nodes, edges = river["nodes"], river["edges"]
        inflow: dict[int, float] = {}
        outflow: dict[int, float] = {}
        for e in edges:
            outflow[e["s"]] = outflow.get(e["s"], 0) + e["v"]
            inflow[e["t"]] = inflow.get(e["t"], 0) + e["v"]
        for i, n in enumerate(nodes):
            if n["level"] != root_level and abs(inflow.get(i, 0) - n["value"]) > TOL_INTERNAL:
                errors.append(f"a: {label} {n['id']} inflow")
            if n["level"] not in terminal and abs(outflow.get(i, 0) - n["value"]) > TOL_INTERNAL:
                errors.append(f"a: {label} {n['id']} outflow")
            if "other" in n:
                ms = sum(m["v"] for m in n["other"]["members"])
                if abs(ms + n["other"]["omitted_value"] - n["value"]) > TOL_INTERNAL:
                    errors.append(f"a: {label} {n['id']} drilldown")
        root = next(n for n in nodes if n["level"] == root_level)
        if root["value"] > 0:
            scale = (root["y1"] - root["y0"]) / root["value"]
            for n in nodes:
                if abs(n["y1"] - n["y0"] - max(n["value"], 0) * scale) > 0.05:
                    errors.append(f"a: {label} {n['id']} height")
            pos_out: dict[int, float] = {}
            pos_in: dict[int, float] = {}
            for e in edges:
                pos_out[e["s"]] = pos_out.get(e["s"], 0) + max(e["v"], 0)
                pos_in[e["t"]] = pos_in.get(e["t"], 0) + max(e["v"], 0)

            def factor(node, pos):
                return min(1, max(node["value"], 0) / pos) if pos and pos > 0 else 0

            for e in edges:
                sn, tn = nodes[e["s"]], nodes[e["t"]]
                sy0, sy1, ty0, ty1 = e["g"]
                if (sy0 < sn["y0"] - 0.02 or sy1 > sn["y1"] + 0.02
                        or ty0 < tn["y0"] - 0.02 or ty1 > tn["y1"] + 0.02):
                    errors.append(f"a: {label} {sn['id']}->{tn['id']} escapes")
                exp_s = max(e["v"], 0) * scale * factor(sn, pos_out.get(e["s"]))
                exp_t = max(e["v"], 0) * scale * factor(tn, pos_in.get(e["t"]))
                if abs(sy1 - sy0 - exp_s) > 0.05 or abs(ty1 - ty0 - exp_t) > 0.05:
                    errors.append(f"a: {label} {sn['id']}->{tn['id']} thickness")

    b, s = payload["budget"], payload["spend"]
    check_river("budget", b, ("bridge",))
    for fy, river in s["by_fy"].items():
        check_river(f"spend FY{fy}", river, ("family",))
    br = b["bridge"]
    if milli(br["budget_total_str"]) - milli(br["crosswalked_total_str"]) != milli(
            br["not_yet_crosswalked_str"]):
        errors.append("b: bridge remainder not exact")
    by_id = {n["id"]: n for n in b["nodes"]}
    for nid, key in (("b:total", "budget_total_str"),
                     ("b:bridge:crosswalked", "crosswalked_total_str"),
                     ("b:bridge:not-crosswalked", "not_yet_crosswalked_str")):
        if abs(by_id[nid]["value"] - float(br[key])) > TOL_CITE:
            errors.append(f"b: {nid} != {key}")
    if abs(sum(p["value"] for p in br["programs"]) - float(br["crosswalked_total_str"])) > 0.01:
        errors.append("b: programs sum != crosswalked_total")
    if not re.search("not yet crosswalked", br["coverage_note"], re.I):
        errors.append("b: coverage_note lost the gap")
    if s["competed_classes"] != list(COMPETED_CLASSES) or s["offers_buckets"] != list(OFFERS_BUCKETS):
        errors.append("d: vocabulary drifted")
    for fy, river in s["by_fy"].items():
        for e in river["edges"]:
            if abs(sum(e["c"]) - e["v"]) > TOL_INTERNAL or abs(sum(e["o"]) - e["v"]) > TOL_INTERNAL:
                errors.append(f"d: FY{fy} #{e['s']}->#{e['t']} partition")
    return errors


def _as_shipped(payload) -> dict:
    """What every consumer reads: export_site._write_json's bytes, re-parsed."""
    return json.loads(json.dumps(payload, sort_keys=True))


def test_payload_budget_is_never_raised():
    """614,400 bytes here AND in gate 22 — the refresh overshoot is fixed in
    the payload, and a later one must be too."""
    assert PAYLOAD_BUDGET_BYTES == 600 * 1024 == 614_400
    gate = (_REPO / "site/scripts/gates/flowdown.mjs").read_text()
    assert re.search(r"^const PAYLOAD_BUDGET_BYTES = 600 \* 1024;$", gate, re.M)


def test_integral_values_serialize_without_a_trailing_zero(flow_db, bl_rows):
    """JSON has one number type: 30000.0 and 30000 parse to the same double in
    JS and compare equal in Python. The ".0" is two bytes of Python float repr,
    not precision, and the real payload carried 7,158 of them."""
    payload, _ = _build(flow_db, bl_rows)
    raw = json.dumps(payload, sort_keys=True)
    assert re.search(r"\d\.0(?=[,\]}])", raw) is None, (
        re.search(r".{40}\d\.0(?=[,\]}])", raw)
    )
    # the fixture really does carry integral values (else this passes vacuously)
    assert _node_by_id(payload["budget"], "b:other:component")["value"] == 30000


def test_compaction_changes_no_value(flow_db, bl_rows, collision_db,
                                     collision_bl_rows, monkeypatch):
    """Identical numbers, fewer bytes: the payload with compaction disabled
    equals the shipped one value-for-value (Python ==, i.e. 30000 == 30000.0),
    so no rendered number, label, geometry or gate recompute can move."""
    from govbudget import flow_chart

    for build in (lambda: _build(flow_db, bl_rows)[0],
                  lambda: _build_collide(collision_db, collision_bl_rows)[0]):
        shipped = _as_shipped(build())
        with monkeypatch.context() as m:
            m.setattr(flow_chart, "_compact_numbers", lambda obj: obj)
            reference = _as_shipped(build())
        assert shipped == reference
        assert len(json.dumps(shipped, sort_keys=True)) < len(
            json.dumps(reference, sort_keys=True))


def test_compact_numbers_is_exact():
    assert _compact_numbers(2.0) == 2 and type(_compact_numbers(2.0)) is int
    assert type(_compact_numbers(2.5)) is float
    # -0.0 keeps its sign bit: JSON.parse("-0.0") is -0, "0" would be +0
    z = _compact_numbers(-0.0)
    assert type(z) is float and math.copysign(1.0, z) == -1.0
    # 1e16 would print as 17 digits where repr prints "1e+16": left alone
    assert type(_compact_numbers(1e16)) is float
    assert _compact_numbers(True) is True
    assert _compact_numbers({"a": [1.0, {"b": 0.5}], "s": "1.0"}) == {
        "a": [1, {"b": 0.5}], "s": "1.0"}
    assert type(_compact_numbers({"a": [1.0]})["a"][0]) is int


def test_bridge_programs_carry_no_unread_title(flow_db, bl_rows):
    """No consumer reads bridge.programs[].title: the /flow/ list renders the
    PE code (a link to /program/{pe}/, which carries the cited title), the
    confidence badge and the value, and flow.ts types `title` optional. It was
    18,253 bytes of the real payload that nothing drew."""
    payload, _ = _build(flow_db, bl_rows)
    progs = payload["budget"]["bridge"]["programs"]
    assert progs, "fixture must carry bridge programs"
    for p in progs:
        assert "title" not in p, p


def test_consumer_fields_survive(flow_db, bl_rows, collision_db, collision_bl_rows):
    for payload in (_build(flow_db, bl_rows)[0],
                    _build_collide(collision_db, collision_bl_rows)[0]):
        assert _assert_consumer_fields(_as_shipped(payload)) > 20


def test_gate22_payload_legs_hold_on_the_shipped_bytes(
        flow_db, bl_rows, collision_db, collision_bl_rows):
    for payload in (_build(flow_db, bl_rows)[0],
                    _build_collide(collision_db, collision_bl_rows)[0]):
        assert _gate22_payload_legs(_as_shipped(payload)) == []


def test_gate22_payload_port_can_fail(flow_db, bl_rows):
    """Proof the port above is not vacuous: break one value, it reports."""
    shipped = _as_shipped(_build(flow_db, bl_rows)[0])
    shipped["spend"]["by_fy"]["2025"]["edges"][0]["c"][0] += 1
    shipped["budget"]["bridge"]["not_yet_crosswalked_str"] = "1.000"
    errs = _gate22_payload_legs(shipped)
    assert any(e.startswith("d:") for e in errs)
    assert any(e.startswith("b: bridge remainder") for e in errs)


def _mutate_edge_value(river):
    e = next(e for e in river["edges"] if e["v"] > 0)
    e["v"] += 1
    return "inflow"


def _mutate_edge_value_source(river):
    e = next(e for e in river["edges"] if e["v"] > 0)
    e["v"] += 1
    return "outflow"


def _mutate_drilldown(river):
    n = next(n for n in river["nodes"] if "other" in n)
    n["other"]["omitted_value"] += 1
    return "drilldown"


def _mutate_height(river):
    n = next(n for n in river["nodes"] if n["level"] != "total")
    n["y1"] += 1
    return "height"


def _mutate_escape(river):
    e = next(e for e in river["edges"] if e["v"] > 0)
    e["g"][0] -= 5
    return "escapes"


def _mutate_thickness(river):
    e = next(e for e in river["edges"] if e["v"] > 0)
    sn = river["nodes"][e["s"]]
    # shrink the source band inside its node: contained, wrong thickness
    e["g"][1] = e["g"][0] + (e["g"][1] - e["g"][0]) / 2
    assert e["g"][1] <= sn["y1"] + 0.02
    return "thickness"


@pytest.mark.parametrize("mutate", [
    _mutate_edge_value, _mutate_edge_value_source, _mutate_drilldown,
    _mutate_height, _mutate_escape, _mutate_thickness,
])
def test_gate22_payload_port_leg_a_each_check_can_fail(flow_db, bl_rows, mutate):
    """Polish (Task 29 fix round, closed in the Task 26 fix wave): one
    mutation per leg-a check the port carries — in/out conservation, the
    Other drill-down's members + omitted, proportional height, band
    containment and band thickness. The unmutated payload is clean, so each
    named error is the mutation's own."""
    shipped = _as_shipped(_build(flow_db, bl_rows)[0])
    assert _gate22_payload_legs(shipped) == []
    check = mutate(shipped["budget"])
    errs = _gate22_payload_legs(shipped)
    assert any(e.startswith("a: budget ") and e.endswith(check) for e in errs), errs
