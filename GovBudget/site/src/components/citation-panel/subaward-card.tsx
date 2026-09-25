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
 * The caveat is authorship-neutral on purpose. An FSRS/FFATA subaward report
 * is filed by the PRIME awardee, so the record establishes that a reported
 * description of the work names this program — NOT that the subawardee
 * described its own work. docs/methodology.md is careful about exactly this
 * ("FSRS subaward reports describe the work a subcontractor performs under a
 * prime contract"); this card must not upgrade that.
 *
 * And the naming clause is conditional: the card supports match_basis = null,
 * and on that path it makes no claim that the description named the program
 * (the same hazard announcement-card.tsx documents at its own :17-24). Every
 * published row carries 'subaward-description-exact' today, so the null path
 * is latent — which is exactly when a false sentence ships unnoticed.
 *
 * Nothing here is a figure: contract dollars come from award data, and the
 * record's own subaward_amount is deliberately not shown.
 *
 * matchBasisPhrase is imported from announcement-card so ONE phrase map
 * serves both cards; it already carries 'subaward-description-exact'.
 *
 * parseSubawardEvidence (integration 2026-09-25, from the receipt-validation
 * work on codex/f15-family-browser) is the panel's fail-closed gate IN FRONT
 * of this card: a subaward row renders only when its body is the exact-basis
 * record with a number and a subawardee, it carries no amount, its formula
 * is the medium 'subaward+lexicon' crosswalk sentence, and its URL is the
 * USAspending page of the very PIID that formula names. Anything else is the
 * panel's degraded state, never this card — a prime-award URL or an amount
 * cannot stand in for link evidence. All 114 published rows pass it
 * (measured 2026-09-25), so the card's non-exact branches below stay latent
 * defence in depth, reachable only by rendering the card directly.
 */

import React from "react";
import { ExternalLink } from "lucide-react";
import { matchBasisPhrase } from "./announcement-card";
import type { SubawardCitation } from "@/lib/data";

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

/** The one match basis that licenses "names this program" (Task 26). */
const SUBAWARD_EXACT_BASIS = "subaward-description-exact";

/** The exporter's provenance sentence for a subaward link; group 1 is the
 *  prime PIID the link names. */
const SUBAWARD_LINK_FORMULA =
  /^crosswalk link: pe_bli=\S+(?: \(account [^)]+\))? matched to award PIID (\S+) via method='subaward\+lexicon', confidence='medium' \(dollars live at award grain in fct_award_transactions\)$/;

const USASPENDING_ORIGINS = ["https://www.usaspending.gov", "https://usaspending.gov"];

/**
 * Fail closed: a prime-award URL or an amount cannot stand in for link
 * evidence. Returns the body only when the whole row is the evidence this
 * card describes (see the header); null sends the panel to its degraded
 * state.
 */
export function parseSubawardEvidence(citation: SubawardCitation): SubawardBody | null {
  try {
    const body = JSON.parse(citation.query_body) as Partial<SubawardBody> | null;
    if (
      !body ||
      typeof body !== "object" ||
      Array.isArray(body) ||
      body.match_basis !== SUBAWARD_EXACT_BASIS ||
      typeof body.subaward_number !== "string" ||
      !body.subaward_number.trim() ||
      typeof body.subawardee !== "string" ||
      !body.subawardee.trim() ||
      citation.recorded_value != null ||
      citation.amount_text != null ||
      citation.amount_thousands != null ||
      citation.units != null
    ) {
      return null;
    }
    const match = citation.formula?.match(SUBAWARD_LINK_FORMULA);
    const url = new URL(citation.official_url);
    if (
      !match ||
      !USASPENDING_ORIGINS.includes(url.origin) ||
      url.username ||
      url.password ||
      url.search ||
      url.hash ||
      !/^\/award\/CONT_AWD_[A-Za-z0-9_.-]+\/?$/.test(url.pathname) ||
      !url.pathname.startsWith(`/award/CONT_AWD_${match[1]}_`)
    ) {
      return null;
    }
    return {
      subaward_number: body.subaward_number,
      subawardee: body.subawardee,
      match_basis: body.match_basis,
    };
  } catch {
    return null;
  }
}

export function SubawardCard({ url, body, formula }: SubawardCardProps) {
  const basisToken =
    typeof body.match_basis === "string" ? body.match_basis.trim() : "";
  const basisPhrase = matchBasisPhrase(basisToken);
  const subawardee =
    typeof body.subawardee === "string" && body.subawardee.trim()
      ? body.subawardee.trim()
      : null;

  // What the FSRS record establishes — and only on the one basis that
  // licenses it. Task 26 (polish 7): this was gated on ANY non-empty token,
  // so an LLM-judged or future basis would have claimed the description
  // "names this program". Only subaward-description-exact — the one basis
  // verify_phase5b1's _SUBAWARD_MATCH_BASES admits — makes that claim; any
  // other recorded basis says what it is not, and no basis says so.
  const tail =
    " the link rests on evidence one hop removed from the award itself," +
    " which is why these links publish at medium, never high.";
  const basisCaveat =
    basisToken === SUBAWARD_EXACT_BASIS
      ? "The subaward's reported description of the work names this program," +
        " and the prime award is linked on that basis — evidence one hop" +
        " removed from the award itself, which is why these links publish at" +
        " medium, never high."
      : basisToken
        ? "This match's recorded basis is not an exact description match, so" +
          " nothing here establishes that the record's description named the" +
          " program —" +
          tail
        : "No basis was recorded for this match, so nothing here establishes" +
          " that the record's description named the program —" +
          tail;

  return (
    <div
      className="space-y-3"
      data-cite-kind="subaward"
      data-testid="subaward-card"
    >
      <div>
        <span className="t-label block mb-0.5">
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
        <span className="t-label">
          Prime award URL
        </span>
        <p className="t-id break-all leading-relaxed">
          {url}
        </p>
      </div>

      {/* The record's identity — how to find it on the Subawards tab */}
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="t-label self-center">
          Subaward number
        </dt>
        <dd className="t-id text-foreground break-all" data-testid="subaward-number">
          {body.subaward_number}
        </dd>
        <dt className="t-label self-center">
          Subawardee
        </dt>
        <dd data-testid="subaward-subawardee">{subawardee ?? "not recorded"}</dd>
      </dl>

      {/* How the program was matched — the claim this citation supports */}
      <div className="space-y-0.5">
        <span className="t-label block">
          Match basis
        </span>
        <p className="text-sm" data-testid="subaward-match-basis">
          Matched by: {basisPhrase}
        </p>
      </div>

      {/* Method + confidence tier, as the derived row this replaced stated */}
      {formula && (
        <div>
          <span className="t-label block mb-1">
            Link
          </span>
          <p
            className="t-id rounded bg-muted px-2.5 py-2 break-words leading-relaxed"
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
        award page above lists this record under its Subawards tab, and the
        description itself is not reproduced in this receipt.{" "}
        {basisCaveat} Contract dollars come from award data, not from this
        record.
      </p>
    </div>
  );
}
