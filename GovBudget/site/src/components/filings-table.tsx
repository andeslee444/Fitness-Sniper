"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { FilingIndexRow } from "@/lib/data";
import { CompanyName } from "@/components/company-name";
import { companyDisplay } from "@/lib/company-name.mjs";
import { formatCount } from "@/lib/format";

/**
 * FilingsTable — client-side filter/search over the filings index (Task 6a).
 *
 * - year filter (select)
 * - client search input (case-insensitive substring over client + registrant)
 * - mentions-first ordering (pre-sorted by the exporter; filtering preserves it)
 * - capped rendering with "show more" (5,393 rows would bloat the DOM)
 */

interface Props {
  filings: FilingIndexRow[];
}

const PAGE = 100;

export function FilingsTable({ filings }: Props) {
  const [query, setQuery] = useState("");
  const [year, setYear] = useState("");
  const [limit, setLimit] = useState(PAGE);

  const years = useMemo(
    () =>
      [...new Set(filings.map((f) => f.filing_year).filter(Boolean))]
        .sort()
        .reverse() as string[],
    [filings],
  );

  // Haystack: raw + display spellings, lowercased, precomputed ONCE per
  // filings load — not per keystroke. Repo precedent: companies-table.tsx
  // (haystacks memo, :285-307). Both spellings stay searchable: the registry
  // string the LDA recorded and the cased name the row actually shows. Typing
  // what you can see must match, and so must typing what the Senate has on
  // file. Keyed on filing_uuid so the filter below is a bare map lookup.
  const haystacks = useMemo(
    () =>
      new Map(
        filings.map((f) => [
          f.filing_uuid,
          [
            f.client_name ?? "",
            f.registrant_name ?? "",
            f.client_name ? companyDisplay(f.client_name) : "",
            f.registrant_name ? companyDisplay(f.registrant_name) : "",
          ]
            .join(" ")
            .toLowerCase(),
        ]),
      ),
    [filings],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    // Exporter pre-sorts mentions-first / year desc / client asc — keep it.
    return filings.filter((f) => {
      if (year && f.filing_year !== year) return false;
      if (!q) return true;
      return (haystacks.get(f.filing_uuid) ?? "").includes(q);
    });
  }, [filings, haystacks, query, year]);

  const visible = filtered.slice(0, limit);

  /**
   * §P1-7 sort contract (gate 24 leg f). The exporter's declared order is a
   * COMPOSITE — mentions-first, then year desc, then client asc — so the row
   * key is the composite serialized to sort ASCENDING as a plain string:
   * "0|7973|boeing" precedes "1|7974|acme". Filtering and the "load more"
   * limit both preserve it (a filtered prefix of a sorted list is sorted).
   *
   * The key stays on the RAW client_name even though the cell now displays a
   * cased one. The two lowercase to the same string today — measured 0
   * beyond-case divergences, 2026-09-18 — so this is not a behaviour change;
   * it is the contract staying where it was declared. The exporter's order is
   * over the registry strings and gate 24 leg (f) checks this page against
   * that declaration, so the key must not start reading a display string
   * that could later diverge.
   */
  function sortValue(f: FilingIndexRow): string {
    const yr = Number(f.filing_year);
    const yrKey = Number.isFinite(yr)
      ? String(9999 - yr).padStart(4, "0")
      : "9999";
    return `${f.has_mentions ? 0 : 1}|${yrKey}|${(f.client_name ?? "").toLowerCase()}`;
  }

  return (
    <div>
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <input
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setLimit(PAGE);
          }}
          placeholder="Search client or registrant…"
          aria-label="Search filings by client or registrant"
          className="w-full sm:w-72 rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <label htmlFor="filing-year" className="text-sm text-muted-foreground">
          Year:
        </label>
        <select
          id="filing-year"
          value={year}
          onChange={(e) => {
            setYear(e.target.value);
            setLimit(PAGE);
          }}
          className="rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
        >
          <option value="">All years</option>
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
        <span className="text-xs text-muted-foreground ml-auto">
          {formatCount(filtered.length)} filing
          {filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="rounded-lg border border-border overflow-hidden bg-card">
        <div className="overflow-x-auto">
          <table
            className="w-full text-sm"
            data-sort-table="filings"
            data-sort-order="mentions_then_year_desc_then_client:asc"
          >
            <thead className="bg-muted/50">
              <tr>
                <th className="t-label px-4 py-3 text-left">
                  Client
                </th>
                <th className="t-label px-4 py-3 text-left hidden sm:table-cell">
                  Registrant
                </th>
                <th className="t-label px-4 py-3 text-left">
                  Year
                </th>
                <th className="t-label px-4 py-3 text-left hidden md:table-cell">
                  Type
                </th>
                <th className="t-label px-4 py-3 text-right">
                  Program mentions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {visible.map((f) => (
                <tr
                  key={f.filing_uuid}
                  className="hover:bg-muted/40 transition-colors"
                  data-sort-value={sortValue(f)}
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/filing/${f.filing_uuid}/`}
                      className="font-medium text-primary hover:underline"
                    >
                      {f.client_name ? (
                        <CompanyName raw={f.client_name} />
                      ) : (
                        "Unknown client"
                      )}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground hidden sm:table-cell">
                    {f.registrant_name ? (
                      <CompanyName raw={f.registrant_name} />
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground tabular-nums">
                    {f.filing_year ?? "—"}
                  </td>
                  <td className="t-id px-4 py-3 hidden md:table-cell">
                    {f.filing_type ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums">
                    {f.has_mentions ? (
                      <span className="font-medium">{f.mention_count}</span>
                    ) : (
                      <span className="text-muted-foreground/60">0</span>
                    )}
                  </td>
                </tr>
              ))}
              {visible.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-muted-foreground"
                  >
                    No filings match.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {filtered.length > limit && (
        <div className="mt-3 text-center">
          <button
            onClick={() => setLimit((n) => n + PAGE * 5)}
            className="rounded-md border border-border bg-card px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
          >
            Show more ({(filtered.length - limit).toLocaleString("en-US")}{" "}
            remaining)
          </button>
        </div>
      )}
    </div>
  );
}
