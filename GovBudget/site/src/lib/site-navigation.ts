/** One route vocabulary for the desktop menu, mobile menu, and active state. */
export const SITE_NAVIGATION = [
  { label: "Explore", links: [
    { href: "/explore/", label: "Visual field guide", detail: "See what programs build" },
    { href: "/programs/", label: "Programs", detail: "Browse the budget, line by line" },
    { href: "/years/", label: "Budget over time", detail: "Compare program funding by year" },
  ] },
  { label: "Investigate", links: [
    { href: "/companies/", label: "Companies", detail: "Find contractors and their awards" },
    { href: "/feed/", label: "Signals", detail: "Follow changes worth a closer look" },
    { href: "/flow/", label: "Follow the money", detail: "Explore budget and contract flows" },
    { href: "/lineage/", label: "Program lineage", detail: "Trace identities across budget years" },
    { href: "/filings/", label: "Lobbying filings", detail: "Read the reported activity" },
    { href: "/companies/families/", label: "Corporate families", detail: "Understand parent and subsidiary links" },
  ] },
  { label: "Places & agencies", links: [
    { href: "/district/", label: "Districts", detail: "Explore where the work happens" },
    { href: "/agency/", label: "Agencies", detail: "Browse the organizations behind programs" },
  ] },
  { label: "Data & methods", links: [
    { href: "/data/", label: "Data explorer", detail: "Ask questions of the underlying data" },
    { href: "/downloads/", label: "Downloads", detail: "Take the data into your own analysis" },
    { href: "/coverage/", label: "Coverage", detail: "Know what is included and missing" },
    { href: "/methodology/", label: "Methodology", detail: "Understand how evidence is connected" },
    { href: "/glossary/", label: "Glossary", detail: "Translate the budget terminology" },
    { href: "/about/", label: "About", detail: "The purpose behind Fiscal Receipts" },
  ] },
] as const;

export const PRIMARY_NAVIGATION = [
  { href: "/explore/", label: "Explore" },
  { href: "/programs/", label: "Programs" },
  { href: "/companies/", label: "Companies" },
  { href: "/district/", label: "Districts" },
  { href: "/feed/", label: "Signals" },
] as const;

export function isNavigationCurrent(pathname: string, href: string): boolean {
  const path = pathname.replace(/\/$/, "");
  const route = href.replace(/\/$/, "");
  if (path === route) return true;
  if (route === "/programs") return path.startsWith("/program/");
  if (route === "/companies") return path.startsWith("/company/");
  if (route === "/filings") return path.startsWith("/filing/");
  return (route === "/district" || route === "/agency") && path.startsWith(`${route}/`);
}
