import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { WatchFeed } from "@/components/watch-feed";
import { trackReaderEvent } from "@/lib/reader-events";

vi.mock("@/lib/reader-events", () => ({ trackReaderEvent: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const urls = { rss: "https://fiscalreceipts.com/feeds/program/2013.xml", atom: "https://fiscalreceipts.com/feeds/program/2013.atom.xml" };

describe("watch feed actions", () => {
  it("keeps eligible RSS/Atom links and records only a completed copy", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    render(<WatchFeed urls={urls} label="Watch this program" scope="program" program="2013" />);
    fireEvent.click(screen.getByText("Watch this program"));
    expect(screen.getByRole("link", { name: "Atom" })).toHaveAttribute("href", urls.atom);
    fireEvent.click(screen.getByRole("button", { name: "Copy feed address" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("copied"));
    expect(writeText).toHaveBeenCalledWith(urls.rss);
    expect(trackReaderEvent).toHaveBeenCalledExactlyOnceWith("watch_feed_copied", { program: "2013", surface: "watch_program", format: "rss" });
  });
  it("provides a selectable fallback without counting a failed copy", async () => {
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: vi.fn().mockRejectedValue(new Error("denied")) } });
    render(<WatchFeed urls={urls} label="Watch this program" />);
    fireEvent.click(screen.getByText("Watch this program"));
    fireEvent.click(screen.getByRole("button", { name: "Copy feed address" }));
    expect(await screen.findByLabelText("RSS address")).toHaveValue(urls.rss);
    expect(trackReaderEvent).not.toHaveBeenCalled();
  });
  it("does not advertise a feed when the existing eligibility resolver has none", () => {
    render(<WatchFeed urls={null} label="Watch this program" />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText(/No watch feed is available/)).toBeVisible();
  });
});
