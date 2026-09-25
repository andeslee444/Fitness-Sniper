// Convert art/exhibits/<subject>-line.png → site/public/exhibits/<subject>-line.webp
// Format conversion only (Sharp WebP q88, effort 6); no crop or resize.
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(here, "../..");
const require = createRequire(path.join(ROOT, "site/package.json"));
const sharp = require("sharp");
const args = process.argv.slice(2);
const suffix = args.includes("--blueprint") ? "-blueprint" : "-line";
const subjects = args.filter(a => a !== "--blueprint");
const list = subjects.length ? subjects : ["virginia", "f35", "cyber"];
for (const s of list) {
  const src = path.join(ROOT, "art/exhibits", `${s}${suffix}.png`);
  const out = path.join(ROOT, "site/public/exhibits", `${s}${suffix}.webp`);
  const info = await sharp(src).webp({ quality: 88, effort: 6 }).toFile(out);
  console.log(`${s}${suffix}.webp  ${info.width}x${info.height}  ${info.size} bytes`);
}
