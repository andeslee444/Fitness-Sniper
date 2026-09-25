import * as THREE from './vendor/three.module.min.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';
import { OrbitControls } from './vendor/OrbitControls.js';
import { layoutPins } from './pin-layout.mjs';

// Browser-only, locally served and fetched only after "Explore in 3D".
// Render on interaction; no idle animation loop or outside network requests.
class FiscalScene extends HTMLElement {
  static observedAttributes = ['selected', 'blueprint', 'reset'];
  connectedCallback() { this.start(); }
  attributeChangedCallback(name) {
    if (!this.model) return;
    if (name === 'reset') this.resetView();
    this.styleModel(); this.draw();
  }
  async start() {
    this.disposed = false;
    this.life = new AbortController();
    try {
      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.renderer.setClearColor(0x0a161f);
      this.renderer.outputColorSpace = THREE.SRGBColorSpace;
      this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
      this.renderer.toneMappingExposure = 1.5;
      this.world = new THREE.Scene();
      this.world.add(new THREE.HemisphereLight(0xc4eeff, 0x17202b, 2));
      const key = new THREE.DirectionalLight(0xffffff, 3.5); key.position.set(-4, 9, 6); this.world.add(key);
      const rim = new THREE.DirectionalLight(0x6fd8ff, 2.5); rim.position.set(2, 5, -7); this.world.add(rim);
      this.camera = new THREE.PerspectiveCamera(34, 2, .1, 150);
      const canvas = this.renderer.domElement;
      canvas.tabIndex = 0;
      canvas.setAttribute('aria-label', this.getAttribute('aria-label'));
      canvas.setAttribute('role', 'img');
      this.append(canvas);
      this.controls = new OrbitControls(this.camera, canvas);
      canvas.style.touchAction = 'pan-y';
      this.controls.enablePan = false;
      this.controls.enableZoom = false; // preserve page scrolling; +/- keys zoom.
      this.controls.minPolarAngle = .15;
      this.controls.maxPolarAngle = Math.PI * .49;
      this.controls.addEventListener('change', () => this.draw());
      canvas.addEventListener('keydown', e => this.onKey(e), { signal: this.life.signal });
      canvas.addEventListener('webglcontextlost', e => { e.preventDefault(); this.fail(); }, { signal: this.life.signal });
      this.raycaster = new THREE.Raycaster();
      let down;
      canvas.addEventListener('pointerdown', e => { down = [e.clientX, e.clientY]; }, { signal: this.life.signal });
      canvas.addEventListener('pointerup', e => {
        if (!this.model || !down || Math.hypot(e.clientX-down[0],e.clientY-down[1]) > 5) return;
        const r = canvas.getBoundingClientRect();
        this.raycaster.setFromCamera(new THREE.Vector2((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1),this.camera);
        const hit = this.raycaster.intersectObjects(this.meshes).find(h => this.topics.some(t=>t.id===h.object.userData.topic));
        if (hit) this.dispatchEvent(new CustomEvent('topic-select', { detail: { topic: hit.object.userData.topic } }));
      }, { signal: this.life.signal });
      this.resize = new ResizeObserver(() => this.resizeScene()); this.resize.observe(this);
      this.topics = JSON.parse(this.getAttribute('topics') || '[]');
      const gltf = await new GLTFLoader().loadAsync(this.getAttribute('src'));
      if (this.disposed) { this.disposeObject(gltf.scene); return; }
      this.model = gltf.scene; this.world.add(this.model); this.meshes = [];
      const bounds = new THREE.Box3().setFromObject(this.model);
      this.center = bounds.getCenter(new THREE.Vector3());
      this.radius = bounds.getSize(new THREE.Vector3()).length() / 2;
      this.model.traverse(obj => {
        if (!obj.isMesh) return;
        if (obj.userData.topic === 'propulsion') obj.userData.topic = 'airframe';
        obj.material = obj.material.clone();
        obj.userData.original = { color: obj.material.color.clone(), emissive: obj.material.emissive.clone() };
        this.meshes.push(obj);
      });
      for (const mesh of this.meshes) {
        const edges = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry, 26),
          new THREE.LineBasicMaterial({ color: 0x75cbe9, transparent: true, opacity: .21 }));
        edges.userData.outline = true; mesh.add(edges);
      }
      this.grid = new THREE.GridHelper(24, 32, 0x23404e, 0x172c38); this.grid.position.y = -.23; this.world.add(this.grid);
      this.pins = this.topics.map((topic, index) => {
        const b = new THREE.Box3();
        let anchors = this.meshes.filter(m => m.userData.topic === topic.id);
        if (this.getAttribute('subject') === 'cyber') {
          if (topic.id === 'networks') anchors = anchors.filter(m => m.name.startsWith('Network_node')).slice(-1);
          if (topic.id === 'research') anchors = anchors.filter(m => m.name.startsWith('Research_screen'));
        }
        for (const mesh of anchors) b.expandByObject(mesh);
        const position = b.getCenter(new THREE.Vector3()); position.y = b.max.y + .35;
        const button = document.createElement('button');button.className = 'scene-pin';button.textContent = `0${index+1}`;
        button.setAttribute('aria-label', `Explore ${topic.label}`);button.title=topic.label;
        button.addEventListener('click', () => this.dispatchEvent(new CustomEvent('topic-select', {detail:{topic:topic.id}})), {signal:this.life.signal});
        this.append(button);return {button,position,id:topic.id};
      });
      this.resetView();this.styleModel();this.resizeScene();
      this.setAttribute('data-ready','true');
      this.dispatchEvent(new CustomEvent('scene-ready'));
    } catch (error) { console.warn('Program exhibit: 3D unavailable', error); this.fail(); }
  }
  resetView() {
    if (!this.center) return;
    const direction = new THREE.Vector3(...(this.getAttribute('subject') === 'virginia' ? [9,7,15] : [10,13,16])).normalize();
    this.distance = this.radius * (this.clientWidth / Math.max(1,this.clientHeight) < 1.5 ? 3.4 : 2.65);
    this.camera.position.copy(this.center).addScaledVector(direction,this.distance);
    this.controls.target.copy(this.center);this.controls.update();this.draw();
  }
  resizeScene() {
    if (!this.renderer || this.disposed) return;
    const w=this.clientWidth,h=this.clientHeight;if (!w || !h) return;
    this.renderer.setSize(w,h,false);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.draw();
  }
  styleModel() {
    const selected=this.getAttribute('selected'), blueprint=this.getAttribute('blueprint') === 'true';
    for (const mesh of this.meshes) {
      const material=mesh.material, original=mesh.userData.original, active=mesh.userData.topic === selected;
      material.color.copy(original.color);
      material.emissive.copy(original.emissive);
      material.wireframe=blueprint;material.transparent=blueprint;material.opacity=blueprint ? .75 : 1;
      if (blueprint) { material.color.set(0x75c9e3);material.emissive.set(0x143341); }
      else if (active) material.emissive.add(new THREE.Color(.025,.075,.09));
      for(const edge of mesh.children.filter(c=>c.userData.outline)) {
        edge.visible=!blueprint;edge.material.opacity=active ? .45 : .16;
      }
    }
    for (const pin of this.pins || []) pin.button.setAttribute('aria-pressed',String(pin.id===selected));
  }
  onKey(e) {
    if (!this.center) return;
    const d=this.camera.position.clone().sub(this.controls.target);const s=new THREE.Spherical().setFromVector3(d);
    const actions={ArrowLeft:()=>s.theta-=.14,ArrowRight:()=>s.theta+=.14,ArrowUp:()=>s.phi=Math.max(.15,s.phi-.1),ArrowDown:()=>s.phi=Math.min(Math.PI*.49,s.phi+.1),'+':()=>s.radius=Math.max(this.radius*1.8,s.radius*.9),'=':()=>s.radius=Math.max(this.radius*1.8,s.radius*.9),'-':()=>s.radius=Math.min(this.radius*5,s.radius*1.1)};
    if (!actions[e.key]) return;e.preventDefault();actions[e.key]();
    this.camera.position.copy(this.controls.target).add(new THREE.Vector3().setFromSpherical(s));this.controls.update();this.draw();
  }
  draw() {
    if (!this.renderer || this.disposed || !this.world) return;
    this.renderer.render(this.world,this.camera);
    const projected = (this.pins || []).map(pin => {
      const p=pin.position.clone().project(this.camera);
      return { pin, x:(p.x+1)*.5*this.clientWidth, y:(-p.y+1)*.5*this.clientHeight,
        hidden:Math.abs(p.x)>1 || Math.abs(p.y)>1 || p.z>1 };
    });
    for (const {pin,x,y,hidden} of layoutPins(projected,this.clientWidth,this.clientHeight)) {
      pin.button.style.left=`${x}px`;pin.button.style.top=`${y}px`;pin.button.hidden=hidden;
    }
  }
  fail() { if(!this.disposed)this.dispatchEvent(new CustomEvent('scene-error')); }
  disposeObject(object) {
    object.traverse(o=> {o.geometry?.dispose();if(o.material){for(const m of (Array.isArray(o.material)?o.material:[o.material]))m.dispose();}});
  }
  disconnectedCallback() {
    this.disposed=true;this.life?.abort();this.resize?.disconnect();this.controls?.dispose();
    if(this.world)this.disposeObject(this.world);
    this.renderer?.dispose();this.renderer?.forceContextLoss();this.replaceChildren();
  }
}
if(!customElements.get('fiscal-scene'))customElements.define('fiscal-scene',FiscalScene);
