import type {
  KnowledgeSource,
  OperatorContext,
  ProcurementEvent,
} from "./f15-knowledge-types";

/** Dated public-source snapshots. These are not a live fleet census or an additive spending ledger. */
export const OPERATORS_ORDERS_SOURCES: KnowledgeSource[] = [
  {
    id: "oo-us-lot1",
    title: "DAF awards contract for first lot of F-15EX fighter aircraft",
    publisher: "U.S. Air Force",
    url: "https://www.af.mil/News/Features/Article/2272575/daf-awards-contract-for-first-lot-of-f-15ex-fighter-aircraft/",
    published: "2020-07-13",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-fy26-briefing",
    title: "Background Briefing on FY 2026 Defense Budget",
    publisher: "U.S. Department of Defense",
    url: "https://www.war.gov/News/Transcripts/Transcript/Article/4228828/background-briefing-on-fy-2026-defense-budget/",
    published: "2025-06-26",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-fy27-aircraft",
    title: "FY 2027 Aircraft Procurement, Air Force, Volume I — F015EX, P-40",
    publisher: "Department of the Air Force",
    url: "https://www.af.mil/Portals/1/documents/Secretariat%20of%20the%20AF/SAF-FM/Budget%20-%202027/Budget%20docs/FY27%20Air%20Force%20Aircraft%20Procurement%20Volume%20I.pdf?ver=4kiKWbFkcqsD4dDrO7-P4g%3D%3D",
    published: "2026-04",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-fy27-msar",
    title:
      "F-15EX Modernized Selected Acquisition Report — FY 2027 President's Budget",
    publisher:
      "Department of the Air Force / Defense Acquisition Visibility Environment",
    url: "https://www.esd.whs.mil/Portals/54/Documents/FOID/Reading%20Room/Selected_Acquisition_Reports/PB_2027_MSARs/F15EX_MSAR_FY2027_PB.pdf",
    published: "2026-04-21",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-global-family",
    title: "Built to adapt: The F-15's transformation and global impact",
    publisher: "Boeing",
    url: "https://www.boeing.com/features/2026/02/built-to-adapt-the-f-15s-transformation-and-global-impact",
    published: "2026-02-24",
    accessed: "2026-09-09",
    evidence: "manufacturer",
  },
  {
    id: "oo-fms-portfolio",
    title:
      "Industry Outreach: Customer Portfolios — F-15 FMS, slides 8, 10 and 12",
    publisher:
      "Air Force Sustainment Center / Robins AFB Contracting (NDIA-hosted presentation)",
    url: "https://higherlogicdownload.s3.amazonaws.com/NDIA/e030b777-57bf-4022-91db-b390fd95a0c4/UploadedFiles/gIMIAKrvQX2FRz5RY0bs_March%202023%20Industry%20Outreach%20Event%20-%20F-15%20FMS.pdf",
    published: "2023-03-07",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-japan-equipment",
    title: "F-15J/DJ Fighter — Japan Defense Focus No. 116",
    publisher: "Japan Ministry of Defense",
    url: "https://www.mod.go.jp/en/jdf/no116/equipment.html",
    published: null,
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-israel-agreement",
    title: "Israel MOD Acquires 25 Advanced F-15 Aircraft for $5.2 Billion",
    publisher: "Israel Ministry of Defense",
    url: "https://www.mod.gov.il/en/press-releases/press-room/israel-mod-acquires-25-advanced-f-15-aircraft-for-52-billion",
    published: "2024-11-07",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-israel-contract",
    title:
      "Contracts for December 29, 2025 — F-15 Israel Program, FA8634-26-C-B001",
    publisher: "U.S. Department of War",
    url: "https://www.war.gov/News/Contracts/Contract/Article/4368246/contracts-for-dec-29-2025/",
    published: "2025-12-29",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-saudi-agreement",
    title: "Boeing Statement on Saudi Arabia Purchase Agreement",
    publisher: "Boeing",
    url: "https://boeing.mediaroom.com/2011-12-29-Boeing-Statement-on-Saudi-Arabia-Purchase-Agreement",
    published: "2011-12-29",
    accessed: "2026-09-09",
    evidence: "manufacturer",
  },
  {
    id: "oo-saudi-sustainment",
    title: "Kingdom of Saudi Arabia — F-15 Sustainment, Transmittal 25-103",
    publisher: "Defense Security Cooperation Agency",
    url: "https://www.dsca.mil/Press-Media/Major-Arms-Sales/Article-Display/Article/4396586/kingdom-of-saudi-arabia-f-15-sustainment",
    published: "2026-02-03",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-singapore-original",
    title: "RSAF Rolls Out First F-15SG Multi-Role Fighter Aircraft",
    publisher: "Singapore Ministry of Defence / National Archives of Singapore",
    url: "https://www.nas.gov.sg/archivesonline/data/pdfdoc/MINDEF_20081104001.pdf",
    published: "2008-11-04",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-singapore-report",
    title: "Boeing completes deliveries of F-15SG jets to Singapore",
    publisher: "Defense News — Mike Yeo",
    url: "https://www.defensenews.com/air/2017/07/12/boeing-completes-deliveries-of-f-15sg-jets-to-singapore/",
    published: "2017-07-12",
    accessed: "2026-09-09",
    evidence: "reporting",
  },
  {
    id: "oo-singapore-operation",
    title:
      "RSAF's F-15SG Fighter Aircraft and Apache AH-64D Helicopter at Singapore Airshow 2024",
    publisher: "Singapore Ministry of Defence",
    url: "https://www.mindef.gov.sg/news-and-events/latest-releases/18feb24_nr2/",
    published: "2024-02-18",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-korea-deliveries",
    title:
      "Boeing Completes On-cost, On-schedule Delivery of F-15K Slam Eagles to Korea",
    publisher: "Boeing",
    url: "https://boeing.mediaroom.com/2012-04-03-Boeing-Completes-On-cost-On-schedule-Delivery-of-F-15K-Slam-Eagles-to-Korea",
    published: "2012-04-03",
    accessed: "2026-09-09",
    evidence: "manufacturer",
  },
  {
    id: "oo-korea-upgrade",
    title: "Republic of Korea — F-15K Aircraft Upgrade, Transmittal 25-02",
    publisher: "Defense Security Cooperation Agency",
    url: "https://media.defense.gov/2024/Dec/12/2003610836/-1/-1/0/PRESS%20RELEASE%20-%20KOREA%2025-02%20CN.PDF",
    published: "2024-11-19",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-korea-2026-contract",
    title: "Contracts for January 30, 2026 — F-15K upgrade, FA8634-26-C-B002",
    publisher: "U.S. Department of War",
    url: "https://www.war.gov/News/Contracts/Contract/Article/4394525/contracts-for-jan-30-2026/",
    published: "2026-01-30",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-qatar-completion",
    title: "Boeing 2023 Annual Report — Selected Programs, page 133",
    publisher: "Boeing",
    url: "https://investors.boeing.com/files/doc_financials/2023/ar/Boeing-2023-Annual-Report.pdf#page=134",
    published: "2024",
    accessed: "2026-09-09",
    evidence: "manufacturer",
  },
  {
    id: "oo-indonesia-approval",
    title: "Indonesia — F-15ID Aircraft, Transmittal 22-13",
    publisher: "Defense Security Cooperation Agency",
    url: "https://media.defense.gov/2024/Dec/12/2003610492/-1/-1/0/PRESS%20RELEASE%20-%20INDONESIA%2022-13%20CN.PDF",
    published: "2022-02-10",
    accessed: "2026-09-09",
    evidence: "government",
  },
  {
    id: "oo-indonesia-mou",
    title: "Indonesia Announces Commitment to Acquire Boeing F-15EX",
    publisher: "Boeing",
    url: "https://boeing.mediaroom.com/news-releases-statements?item=131310",
    published: "2023-08-21",
    accessed: "2026-09-09",
    evidence: "manufacturer",
  },
  {
    id: "oo-indonesia-inactive-janes",
    title:
      "Singapore Airshow 2026: Boeing pulls plug on Indonesian F-15EX campaign",
    publisher: "Janes",
    url: "https://www.janes.com/defence-intelligence-insights/defence-news/air/singapore-airshow-2026-boeing-pulls-plug-on-indonesian-f-15ex-campaign",
    published: null,
    accessed: "2026-09-09",
    evidence: "reporting",
  },
  {
    id: "oo-indonesia-inactive-dated",
    title:
      "Boeing confirms F-15EX fighter campaign with Indonesia is no longer active",
    publisher: "Air Data News — Ricardo Meier",
    url: "https://www.airdatanews.com/boeing-confirms-f-15ex-fighter-campaign-with-indonesia-is-no-longer-active/",
    published: "2026-02-04",
    accessed: "2026-09-09",
    evidence: "reporting",
  },
];

