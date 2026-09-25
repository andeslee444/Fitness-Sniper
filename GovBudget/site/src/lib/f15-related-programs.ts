/** Shared-program context is evidence of a relationship, never an allocation. */
export interface F15RelatedProgram {
  /** Null when an older, edition-scoped line has no canonical program page. */
  slug: string | null;
  identifier: string;
  title: string;
  association: string;
  /** Budget edition carrying this passage, not a history of yearly funding. */
  sourceEdition: number;
  /** Null when imported historical evidence has no published receipt. */
  factId: string | null;
  officialUrl: string;
  pageNumber: number | null;
  /** Exact source XML locator; PDF page is supplied separately when known. */
  locator: string;
  excerpt: string;
}
