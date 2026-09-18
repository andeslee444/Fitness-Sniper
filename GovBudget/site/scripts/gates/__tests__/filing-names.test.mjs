/**
 * Proof-it-can-fail for gate 10 leg (e). The "before" fixture is the markup
 * /filing/{uuid}/ shipped before this change: the registry string as the h1's
 * own text, with no marker and no provenance line. Both names are real rows of
 * filings_index.json and both case (verified 2026-09-18).
 */
import { describe, it, expect } from "vitest";
import { filingNameFindings } from "../filing.mjs";

const filing = {
  client_name: "AECOM TECHNICAL SERVICES, INC.",
  registrant_name: "ELEVATE GOVERNMENT AFFAIRS, LLC",
};

const BEFORE = `<h1 class="text-3xl">AECOM TECHNICAL SERVICES, INC.</h1>
  <span>Registrant: <span class="text-foreground">ELEVATE GOVERNMENT AFFAIRS, LLC</span></span>`;

const AFTER = `<h1 class="text-3xl"><span data-company-name="AECOM TECHNICAL SERVICES, INC." title="AECOM TECHNICAL SERVICES, INC.">AECOM Technical Services, Inc.</span></h1>
  <span>Registrant: <span data-company-name="ELEVATE GOVERNMENT AFFAIRS, LLC" title="ELEVATE GOVERNMENT AFFAIRS, LLC">Elevate Government Affairs, LLC</span></span>
  <p data-filed-as>Filed as: AECOM TECHNICAL SERVICES, INC. — ELEVATE GOVERNMENT AFFAIRS, LLC.</p>`;

describe("filingNameFindings", () => {
  it("catches the shipped page: shouted h1, no marker, no provenance", () => {
    const found = filingNameFindings({ rel: "filing/abc/index.html", html: BEFORE, filing });
    expect(found.length).toBeGreaterThanOrEqual(2);
    expect(found.join(" ")).toContain("h1");
    expect(found.join(" ")).toContain("AECOM TECHNICAL SERVICES, INC.");
  });

  it("catches a page that cased the name and dropped the registry string", () => {
    const html = `<h1><span data-company-name="">AECOM Technical Services, Inc.</span></h1>`;
    expect(filingNameFindings({ rel: "filing/abc/index.html", html, filing }).join(" ")).toContain("registry string");
  });

  it("catches a registry string that is not the payload's own", () => {
    const html = AFTER.replace('data-company-name="AECOM TECHNICAL SERVICES, INC."', 'data-company-name="AECOM INC"');
    expect(filingNameFindings({ rel: "filing/abc/index.html", html, filing }).join(" ")).toContain("does not match the filing payload");
  });

  it("catches a [data-filed-as] line that omits one of the cased names", () => {
    const html = AFTER.replace(
      "Filed as: AECOM TECHNICAL SERVICES, INC. — ELEVATE GOVERNMENT AFFAIRS, LLC.",
      "Filed as: AECOM TECHNICAL SERVICES, INC.",
    );
    expect(filingNameFindings({ rel: "filing/abc/index.html", html, filing }).join(" ")).toContain(
      "[data-filed-as] omits",
    );
  });

  it("passes the fixed page", () => {
    expect(filingNameFindings({ rel: "filing/abc/index.html", html: AFTER, filing })).toEqual([]);
  });

  it("passes a self-filed refused name rendered verbatim, with no [data-filed-as]", () => {
    const raw = "MICHAEL BEST STRATEGIES LLC";   // refuses on 'BEST'
    const html = `<h1><span data-company-name="${raw}">${raw}</span></h1>
      <span>Registrant: <span data-company-name="${raw}">${raw}</span></span>`;
    expect(
      filingNameFindings({ rel: "filing/x/index.html", html, filing: { client_name: raw, registrant_name: raw } }),
    ).toEqual([]);
  });
});