export const F15_OPERATORS: OperatorContext[] = [
  {
    id: "united-states",
    country: "United States",
    status: "operator",
    variants: ["F-15C/D (legacy)", "F-15E", "F-15EX"],
    summary:
      "The U.S. family spans air superiority, Strike Eagle missions and the EX replacement of aging C/D aircraft. EX procurement and development records cover different parts of that transition.",
    quantityNote:
      "18 EX aircraft delivered as of April 14, 2026: 2 development and 16 procurement aircraft. This is a dated delivery total, not today's operational fleet.",
    asOf: "2026-04-14",
    sourceIds: ["oo-fy27-msar", "oo-global-family"],
  },
  {
    id: "japan",
    country: "Japan",
    status: "operator",
    variants: ["F-15J", "F-15DJ", "F-15JSI upgrade"],
    summary:
      "Japan operates licensed, domestically produced J/DJ Eagles. The Japan Super Interceptor program modernizes existing aircraft; it is not a purchase of new F-15EX airframes.",
    quantityNote:
      "A March 2023 U.S. Air Force program brief scoped the major upgrade to 68 F-15J aircraft. That is an upgrade-program quantity, not Japan's complete fleet.",
    asOf: "2023-03-07",
    sourceIds: ["oo-japan-equipment", "oo-fms-portfolio", "oo-global-family"],
  },
  {
    id: "israel",
    country: "Israel",
    status: "operator",
    variants: ["F-15A/B/C/D", "F-15I", "F-15IA (ordered)"],
    summary:
      "Israel's existing Eagles and F-15I fleet are separate from the new IA acquisition. The IA contract includes Israeli requirements and an additional-aircraft option.",
    quantityNote:
      "December 2025 U.S. award: 25 new F-15IA aircraft plus an option for 25 more. The option is not counted as delivered or exercised; existing-fleet totals are not inferred.",
    asOf: "2025-12-29",
    sourceIds: [
      "oo-fms-portfolio",
      "oo-israel-agreement",
      "oo-israel-contract",
    ],
  },
  {
    id: "saudi-arabia",
    country: "Saudi Arabia",
    status: "operator",
    variants: ["F-15C/D", "F-15S", "F-15SA"],
    summary:
      "Saudi Arabia's family combines legacy air-superiority aircraft, strike models and Saudi Advanced aircraft. New aircraft, conversions and continuing sustainment are distinct purchases.",
    quantityNote:
      "The December 2011 agreement announced 84 new aircraft. This historical order does not measure the current fleet; the February 2026 support notice gives no aircraft purchase quantity.",
    asOf: "2026-02-03",
    sourceIds: [
      "oo-fms-portfolio",
      "oo-saudi-agreement",
      "oo-saudi-sustainment",
    ],
  },
  {
    id: "singapore",
    country: "Singapore",
    status: "operator",
    variants: ["F-15SG"],
    summary:
      "The RSAF operates the SG variant. Official procurement announcements and later reporting describe different snapshots of the fleet's growth.",
    quantityNote:
      "MINDEF disclosed 24 acquired in 2008. Defense News counted evidence of 40 airframes in 2017, while noting that MINDEF declined confirmation. Neither is presented as a current official inventory.",
    asOf: "2024-02-18",
    sourceIds: [
      "oo-singapore-original",
      "oo-singapore-report",
      "oo-singapore-operation",
    ],
  },
  {
    id: "south-korea",
    country: "South Korea",
    status: "operator",
    variants: ["F-15K Slam Eagle"],
    summary:
      "Korea's K variant connects aircraft acquisition with local industrial participation and later upgrades. A January 2026 U.S. contract funds design and development of an integrated suite of systems for F-15K modification.",
    quantityNote:
      "Boeing reported completion of the 40-aircraft first order and 21-aircraft follow-on in April 2012. These historical order quantities are not a surviving-aircraft inventory.",
    asOf: "2026-01-30",
    sourceIds: [
      "oo-korea-deliveries",
      "oo-korea-upgrade",
      "oo-korea-2026-contract",
    ],
  },
  {
    id: "qatar",
    country: "Qatar",
    status: "operator",
    variants: ["F-15QA"],
    summary:
      "Qatar's QA variant is an important predecessor of the U.S. EX configuration. Aircraft manufacturing, training and support packages have their own contract scopes.",
    quantityNote:
      "Boeing's 2023 annual report says delivery of 6 aircraft that year completed the original 36-aircraft order. This original-order milestone is not a claim about all later orders or today's fleet.",
    asOf: "2023-12-31",
    sourceIds: ["oo-qatar-completion", "oo-fy27-msar", "oo-global-family"],
  },
  {
    id: "indonesia",
    country: "Indonesia",
    status: "inactive",
    variants: ["F-15ID / F-15IDN (former proposal)"],
    summary:
      "At Singapore Airshow in February 2026, Janes reported Boeing's confirmation that its Indonesian F-15EX sales campaign was no longer active. This establishes the company's campaign status, not a formal government cancellation or operator status.",
    quantityNote:
      "The 2022 DSCA notice covered up to 36 aircraft; the August 2023 MoU concerned up to 24. These remain historical proposal stages, not aircraft orders to add together or evidence of deliveries.",
    asOf: "2026-02",
    sourceIds: [
      "oo-indonesia-approval",
      "oo-indonesia-mou",
      "oo-indonesia-inactive-janes",
      "oo-indonesia-inactive-dated",
    ],
  },
];

