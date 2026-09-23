import { beforeEach, describe, expect, it, vi } from "vitest";
import { track } from "@vercel/analytics";
import { trackReaderEvent, type ReaderEventMetadata } from "@/lib/reader-events";

vi.mock("@vercel/analytics", () => ({ track: vi.fn() }));
beforeEach(() => { vi.mocked(track).mockReset(); });

describe("reader event privacy and resilience", () => {
  it("allows only controlled identifiers and finite counts", () => {
    trackReaderEvent("answer_copied", { program: "F015EX", fiscalYear: 2026, factId: "4a9ae7cc78dcf0ba", surface: "f15", count: NaN, selection: "private notes contain spaces", format: "https://private.example", url: "https://private.example", note: "personal research" } as ReaderEventMetadata);
    expect(track).toHaveBeenCalledExactlyOnceWith("answer_copied", { program: "F015EX", fiscalYear: 2026, factId: "4a9ae7cc78dcf0ba", surface: "f15" });
  });
  it("keeps the action usable when analytics throws", () => {
    vi.mocked(track).mockImplementation(() => { throw new Error("offline"); });
    expect(() => trackReaderEvent("receipt_saved", { program: "2013", count: 1 })).not.toThrow();
  });
});
