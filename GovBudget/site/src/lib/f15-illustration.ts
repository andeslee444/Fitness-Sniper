import type { F15VariantId } from './f15-browser-state';

/** Depicted configuration, never an assertion that every aircraft has this fit. */
export function f15Illustration(variant: F15VariantId, conformal = false) {
  const seats = variant === 'A' || variant === 'C' ? 1 : 2;
  const tanks = variant === 'E' || (variant === 'EX' && conformal);
  const profile = tanks ? 'strike' : seats === 1 ? 'single' : 'twin';
  return {
    seats, tanks, profile,
    href: `/exhibits/plates/f15-${profile}.svg#f15-plate`,
    canopyHref: `/exhibits/plates/f15-${profile}.svg#canopy`,
    description: `F-15${variant}: ${seats === 1 ? 'single-seat cockpit' : 'two-seat cockpit'}${tanks ? ', conformal fuel tanks shown' : ''}`,
  } as const;
}
