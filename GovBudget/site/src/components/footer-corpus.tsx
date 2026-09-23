"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export interface FooterCorpusCounts {
  programs: number;
  citations: number;
  companies: number;
  agencies: number;
}

/**
 * The corpus statement, ONE sentence with the four linked figures — the
 * [data-stat] contract the linkgraph gate holds on the HOME page only.
 * Iteration 4 rendered it from the root layout, which put its ~600 bytes
 * (and four links) on every page of the site and pushed /companies/ and
 * /coverage/ over their gate-1 weight ceilings. It now renders from the
 * shared footer only when the pathname is "/" — a pathname check, the
 * same mechanism SiteHeader already uses for aria-current, baked per
 * route at static-export time. Sentence moved VERBATIM from layout.tsx;
 * nothing about what it claims has changed.
 */
export function FooterCorpus({ counts }: { counts: FooterCorpusCounts | null }) {
  const pathname = usePathname();
  if (!counts || pathname !== "/") return null;
  return (
    <p className="site-footer-corpus mt-3 text-sm text-muted-foreground">
      Built from{" "}
      <Link href="/programs/" data-stat="programs">
        <strong className="t-figure t-figure--3">{counts.programs.toLocaleString("en-US")}</strong> program elements
      </Link>{" "}
      and{" "}
      <Link href="/methodology/#verification" data-stat="citations">
        <strong className="t-figure t-figure--3">{counts.citations.toLocaleString("en-US")}</strong> source citations
      </Link>{" "}
      across{" "}
      <Link href="/companies/" data-stat="companies">
        <strong className="t-figure t-figure--3">{counts.companies.toLocaleString("en-US")}</strong> contractor families
      </Link>{" "}
      and{" "}
      <Link href="/agency/" data-stat="agencies">
        <strong className="t-figure t-figure--3">{counts.agencies.toLocaleString("en-US")}</strong> agencies
      </Link>
      . Coverage varies by dataset —{" "}
      <Link href="/methodology/#coverage" className="underline">
        see methodology
      </Link>
      .
    </p>
  );
}
