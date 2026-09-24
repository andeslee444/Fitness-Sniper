import React from 'react';
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { F15Model } from '@/components/f15-model';
import { f15Illustration } from '@/lib/f15-illustration';
import { F15ProgramNavigation } from '@/components/family-entry';
vi.mock('next/script', () => ({ default: () => null }));
afterEach(cleanup);
describe('F-15 visible configuration', () => {
 it('changes the actual drawing when the aircraft changes, before loading 3D', () => {
  const props = { topic: 'airframe' as const, onTopicChange: vi.fn() };
  const {container, rerender} = render(<F15Model {...props} variant="A" />);
  for (const [variant, profile, seats] of [['A','single',1],['B','twin',2],['C','single',1],['D','twin',2],['E','strike',2],['EX','twin',2]] as const) {
   rerender(<F15Model {...props} variant={variant} />);
   expect(container.querySelector('use')).toHaveAttribute('href', `/exhibits/plates/f15-${profile}.svg#f15-plate`);
   expect(screen.getByRole('img', {name: `F-15${variant}: ${seats === 1 ? 'single-seat cockpit' : 'two-seat cockpit'}${variant === 'E' ? ', conformal fuel tanks shown' : ''}`})).toBeVisible();
   expect(container.querySelector('f15-family-scene')).toBeNull();
  }
 });
 it('ships separate cockpit geometry and conformal tanks only in the strike schematic', () => {
  for (const variant of ['A','B','E'] as const) {
   const drawing=f15Illustration(variant);
   const text=readFileSync(`public/exhibits/plates/f15-${drawing.profile}.svg`,'utf8');
   const doc=new DOMParser().parseFromString(text,'image/svg+xml');
   expect(doc.querySelectorAll('[data-seat]')).toHaveLength(drawing.seats);
   expect(Boolean(doc.querySelector('#cft'))).toBe(drawing.tanks);
  }
 });
 it.each(['0207134F','0207146F','0207171F','F01500','F015EX','F15EWS'])('keeps all six family destinations available from %s', slug => {
  render(<F15ProgramNavigation programSlug={slug} />);
  const links=screen.getByRole('navigation', {name:'F-15 family sections'}).querySelectorAll('a');
  expect(links).toHaveLength(6);
  for(const link of links) expect(new URL(link.href).searchParams.get('record')).toBe(slug);
  expect(screen.getByRole('link',{name:'Budget & receipts'})).toHaveAttribute('aria-current','page');
 });
});
