import * as THREE from '../vendor/three.module.min.js';

// Public-facing schematic, built from broad published configuration distinctions.
// This is not a manufacturing model. A/C and B/D intentionally share geometry.
// E and EX share a two-seat schematic; unverified configuration details are omitted.
export const TOPICS = ['airframe', 'cockpit', 'sensors', 'support'];
export const ANCHORS = { airframe: [4.7, .4, 2], cockpit: [0, 1.9, -4.4], sensors: [0, .55, -8.3], support: [-2.1, -.3, 4.8] };

export function createF15(variant = 'EX', options = {}) {
  const root = new THREE.Group();
  root.name = `F-15${variant} simplified schematic`;
  const mats = {
    skin: new THREE.MeshStandardMaterial({ color: 0xb6c5bf, metalness: .18, roughness: .74 }),
    dark: new THREE.MeshStandardMaterial({ color: 0x3d585b, metalness: .24, roughness: .62 }),
    nose: new THREE.MeshStandardMaterial({ color: 0x758d8e, metalness: .12, roughness: .85 }),
    glass: new THREE.MeshStandardMaterial({ color: 0x163944, metalness: .48, roughness: .3 }),
    engine: new THREE.MeshStandardMaterial({ color: 0x50625f, metalness: .65, roughness: .56 }),
    interior: new THREE.MeshStandardMaterial({ color: 0x091216, metalness: .1, roughness: .8 }),
  };
  function add(geometry, material, topic, name) {
    const mesh = new THREE.Mesh(geometry, mats[material].clone());
    mesh.name = name; mesh.userData.topic = topic; mesh.userData.materialRole = material;
    mesh.userData.baseColor = mesh.material.color.clone();
    mesh.userData.baseEmissive = mesh.material.emissive.clone();
    const edge = new THREE.LineSegments(new THREE.EdgesGeometry(geometry, 24), new THREE.LineBasicMaterial({ color: 0xe3eee5, transparent: true, opacity: .48 }));
    edge.userData.edge = true; mesh.add(edge); root.add(mesh); return mesh;
  }
  // Elliptical sections [z, centerY, halfWidth, halfHeight] form continuous skin.
  function loft(sections, material, topic, name, x = 0, segments = 24) {
    const positions = [], indices = [];
    for (const [z, y, rx, ry] of sections) for (let j = 0; j < segments; j++) {
      const a = j / segments * Math.PI * 2;
      positions.push(x + Math.cos(a) * rx, y + Math.sin(a) * ry, z);
    }
    for (let i = 0; i < sections.length - 1; i++) for (let j = 0; j < segments; j++) {
      const a = i * segments + j, b = i * segments + (j + 1) % segments;
      indices.push(a, b, a + segments, b, b + segments, a + segments);
    }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));g.setIndex(indices);g.computeVertexNormals();
    return add(g, material, topic, name);
  }
  function plate(points, thickness, material, topic, name) {
    const vertices = [], indices = [], n = points.length;
    for (const dy of [-thickness / 2, thickness / 2]) for (const [x, y, z] of points) vertices.push(x, y + dy, z);
    for (let i = 1; i < n - 1; i++) indices.push(0, i, i + 1, n, n + i + 1, n + i);
    for (let i = 0; i < n; i++) {const j = (i + 1) % n;indices.push(i, n + i, j, j, n + i, n + j);}
    const g = new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.setIndex(indices);g.computeVertexNormals();
    return add(g, material, topic, name);
  }
  function line(points, opacity = .3, color = 0x254951) {
    const g = new THREE.BufferGeometry().setFromPoints(points.map(p=>new THREE.Vector3(...p)));
    const l = new THREE.Line(g, new THREE.LineBasicMaterial({ color, transparent: true, opacity }));
    l.userData.panel = true;root.add(l);return l;
  }
  function box(size, pos, material, topic, name) {const m=add(new THREE.BoxGeometry(...size),material,topic,name);m.position.set(...pos);return m;}

  loft([[-9.75,.1,.025,.025],[-9.15,.12,.2,.23],[-8.35,.12,.43,.42],[-7.45,.13,.59,.51]],'nose','sensors','Radome');
  loft([[-7.45,.13,.59,.51],[-6.5,.14,.72,.66],[-5.5,.14,.8,.75],[-3.8,.1,.98,.7],[-2,.02,1.38,.64],[.2,-.06,1.55,.62],[3.5,-.05,1.63,.57],[6.25,-.05,1.45,.38],[7.2,-.05,.4,.17]],'skin','airframe','Fuselage');
  for (const sign of [-1,1]) {
    // Prominent rectangular variable-ramp intakes and twin-engine nacelles.
    const x = sign * 1.28;
    const intake = plate([[x-sign*.59,.48,-4.1],[x+sign*.59,.48,-3.6],[x+sign*.62,.48,-.65],[x-sign*.59,.48,-.95]],.95,'skin','airframe','Intake nacelle');
    intake.userData.topic='airframe';
    box([1.0,.55,.04],[x,-.02,-3.99],'interior','airframe','Intake opening').rotation.y=sign*.24;
    box([1.13,.095,.42],[x,.49,-3.88],'nose','airframe','Intake ramp').rotation.y=sign*.24;
    loft([[-1.25,-.12,.6,.52],[.4,-.16,.75,.66],[3.9,-.18,.76,.67],[6.2,-.16,.67,.61],[7.2,-.14,.65,.59]],'skin','airframe','Engine housing',sign*.94);
    loft([[6.9,-.14,.655,.59],[7.35,-.14,.63,.57],[7.9,-.14,.56,.51]],'engine','airframe','Exhaust nozzle',sign*.94);
    const exhaust = add(new THREE.CylinderGeometry(.48,.48,.045,28),'interior','airframe','Exhaust interior');exhaust.rotation.x=Math.PI/2;exhaust.position.set(sign*.94,-.14,7.88);
    for(let j=0;j<18;j++){const a=j/18*Math.PI*2;line([[sign*.94+Math.cos(a)*.65,-.14+Math.sin(a)*.59,6.95],[sign*.94+Math.cos(a)*.56,-.14+Math.sin(a)*.51,7.9]],.3,0xa8a5a0);}
    const wing = [[1.2,.15,-2.5],[1.9,.13,-2.2],[6.5,.03,1.65],[6.42,.01,3.18],[3.05,.1,3.2],[1.42,.16,2.8]].map(([a,b,c])=>[a*sign,b,c]);
    if(sign<0)wing.reverse();plate(wing,.15,'skin','airframe','Main wing');
    line([[sign*2.7,.25,1.15],[sign*5.87,.15,2.47],[sign*5.82,.13,3.17]],.36);
    line([[sign*2.38,.24,-1.63],[sign*2.92,.22,3.1]],.2);
    line([[sign*3.7,.19,-.51],[sign*4.34,.17,3.14]],.15);
    line([[sign*1.77,.25,2.34],[sign*6.39,.11,2.63]],.23);
    const stabilizer=[[1.26,.16,4.64],[2.0,.14,4.8],[4.36,.1,7.2],[4.34,.1,8.47],[1.5,.2,7.76]].map(([a,b,c])=>[sign*a,b,c]);
    if(sign<0)stabilizer.reverse();plate(stabilizer,.13,'skin','airframe','Horizontal stabilizer');
    line([[sign*2.14,.24,6.53],[sign*4.3,.18,7.82]],.35);
    // Twin vertical stabilizers: flat fin thickness follows the transverse axis.
    const shape = new THREE.Shape();shape.moveTo(3.55,.45);shape.lineTo(5.44,3.44);shape.lineTo(6.27,3.46);shape.lineTo(8.13,.5);shape.closePath();
    const fg = new THREE.ExtrudeGeometry(shape,{depth:.11,bevelEnabled:true,bevelSize:.025,bevelThickness:.025,bevelSegments:1,steps:1});
    fg.rotateY(-Math.PI/2);fg.translate(sign*1.61,.03,0);
    add(fg,'skin','airframe','Vertical stabilizer');
    line([[sign*1.7,.73,7.75],[sign*1.7,3.38,6.11]],.42);
    for(const z of [.7,2.1,3.5,5])line([[sign*1.13,.61,z],[sign*1.53,.39,z],[sign*1.7,-.08,z]],.18);
    if(variant==='E' || (variant==='EX' && options.conformal)) {
      loft([[-3.1,-.56,.03,.03],[-2.25,-.57,.36,.48],[0,-.59,.48,.55],[3.55,-.57,.38,.45],[4.8,-.44,.02,.02]],'skin','airframe','Conformal fuel tank',sign*1.71,18);
      line([[sign*1.91,-.22,-2.25],[sign*2.19,-.22,0],[sign*2.03,-.22,3.55]],.3);
    }
  }
  const twoSeat = !['A','C'].includes(variant);
  const rear = twoSeat ? -2.8 : -3.65;
  // Canopy elongation and seating are the only asserted variant geometry changes.
  loft([[-6.85,.67,.035,.02],[-6.35,.82,.33,.23],[-5.67,.92,.48,.46],[-4.75,.93,.51,.54],[rear+.25,.75,.28,.23],[rear+.65,.65,.02,.01]],'glass','cockpit',twoSeat?'Two-seat canopy':'Single-seat canopy',0,24);
  const framePositions = twoSeat ? [-5.67,-4.48,-3.12] : [-5.67,-3.95];
  for(const z of framePositions){const r=z<-5? .48 : z<rear+.1 ? .47 : .31;const points=[];for(let j=0;j<=16;j++){const a=j/16*Math.PI;points.push([Math.cos(a)*r,.88+Math.sin(a)*r,z]);}line(points,.7);}
  line([[0,.69,-6.8],[0,1.38,-5.55],[0,1.46,-4.6],[0,1.03,rear+.2],[0,.67,rear+.63]],.45);
  // Aerials are general schematic marks, not claims about a specific sensor fit.
  plate([[-.08,.69,-1.5],[.08,.69,-1.5],[.055,1.09,-.77],[-.055,1.09,-.77]],.06,'dark','sensors','Dorsal aerial');
  line([[0,.64,-2.0],[0,.59,.6],[0,.57,3.8]],.25);
  for(const z of [-7.44,-6.87]){const r=z<-7?.59:.66;const points=[];for(let j=0;j<=30;j++){const a=j/30*Math.PI*2;points.push([Math.cos(a)*r,.13+Math.sin(a)*(r*.88),z]);}line(points,.32);}
  root.userData.variant=variant;root.userData.twoSeat=twoSeat;
  return root;
}

export function disposeModel(root) {
  root.traverse(object => { object.geometry?.dispose();if(object.material)for(const material of Array.isArray(object.material)?object.material:[object.material])material.dispose(); });
}
