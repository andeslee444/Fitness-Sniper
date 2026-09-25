# Source Sans 3 — site type system (apparatus face)

Vendored 2026-09-12 for self-hosting from the site origin. Unchanged distributor asset:
no subsetting, format conversion, instancing, outline or internal-name changes.
The version directory (`v19/`) is part of the served path — re-vendor into a new one.

## Files

| Local file under `/fonts/source-sans-3/v19/` | CSS family | Style | Weight | Bytes |
| --- | --- | --- | --- | ---: |
| `SourceSans3Variable-Roman.woff2` | `Source Sans 3` | normal | 200–900 (variable) | 28,792 |

Role: `--font-sans` — the html default, UI, labels (`.t-label` through `--font-label`),
notes, table text. No italic is vendored (`font-synthesis: none`; italics live in prose,
which is set in the serif). Weights used on the site: 400 / 500 / 600 only.

## Google Fonts (official Latin slice)

- Specimen: https://fonts.google.com/specimen/Source+Sans+3
- css2 request: https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@200..900&display=swap
  (response preserved as `SourceSans3-GoogleFonts-CSS.txt`); served asset
  https://fonts.gstatic.com/s/sourcesans3/v19/nwpStKy2OAdR1K-IwhWudF-R3w8aZejf5Hc.woff2
- Requested user agent: `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36`
- Pinned metadata: `METADATA.txt` = google/fonts `ofl/sourcesans3/METADATA.pb` at revision
  809e4d8b8d7e9364a914909bb777679606c178b8. Upstream: https://github.com/adobe-fonts/source-sans (Adobe, Paul D. Hunt).

## Actual font metadata (fontTools on the vendored bytes, 2026-09-12)

Source Sans 3, Version 3.052; UPM 1000; axes wght 200–900; fsType 0; italicAngle 0;
xHeight 478 / capHeight 660; hhea 1024 / −400 / 0; 324 glyphs, 231 mapped; digits 472 units,
tabular by default (`pnum` opts into proportional); GSUB ccmp dnom frac liga locl numr pnum.

## unicode-range (served, verbatim — declare the same in @font-face)

`U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD`

**Dropped by the Google latin slice:** GSUB `zero`, `onum`, `smcp`, `case`, `cv*`, `ss*`;
code points U+2192 → U+2197 ↗ U+2042 ⁂ (U+2191 ↑ and U+2193 ↓ present).

## Licence

SIL Open Font License 1.1 — `OFL.txt` (google/fonts copy at the pinned revision;
Copyright 2010, 2012, 2014 Adobe Systems Incorporated). Reserved font name: Source.

## Integrity and sources

| File | Source URL | SHA-256 | Bytes |
| --- | --- | --- | ---: |
| `v19/SourceSans3Variable-Roman.woff2` | https://fonts.gstatic.com/s/sourcesans3/v19/nwpStKy2OAdR1K-IwhWudF-R3w8aZejf5Hc.woff2 | ac057a5593cbe3df0d2585da5dd5f33b8efa84aa30550c710fe061b37fc5c54b | 28,792 |
