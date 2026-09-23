# Fiscal Receipts visual exhibits

Original, simplified illustrative meshes and posters. Geometry is CC0 1.0.
Submarine and aircraft silhouettes are conceptual public illustrations, not
engineering models. Cyber devices and connections are symbolic. Object counts,
dimensions, positions and component colors are not quantitative budget data.

Rebuild: `scripts/exhibits/build_assets.py` (numpy + Pillow).
Check the shipped geometry with the actual web loader:
`node scripts/exhibits/check_assets.mjs`.
Editable Blender files and reviewed Cycles renders are in `art/exhibits/`.
Recreate them in a fresh background Blender process:

```sh
blender --background --python scripts/exhibits/blender_sources.py -- --render-posters
```

This imports the published GLBs, preserves named objects and topic properties,
and adds lighting, cameras, beveled presentation edges, and a drafting grid.
The site's WebP posters are 1440 × 768 conversions of those Blender PNGs.
`build_assets.py` also produces CPU fallback posters; run Blender and convert
its PNGs after rebuilding geometry to retain the reviewed presentation.
Release verification is recorded in
`docs/superpowers/plans/2026-09-07-visual-exhibits-pilots.md`.

Topics are curated in `site/src/lib/program-exhibits.ts`, each with a narrative
fact ID and source phrase checked against the current sidecars at build time.
Budget figures are always read from the site's summary cards, never from meshes.

## Renderer dependency

The local vendor directory contains Three.js **r180**, MIT licensed, fetched
from https://github.com/mrdoob/three.js/tree/r180 on 2026-09-07. LICENSE is
preserved. Only the addon import specifiers were changed to relative local
paths; library behavior is unchanged. No runtime CDN calls are needed.

- three.module.min.js: Git blob 20d3c112761a519c7780a5ccc9f72a40937fa83b
- three.core.min.js: Git blob 70c40977daa0f6e1e312c6b58e9bfe49cb5a87a4
- GLTFLoader.js: Git blob 38f8c14fb500631f01d39cd54c202eefddcf0987
- OrbitControls.js: Git blob eea26706dae735dade19367026185f6e68f5cf55
- BufferGeometryUtils.js: Git blob c84dc7b2bbc99849373e17a6efae609e326f9536

viewer.js is loaded only when the reader chooses Explore in 3D. It renders on
interaction or resize, has no autonomous animation, supports keyboard rotation,
disposes GPU resources, and leaves the poster and evidence available on failure.
