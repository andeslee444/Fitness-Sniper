# F-15 family schematic

`geometry.mjs` creates an original, simplified model for public-budget exploration.
It is not engineering geometry, an authoritative equipment fit, or a unit-cost map.
All assets are locally served. The scene renders only after interaction or resize;
Three.js is fetched only after the user activates inspection.

## Depicted distinctions

- A/C: shared single-seat schematic.
- B/D: shared two-seat schematic.
- E: two-seat schematic with conformal fuel tanks.
- EX: two-seat schematic, with an optional CFT-equipped configuration. Neither the
  default nor the toggle implies the configuration of every operational aircraft.
- Fuselage, intakes, wings, twin engines and tails are schematic. Generic aerials
  and part hotspots are navigation, not claims about exact sensor installation.
- Tooling/support has a conceptual anchor, not a physical part or allocated price.

Sources for configuration distinctions:

- [USAF F-15 Eagle fact sheet](https://www.af.mil/About-Us/Fact-Sheets/Display/Article/104501/f-15-eagle/)
- [USAF F-15E Strike Eagle fact sheet](https://www.af.mil/About-Us/Fact-Sheets/Display/Article/104499/f-15e-strike-eagle/)
- F015EX FY2026 budget narratives `cb4796e48126e4a7` (18 CFT sets as a modification)
  and `da8fcf0561c0e6e8` (Lot 7 CFT-equipped aircraft). The family data layer retains
  citations and source passages for these claims.

## Assets and regeneration

`single.png`, `twin.png`, and `strike.png` are transparent stills rendered from the
same interactive geometry. Regenerate with:

```sh
node scripts/exhibits/f15-family-posters.mjs
```

The script uses the site's existing Playwright installation and an ephemeral
local HTTP server; no new runtime dependency or external model host is needed.
