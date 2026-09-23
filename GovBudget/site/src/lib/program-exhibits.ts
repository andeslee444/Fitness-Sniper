/** Curated visual explanations. Financial values come exclusively from sidecars. */
export interface ExhibitTopic {
  id: string;
  label: string;
  text: string;
  factId: string;
  /** A short source phrase: build validation detects a drifted/missing narrative. */
  evidenceContains: string;
  position: [number, number];
}
export interface ProgramExhibitConfig {
  slug: string;
  subject: "virginia" | "f35" | "cyber";
  name: string;
  eyebrow: string;
  title: string;
  caption: string;
  topics: ExhibitTopic[];
  related?: { slug: string; label: string }[];
}

export const PROGRAM_EXHIBITS: Record<string, ProgramExhibitConfig> = {
  "2013": {
    slug: "2013", subject: "virginia", name: "Virginia Class Submarine",
    eyebrow: "01 / Sea", title: "Explore the investment beneath the surface.",
    caption: "Simplified submarine and shipyard illustration. Objects show funding topics, not quantities or component costs.",
    topics: [
      { id: "construction", label: "Ship construction", position: [51.1, 72.9],
        text: "The Navy’s request supports construction of Virginia-class submarines. The budget narrative also describes funding to complete ships procured in earlier years.",
        factId: "ab7edeece9637c51", evidenceContains: "Completion of Prior Year Shipbuilding Programs" },
      { id: "future", label: "Future procurement", position: [56.1, 49.0],
        text: "Advance procurement and economic order quantity funding support future submarines. Part of this program’s funding prepares for work beyond the current year’s ships.",
        factId: "cf2850271c560361", evidenceContains: "economic order quantity funds for future" },
      { id: "shipyard", label: "Shipyard capacity", position: [33.3, 18.4],
        text: "The request includes continued investment in shipbuilder productivity and wages. Its justification also describes industrial-base investment in construction spares to reduce schedule risk.",
        factId: "ab7edeece9637c51", evidenceContains: "shipbuilder productivity wage enhancements" },
    ],
  },
  ATA000: {
    slug: "ATA000", subject: "f35", name: "F-35 aircraft procurement",
    eyebrow: "02 / Air", title: "See what it takes to field an aircraft.",
    caption: "Conceptual F-35 planform on a hangar floor with ground equipment. Nothing drawn is an equipment list; this page covers the Air Force procurement line.",
    related: [{ slug: "ATA000", label: "Aircraft procurement" }, { slug: "0604840F", label: "Capability development" }],
    topics: [
      { id: "airframe", label: "Aircraft & engines", position: [48.2, 68.2],
        text: "The procurement request funds F-35A aircraft, engines, and equipment associated with production and delivery. It also supports the requirements for establishing squadrons.",
        factId: "b39c55839c9f8d21", evidenceContains: "Aircraft, Engines" },
      { id: "support", label: "Ground & training support", position: [10.2, 49.8],
        text: "Support funding includes ground equipment for aircraft, engines, and avionics, as well as training equipment for squadron and site stand-ups.",
        factId: "b39c55839c9f8d21", evidenceContains: "training equipment to support squadron" },
      { id: "software", label: "Logistics & repair", position: [32.8, 49.8],
        text: "The request describes the transition from ALIS to the ODIN logistics information system and investment in depot repair capability and capacity.",
        factId: "b39c55839c9f8d21", evidenceContains: "Operational Data Integrated Network" },
    ],
  },
  "0604840F": {
    slug: "0604840F", subject: "f35", name: "F-35 capability development",
    eyebrow: "02 / Air", title: "Follow the investment in new capability.",
    caption: "The same illustrative aircraft, a separate funding line: Air Force research and development. Topics are not a cost breakdown.",
    related: [{ slug: "ATA000", label: "Aircraft procurement" }, { slug: "0604840F", label: "Capability development" }],
    topics: [
      { id: "avionics", label: "Computing & displays", position: [22.8, 49.8],
        text: "Technology Refresh 3 develops and certifies updated processing, memory, and cockpit-display systems to support existing functions and future capabilities.",
        factId: "e9e78eec9d5c5ac9", evidenceContains: "Integrated Core Processor" },
      { id: "software", label: "Software & integration", position: [32.8, 49.8],
        text: "The Block 4 development portfolio combines software-based capabilities, modernized hardware, and integration work. The separate tile is a visual metaphor for software.",
        factId: "a73eac1755efb346", evidenceContains: "software-based capabilities" },
      { id: "airframe", label: "Engineering & testing", position: [48.2, 68.2],
        text: "Planning, systems engineering, development, and testing continue across the air vehicle, propulsion, combat data, maintenance, and training systems.",
        factId: "68690938ba32ad9c", evidenceContains: "Planning, systems engineering, development, and testing" },
    ],
  },
  "0602668D8Z": {
    slug: "0602668D8Z", subject: "cyber", name: "Cyber Security Research",
    eyebrow: "03 / Cyber", title: "Explore a program you cannot see in a hangar.",
    caption: "Conceptual research benches. The instruments and rack are symbols, not a map of an operational system or a hardware purchase list.",
    topics: [
      { id: "cognition", label: "Research foundations", position: [21.0, 24.8],
        text: "This applied research program explores higher-risk cyber technology. Its named research areas include augmented cognition and cyber foundations.",
        factId: "2ab7173319765057", evidenceContains: "Augmented Cognition" },
      { id: "networks", label: "Dependable networks", position: [56.6, 26.1],
        text: "Dependable systems and networks are another named research area. The connected devices illustrate that topic; their number and arrangement are conceptual.",
        factId: "2ab7173319765057", evidenceContains: "Dependable Systems and Networks" },
      { id: "research", label: "Technology options", position: [81.8, 48.6],
        text: "The program integrates defensive and offensive cyber research to develop interoperable technology options for the joint force, including integrated sensing and cyber operations.",
        factId: "9274efe61e206399", evidenceContains: "interoperable, defense-wide technology options" },
    ],
  },
};

export const EXHIBIT_PILOTS = ["2013", "ATA000", "0602668D8Z"] as const;

/** One-sentence <desc> for each drawn plate (gate 2's illustration
    contract: svg[role="img"][data-illustration] carries a name AND a
    non-empty desc of WHAT IS DRAWN — never a figure, never what it means).
    Keyed by subject so the homepage gallery and the program-page exhibit
    cannot drift into two descriptions of the same drawing. */
export const PLATE_DESCS: Record<ProgramExhibitConfig["subject"], string> = {
  virginia:
    "Side elevation of a Virginia-class submarine in a drydock under a gantry crane, with a second hull in sections on the apron.",
  f35: "Overhead planform view of an F-35 fighter jet on a hangar floor, with a tow tractor at the nose, a boarding ladder and work stand beside the cockpit, a ground power cart on a cable, and an equipment box aft.",
  cyber:
    "Three lab benches drawn in isometric view: test instruments and a whiteboard with a network sketch on the left, a desk with a monitor beside a server rack in the centre, and an open shielded enclosure holding a circuit board under a magnifier on the right.",
};

export function validateExhibitNarratives(config: ProgramExhibitConfig, narratives: { fact_id?: string | null; body: string }[]) {
  for (const topic of config.topics) {
    const evidence = narratives.find((n) => n.fact_id === topic.factId);
    if (!evidence?.body.toLowerCase().includes(topic.evidenceContains.toLowerCase())) {
      throw new Error(`Exhibit ${config.slug}/${topic.id}: missing or changed narrative evidence ${topic.factId}`);
    }
  }
}
