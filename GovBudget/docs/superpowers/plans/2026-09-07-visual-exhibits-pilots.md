# Visual program pilots — implementation and release status

Requested: continue the three visual pilots and publish to the existing Vercel
`andeslee444s-projects/govbudget` project. Publishing is authorized. **Status:
production export built; automated gates pass after corrections; pilot browser
review and deployment pending; not published.**

## Delivered source

- `/explore/` gallery, homepage entry point, and sitemap entry.
- Program exhibits after the existing answer strip on `2013`, `ATA000`,
  `0604840F`, and `0602668D8Z`. The two F-35 lines remain separate, with their
  own fiscal values, accounting basis, source IDs, and cross-links.
- Three original conceptual scenes: submarine/shipyard, aircraft/support,
  and a symbolic cyber research network. Simplification is stated in captions.
  No component costs, production quantities, or operational specifications
  are inferred from geometry.
- A shared graphite/cyan visual system with a light evidence panel, numbered
  topics, native fiscal-year selector, source-passage links, and share links.
- Still WebP images first; the local Three.js renderer loads only on request.
  Orbit controls, blueprint mode, reset, keyboard rotation/zoom, selectable
  mesh topics, and a still-image fallback. No autonomous render loop.
- Financial values use existing summary sidecars and `Cite`. Narrative
  selections pin an existing fact ID and check a source phrase during build.

## Art pipeline

`scripts/exhibits/build_assets.py` creates GLBs, scene JSON, and CPU-projected
posters under `site/public/exhibits/`, using Python with numpy and Pillow.
`scripts/exhibits/check_assets.mjs` loads those files with the production
GLTFLoader and checks topology bounds, normals, materials, size, and topics.

`scripts/exhibits/blender_sources.py` is prepared to import the GLBs into fresh
Blender scenes and save editable files under `art/exhibits/`, adding cameras
and lighting. **This script has not run successfully and no `.blend` files
have been produced.** Blender 5.2.1 crashes in Metal device initialization
before running the script. The Blender MCP scene read was also rejected because
the tool required approval while the session's approval policy was `never`.
The current images are CPU-rendered illustrations, not Blender renders.

Three.js r180 is vendored from the official tagged upstream source, with its
MIT license and original blob hashes in the public asset README. Only local
import paths were adjusted; no runtime CDN dependency. New assets total 1.6 MB
uncompressed, including source JSON and the renderer dependency. GLBs are
283,104 bytes (Virginia), 39,548 (F-35), and 59,896 (cyber).

## Validation evidence

- Full Vitest run: 1,152 passed, one failed. The failure caught the new use of
  `data-source-text="exhibit-claim"`, which is reserved for registered source
  text. Removed that marker from the authored explanation; retained a distinct
  `data-exhibit-claim` attribute for provenance inspection.
- Affected rerun: 26/26 tests pass (six new exhibit tests plus the 20 source
  classification tests). Tests cover narrative ownership, source clicks, actual
  fiscal metadata switching, keyboard topics, lazy loading and failure fallback,
  and separate F-35 funding routes. A Next Link trailing-slash normalization
  mismatch in the initial test was corrected to assert pathname plus fragment.
- `npx tsc --noEmit`: pass.
- `npm run lint`: zero errors, 18 existing warnings. Third-party vendor files
  are excluded; authored renderer code remains linted.
- `node --check site/public/exhibits/viewer.js`: pass.
- `node scripts/exhibits/check_assets.mjs`: all three assets load, respectively
  219/17/49 meshes, finite geometry/normals, valid indices, all topics present.
- Twenty unique narrative and fiscal fact IDs resolve in the current citation
  registry; existing page citation collection includes all of them.
- All three latest poster files were visually inspected as local images.

## Incomplete checks and access limitations

The following records the initial sandbox attempt. The later operator build
and verification results below supersede its build and gate status.

1. `npm run build` completed asset preparation, then Next Turbopack failed while
   processing CSS: spawning its helper required binding to a local port, denied
   by the session sandbox (`Operation not permitted`). No successful fresh SSG
   export exists. Build log: `/private/tmp/fiscal-exhibits-build.log`.
2. Full `npm run verify` and rendered-page checks have not run for this change.
   A separate offline component harness was generated under
   `/private/tmp/fiscal-exhibits-qa`, but browser policy denied opening its local
   file URL. It was not viewed through another browser surface. That harness
   stubs Next routing and the source drawer; it is not a production build.
3. Blender source generation and native Blender render review remain pending.
4. Vercel's connected app returned no teams and denied the target project.
   The user was given the official reconnect instructions and must choose the
   account that can access `andeslee444s-projects/govbudget`. This restores app
   access only; local build and CLI authorization are separate requirements.

