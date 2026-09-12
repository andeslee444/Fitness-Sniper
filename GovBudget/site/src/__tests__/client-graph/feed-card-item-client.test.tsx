/**
 * client-graph/feed-card-item-client.test.tsx — ROADMAP #81.
 *
 * Runs ONLY under vitest.client-graph.config.ts, where `server-only` is the
 * REAL package (throws on import) rather than the no-op the main config
 * aliases in. Importing the "use client" card here proves nothing in its
 * import graph is `import "server-only"` — the property `next build`
 * enforces on the client bundle, checked in a second instead of 35 minutes.
 *
 * The two control cases are the proof this file can fail: under this config
 * lib/data.ts and the SERVER card (which renders <FeedHeadline> → lib/data.ts
 * by design) both reject with the real error. A leak into the client twin
 * would make the first case reject with that same message.
 */

import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import type { FeedCard } from "@/lib/data";

const CARD: FeedCard = {
  event_type: "concentration_shift",
  family_key: null,
  figure_fact_id: "a".repeat(16),
  figure_units: "hhi",
  figure_value: 8662.294,
  fiscal_year: 2020,
  headline: "Defense Research Sciences award concentration HHI=8662 (2020)",
  headline_segments: [
    { text: "Defense Research Sciences award concentration HHI=8662 (2020)" },
  ],
  organization: null,
  pe_bli: "0601101E",
  program_url: "/program/0601101E/",
  title: "Defense Research Sciences",
  why_url: "/methodology/#feed-concentration_shift",
  basis: null,
  fy: null,
  measure: null,
  edition: null,
  magnitude: {
    kind: "single",
    units: "dollars",
    from: null,
    to: { label: "FY2020 matched obligations", fy: 2020, value: 25_351_139_885.2, fact_id: "b".repeat(16) },
    delta: null,
    pct_change: null,
  },
};

describe("client graph: feed-card-item-client under the REAL server-only package", () => {
  it("imports and renders without reaching a server-only module", async () => {
    const { FeedCardItemClient } = await import("@/components/feed-card-item-client");
    const { container } = render(
      <FeedCardItemClient card={CARD} companySlug={null} hasProgramPage={true} />,
    );
    expect(container.querySelector("[data-feed-card]")).not.toBeNull();
    expect(container.querySelector("[data-hhi-scope-note]")?.textContent).toContain(
      "Highly Concentrated",
    );
  });

  it("control: lib/data rejects — this config is NOT mocking server-only", async () => {
    await expect(import("@/lib/data")).rejects.toThrow(/Client Component/);
  });

  it("control: the SERVER card rejects — it renders <FeedHeadline> → lib/data by design", async () => {
    await expect(import("@/components/feed-card-item")).rejects.toThrow(/Client Component/);
  });
});
