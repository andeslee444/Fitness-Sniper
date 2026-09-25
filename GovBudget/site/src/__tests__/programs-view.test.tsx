import React from "react";
import { renderToString } from "react-dom/server";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ProgramsTable } from "@/components/programs-table";
import type { ProgramsTableRow } from "@/lib/programs-row";

const ORGS = ["A", "F"];
const PROGRAMS: ProgramsTableRow[] = [
  { pe: "P1", title: "Alpha project", org: "A", fy24: 10, fy26: 100, fy24Fid: null, fy26Fid: null },
  { pe: "P2", title: "Beta project", org: "F", fy24: 20, fy26: 300, fy24Fid: null, fy26Fid: null },
  { pe: "P3", title: "Gamma project", org: "A", fy24: 30, fy26: 200, fy24Fid: null, fy26Fid: null },
];
const table = () => screen.getByRole("table");
const visiblePrograms = () => Array.from(table().querySelectorAll("tbody tr[data-entity]")).map((row) => row.getAttribute("data-entity"));

afterEach(() => { cleanup(); window.history.replaceState({}, "", "/"); });

describe("shareable programs view", () => {
  it("keeps the prerendered full table and restores a shared query after hydration", async () => {
    window.history.replaceState({}, "", "/programs/?q=Alpha&org=A&sort=title&dir=asc");
    const html = renderToString(<ProgramsTable programs={PROGRAMS} orgs={ORGS} />);
    expect(html).toContain("Alpha project");
    expect(html).toContain("Beta project");
    expect(html).toContain("Gamma project");
    expect(html).toContain('data-sort-order="fy2026_total:desc"');
    render(<ProgramsTable programs={PROGRAMS} orgs={ORGS} />);
    await waitFor(() => expect(screen.getByTestId("programs-filter")).toHaveValue("Alpha"));
    expect(screen.getByRole("combobox")).toHaveValue("A");
    expect(table()).toHaveAttribute("data-sort-order", "title:asc");
    expect(visiblePrograms()).toEqual(["P1"]);
  });

  it("writes filter and sort changes without dropping history state, other parameters, or anchors", async () => {
    const historyState = { __NA: true, tree: ["retained"] };
    window.history.replaceState(historyState, "", "/programs/?ref=report#fact-12345678");
    render(<ProgramsTable programs={PROGRAMS} orgs={ORGS} />);
    // Allow initial URL restoration before user interaction.
    await act(async () => {});
    fireEvent.change(screen.getByTestId("programs-filter"), { target: { value: "Gamma" } });
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "A" } });
    fireEvent.click(screen.getByRole("button", { name: "Program" }));
    const params = new URLSearchParams(window.location.search);
    expect(params.get("q")).toBe("Gamma");
    expect(params.get("org")).toBe("A");
    expect(params.get("sort")).toBe("title");
    expect(params.get("dir")).toBe("asc");
    expect(params.get("ref")).toBe("report");
    expect(window.location.hash).toBe("#fact-12345678");
    expect(window.history.state).toEqual(historyState);
    expect(visiblePrograms()).toEqual(["P3"]);
  });

  it("restores browser navigation and falls back safely for invalid organization or sort parameters", async () => {
    window.history.replaceState({}, "", "/programs/?q=Beta&org=F");
    render(<ProgramsTable programs={PROGRAMS} orgs={ORGS} />);
    await waitFor(() => expect(visiblePrograms()).toEqual(["P2"]));
    act(() => {
      window.history.replaceState({}, "", "/programs/?org=unknown&sort=unsupported&dir=invalid");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(screen.getByTestId("programs-filter")).toHaveValue("");
    expect(screen.getByRole("combobox")).toHaveValue("all");
    expect(table()).toHaveAttribute("data-sort-order", "fy2026_total:desc");
    expect(visiblePrograms()).toEqual(["P2", "P3", "P1"]);
  });
});