## Remaining release work

### Connection recheck after the user reconnected

Vercel access is now restored. The connected app lists team
`team_b94lNMYEXzNevW7VmSNvdeYZ` (`andeslee444s-projects`) and returns project
`prj_oen0seknELM3lK6UcZPS5252D7QD` (`govbudget`), including the
`fiscalreceipts.com` domain. Existing production is still deployment
`dpl_X9chB9pio9S9Dau3ybL53QQb9b5G`; no deployment was created during the recheck.
Local sandbox restrictions are unchanged, so the blocked build was not retried.

An operator handoff is available:
`bash scripts/exhibits/verify-preview.sh`. It builds, runs the full gate suite,
and starts the repository's preview server on loopback only if those pass.
It saves logs under `site/test-results/exhibits/` and performs no deployment.
The script's shell syntax was checked; it has not been executed in this session.

### Release checklist

- Build and automated verification: completed through the operator run and
  the two corrected-gate reruns recorded below. Rebuild if product source
  changes during visual review; do not rewrite build freshness metadata.
- Verify all four program routes and `/explore/` at desktop, tablet, and mobile
  widths. Check poster still image versus 3D, topic selection by mesh and
  keyboard, blueprint/reset, share restoration, fiscal values/basis/edition,
  source drawer/PDF highlight, failed-WebGL fallback, and no idle animation.
- Finish native Blender import and render review; improve lighting/materials
  and model detail before calling these polished Blender exhibits.
- Once Vercel access, build, and gates pass, use the repository's authorized
  deployment path, `scripts/launch/deploy.sh`, and verify the production routes
  and source assets. No replacement project or hosting service is needed.
- The R2 upload script currently uses `rclone sync` despite comments claiming
  non-deletion. Review that before running a sync; do not assume it is a
  non-destructive copy. This pilot changed no warehouse data or source PDFs.

No commit, deployment, domain change, or external message was made in this run.

## Operator run: failure diagnosed and corrected

The user's Terminal run successfully compiled Next.js, generated 8,368 static
routes, and indexed 4,640 pages. Build metadata records
`2026-09-07T20:42:55.912Z`. Logs are in `site/test-results/exhibits/`.
The full verification run passed 22 of 24 gates. The two failures were:

1. Build gate: its independently maintained sitemap count still expected 14
   static routes rather than 15 after `/explore/` was added. Also, the handoff
   script set `NEXT_PUBLIC_SITE_URL` for the build but not the verification
   command, so the gate compared the correct production URLs to a placeholder.
   Updated the route count and exported the URL for the whole script.
2. Program skeleton: the WHO GETS IT gate parsed everything from the recipient
   card to the following budget section. The intervening exhibit was incorrectly
   included, so its program budget appeared to be recipient money. The bounded
   fragment now selects only `[data-testid="answer-who"]`; amount, tier, named
   entity, and disclaimer-order assertions retain their original requirements.

The regression test first reproduced the mistaken sibling-dollar count (one
failure, three passes), then passed after the element-scoping fix. It also
confirms that nested dollars inside the recipient card remain visible to the
gate, award dataset metadata is preserved, and missing cards remain failures.

A local recheck exposed Node gzip-version variance on the unchanged agency
page: 192,368 raw bytes compress to 50,597 with Node 24.13 / zlib
1.3.1-470d3a2, or 52,253 with Node 24.15 / zlib 1.2.12. Recorded the larger
measured size to avoid overstating headroom. Neither ceiling was raised.

Both corrected gates now pass against the same successful export:
`site/test-results/exhibits/recheck.log`. Gate 21 checks all 2,562 recipient
cards, including 443 award, 5 J-book, 37 lobbying, and 2,077 absence tiers.
Targeted lint passes, shell syntax passes, and all 16 affected tests pass.
No product source changed during these fixes, so another build is unnecessary.
This is evidence from the original 22 passes plus the two passing reruns,
not a claim that a second full 24-gate run was performed.

The user was asked to start `site/scripts/serve-static.mjs` in Terminal for
direct pilot browser review. It serves the built export on loopback only.


## Permission recovery and native Blender review

After the user enabled local execution, Blender and the Vercel CLI both ran
successfully. `vercel whoami` returns `andeslee444`. The repository deployment
dry run resolves the existing `govbudget` project, with no upload performed.

All three editable files now exist under `art/exhibits/`, alongside reviewed
1800 × 960 Cycles renders. Each imports the published GLB and retains its named
objects and topic metadata. The final scenes add a dark world, cool area lights,
a drafting grid, and presentation bevels. Their PNGs were converted to the site's
1440 × 768 WebP posters (93 KB / 67 KB / 73 KB). These are simplified original
illustrations, not engineering models. The initial native render was reviewed,
then the final three renders were reviewed after presentation improvements.

