# Source Code Pro — site type system (identifier face)

Vendored 2026-09-12 for self-hosting from the site origin. Unchanged distributor asset:
no subsetting, format conversion, instancing, outline or internal-name changes.
The version directory (`v31/`) is part of the served path — re-vendor into a new one.

## Files

| Local file under `/fonts/source-code-pro/v31/` | CSS family | Style | Weight | Bytes |
| --- | --- | --- | --- | ---: |
| `SourceCodePro-Variable-Roman.woff2` | `Source Code Pro` | normal | 200–900 (variable) | 21,968 |

Role: `--font-mono` → `--font-id` — identifiers only: PE/BLI numbers, fact-id chips,
cell references, document paths, plate marks. Money is never set in this face
(`--font-figure` points at the serif). Not preloaded; CSS-discovered.

## Google Fonts (official Latin slice)

- Specimen: https://fonts.google.com/specimen/Source+Code+Pro
- css2 request: https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@200..900&display=swap
  (response preserved as `SourceCodePro-GoogleFonts-CSS.txt`); served asset
  https://fonts.gstatic.com/s/sourcecodepro/v31/HI_SiYsKILxRpg3hIP6sJ7fM7PqlPevWnsUnxg.woff2
- Requested user agent: `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36`
- Pinned metadata: `METADATA.txt` = google/fonts `ofl/sourcecodepro/METADATA.pb` at revision
  809e4d8b8d7e9364a914909bb777679606c178b8. Upstream: https://github.com/adobe-fonts/source-code-pro (Adobe, Paul D. Hunt).

## Actual font metadata (fontTools on the vendored bytes, 2026-09-12)

Source Code Pro, Version 1.026; UPM 1000; axes wght 200–900; fsType 0; italicAngle 0;
xHeight 478 / capHeight 660; hhea 984 / −273 / 0; 296 glyphs, 229 mapped; every advance
600 units; GSUB ccmp dnom frac locl numr.

## Zero policy

The default zero is dotted. The served slice carries **no** `zero` GSUB feature, so
`font-feature-settings: "zero"`, `slashed-zero` and `ss03` must never be requested —
they would silently do nothing (and `ss03` un-slashed SF Mono's zero on the old stack).
Escape hatch, not vendored (+67 KB): Adobe's release
`WOFF2/VF/SourceCodeVF-Upright.otf.woff2` (2.042R-u / 1.062R-i / 1.026R-vf) carries
`zero` and the arrow glyphs.

## unicode-range (served, verbatim — declare the same in @font-face)

`U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD`

**Dropped by the Google latin slice:** GSUB `zero`, `onum`, `smcp`, `case`, `cv*`, `ss*`;
code points U+2192 → U+2197 ↗ U+2042 ⁂ (U+2191 ↑ and U+2193 ↓ present).

## Licence

SIL Open Font License 1.1 — `OFL.txt` (google/fonts copy at the pinned revision;
Copyright 2010, 2012 Adobe Systems Incorporated). Reserved font name: Source.

## Integrity and sources

| File | Source URL | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| `v31/SourceCodePro-Variable-Roman.woff2` | https://fonts.gstatic.com/s/sourcecodepro/v31/HI_SiYsKILxRpg3hIP6sJ7fM7PqlPevWnsUnxg.woff2 | 2c935ccea0efa74f1d034628790a2aebfe2ccb6f5d60e8f5b224366066e10188 | 21,968 |
