#!/usr/bin/env node
/**
 * run-mobile-leg.mjs — standalone runner for gate 3's mobile-viewport leg
 * (390×844, PM Sprint 3 Task 1 / backlog #31). Serves out/ like the verify
 * suite, runs runMobileLeg once, prints PASS/NOTES/ERRORS, exits 0/1.
 *
 * Used to record the proof-can-fail for a new leg: revert a mobile
 * treatment in a scratch copy of the built artifact, run this, restore,
 * run again.
 *
 * THE BODY IS A FUNCTION, not module top-level, and that is the point.
 * The 2026-08-27 tri-persona review deferred "run-mobile-leg.mjs
 * standalone crash — gate fine, runner broken". The crash was real
 * (d78dfec1, 2026-08-31: the leg closed the browser it owned before m4 and
 * m5 used it; gate 3 passes its OWN browser, so gate 3 was structurally
 * blind to it — the bug fired only on the standalone path, which is
 * exactly how a new leg gets proved). Nothing could pin the fix, because a
 * module that does its work at import time cannot be imported by a test.
 * Dependencies are injectable for the same reason.
 *
 *   node scripts/run-mobile-leg.mjs [--port 4182]
 */

import { fileURLToPath } from "url";
import { startServer as defaultStartServer } from "./serve-static.mjs";
import { runMobileLeg as defaultRunMobileLeg } from "./gates/mobile.mjs";

/** Distinct from the suite's 4173 and from the sibling runners
 *  (4179 flowdown, 4181 yearsmatrix, 4183 spine). */
export const DEFAULT_PORT = 4182;

/**
 * Serve out/, run the mobile leg once, print a verdict. Returns the
 * process exit code (0 pass, 1 anything else). Never throws.
 */
export async function runStandaloneMobileLeg({
  port = DEFAULT_PORT,
  startServer = defaultStartServer,
  runMobileLeg = defaultRunMobileLeg,
  log = console.log,
} = {}) {
  let server;
  try {
    server = await startServer(port);
  } catch (e) {
    log("PASS: false");
    log("ERRORS:");
    log(
      `  ✗ could not listen on 127.0.0.1:${port}: ${e.message}` +
        (e.code === "EADDRINUSE"
          ? " — another gate run holds it; re-run with --port <n>"
          : "")
    );
    return 1;
  }

  try {
    const res = await runMobileLeg({ baseUrl: server.url });
    log(`PASS: ${res.pass}`);
    log("NOTES:");
    for (const n of res.notes) log(`  ${n}`);
    if (res.errors.length) {
      log("ERRORS:");
      for (const e of res.errors) log(`  ✗ ${e}`);
    }
    return res.pass ? 0 : 1;
  } catch (e) {
    // The leg blew up instead of returning a verdict. Say so with a
    // verdict line rather than letting it escape as an unhandled
    // rejection — that is how the d78dfec1 breakage looked to a reader.
    log("PASS: false");
    log("ERRORS:");
    log(`  ✗ the leg threw before returning a verdict: ${e.stack ?? e.message}`);
    return 1;
  } finally {
    await server.close();
  }
}

/**
 * Port from `--port <n>`, or DEFAULT_PORT. A `--port` with nothing after it
 * used to yield Number(undefined) → NaN, which http.listen(NaN) turns into
 * "pick any free port" — the runner then served the site on a port the
 * operator never saw and never mentioned it. A non-numeric or out-of-range
 * value did the same. Both now say so on stderr and fall back.
 */
export function parsePort(argv, warn = console.error) {
  const i = argv.indexOf("--port");
  if (i === -1) return DEFAULT_PORT;
  const raw = argv[i + 1];
  const n = Number(raw);
  if (raw === undefined || raw.startsWith("--") || !Number.isInteger(n) || n < 1 || n > 65535) {
    warn(
      `run-mobile-leg: --port ${raw === undefined ? "(no value)" : `"${raw}"`}` +
        ` is not a port number — using ${DEFAULT_PORT}`
    );
    return DEFAULT_PORT;
  }
  return n;
}

// ── CLI mode ───────────────────────────────────────────────────────────
// Same guard serve-static.mjs uses (:236).
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  process.exitCode = await runStandaloneMobileLeg({ port: parsePort(process.argv) });
}
