/**
 * Gate 1's shipped-receipts leg (ROADMAP #196; follow-ups design §5.7).
 * out/json/budget-pdf-receipts must hold exactly v2/ with its 4,096
 * three-hex-digit shards: the 256 two-hex v1 shards an older export left
 * beside v2/ (419,075 bytes) are read by nothing and used to deploy.
 */
import fs from "fs";
import os from "os";
import path from "path";
import { afterEach, describe, expect, it } from "vitest";
import { checkShippedPdfReceipts } from "../build.mjs";

const roots = [];
function outRoot({ shards = 4096, beside = [], inV2 = [] } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "receipts-out-"));
  roots.push(root);
  const dir = path.join(root, "json", "budget-pdf-receipts");
  fs.mkdirSync(path.join(dir, "v2"), { recursive: true });
  for (let i = 0; i < shards; i++) fs.writeFileSync(path.join(dir, "v2", `${i.toString(16).padStart(3, "0")}.json`), "{}\n");
  for (const name of beside) fs.writeFileSync(path.join(dir, name), "{}\n");
  for (const name of inV2) fs.writeFileSync(path.join(dir, "v2", name), "{}\n");
  return root;
}
afterEach(() => { for (const root of roots.splice(0)) fs.rmSync(root, { recursive: true, force: true }); });

describe("checkShippedPdfReceipts", () => {
  it("passes on exactly v2/ with 4,096 shards", () => {
    expect(checkShippedPdfReceipts(outRoot())).toEqual({
      errors: [], notes: ["budget-pdf-receipts: exactly v2/ with 4,096 shards ✓"] });
  });

  it("fails when a v1 shard ships beside v2/", () => {
    expect(checkShippedPdfReceipts(outRoot({ beside: ["00.json"] })).errors).toEqual([
      'out/json/budget-pdf-receipts/ holds ["00.json","v2"]; it must hold exactly v2/ (ROADMAP #196)']);
  });

  it("fails on a missing shard or a stray file in v2/", () => {
    expect(checkShippedPdfReceipts(outRoot({ shards: 4095 })).errors).toEqual([
      "out/json/budget-pdf-receipts/v2/ holds 4095 entries, 4095 of them [0-9a-f]{3}.json shards; it must hold exactly the 4,096 shards"]);
    expect(checkShippedPdfReceipts(outRoot({ inV2: ["notes.txt"] })).errors).toEqual([
      "out/json/budget-pdf-receipts/v2/ holds 4097 entries, 4096 of them [0-9a-f]{3}.json shards; it must hold exactly the 4,096 shards"]);
  });

  it("fails when the directory was never copied", () => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "receipts-out-"));
    roots.push(root);
    expect(checkShippedPdfReceipts(root).errors).toEqual([
      "out/json/budget-pdf-receipts/ not found — prepare-assets 5d2 copies v2/ there"]);
  });
});
