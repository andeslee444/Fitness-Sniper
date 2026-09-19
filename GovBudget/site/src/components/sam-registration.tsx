"use client";

/**
 * SamRegistrationNote — the SAM.gov registration line on /company/{slug}/
 * (ROADMAP #10).
 *
 * WHY THE DENIAL IS IN THE COPY. The spike
 * (docs/superpowers/reviews/10-entity-resolution-spike.md §4) found that
 * `recipient_parent_name` IS the SAM registration name — SAM is where the
 * page's registered name comes from, so showing SAM beside it must not read as
 * corroboration or as a confidence upgrade. The flagship counter-example is a
 * family where SAM recorded a common registered parent and it was wrong. The
 * last sentence of this note says so in the reader's words.
 *
 * CITED OR ABSENT. No `sam` payload, no fact_id, or no registration status →
 * the component renders NOTHING. That is the state every company page is in
 * today (the extract is blocked on an owner-minted key) and the state ~190 of
 * them stay in while a 10-requests/day key works through the published 200.
 *
 * The status token is a <ProseCite>, not a <Cite>: <Cite> marks its text as
 * data-amount, and this is not a currency figure. render-static leg (a1)
 * checks every [data-prose-cite] fact_id resolves in citations.json.
 *
 * WHY THE LAST SENTENCE NAMES THE TIE-BREAK. It used to say this was the
 * registration of "the one its registered name is read from". The mart takes
 * the two from different rules — `display_name` from rn = 1 (row_number, ties
 * broken arbitrarily), the registration from
 * `max(coalesce(parent_uei, recipient_uei)) filter (rk = 1)` — so on an exact
 * obligation tie they can be two different members, and the identity would be
 * a sentence the reader cannot check and the data does not support. And it is
 * that REGISTRATION UEI the max() runs over, not the tied member's own
 * recipient UEI: two tied members with different parents can order the two
 * ways round, so the sentence names the UEI it actually sorts on. 46
 * families in the lake tie at the top, none in today's published 200; the
 * smaller true claim is the one that survives the day one does. The tie-break
 * itself is pinned by
 * tests/test_sam_entities.py::test_dominant_parent_ueis_breaks_an_obligation_tie_the_way_the_mart_does.
 */

import React from "react";
import type { EntitySamRegistration } from "@/lib/data";
import { ProseCite } from "@/components/prose-cite";

export function SamRegistrationNote({ sam }: { sam?: EntitySamRegistration }) {
  if (!sam || !sam.fact_id || !sam.registration_status) return null;
  const bits: string[] = [];
  if (sam.cage_code) bits.push(`CAGE ${sam.cage_code}`);
  if (sam.registration_expiration_date)
    bits.push(`expires ${sam.registration_expiration_date}`);
  if (sam.primary_naics) bits.push(`primary NAICS ${sam.primary_naics}`);
  return (
    <p
      data-sam-registration=""
      className="mb-4 text-xs leading-5 text-muted-foreground"
    >
      SAM.gov registration:{" "}
      <span className="font-mono text-foreground">{sam.uei}</span>
      {sam.legal_business_name ? (
        <>
          {" — "}
          <span className="font-mono text-foreground">
            {sam.legal_business_name}
          </span>
        </>
      ) : null}
      {". Registration "}
      <ProseCite factId={sam.fact_id}>{sam.registration_status}</ProseCite>
      {bits.length > 0 ? `, ${bits.join(", ")}` : ""}.
      {sam.business_types ? ` Business types: ${sam.business_types}.` : ""}{" "}
      This is the registration of the family&rsquo;s largest member by
      obligations &mdash; where members tie, the one whose registration UEI
      sorts highest &mdash; and it does not change how this family was
      resolved.
    </p>
  );
}
