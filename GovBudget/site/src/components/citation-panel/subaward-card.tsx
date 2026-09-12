"use client";

/**
 * subaward-card.tsx — Display card for subaward citations (#84).
 *
 * The evidence behind a 'subaward+lexicon' budget→award link: an FSRS
 * subaward record whose description of the subcontractor's work names a
 * program the PE's own narrative owns. Shows:
 *   - The prime award's USAspending page (the durable public artifact —
 *     USAspending publishes no page for an individual subaward; the prime
 *     page's Subawards tab lists the record)
 *   - The subaward number and the subawardee, so the record can be found
 *   - HOW the program was matched, in words (match_basis)
 *   - The link's method and confidence tier (formula), as the derived row
 *     this replaced used to state
 *   - The caveat that the evidence is one hop removed from the award — the
 *     reason this tier publishes at medium
 *
 * Nothing here is a figure: contract dollars come from award data, and the
 * record's own subaward_amount is deliberately not shown.
 *
 * matchBasisPhrase is imported from announcement-card so ONE phrase map
 * serves both cards; it already carries 'subaward-description-exact'.
 */

import React from "react";
import { ExternalLink } from "lucide-react";
import { matchBasisPhrase } from "./announcement-card";

export interface SubawardBody {
  subaward_number: string;
  subawardee?: string | null;
  /** How the record's description was matched to this PE; null when the
   *  verification packet recorded no basis. */
  match_basis?: string | null;
}

interface SubawardCardProps {
  url: string;
  body: SubawardBody;
  /** The link's provenance sentence (crosswalk method + confidence tier),
   *  carried over from the derived row this citation replaced. */
  formula?: string | null;
}

export function SubawardCard({ url, body, formula }: SubawardCardProps) {
  const basisPhrase = matchBasisPhrase(body.match_basis);
  const subawardee =
    typeof body.subawardee === "string" && body.subawardee.trim()
      ? body.subawardee.trim()
      : null;

  return (
    <div
      className="space-y-3"
      data-cite-kind="subaward"
      data-testid="subaward-card"
    >
      <div>
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground block mb-0.5">
          Source
        </span>
        <p className="text-sm font-medium">FSRS subaward record, via USAspending</p>
      </div>

      {/* The prime award page — prominent action */}
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        data-testid="subaward-prime-link"
        className="flex items-center gap-2 rounded-md border border-border bg-muted/40 px-3 py-2.5 text-sm font-medium hover:bg-muted transition-colors group"
      >
        <ExternalLink
          className="h-4 w-4 shrink-0 text-muted-foreground group-hover:text-foreground transition-colors"
          aria-hidden="true"
        />
        <span>Open the prime award on USAspending.gov</span>
        <span className="sr-only">(opens in new tab)</span>
      </a>

      {/* Raw URL co-cited */}
      <div className="space-y-0.5">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Prime award URL
        </span>
        <p className="font-mono text-xs text-muted-foreground break-all leading-relaxed">
          {url}
        </p>
      </div>

      {/* The record's identity — how to find it on the Subawards tab */}
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground self-center">
          Subaward number
        </dt>
        <dd className="font-mono text-xs break-all" data-testid="subaward-number">
          {body.subaward_number}
        </dd>
        <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground self-center">
          Subawardee
        </dt>
        <dd data-testid="subaward-subawardee">{subawardee ?? "not recorded"}</dd>
      </dl>

      {/* How the program was matched — the claim this citation supports */}
      <div className="space-y-0.5">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground block">
          Match basis
        </span>
        <p className="text-sm" data-testid="subaward-match-basis">
          Matched by: {basisPhrase}
        </p>
      </div>

      {/* Method + confidence tier, as the derived row this replaced stated */}
      {formula && (
        <div>
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground block mb-1">
            Link
          </span>
          <p
            className="rounded bg-muted px-2.5 py-2 font-mono text-xs text-foreground break-words leading-relaxed"
            data-testid="subaward-formula"
          >
            {formula}
          </p>
        </div>
      )}

      <p
        className="text-xs text-muted-foreground leading-relaxed"
        data-testid="subaward-caveat"
      >
        USAspending publishes no page for an individual subaward; the prime
        award page above lists this record under its Subawards tab. The
        subawardee&apos;s description of its own work names this program, and
        the prime award is linked on that basis — evidence one hop removed from
        the award itself, which is why these links publish at medium, never
        high. Contract dollars come from award data, not from this record.
      </p>
    </div>
  );
}
