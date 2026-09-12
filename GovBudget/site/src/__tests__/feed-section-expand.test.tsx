/**
 * feed-section-expand.test.tsx — Task 6 (#73) → ROADMAP #88: /feed/
 * sections expand in place past the digest cap, client-side, by fetching
 * the PER-EVENT-TYPE sidecar /json/feed-sections/{event_type}.json — never
 * the whole feed.json.
 *
 * Contract under test:
 *   - Collapsed state renders [data-feed-truncation-note] (gate 23 leg g4
 *     reads the attribute against the static HTML) carrying
 *     data-feed-event-type / data-feed-shown / data-feed-total (gate 8 leg o
 *     reads these), and a "Show all N" button.
 *   - Clicking fetches /json/feed-sections/{eventType}.json and renders
 *     its `cards` (already the cards past the cap — no client filter, no
 *     client slice) via <FeedCardItemClient> (the shared shell, with a
 *     client-safe headline).
 *   - companySlug/hasProgramPage come PRE-RESOLVED on each sidecar card
 *     (company_slug, has_program_page).
 *   - A sidecar cut LOWER than this page's `shown` has its overlap dropped;
 *     the footer states what is on screen, never "all", when short.
 *   - A failed fetch surfaces an error state without crashing.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

import { FeedSectionExpand } from "@/components/feed-section-expand";
import type { FeedSectionCard, FeedSectionSidecar } from "@/lib/data";

function card(pe_bli: string, overrides: Partial<FeedSectionCard> = {}): FeedSectionCard {
  return {
    event_type: "concentration_shift",
    family_key: null,
    figure_fact_id: "f".repeat(16),
    figure_units: "hhi",
    figure_value: 5000,
    fiscal_year: 2022,
    headline: `${pe_bli} award concentration HHI=5000 (2022)`,
    headline_segments: [{ text: `${pe_bli} award concentration HHI=5000 (2022)` }],
    organization: null,
    pe_bli,
    program_url: `/program/${pe_bli}/`,
    title: pe_bli,
    why_url: "/methodology/#feed-concentration_shift",
    basis: null,
    fy: null,
    measure: null,
    edition: null,
    magnitude: null,
    company_slug: null,
    has_program_page: false,
    ...overrides,
  };
}

function sidecar(
  cards: FeedSectionCard[],
  overrides: Partial<FeedSectionSidecar> = {},
): FeedSectionSidecar {
  return {
    event_type: "concentration_shift",
    section_cap: 75,
    shown: 75,
    total: 75 + cards.length,
    cards,
    ...overrides,
  };
}

function jsonResponse(body: unknown): Response {
  return { ok: true, status: 200, json: () => Promise.resolve(body) } as unknown as Response;
}

const SECTION_URL = "/json/feed-sections/concentration_shift.json";

/** The 15 cards past a 75-cap in a 90-card section — indices 75..89. */
function fifteenHidden(): FeedSectionCard[] {
  return Array.from({ length: 15 }, (_, i) => card(String(75 + i).padStart(4, "0")));
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockSection(body: unknown) {
  fetchMock.mockImplementation((url: string) =>
    String(url) === SECTION_URL
      ? Promise.resolve(jsonResponse(body))
      : Promise.reject(new Error(`unmocked fetch ${url}`)),
  );
}

describe("<FeedSectionExpand> — collapsed state", () => {
  it("renders the truncation note with the gate-readable counts and a Show all button", () => {
    const { container } = render(
      <FeedSectionExpand eventType="concentration_shift" shown={75} total={90} />,
    );
    const note = container.querySelector("[data-feed-truncation-note]");
    expect(note).not.toBeNull();
    expect(note!.getAttribute("data-feed-event-type")).toBe("concentration_shift");
    expect(note!.getAttribute("data-feed-shown")).toBe("75");
    expect(note!.getAttribute("data-feed-total")).toBe("90");
    expect(note!.textContent).toContain("75");
    expect(note!.textContent).toContain("90");
    expect(screen.getByRole("button", { name: /show all 90/i })).toBeInTheDocument();
  });

  it("renders no [data-feed-card] and fetches nothing before expansion", () => {
    const { container } = render(
      <FeedSectionExpand eventType="concentration_shift" shown={75} total={90} />,
    );
    expect(container.querySelectorAll("[data-feed-card]").length).toBe(0);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("<FeedSectionExpand> — expand", () => {
  it("fetches the section sidecar (never feed.json), renders its cards, hides the note", async () => {
    mockSection(sidecar(fifteenHidden(), { total: 90 }));
    const { container } = render(
      <FeedSectionExpand eventType="concentration_shift" shown={75} total={90} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /show all 90/i }));

    await waitFor(() => {
      expect(container.querySelectorAll("[data-feed-card]").length).toBe(15);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(SECTION_URL);
    expect(fetchMock).not.toHaveBeenCalledWith("/json/feed.json");
    expect(container.querySelector("[data-feed-truncation-note]")).toBeNull();
    // The sidecar's first card is index 75 — the sequence CONTINUES.
    expect(container.textContent).toContain("0075");
    expect(container.textContent).toContain("Showing all 90 cards in this section.");
  });

  it("interpolates the event type into the sidecar path", async () => {
    fetchMock.mockImplementation((url: string) =>
      String(url) === "/json/feed-sections/yoy_swing.json"
        ? Promise.resolve(
            jsonResponse(
              sidecar([card("0101213F", { event_type: "yoy_swing" })], {
                event_type: "yoy_swing",
                shown: 1,
                total: 2,
              }),
            ),
          )
        : Promise.reject(new Error(`unmocked fetch ${url}`)),
    );
    const { container } = render(
      <FeedSectionExpand eventType="yoy_swing" shown={1} total={2} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /show all 2/i }));
    await waitFor(() => {
      expect(container.querySelectorAll("[data-feed-card]").length).toBe(1);
    });
    expect(fetchMock).toHaveBeenCalledWith("/json/feed-sections/yoy_swing.json");
  });

  it("renders the program link from the card's pre-resolved has_program_page", async () => {
    mockSection(
      sidecar(
        [
          card("0075", { has_program_page: true }),
          card("0076", { has_program_page: false }),
        ],
        { shown: 75, total: 77 },
      ),
    );
    const { container } = render(
      <FeedSectionExpand eventType="concentration_shift" shown={75} total={77} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /show all 77/i }));
    await waitFor(() => {
      expect(container.querySelectorAll("[data-feed-card]").length).toBe(2);
    });
    const links = Array.from(container.querySelectorAll("a")).filter((a) =>
      a.textContent?.includes("view program"),
    );
    expect(links.length).toBe(1);
    // next/link normalizes the trailing slash away under jsdom — same reason
    // feed-headline.test.tsx asserts with toContain, not toBe.
    expect(links[0].getAttribute("href")).toContain("/program/0075");
  });

  it("renders the company link from the card's pre-resolved company_slug", async () => {
    fetchMock.mockImplementation((url: string) =>
      String(url) === "/json/feed-sections/new_entrant.json"
        ? Promise.resolve(
            jsonResponse(
              sidecar(
                [
                  card("", {
                    event_type: "new_entrant",
                    pe_bli: null,
                    program_url: null,
                    family_key: "ACME CORP",
                    headline: "ACME CORP new defense contractor",
                    headline_segments: [{ text: "ACME CORP new defense contractor" }],
                    figure_units: "dollars",
                    figure_value: 2_000_000,
                    why_url: "/methodology/#feed-new_entrant",
                    company_slug: "acme-corp",
                  }),
                  card("", {
                    event_type: "new_entrant",
                    pe_bli: null,
                    program_url: null,
                    family_key: "NOBODY LLC",
                    headline: "NOBODY LLC new defense contractor",
                    headline_segments: [{ text: "NOBODY LLC new defense contractor" }],
                    figure_units: "dollars",
                    figure_value: 1_500_000,
                    why_url: "/methodology/#feed-new_entrant",
                    company_slug: null,
                  }),
                ],
                { event_type: "new_entrant", shown: 0, total: 2 },
              ),
            ),
          )
        : Promise.reject(new Error(`unmocked fetch ${url}`)),
    );
    const { container } = render(
      <FeedSectionExpand eventType="new_entrant" shown={0} total={2} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /show all 2/i }));
    await waitFor(() => {
      expect(container.querySelectorAll("[data-feed-card]").length).toBe(2);
    });
    const companyLink = Array.from(container.querySelectorAll("a")).find((a) =>
      (a.getAttribute("href") ?? "").includes("/company/acme-corp"),
    );
    expect(companyLink).not.toBeUndefined();
    expect(companyLink!.textContent).toBe("ACME CORP");
    // The family outside the top 200 renders as text, flagged for gate 4.
    expect(container.querySelector("[data-no-company-page]")).not.toBeNull();
    expect(
      Array.from(container.querySelectorAll("a")).some((a) =>
        (a.getAttribute("href") ?? "").includes("/company/nobody"),
      ),
    ).toBe(false);
  });

  it("surfaces an error state on a failed fetch, without crashing", async () => {
    fetchMock.mockImplementation(() => Promise.reject(new Error("network down")));
    const { container } = render(
      <FeedSectionExpand eventType="concentration_shift" shown={75} total={90} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /show all 90/i }));
    await waitFor(() => {
      expect(container.textContent).toMatch(/failed to load/i);
    });
    expect(container.querySelector("[data-feed-truncation-note]")).not.toBeNull();
    expect(container.querySelectorAll("[data-feed-card]").length).toBe(0);
  });

  it("surfaces an error on a 404 (a section whose sidecar did not ship)", async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) } as unknown as Response),
    );
    const { container } = render(
      <FeedSectionExpand eventType="concentration_shift" shown={75} total={90} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /show all 90/i }));
    await waitFor(() => {
      expect(container.textContent).toMatch(/HTTP 404/);
    });
    expect(container.querySelectorAll("[data-feed-card]").length).toBe(0);
  });

  it("surfaces an error when the sidecar has no cards array", async () => {
    mockSection({ event_type: "concentration_shift", total: 90 });
    const { container } = render(
      <FeedSectionExpand eventType="concentration_shift" shown={75} total={90} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /show all 90/i }));
    await waitFor(() => {
      expect(container.textContent).toMatch(/no cards array/i);
    });
  });

  // ── K.5 / M8: the footer states what is ON SCREEN, never "all" ──────────
  it("says 'Showing 4 of 5' when the shipped sidecar is short of `total`", async () => {
    // Page built from total=5, shown=3; the shipped file carries only 1
    // card past its own cut at 3 (a file behind a newer page).
    mockSection(sidecar([card("0003")], { shown: 3, total: 4 }));
    const { container } = render(
      <FeedSectionExpand eventType="concentration_shift" shown={3} total={5} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /show all 5/i }));
    await waitFor(() => {
      expect(container.querySelectorAll("[data-feed-card]").length).toBe(1);
    });
    expect(container.textContent).toContain("Showing 4 of 5 cards in this section.");
    expect(container.textContent).not.toContain("Showing all");
  });

  it("counts the server-rendered cards when the sidecar carries nothing past the cap", async () => {
    mockSection(sidecar([], { shown: 3, total: 3 }));
    const { container } = render(
      <FeedSectionExpand eventType="concentration_shift" shown={3} total={5} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /show all 5/i }));
    await waitFor(() => {
      expect(container.textContent).toContain("cards in this section.");
    });
    expect(container.textContent).toContain("Showing 3 of 5 cards in this section.");
    expect(container.textContent).not.toContain("Showing 2 of 5");
  });

  it("drops the overlap when the sidecar was cut LOWER than this page's shown", async () => {
    // Page shows 3; the shipped file was cut at 1 and carries cards 1..4.
    // Cards 1 and 2 are already on screen — render only 3 and 4.
    mockSection(
      sidecar([card("0001"), card("0002"), card("0003"), card("0004")], { shown: 1, total: 5 }),
    );
    const { container } = render(
      <FeedSectionExpand eventType="concentration_shift" shown={3} total={5} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /show all 5/i }));
    await waitFor(() => {
      expect(container.querySelectorAll("[data-feed-card]").length).toBe(2);
    });
    expect(container.textContent).toContain("0003");
    expect(container.textContent).toContain("0004");
    expect(container.textContent).not.toContain("0001 award concentration");
    expect(container.textContent).toContain("Showing all 5 cards in this section.");
  });

  // ── K.3: two hidden cards sharing a pe_bli must not collide on key ───────
  it("renders two cards sharing a pe_bli without a duplicate-key warning", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    mockSection(sidecar([card("0002"), card("0002")], { shown: 1, total: 3 }));
    const { container } = render(
      <FeedSectionExpand eventType="concentration_shift" shown={1} total={3} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /show all 3/i }));
    await waitFor(() => {
      expect(container.querySelectorAll("[data-feed-card]").length).toBe(2);
    });
    const keyWarnings = consoleError.mock.calls
      .map((args) => String(args[0] ?? ""))
      .filter((msg) => /same key|duplicate key|unique "key"/i.test(msg));
    expect(keyWarnings).toEqual([]);
    consoleError.mockRestore();
  });

  it("does not refetch on a second expand", async () => {
    mockSection(sidecar(fifteenHidden(), { total: 90 }));
    const { container } = render(
      <FeedSectionExpand eventType="concentration_shift" shown={75} total={90} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /show all 90/i }));
    await waitFor(() => {
      expect(container.querySelectorAll("[data-feed-card]").length).toBe(15);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
