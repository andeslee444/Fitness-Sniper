import { normalizeAmount, valuesAgree } from "./basis.mjs";
import { isDeepStrictEqual } from "node:util";

/** Older rows and receipts must remain available outside the initial page. */
export function checkFamilyHistoryAssets(history, citations, shippedHistory, shippedShards) {
  const errors = [];
  if (!isDeepStrictEqual(history, shippedHistory)) errors.push("shipped family history differs from the audited export");
  const ids = new Set([history.cumulative.fact_id, ...history.points.flatMap(point => [point.fact_id, ...point.components.map(row => row.fact_id), ...point.program_cells.map(cell => cell.fact_id)])]);
  for (const id of ids) {
    if (!citations[id] || !isDeepStrictEqual(citations[id], shippedShards[id.slice(0, 2)]?.[id])) errors.push(`receipt ${id} is missing or changed in built citation shards`);
  }
  return errors;
}

/** Independent release audit: a family headline is an actuals sum, never one PE. */
export function checkFamilyHistory(root, history, citations, slice) {
  const errors = [];
  const check = (ok, message) => { if (!ok) errors.push(message); };
  const sameIds = (a, b) => [...a].sort().join(",") === [...b].sort().join(",");
  const defaults = history.default_point_ids.map(id => history.points.find(p => p.id === id));
  check(defaults.every(Boolean), "default years must resolve to exported points");
  if (!defaults.every(Boolean)) return errors;
  check(new Set(defaults.map(p => p.fy)).size === defaults.length, "default history double-counts a fiscal year");
  check(defaults.length === history.end_fy - history.start_fy + 1, "history silently omits a covered year");
  const total = history.cumulative;
  const actuals = defaults.filter(p => p.kind === "actuals");
  check(sameIds(total.point_ids, actuals.map(p => p.id)), "cumulative inputs must be exactly the default actuals years");
  check(total.amount_thousands === actuals.reduce((n, p) => n + p.amount_thousands, 0), "cumulative actuals do not add up");
  check(total.start_fy === Math.min(...actuals.map(p => p.fy)) && total.end_fy === Math.max(...actuals.map(p => p.fy)), "cumulative year range disagrees with inputs");

  const checkReceipt = (id, amount, inputs) => {
    const c = citations[id];
    check(c?.kind === "derived" && Number(c.recorded_value) === amount && c.units === history.units, `aggregate ${id} lacks an agreeing derived receipt`);
    let found = [];
    try { found = JSON.parse(c?.inputs ?? "[]"); } catch { /* fails identity below */ }
    check(sameIds(found, inputs), `aggregate ${id} receipt inputs differ from summed records`);
  };
  checkReceipt(total.fact_id, total.amount_thousands, actuals.map(p => p.fact_id));
  for (const point of history.points) {
    check(point.edition - point.fy === { actuals: 2, enacted: 1, request: 0 }[point.kind], `${point.id} fiscal status and edition do not agree`);
    const ids = point.components.map(row => row.fact_id);
    check(new Set(ids).size === ids.length, `${point.id} repeats a source receipt`);
    check(point.amount_thousands === point.components.reduce((n, r) => n + r.amount_thousands, 0), `${point.id} source rows do not sum to the annual total`);
    checkReceipt(point.fact_id, point.amount_thousands, ids);
    for (const row of point.components) {
      const c = citations[row.fact_id];
      check(row.amount_type.startsWith(`fy_${point.fy}_`), `${point.id} input ${row.fact_id} belongs to another fiscal year`);
      check(c?.kind === "workbook" && c.official_url === row.official_url && c.units === history.units, `${point.id} input ${row.fact_id} lacks its government workbook receipt`);
      check(c?.amount_thousands === row.amount_thousands && c?.sheet === row.sheet && c?.cells === row.cells, `${point.id} input ${row.fact_id} amount or locator differs from its receipt`);
      check(/^https:\/\/[^/]+\.(?:mil|gov)\//.test(row.official_url), `${point.id} input ${row.fact_id} does not link to an official workbook`);
    }
  }
  const programIds = history.programs.map(program => program.id);
  check(new Set(programIds).size === programIds.length, "matrix repeats a program identity");
  for (const point of history.points) {
    const cells = point.program_cells;
    check(new Set(cells.map(cell => cell.program_id)).size === cells.length, `${point.id} repeats a program cell`);
    check(sameIds(cells.flatMap(cell => cell.input_fact_ids), point.components.map(row => row.fact_id)), `${point.id} matrix cells do not partition annual inputs`);
    for (const cell of cells) {
      const inputs = point.components.filter(row => row.program_id === cell.program_id);
      check(programIds.includes(cell.program_id) && sameIds(cell.input_fact_ids, inputs.map(row => row.fact_id)), `${point.id} cell ${cell.program_id} combines unrelated program identities`);
      check(cell.amount_thousands === inputs.reduce((sum, row) => sum + row.amount_thousands, 0), `${point.id} cell ${cell.program_id} does not sum its exact inputs`);
      if (inputs.length === 1) check(cell.fact_id === inputs[0].fact_id && cell.dataset === inputs[0].dataset && cell.measure === inputs[0].measure, `${point.id} single-input cell substituted its workbook receipt`);
      else checkReceipt(cell.fact_id, cell.amount_thousands, cell.input_fact_ids);
    }
  }
  const shown = [total.fact_id, defaults.at(-1).fact_id, ...defaults.at(-1).components.map(r => r.fact_id), ...defaults.at(-1).program_cells.map(cell => cell.fact_id)];
  for (const id of shown) check(slice.has(id), `receipt ${id} is absent from the page citation slice`);

  const receipt = root.querySelector('[data-testid="family-receipt"]');
  check(receipt?.getAttribute("data-family-cumulative") === total.fact_id, "headline is not the exported family actuals total");
  const amounts = receipt?.querySelectorAll('[data-testid="family-receipt-figure"] [data-amount]') ?? [];
  check(amounts.length === 1, "headline must show one cited actuals total");
  if (amounts.length === 1) {
    const a = amounts[0];
    for (const [key, value] of Object.entries({ "data-fact-id": total.fact_id, "data-fy": `${total.start_fy}-${total.end_fy}`, "data-measure": "actuals", "data-basis": "toa", "data-entity": `family:${history.family_id}` })) {
      check(a.getAttribute(key) === value, `headline ${key} disagrees with family history`);
    }
    check(valuesAgree(normalizeAmount(a.text), total.amount_thousands * 1000), "rendered headline differs from actuals total");
  }
  const coverage = receipt?.querySelector("[data-history-coverage]")?.text ?? "";
  check(coverage.includes(`FY${history.start_fy}`) && coverage.includes("earlier funding is not included"), "family headline must state its historical coverage limit");
  check(!/Largest cited|lifetime total/i.test(receipt?.text ?? ""), "family headline still ranks one record or claims lifetime coverage");
  const bars = root.querySelectorAll("[data-history-year]");
  check(sameIds(bars.map(b => b.getAttribute("data-history-fact")), defaults.map(p => p.fact_id)), "annual chart omits or substitutes exported years");
  for (const point of defaults) {
    const bar = bars.find(b => b.getAttribute("data-history-fact") === point.fact_id);
    check(bar?.getAttribute("data-history-year") === String(point.fy) && bar?.getAttribute("data-kind") === point.kind && bar?.getAttribute("aria-label")?.startsWith(`FY${point.fy} ${point.measure_label},`), `${point.id} chart year/status differs from its source`);
  }
  const selected = defaults.at(-1);
  const annual = root.querySelector(`[data-history-selected="${selected.id}"] [data-amount]`);
  check(annual?.getAttribute("data-fact-id") === selected.fact_id && valuesAgree(normalizeAmount(annual?.text), selected.amount_thousands * 1000), "initial annual selection disagrees with family total");
  const ledger = root.querySelector('[data-testid="family-ledger"]');
  check(Boolean(ledger?.querySelector("table")), "family sources must be an accessible table, not a selected-year disclosure");
  const columns = ledger?.querySelectorAll("thead [data-history-column]") ?? [];
  check(columns.map(column => column.getAttribute("data-history-column")).join(",") === defaults.map(point => point.id).join(","), "matrix years must be chronological columns");
  const programRows = ledger?.querySelectorAll("[data-history-program]") ?? [];
  check(sameIds(programRows.map(row => row.getAttribute("data-history-program")), programIds), "matrix omits or repeats a program row");
  for (const program of history.programs) {
    const row = programRows.find(row => row.getAttribute("data-history-program") === program.id);
    check(row?.querySelector('th[scope="row"]')?.text.includes(program.code), `matrix row ${program.id} lacks its government code`);
    check(row?.querySelectorAll("[data-history-cell]").length === defaults.length, `matrix row ${program.id} omits year cells`);
    for (const point of defaults) {
      const cell = point.program_cells.find(cell => cell.program_id === program.id);
      const el = row?.querySelector(`[data-history-cell="${point.id}"]`);
      const amount = el?.querySelector("[data-amount]");
      if (cell) {
        check(sameIds((el?.getAttribute("data-history-inputs") ?? "").split(","), cell.input_fact_ids), `${point.id} matrix cell ${program.code} omits or duplicates inputs`);
        check(amount?.getAttribute("data-fact-id") === cell.fact_id && amount?.getAttribute("data-fy") === String(point.fy) && amount?.getAttribute("data-measure") === cell.measure && amount?.getAttribute("data-entity") === program.id && amount?.getAttribute("role") === "button", `${point.id} matrix cell ${program.code} lacks a correctly scoped clickable receipt`);
        check(valuesAgree(normalizeAmount(amount?.text), cell.amount_thousands * 1000), `${point.id} matrix cell ${program.code} rendered amount differs from its source`);
      } else {
        check(!amount && Boolean(el?.text.trim()), `${point.id} matrix invents funding for absent ${program.code}`);
        if (point.missing_programs.includes(program.code)) check(el?.querySelector("[data-history-missing]")?.getAttribute("data-history-missing") === program.code, `${point.id} ledger hides missing record ${program.code}`);
      }
    }
  }
  for (const point of defaults) {
    const amount = ledger?.querySelector(`[data-history-annual="${point.id}"] [data-amount]`);
    check(amount?.getAttribute("data-fact-id") === point.fact_id && amount?.getAttribute("data-fy") === String(point.fy) && amount?.getAttribute("data-measure") === point.measure && valuesAgree(normalizeAmount(amount?.text), point.amount_thousands * 1000), `${point.id} table annual total disagrees with its receipt`);
  }
  const clone = root.querySelector("[data-family-history]")?.clone();
  if (clone) {
    for (const a of clone.querySelectorAll("[data-amount]")) a.remove();
    check(!/\$[\d,]+(\.\d+)?\s*[TBMK]?\b/.test(clone.text), "family history has currency outside a cited figure");
  }
  return errors;
}
