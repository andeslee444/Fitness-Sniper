#!/usr/bin/env node
/**
 * computed-style-snapshot.mjs — proof that a utility-class hoist changes no
 * computed style (families piece 1, Task 19; /coverage/ did the same check by
 * hand for coverage.module.css, see that file's header).
 *
 * Serves out/ (serve-static.mjs), opens one route and records, for every
 * element under one selector, its bounding box and every standard computed
 * property (custom properties skipped), in eight states — 390×844 and
 * 1440×900, light and dark, screen and print — plus the first body row's
 * :hover state at 1440×900 light screen.
 *
 *   node scripts/computed-style-snapshot.mjs --route /data/ \
 *     --selector "#dataset-inventory table" --out /abs/before.json [--port 4191]
 *   node scripts/computed-style-snapshot.mjs --diff /abs/before.json /abs/after.json
 *
 * --diff prints up to 50 differences and "computed-style diff: N difference(s)",
 * exiting 1 when N > 0.
 */
import fs from "fs";
import { chromium } from "playwright";
import { startServer } from "./serve-static.mjs";

const VIEWPORTS = [{ width: 390, height: 844 }, { width: 1440, height: 900 }];
const SCHEMES = ["light", "dark"];
const MEDIA = ["screen", "print"];

function arg(name) {
  const i = process.argv.indexOf(name);
  return i > -1 ? process.argv[i + 1] : undefined;
}

/** Runs in the page. Self-contained: Playwright serialises its source. */
function collect(selector) {
  const root = document.querySelector(selector);
  if (!root) throw new Error(`no element matches ${selector}`);
  return [root, ...root.querySelectorAll("*")].map((el) => {
    const cs = getComputedStyle(el);
    const props = {};
    for (let i = 0; i < cs.length; i++) {
      const p = cs[i];
      if (!p.startsWith("--")) props[p] = cs.getPropertyValue(p);
    }
    const r = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      box: [r.x, r.y, r.width, r.height].map((v) => Math.round(v * 100) / 100),
      props,
    };
  });
}

async function snapshot(route, selector, port) {
  const server = await startServer(port);
  const browser = await chromium.launch();
  const out = {};
  try {
    for (const viewport of VIEWPORTS) {
      for (const colorScheme of SCHEMES) {
        for (const media of MEDIA) {
          const page = await browser.newPage({ viewport });
          await page.emulateMedia({ colorScheme, media });
          await page.goto(`${server.url}${route}`, { waitUntil: "load" });
          const key = `${viewport.width}x${viewport.height}/${colorScheme}/${media}`;
          out[key] = await page.evaluate(collect, selector);
          if (viewport.width === 1440 && colorScheme === "light" && media === "screen") {
            await page.locator(`${selector} tbody tr`).first().hover();
            await page.waitForTimeout(1000);
            out[`${key}/hover`] = await page.evaluate(collect, `${selector} tbody tr`);
          }
          await page.close();
        }
      }
    }
  } finally {
    await browser.close();
    await server.close();
  }
  return out;
}

function diff(a, b) {
  const A = JSON.parse(fs.readFileSync(a, "utf8"));
  const B = JSON.parse(fs.readFileSync(b, "utf8"));
  const lines = [];
  for (const key of new Set([...Object.keys(A), ...Object.keys(B)])) {
    const x = A[key];
    const y = B[key];
    if (!x || !y) {
      lines.push(`${key}: present in one snapshot only`);
      continue;
    }
    if (x.length !== y.length) {
      lines.push(`${key}: ${x.length} elements vs ${y.length}`);
      continue;
    }
    x.forEach((e, i) => {
      const f = y[i];
      if (e.tag !== f.tag) lines.push(`${key} #${i}: <${e.tag}> vs <${f.tag}>`);
      if (e.box.join() !== f.box.join()) lines.push(`${key} #${i} <${e.tag}> box ${e.box} -> ${f.box}`);
      for (const p of new Set([...Object.keys(e.props), ...Object.keys(f.props)])) {
        if (e.props[p] !== f.props[p]) {
          lines.push(`${key} #${i} <${e.tag}> ${p}: ${e.props[p]} -> ${f.props[p]}`);
        }
      }
    });
  }
  return lines;
}

if (process.argv.includes("--diff")) {
  const i = process.argv.indexOf("--diff");
  const lines = diff(process.argv[i + 1], process.argv[i + 2]);
  for (const l of lines.slice(0, 50)) console.log(l);
  console.log(`computed-style diff: ${lines.length} difference(s)`);
  process.exit(lines.length === 0 ? 0 : 1);
} else {
  const route = arg("--route");
  const selector = arg("--selector");
  const outPath = arg("--out");
  const port = Number(arg("--port") ?? 4191);
  if (!route || !selector || !outPath) {
    console.error("usage: --route /path/ --selector CSS --out /abs/file.json [--port N] | --diff A B");
    process.exit(2);
  }
  const snap = await snapshot(route, selector, port);
  fs.writeFileSync(outPath, JSON.stringify(snap));
  const n = Object.values(snap).reduce((s, els) => s + els.length, 0);
  console.log(`computed-style snapshot: ${Object.keys(snap).length} states, ${n} elements -> ${outPath}`);
}
