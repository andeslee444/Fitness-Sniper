/**
 * Unit tests for the standalone mobile-leg runner.
 *
 * WHY THIS EXISTS. The 2026-08-27 tri-persona review deferred
 * "run-mobile-leg.mjs standalone crash (chip task_08cdaf37) — gate fine,
 * runner broken". The crash was fixed on 2026-08-31 (d78dfec1:
 * runMobileLeg closed the browser it OWNED in a finally block and then m4
 * and m5 used it; gate 3 never saw it because gate 3 passes its own
 * browser, so ownBrowser was false). Nothing pinned the fix, because the
 * runner could not be imported without being run: its entire body executed
 * at module load.
 *
 * A gate suite whose proving tool has no test surface raises the cost of
 * every future leg. These pin the runner's contract with injected fakes,
 * so they need neither a built site nor a browser.
 *
 * Run via `npm test` (vitest).
 */
import net from "net";
import { describe, it, expect, vi } from "vitest";
import { runStandaloneMobileLeg, DEFAULT_PORT, parsePort } from "../run-mobile-leg.mjs";

function fakeServer() {
  const close = vi.fn(async () => {});
  return {
    close,
    start: vi.fn(async (port) => ({
      url: `http://127.0.0.1:${port}`,
      close,
    })),
  };
}

describe("runStandaloneMobileLeg", () => {
  it("importing the module starts no server (it used to run at import time)", async () => {
    // A fresh import with every listen() watched: http.Server extends
    // net.Server, so a top-level `await startServer(4182)` would call this
    // spy. (Task 26: the test used to assert only that the import returned,
    // which a top-level server on a free port also does.)
    const listen = vi.spyOn(net.Server.prototype, "listen");
    try {
      vi.resetModules();
      const mod = await import("../run-mobile-leg.mjs");
      expect(typeof mod.runStandaloneMobileLeg).toBe("function");
      expect(mod.DEFAULT_PORT).toBe(4182);
      expect(listen).not.toHaveBeenCalled();
    } finally {
      listen.mockRestore();
    }
  });

  it("…and the spy would see one: starting a server calls listen()", async () => {
    // Proof the watch above can fail — the same spy on a real (ephemeral)
    // server does record the call.
    const listen = vi.spyOn(net.Server.prototype, "listen");
    const server = net.createServer();
    try {
      await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
      expect(listen).toHaveBeenCalled();
    } finally {
      listen.mockRestore();
      await new Promise((resolve) => server.close(resolve));
    }
  });

  it("passes the served baseUrl to the leg and returns 0 when it passes", async () => {
    const s = fakeServer();
    const runMobileLeg = vi.fn(async () => ({
      pass: true,
      notes: ["10 nav links checked"],
      errors: [],
    }));
    const lines = [];
    const code = await runStandaloneMobileLeg({
      startServer: s.start,
      runMobileLeg,
      log: (l) => lines.push(l),
    });
    expect(code).toBe(0);
    expect(runMobileLeg).toHaveBeenCalledWith({
      baseUrl: `http://127.0.0.1:${DEFAULT_PORT}`,
    });
    expect(lines).toContain("PASS: true");
    expect(s.close).toHaveBeenCalledTimes(1);
  });

  it("returns 1 and prints every error when the leg fails", async () => {
    const s = fakeServer();
    const lines = [];
    const code = await runStandaloneMobileLeg({
      startServer: s.start,
      runMobileLeg: async () => ({
        pass: false,
        notes: [],
        errors: ["mobile /companies/: 3/12 value(s) outside the 390px viewport"],
      }),
      log: (l) => lines.push(l),
    });
    expect(code).toBe(1);
    expect(lines.join("\n")).toMatch(/outside the 390px viewport/);
    expect(s.close).toHaveBeenCalledTimes(1);
  });

  it("PROOF IT CAN FAIL: a leg that throws still closes the server and reports a verdict", async () => {
    // This is the d78dfec1 shape: the leg blew up mid-run
    // ("browser.newContext: Target page, context or browser has been
    // closed"). The old runner let it escape as an unhandled rejection —
    // no PASS line, no ERRORS line, just a stack.
    const s = fakeServer();
    const lines = [];
    const code = await runStandaloneMobileLeg({
      startServer: s.start,
      runMobileLeg: async () => {
        throw new Error(
          "browser.newContext: Target page, context or browser has been closed"
        );
      },
      log: (l) => lines.push(l),
    });
    expect(code).toBe(1);
    expect(lines).toContain("PASS: false");
    expect(lines.join("\n")).toMatch(/has been closed/);
    expect(s.close).toHaveBeenCalledTimes(1);
  });

  it("PROOF IT CAN FAIL: `--port` with no value falls back instead of listening on NaN", () => {
    // Number(undefined) is NaN, and http.listen(NaN) silently binds an
    // arbitrary free port — the operator reads "4182" in the docs, the
    // server is somewhere else, and nothing says so.
    const warnings = [];
    expect(parsePort(["node", "run-mobile-leg.mjs", "--port"], (w) => warnings.push(w))).toBe(
      DEFAULT_PORT
    );
    expect(warnings.join("\n")).toMatch(/no value/);
  });

  it("parsePort takes a real port, rejects junk and a following flag", () => {
    expect(parsePort(["node", "x", "--port", "4190"])).toBe(4190);
    expect(parsePort(["node", "x"])).toBe(DEFAULT_PORT);
    expect(parsePort(["node", "x", "--port", "abc"], () => {})).toBe(DEFAULT_PORT);
    expect(parsePort(["node", "x", "--port", "--verbose"], () => {})).toBe(DEFAULT_PORT);
    expect(parsePort(["node", "x", "--port", "99999"], () => {})).toBe(DEFAULT_PORT);
    expect(parsePort(["node", "x", "--port", "0"], () => {})).toBe(DEFAULT_PORT);
  });

  it("reports an occupied port instead of an unhandled rejection", async () => {
    const lines = [];
    const code = await runStandaloneMobileLeg({
      startServer: async () => {
        const e = new Error("listen EADDRINUSE: address already in use 127.0.0.1:4182");
        e.code = "EADDRINUSE";
        throw e;
      },
      runMobileLeg: async () => {
        throw new Error("must not be reached");
      },
      log: (l) => lines.push(l),
    });
    expect(code).toBe(1);
    expect(lines.join("\n")).toMatch(/--port/);
  });
});
