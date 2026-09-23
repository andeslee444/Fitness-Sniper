// Variant plates share the existing illustrative airframe, with explicit seat
// and conformal-tank differences. These are schematics, not engineering plans.
import fs from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../../', import.meta.url));
const require = createRequire(`${root}site/package.json`);
const { JSDOM } = require('jsdom');
const original = fs.readFileSync(`${root}site/public/exhibits/plates/f15.svg`, 'utf8');
const ns = 'http://www.w3.org/2000/svg';
for (const [profile, seats, tanks] of [['single', 1, false], ['twin', 2, false], ['strike', 2, true]]) {
  const document = new JSDOM(original, { contentType: 'image/svg+xml' }).window.document;
  const canopy = document.querySelector('#canopy');
  const outline = seats === 1
    ? 'M493 478 C506 446 551 448 576 450 C603 451 622 456 629 478 C622 500 603 505 576 506 C551 508 506 510 493 478 Z'
    : 'M493 478 C506 446 556 448 589 450 C633 450 666 452 677 478 C666 504 633 506 589 506 C556 508 506 510 493 478 Z';
  canopy.replaceChildren();
  function element(tag, attrs) {
    const node = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    canopy.append(node);
    return node;
  }
  element('path', { d: outline, fill: 'currentColor', 'fill-opacity': '.04', 'stroke-width': '1.6' });
  element('path', { d: 'M529 451 Q538 478 529 505', fill: 'none', 'stroke-width': '1.8' });
  for (const x of seats === 1 ? [559] : [559, 625]) {
    element('rect', { x, y: 464, width: 24, height: 28, rx: 3, fill: 'currentColor', 'fill-opacity': '.12', 'stroke-width': '1.8', 'data-seat': '' });
    element('rect', { x: x + 5, y: 470, width: 14, height: 16, rx: 2, fill: 'none', 'stroke-width': '.9' });
  }
  if (seats === 2) element('path', { d: 'M607 451 Q615 478 607 505', fill: 'none', 'stroke-width': '1.5' });
  const end = seats === 1 ? 629 : 677;
  element('path', { d: `M${end} 465 Q710 470 731 471 M${end} 491 Q710 486 731 485`, fill: 'none', 'stroke-width': '1.1' });
  if (!tanks) document.querySelector('#cft').remove();
  const svg = document.documentElement;
  svg.setAttribute('data-profile', profile);
  svg.setAttribute('data-seats', String(seats));
  svg.setAttribute('data-conformal-tanks', String(tanks));
  svg.querySelector('title')?.remove();
  const title = document.createElementNS(ns, 'title');
  title.textContent = `F-15 ${seats}-seat schematic${tanks ? ' with conformal fuel tanks' : ''}`;
  svg.prepend(title);
  fs.writeFileSync(`${root}site/public/exhibits/plates/f15-${profile}.svg`, svg.outerHTML);
  console.log(`f15-${profile}.svg: ${seats} seats, tanks ${tanks}`);
}
