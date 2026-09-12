/**
 * Per-edition rendering of the GAO program tier (ROADMAP #30, "and its
 * predecessors").  Every rendered assessment must carry its edition as data,
 * say it in the sentence a reader sees, and cite its OWN product page; an
 * older edition renders only beneath the ratified anchor it inherits from.
 * Gate 21 leg h8 asserts the same against the built pages.
 */
import { test, expect } from "vitest";
import { render } from "@testing-library/react";
import { GaoProgramFindingsBlock } from "@/components/gao-program-findings";
import type { GaoAssessment } from "@/lib/data";

const base = (over: Partial<GaoAssessment> = {}): GaoAssessment => ({
  assessment_type: "MDAP",
  common_name: "Sentinel",
  description:
    "The Air Force's Sentinel is intended to replace the Minuteman III.",
  edition_year: 2025,
  gao_program: "LGM-35A Sentinel",
  inherited_from: null,
  pdf_page: 89,
  pdf_url: "https://www.gao.gov/assets/gao-25-107569.pdf",
  product_number: "GAO-25-107569",
  program_key: "sentinel",
  released: "2025-06",
  report_page: 79,
  report_title: "WSAA 2025",
  report_url: "https://www.gao.gov/products/gao-25-107569",
  service: "Air Force",
  ...over,
});

const prior = (year: number, product: string, page: number): GaoAssessment =>
  base({
    product_number: product,
    edition_year: year,
    released: `${year}-06`,
    inherited_from: "GAO-25-107569",
    report_page: page,
    pdf_page: page + 10,
    pdf_url: `https://www.gao.gov/assets/${product.toLowerCase()}.pdf`,
    report_url: `https://www.gao.gov/products/${product.toLowerCase()}`,
    report_title: `WSAA ${year}`,
    description: `In ${year} GAO said this about Sentinel.`,
  });

test("each edition is stamped, named in its sentence, and cited to its own product", () => {
  const { container } = render(
    <GaoProgramFindingsBlock
      programTitle="LGM-35A Sentinel"
      findings={{
        reports: [],
        assessments: [
          base(),
          prior(2024, "GAO-24-106831", 84),
          prior(2023, "GAO-23-106059", 77),
        ],
      }}
    />,
  );
  const items = [...container.querySelectorAll('[data-gao-item="assessment"]')];
  expect(items.map((el) => el.getAttribute("data-gao-edition"))).toEqual([
    "2025", "2024", "2023",
  ]);
  for (const el of items) {
    const year = el.getAttribute("data-gao-edition")!;
    const product = el.getAttribute("data-gao-product")!;
    expect(el.textContent).toContain(`${year} Weapon Systems Annual Assessment`);
    expect(el.querySelector("[data-gao-cite]")!.getAttribute("href")).toBe(
      `https://www.gao.gov/products/${product.toLowerCase()}`,
    );
    expect(el.querySelector("[data-gao-quote]")!.textContent).toContain(
      year === "2025" ? "Minuteman III" : `In ${year} GAO said`,
    );
    expect(el.getAttribute("data-gao-common")).toBe("Sentinel");
    expect(el.getAttribute("data-gao-service")).toBe("Air Force");
  }
  expect(items[0].hasAttribute("data-gao-inherited-from")).toBe(false);
  expect(items[1].getAttribute("data-gao-inherited-from")).toBe("GAO-25-107569");
  const details = container.querySelector("details[data-gao-prior-editions]")!;
  expect(details.getAttribute("data-gao-prior-editions")).toBe("2");
  expect(details.querySelector("summary")!.textContent).toContain(
    "June 2024 · June 2023",
  );
  expect(details.querySelectorAll('[data-gao-item="assessment"]')).toHaveLength(2);
  // the pdf deep link names the edition too
  expect(items[1].textContent).toContain("GAO’s 2024 report");
});

test("an older edition never renders without its ratified anchor", () => {
  const { container } = render(
    <GaoProgramFindingsBlock
      programTitle="x"
      findings={{ reports: [], assessments: [prior(2024, "GAO-24-106831", 84)] }}
    />,
  );
  expect(container.querySelectorAll('[data-gao-item="assessment"]')).toHaveLength(0);
  expect(container.querySelector("details")).toBeNull();
});

test("a sidecar without the edition fields renders no edition stamp", () => {
  const legacy = { ...base() } as Partial<GaoAssessment>;
  delete legacy.edition_year;
  delete legacy.inherited_from;
  const { container } = render(
    <GaoProgramFindingsBlock
      programTitle="x"
      findings={{ reports: [], assessments: [legacy as GaoAssessment] }}
    />,
  );
  // `!a.inherited_from` treats undefined as an anchor, so it renders — but
  // with no edition stamp, which leg h8 refuses at verify.  Pin that shape.
  const el = container.querySelector('[data-gao-item="assessment"]')!;
  expect(el.hasAttribute("data-gao-edition")).toBe(false);
});
