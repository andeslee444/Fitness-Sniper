import test from 'node:test';
import assert from 'node:assert/strict';
import { layoutPins } from '../../site/public/exhibits/pin-layout.mjs';

function assertSeparate(points, width, height) {
  for (const [i,p] of points.entries()) {
    assert.equal(Boolean(p.hidden),false);
    assert.ok(p.x >= 18 && p.x <= width-18 && p.y >= 18 && p.y <= height-54);
    for (const q of points.slice(i+1)) assert.ok(Math.abs(p.x-q.x)>=38 || Math.abs(p.y-q.y)>=38);
  }
}
test('mobile cyber buttons remain separately clickable when projections overlap',()=>{
  // Network and research projections were only 5.7px apart in the 390px browser review.
  assertSeparate(layoutPins([{x:179.8,y:120},{x:180,y:125.7},{x:180,y:131}],358,275),358,275);
});
test('overlapping buttons near viewport edges remain visible and separated',()=>{
  for(const [x,y] of [[1,1],[350,270],[180,270]])
    assertSeparate(layoutPins(Array.from({length:3},()=>({x,y})),358,275),358,275);
});
test('well-separated projections retain their positions; offscreen pins stay hidden',()=>{
  const points=[{x:30,y:40},{x:140,y:90},{x:290,y:160},{x:-80,y:20,hidden:true}];
  assert.deepEqual(layoutPins(points,358,275),points);
});
