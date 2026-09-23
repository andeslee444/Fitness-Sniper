import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render } from "@testing-library/react";
import FeedPage from "@/app/feed/page";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("renders the real feed subscription controls without invalid nesting or duplicate event keys", () => {
  const errors = vi.spyOn(console, "error").mockImplementation(() => {});
  const { container } = render(<FeedPage />);
  const controls = container.querySelectorAll("[data-feed-subscribe]");
  expect(controls.length).toBeGreaterThan(1);
  for (const control of controls) {
    expect(control.closest("p")).toBeNull();
    expect(control.querySelectorAll("a")).toHaveLength(2);
  }
  const structuralErrors = errors.mock.calls.filter(args => /cannot (be|contain)|same key|hydration/i.test(args.join(" ")));
  expect(structuralErrors).toEqual([]);
});
