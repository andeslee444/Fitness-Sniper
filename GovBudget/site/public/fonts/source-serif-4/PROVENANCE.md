# Source Serif 4 — site type system (voice face)

Vendored 2026-09-12 for self-hosting from the site origin. Both files are unchanged
distributor assets: no subsetting, format conversion, instancing, outline or
internal-name changes. Descriptive local filenames; the version directory (`v14/`)
is part of the served path — a re-vendor MUST use a new directory, never overwrite.
The Roman file is the byte-identical asset first vendored 2026-09-09 under
`f15-register/` for the F-15 page; it now serves every page.

## Files

| Local file under `/fonts/source-serif-4/v14/` | CSS family | Style | Weight | Bytes |
| --- | --- | --- | --- | ---: |
| `SourceSerif4Variable-Roman.woff2` | `Source Serif 4` | normal | 200–900 (variable, opsz 8–60) | 122,168 |
| `SourceSerif4-Italic-400.woff2` | `Source Serif 4` | italic | 400 (static, opsz default 20) | 20,132 |

Roles: `--font-serif` — h1/h2/h3, prose, and (through `--font-figure`) every standalone
money figure. `font-optical-sizing: auto` engages the opsz axis. The single italic
covers `<em>` in prose; `font-synthesis: none` on `html` prevents faux italics/bolds.

## Google Fonts (official Latin slices)

- Specimen: https://fonts.google.com/specimen/Source+Serif+4
- Roman css2 request: https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400..700&display=swap
  (response preserved as `SourceSerif4-GoogleFonts-CSS.txt`); served asset
  https://fonts.gstatic.com/s/sourceserif4/v14/vEFI2_tTDB4M7-auWDN0ahZJW1gb8te1Xb7G.woff2
- Italic css2 request: https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@1,400&display=swap
  (response preserved as `SourceSerif4-Italic-GoogleFonts-CSS.txt`); served asset
  https://fonts.gstatic.com/s/sourceserif4/v14/vEF02_tTDB4M7-auWDN0ahZJW1ge6NmXpVAHV83Bfb_US2D2QYxoUKIkn98pRl9tDMQCjDDUXmAz.woff2
- Requested user agent (both): `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36`
- Pinned metadata: `SourceSerif4-GoogleFonts-METADATA.txt` (google/fonts revision
  334b789e33413f3aba4264d9aa6c97f7b94c5a2f, ofl/sourceserif4/METADATA.pb). Upstream:
  https://github.com/adobe-fonts/source-serif (Adobe, Frank Grießhammer).

## Actual font metadata (fontTools on the vendored bytes, 2026-09-12)

- Roman: Source Serif 4, Version 4.004; UPM 1000; axes wght 200–900, opsz 8–60; fsType 0;
  xHeight 475 / capHeight 670; hhea 1036 / −335 / 0; 331 glyphs, 231 mapped; digits 500 units,
  tabular by default; GSUB ccmp dnom frac liga locl numr pnum tnum.
- Italic: Source Serif 4 Italic, Version 4.004; static; italicAngle −12; fsType 0;
  xHeight 475 / capHeight 670; hhea 1036 / −335 / 0; 336 glyphs, 231 mapped; GSUB as Roman.

## unicode-range (served, verbatim — declare the same in @font-face)

`U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD`

**Dropped by the Google latin slice:** GSUB `zero`, `onum`, `smcp`, `case`, `cv*`, `ss*`;
code points U+2192 → and U+2197 ↗ and U+2042 ⁂ (U+2191 ↑ and U+2193 ↓ are present). Text
arrows fall to the fallback face — use the icon system instead.

## Licence

SIL Open Font License 1.1 — `OFL-Source-Serif-4-GoogleFonts.txt` (Google-distributed
copy, Copyright 2014 The Source Serif 4 Project Authors) and `OFL-Source-Serif-4.md`
(Adobe upstream). Reserved font name: Source.

## Integrity and sources

| File | Source URL | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| `v14/SourceSerif4Variable-Roman.woff2` | https://fonts.gstatic.com/s/sourceserif4/v14/vEFI2_tTDB4M7-auWDN0ahZJW1gb8te1Xb7G.woff2 | 2a24bad466f09b88b8e9cbc488bf774117c912e66374c57bf4716855849143f8 | 122,168 |
| `v14/SourceSerif4-Italic-400.woff2` | https://fonts.gstatic.com/s/sourceserif4/v14/vEF02_tTDB4M7-auWDN0ahZJW1ge6NmXpVAHV83Bfb_US2D2QYxoUKIkn98pRl9tDMQCjDDUXmAz.woff2 | bdd0e2a056f9d959782ca58fe25611076c77680cba409708f2d700876eedb81d | 20,132 |
