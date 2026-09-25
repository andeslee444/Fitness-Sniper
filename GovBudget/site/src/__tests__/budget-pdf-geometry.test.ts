import { describe, it, expect } from "vitest";
import { pdfHighlightRect } from "@/lib/citations";
describe("budget PDF page geometry", () => {
  it("scales highlights using the source page width, including portrait pages", () => {
    const box={x0:100, x1:150, top_pt:200, bottom_pt:210, page_width:612};
    expect(pdfHighlightRect(box,306)).toEqual({left:"48px",top:"98px",width:"29px",height:"9px"});
    expect(pdfHighlightRect({...box,page_width:792},396)).toEqual(pdfHighlightRect(box,306));
  });
});