export const F15_PROCUREMENT: ProcurementEvent[] = [
  {
    id: "us-fy27-request",
    title: "FY2027: new aircraft and associated support requested",
    country: "United States",
    date: "2026-04",
    status: "request",
    quantity: 24,
    quantityLabel: "F-15EX aircraft requested in FY2027",
    amount: "$2,656.716 million",
    amountBasis:
      "FY2027 P-40 F015EX / BA01 aircraft and associated support / TOA; nominal USD",
    summary:
      "The April 2026 J-book requests aircraft plus associated equipment, training, spares and program support. EX modifications and development have separate exhibits. This newer request does not overwrite the site's stored FY2026 budget edition and is not enacted spending or a bare-aircraft price.",
    sourceIds: ["oo-fy27-aircraft"],
    recordSlugs: ["F015EX"],
  },
  {
    id: "us-fy27-program-plan",
    title: "Expanded EX program estimate",
    country: "United States",
    date: "2026-04-21",
    status: "plan",
    quantity: 268,
    quantityLabel:
      "total planned program aircraft, including 2 development aircraft",
    amount: null,
    amountBasis: null,
    summary:
      "The FY2027 acquisition report estimates 266 procurement aircraft plus 2 development aircraft through FY2031. It combines earlier funding with future requests; it is not 268 signed orders or deliveries. The report says an updated program cost estimate is still being developed.",
    sourceIds: ["oo-fy27-msar"],
    recordSlugs: ["F015EX", "0207146F"],
  },
  {
    id: "us-ex-delivery-snapshot",
    title: "EX delivery progress against contract schedule",
    country: "United States",
    date: "2026-04-14",
    status: "delivery",
    quantity: 18,
    quantityLabel: "EX aircraft delivered by April 14, 2026",
    amount: null,
    amountBasis: null,
    summary:
      "The April 2026 acquisition report records 18 delivered against 33 contractually required by that date. Delivery is a hardware milestone, not a spending figure or an operational-readiness count.",
    sourceIds: ["oo-fy27-msar"],
    recordSlugs: ["F015EX"],
  },
  {
    id: "saudi-2026-support-approval",
    title: "Saudi fleet support package proposed",
    country: "Saudi Arabia",
    date: "2026-02-03",
    status: "approval",
    quantity: null,
    quantityLabel:
      "Sustainment and training package; no aircraft purchase quantity stated",
    amount: "$3.0 billion",
    amountBasis:
      "DSCA highest estimated potential-sale value; not an obligation or payment",
    summary:
      "The notified package covers spare and repair parts, software, training, engineering and logistics. DSCA identifies various contractors and no prime contractor. A congressional notification permits a possible sale; final agreements determine the actual value.",
    sourceIds: ["oo-saudi-sustainment"],
  },
  {
    id: "korea-2026-upgrade-contract",
    title: "Boeing awarded Korean upgrade design contract",
    country: "South Korea",
    date: "2026-01-30",
    status: "contract",
    quantity: null,
    quantityLabel:
      "F-15K upgrade design and development; aircraft quantity not stated in award",
    amount: "$2,805,961,005 not to exceed",
    amountBasis:
      "Undefinitized contract FA8634-26-C-B002; maximum announced value, not a payment",
    summary:
      "The award covers design and development of integrated aircraft systems for the Korean F-15K upgrade. It obligates $540 million in FMS funds at award, with work expected through December 2037. This contract and the earlier $6.2 billion possible-sale notification have different scopes and are not additive spending.",
    sourceIds: ["oo-korea-2026-contract", "oo-korea-upgrade"],
  },
  {
    id: "israel-2025-contract",
    title: "U.S. contract award for Israel's new IA aircraft",
    country: "Israel",
    date: "2025-12-29",
    status: "contract",
    quantity: 25,
    quantityLabel: "new F-15IA aircraft in the base award",
    amount: "$8,577.7 million ceiling",
    amountBasis:
      "Undefinitized contract action FA8634-26-C-B001, including an additional-aircraft option",
    summary:
      "The award covers design, integration, testing, production and delivery, with $840 million in FMS funds obligated at award and completion expected by December 2035. Its ceiling is not cash paid. This and Israel's 2024 agreement are overlapping milestones, not separate purchases to sum.",
    sourceIds: ["oo-israel-contract"],
  },
  {
    id: "israel-2025-option",
    title: "Israel's additional-aircraft option",
    country: "Israel",
    date: "2025-12-29",
    status: "option",
    quantity: 25,
    quantityLabel: "additional F-15IA aircraft covered by an option",
    amount: null,
    amountBasis:
      "Option in FA8634-26-C-B001; no separate exercised-option value established here",
    summary:
      "The U.S. contract notice specifies an option beyond the base aircraft. The source does not report its exercise, so these aircraft stay separate from firm base quantities and deliveries.",
    sourceIds: ["oo-israel-contract"],
  },
  {
    id: "us-fy26-request",
    title: "FY2026: EX request announced",
    country: "United States",
    date: "2025-06-26",
    status: "request",
    quantity: 21,
    quantityLabel: "F-15EX aircraft in the FY2026 request briefing",
    amount: "$3.1 billion",
    amountBasis:
      "Rounded F-15EX program request in the department's FY2026 budget briefing",
    summary:
      "The department announced funding and aircraft requested for continued EX production. This rounded program headline has a different scope from the exact F015EX procurement-only TOA in the receipt browser; it is not a contract award or a unit price.",
    sourceIds: ["oo-fy26-briefing"],
    recordSlugs: ["F015EX", "0207146F"],
  },
  {
    id: "korea-2024-upgrade-approval",
    title: "Korean radar and electronic-warfare upgrade proposed",
    country: "South Korea",
    date: "2024-11-19",
    status: "approval",
    quantity: 70,
    quantityLabel: "APG-82 radars in the potential package, not 70 aircraft",
    amount: "$6.2 billion",
    amountBasis:
      "DSCA estimated potential sale, including equipment, services and support",
    summary:
      "The request includes 70 APG-82 radars, 70 EPAWSS suites and 96 mission computers, plus support. Equipment counts are not a fighter-order count. Boeing, Raytheon and BAE Systems are named contractors; the notice does not establish deliveries or final contract value.",
    sourceIds: ["oo-korea-upgrade"],
  },
  {
    id: "israel-2024-agreement",
    title: "Israel signs initial IA acquisition agreement",
    country: "Israel",
    date: "2024-11-06",
    status: "contract",
    quantity: 25,
    quantityLabel: "F-15IA aircraft in the announced agreement",
    amount: "$5.2 billion",
    amountBasis:
      "Acquisition-agreement value announced by Israel's Ministry of Defense",
    summary:
      "The November 7 release says the agreement was signed the previous day, with an option for 25 more aircraft. It projected deliveries beginning in 2031 at 4–6 annually. Treat that as the schedule announced in 2024; the later U.S. award is another stage of the same acquisition.",
    sourceIds: ["oo-israel-agreement"],
  },
  {
    id: "qatar-original-order-complete",
    title: "Qatar's original QA order completed",
    country: "Qatar",
    date: "2023",
    status: "delivery",
    quantity: 36,
    quantityLabel:
      "aircraft in the original order reported complete during 2023",
    amount: "$6.2 billion",
    amountBasis:
      "2017 manufacturing-contract value cited in Boeing's 2023 annual report",
    summary:
      "Boeing reports six QA deliveries in 2023 completing its original order. The stated manufacturing contract is narrower than a complete foreign-sale package and does not price all training, support or later aircraft. The completion year is known; a specific completion date is not supplied.",
    sourceIds: ["oo-qatar-completion"],
  },
  {
    id: "indonesia-2023-mou",
    title: "Indonesia signs an acquisition MoU",
    country: "Indonesia",
    date: "2023-08-21",
    status: "plan",
    quantity: 24,
    quantityLabel: "up to 24 aircraft in the memorandum of understanding",
    amount: null,
    amountBasis: null,
    summary:
      "Boeing described a commitment to finalize a sale, subject to U.S. government approval. A memorandum of understanding is not a delivered fleet or evidence that a final production contract took effect.",
    sourceIds: ["oo-indonesia-mou"],
  },
  {
    id: "indonesia-2022-approval",
    title: "Potential Indonesian sale notified to Congress",
    country: "Indonesia",
    date: "2022-02-10",
    status: "approval",
    quantity: 36,
    quantityLabel: "up to 36 F-15ID aircraft in the possible sale",
    amount: "$13.9 billion",
    amountBasis:
      "DSCA highest estimated potential-sale value, including equipment and support",
    summary:
      "The package includes engines, radars, electronic warfare, targeting equipment, training and support. DSCA explicitly says final value depends on requirements, budget authority and signed agreements, if concluded. This is not a receipt for money spent.",
    sourceIds: ["oo-indonesia-approval"],
  },
  {
    id: "us-2020-lot1-contract",
    title: "First U.S. EX lot awarded to Boeing",
    country: "United States",
    date: "2020-07-13",
    status: "contract",
    quantity: 8,
    quantityLabel: "F-15EX aircraft in the first lot",
    amount: "Nearly $1.2 billion",
    amountBasis:
      "Air Force announced first-lot contract value, including development and support",
    summary:
      "The contract covers design, development, manufacturing, testing, delivery, sustainment, modifications, spares and training support. Dividing its value by the aircraft count would not yield a bare-aircraft price.",
    sourceIds: ["oo-us-lot1"],
    recordSlugs: ["F015EX", "0207134F"],
  },
  {
    id: "korea-2012-completion",
    title: "Korean follow-on deliveries completed",
    country: "South Korea",
    date: "2012-04-02",
    status: "delivery",
    quantity: 21,
    quantityLabel:
      "aircraft in the follow-on order completed by this milestone",
    amount: null,
    amountBasis: null,
    summary:
      "Boeing delivered the final two aircraft of the follow-on program on April 2. Its release distinguishes the earlier 40-aircraft order from the 21-aircraft contract awarded in April 2008. Historical acquisition totals do not establish today's surviving fleet.",
    sourceIds: ["oo-korea-deliveries"],
  },
  {
    id: "saudi-2011-agreement",
    title: "Saudi agreement for new Eagles and upgrades",
    country: "Saudi Arabia",
    date: "2011-12-29",
    status: "contract",
    quantity: 84,
    quantityLabel: "new aircraft announced in the signed agreement",
    amount: null,
    amountBasis: null,
    summary:
      "Boeing reported a signed government-to-government letter of offer and acceptance for 84 new aircraft and upgrades to 70 existing aircraft. Those are separate scopes; the company's broader sales total also included helicopters and is not assigned here to F-15s.",
    sourceIds: ["oo-saudi-agreement"],
  },
];
