/** Check the shipped GLBs with the same loader used by the interactive viewer. */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { GLTFLoader } from "../../site/public/exhibits/vendor/GLTFLoader.js";
import { Box3 } from "../../site/public/exhibits/vendor/three.module.min.js";

const expected = {
  virginia: ["construction", "future", "shipyard"],
  f35: ["airframe", "support", "software", "avionics"],
  cyber: ["cognition", "networks", "research"],
};
for (const [subject, topics] of Object.entries(expected)) {
  const bytes = await readFile(new URL(`../../site/public/exhibits/${subject}.glb`, import.meta.url));
  assert.equal(bytes.readUInt32LE(0), 0x46546c67, "GLB magic");
  assert.equal(bytes.readUInt32LE(4), 2, "GLB version");
  assert.equal(bytes.readUInt32LE(8), bytes.length, "GLB declared length");
  assert.ok(bytes.length < 350_000, `${subject}: model exceeds pilot download budget`);
  const { scene } = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), "");
  const found = new Set();
  let count = 0;
  scene.traverse(object => {
    if (!object.isMesh) return;
    count++;
    found.add(object.userData.topic);
    const position = object.geometry.getAttribute("position");
    const normal = object.geometry.getAttribute("normal");
    assert.equal(normal.count, position.count, `${subject}: matching normals`);
    assert.ok(Array.from(position.array).every(Number.isFinite), `${subject}: finite positions`);
    assert.ok(Array.from(normal.array).every(Number.isFinite), `${subject}: finite normals`);
    assert.ok(Array.from(object.geometry.index.array).every(i => i < position.count), `${subject}: valid indices`);
    assert.ok(object.material.isMeshStandardMaterial, `${subject}: compatible material`);
  });
  for (const topic of topics) assert.ok(found.has(topic), `${subject}: missing hotspot geometry for ${topic}`);
  const bounds = new Box3().setFromObject(scene);
  assert.ok(!bounds.isEmpty(), `${subject}: visible extent`);
  console.log(`${subject}: ${count} meshes, ${bytes.length} bytes, all selectable topics and geometry valid`);
}
