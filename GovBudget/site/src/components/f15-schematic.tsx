import { f15Illustration } from '@/lib/f15-illustration';
import type { F15VariantId } from '@/lib/f15-browser-state';

/** The same variant drawing is used by aircraft, funding and comparison views. */
export function F15Schematic({ variant, conformal = false, className, cockpit = false }: {
  variant: F15VariantId; conformal?: boolean; className?: string; cockpit?: boolean;
}) {
  const drawing = f15Illustration(variant, conformal);
  return <svg viewBox={cockpit ? '480 430 220 96' : '100 70 1510 815'}
    role="img" aria-label={drawing.description} className={className}
    data-f15-schematic={variant} data-seat-count={drawing.seats} data-conformal-tanks={drawing.tanks}
    preserveAspectRatio="xMidYMid meet" data-illustration="">
    <title>{drawing.description}</title>
    <desc>Simplified configuration illustration. A and C share a single-seat drawing; B and D share a two-seat drawing. Equipment varies.</desc>
    <use href={cockpit ? drawing.canopyHref : drawing.href} stroke={cockpit ? 'currentColor' : undefined} />
  </svg>;
}