The component now uses the site's actual monospace font token, positions its
poster hotspots over the new renders (including the mobile letterbox offset),
clears stale share status when the selection changes, and restores vertical
touch scrolling after OrbitControls initialization. Selecting the F-35 engine
uses the aircraft topic. Six exhibit tests, targeted ESLint, geometry-loader
checks, and the final production build pass. The new build indexes 4,640 pages.
Logs: `site/test-results/exhibits/build-final.log` and
`site/test-results/exhibits/static-gates-final.log`.

A read-only asset audit passes for the five newest cited PDFs and citation
Parquet. All 20 pilot fact IDs resolve; the three distinct hosted narrative
PDFs return HTTP 206 with PDF magic. The other 15 facts use the existing
registry's official-source links; this work does not create missing PDF/page
coordinates. No warehouse data or source PDFs changed, so `--skip-r2` is
appropriate for the eventual deployment.

Browser review remains blocked by a saved user site-access rule for
`http://127.0.0.1:4173`. The user was asked to remove that Block in Settings →
Browser; no alternate host, port, browser, or indirect browser execution was
used to bypass it. Local execution permission and Vercel authentication are
working. Publishing is already authorized but has not occurred. The live gate
suite and direct pilot browser review still need to run after site access is
allowed.


Final static verification completed: **13/13 gates pass** on the final export,
including build freshness, rendered provenance, program structure, accounting
basis, and independently recomputed data truth. This is the static subset of
the 24-gate suite; browser-dependent gates were not rerun while site access is
blocked. No production deployment has been made.


## Browser access restored and release verification

The user asked to retry, and the original loopback address opened successfully
in the Codex in-app browser. Desktop review confirmed the gallery and all four
program routes, optional 3D loading, blueprint mode, keyboard topics, model
rotation and mesh selection, fiscal-year changes, share URL restoration, and
citation drawers. The submarine and procurement PDFs render with source-page
highlights. The F-35 development narrative uses the existing official-source
fallback. Mobile (390 × 844) and tablet (820 × 1180) checks show no horizontal
overflow in the reviewed routes.

A real cyber hotspot bug was reproduced: the network and research projected
buttons were only 5.7px apart, so the latter intercepted the former's click.
The viewer now anchors the network topic to a network node and research to its
screens; a small layout helper separates all projected buttons with 38px center
spacing while keeping them inside the scene. Three regression tests cover the
observed collision, edge cases, and preservation of already separate points.
Targeted lint passes. Direct browser verification on the rebuilt release is
recorded next.

The full 24-gate verification run completed with **overall PASS**, including
accessibility, degraded-mode, clickthrough, search, performance, basis, and data
truth. Log: `site/test-results/exhibits/verify-final.log`. That run checked the
export before the hotspot correction; the release rebuild, build-freshness
recheck, and direct hotspot regression cover the only subsequent product change.


The release rebuild completed successfully and its build gate passes (including
freshness). In the rebuilt 390px browser viewport, all three cyber 3D buttons
select their own named panels, with repeat selection after blueprint mode and
keyboard rotation. The renderer reports no console warnings/errors. This closes
the observed collision regression. Final build log: `build-release.log`; build
gate log: `build-gate-release.log`; both are under `site/test-results/exhibits/`.
The authorized production deployment was started through
`scripts/launch/deploy.sh --skip-r2`; final outcome follows below.


## Published outcome

Production deployment **dpl_QJDYqoHyR6amh5sPB5su7E1icwYG** completed successfully:
- Gallery: https://fiscalreceipts.com/explore/
- Deployment: https://govbudget-9eycr3ei9-andeslee444s-projects.vercel.app
- Dashboard: https://vercel.com/andeslee444s-projects/govbudget/QJDYqoHyR6amh5sPB5su7E1icwYG

`deploy.sh --skip-r2` returned exit 0. The site was published from `site/out/`;
no R2 sync was needed or performed. All **8** post-deploy source/data/permalink
assertions pass. All **13** pilot production checks pass: four program routes,
the gallery, and byte-for-byte release hashes for all three GLBs, all three
WebP posters, the viewer, and its hotspot layout helper. Logs are
`site/test-results/exhibits/deploy.log` and `production-pilots.log`.

Direct browser verification on the public domain confirms the gallery, the
cyber model's 3D loading, correct network topic selection, blueprint mode, and
the actual page-119 PDF render with source highlight. No console warnings or
errors were reported during this flow. The live gallery tab was retained as
the user-facing deliverable. No commit or push was made; implementation and
editable Blender files remain in this workspace.
