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

/**
 * The links painted in the header bar at lg and up. They are server-rendered
 * into `<nav data-site-nav>`; the "More" menu beside them is a client popover
 * and is absent from the static HTML.
 *
 * Glossary is here, not only under "More" (2026-09-25 integration). The
 * glossary was linked only from the footer, below the jargon it defines, and
 * tri-persona Wave 3 filed that. Gate 13 leg (j) requires /glossary/ inside
 * `<nav data-site-nav>` on /. Under "More" alone it would sit behind a
 * client-rendered disclosure again. Measured 2026-09-25 with the link in
 * place, the bar still has 205px spare at 1024, its narrowest desktop width.
 * SITE_NAVIGATION above keeps Glossary under "Data & methods", so the mobile
 * panel and the "More" menu still carry it.
 */
export const PRIMARY_NAVIGATION = [
  { href: "/explore/", label: "Explore" },
  { href: "/programs/", label: "Programs" },
  { href: "/companies/", label: "Companies" },
  { href: "/district/", label: "Districts" },
  { href: "/feed/", label: "Signals" },
  { href: "/glossary/", label: "Glossary" },
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
