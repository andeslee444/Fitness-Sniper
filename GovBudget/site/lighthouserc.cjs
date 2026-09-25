/** @type {import('@lhci/cli').LhciConfig} */
module.exports = {
  ci: {
    collect: {
      staticDistDir: "./out",
      url: [
        "http://localhost/",
        "http://localhost/program/0606301D8Z/",
        "http://localhost/program/0601101E/",
        "http://localhost/company/lockheed-martin/",
        "http://localhost/data/",
        // 2026-09-12, the type system: the two routes that carry the largest
        // display type (the F-15 plate statement) and the densest tabular
        // figures (1,700+ serif ledger cells) — the CLS ≤ 0.1 assertion on the
        // LCP heading is what the metric-matched fallbacks are held to.
        "http://localhost/families/f-15/",
        "http://localhost/programs/",
      ],
      numberOfRuns: 1,
      settings: {
        // Avoid needing a full Chrome install in CI
        chromeFlags: "--no-sandbox --disable-dev-shm-usage",
        // Throttle: desktop-class
        preset: "desktop",
        // Skip service worker (static export)
        disableStorageReset: false,
      },
    },
    assert: {
      assertions: {
        "categories:performance": ["error", { minScore: 0.9 }],
        "largest-contentful-paint": ["error", { maxNumericValue: 2500 }],
        "cumulative-layout-shift": ["error", { maxNumericValue: 0.1 }],
        "total-blocking-time": ["error", { maxNumericValue: 300 }],
      },
    },
    // Reports stay on this machine.  Until 2026-09-25 this was
    // "temporary-public-storage", which posted a report on pages that had not
    // been deployed yet to a public URL on every `npm run verify` (backlog
    // finding #20).  Gate 7 (scripts/verify.mjs runLhci) reads only lhci's
    // exit code, never a report URL, so the target does not change the gate.
    // outputDir resolves against the cwd verify.mjs gives lhci (site/), i.e.
    // site/.lighthouseci/reports/ — ignored by site/.gitignore's
    // `.lighthouseci/`, and outside lhci's own clear-on-collect sweep (which
    // deletes only .lighthouseci/lhr-*.json|html).  The filename carries no
    // timestamp, so each run overwrites the last: one report per URL plus
    // manifest.json, bounded, never accumulating.
    upload: {
      target: "filesystem",
      outputDir: "./.lighthouseci/reports",
      reportFilenamePattern: "%%HOSTNAME%%-%%PATHNAME%%.report.%%EXTENSION%%",
    },
  },
};
