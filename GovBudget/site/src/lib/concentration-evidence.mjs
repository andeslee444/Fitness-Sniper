/** Preserve the cited all-link series; never substitute the high-only sample. */
export function normalizeProgramHHI(value, citations) {
  if (!value || typeof value !== "object") return null;
  const row = value;
  const scoped = "hhi_all" in row;
  const pick = (name) => row[scoped ? `${name}_all` : name];
  const hhi = pick("hhi"), dollars = pick("program_dollars");
  const count = pick("family_count"), top = pick("top_family");
  const hhiId = row[scoped ? "hhi_all_fact_id" : "hhi_fact_id"];
  const dollarsId = row[scoped ? "program_dollars_all_fact_id" : "program_dollars_fact_id"];
  // Sum-of-squares roundoff can exceed 10,000 by a few ULPs. Preserve that
  // exact source value, accepting only machine precision at the upper bound.
  if (typeof hhi !== "number" || !Number.isFinite(hhi) || hhi < 0 || hhi > 10000 + 4 * Number.EPSILON * 10000 ||
      typeof dollars !== "number" || !Number.isFinite(dollars) ||
      typeof count !== "number" || !Number.isInteger(count) || count < 1 ||
      typeof top !== "string" || !top.trim() || typeof hhiId !== "string" || typeof dollarsId !== "string") return null;
  function matches(id, amount, units) {
    const cite = citations[id];
    if (cite?.kind !== "derived" || cite.units !== units || !cite.recorded_value?.trim()) return false;
    const recorded = Number(cite.recorded_value);
    return Number.isFinite(recorded) && Math.abs(recorded - amount) <= 0.0005001 &&
      (!scoped || cite.formula?.includes("high- and medium-confidence links"));
  }
  if (!matches(hhiId, hhi, "Herfindahl-Hirschman Index") || !matches(dollarsId, dollars, "USD")) return null;
  return { hhi, program_dollars: dollars, family_count: count, top_family: top,
    hhi_fact_id: hhiId, program_dollars_fact_id: dollarsId,
    ...(scoped ? { link_scope: "high-and-medium" } : {}) };
}

/** All publishing surfaces must omit claims without a cited canonical destination. */
export function filterSupportedConcentrationCards(feed, programs, citations) {
  const supported = new Set(programs.filter(row => normalizeProgramHHI(row.hhi, citations)).map(row => `/program/${row.slug}/`));
  const cards = feed.cards.filter(card => card.event_type !== "concentration_shift" || supported.has(card.program_url));
  return { ...feed, cards, total: cards.length };
}
