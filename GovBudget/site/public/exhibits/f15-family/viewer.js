import * as THREE from '../vendor/three.module.min.js';
import { OrbitControls } from '../vendor/OrbitControls.js';
import { createF15, disposeModel, TOPICS, ANCHORS } from './geometry.mjs';

// Loaded only after activation. Rendering happens only after input or resize.
class F15FamilyScene extends HTMLElement {
  static observedAttributes = ['variant', 'compare', 'selected', 'blueprint', 'conformal'];
  connectedCallback() { this.start(); }
  attributeChangedCallback(name) {
    if(!this.renderer)return;
    if(['variant','compare','conformal'].includes(name))this.buildModels();
    this.styleModels();this.draw();
  }
  start() {
    this.disposed=false;this.life=new AbortController();this.meshes=[];this.pins=[];
    try {
      this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.75));
      this.renderer.setClearColor(0x0a1b22,0);this.renderer.outputColorSpace=THREE.SRGBColorSpace;
      this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.08;
      this.world=new THREE.Scene();
      this.world.add(new THREE.HemisphereLight(0xe8f1ed,0x193039,2.1));
      this.keyLight=new THREE.DirectionalLight(0xfff6df,3.1);this.keyLight.position.set(-12,18,-15);this.world.add(this.keyLight);
      const rim=new THREE.DirectionalLight(0x9bcad1,1.7);rim.position.set(12,5,12);this.world.add(rim);
      const fill=new THREE.DirectionalLight(0xb6d4da,1.2);fill.position.set(-8,1,9);this.world.add(fill);
      this.camera=new THREE.OrthographicCamera(-15,15,9,-9,.1,180);
      this.camera.position.set(30,19,-18);this.camera.lookAt(0,.8,-.5);
      const canvas=this.renderer.domElement;canvas.tabIndex=0;canvas.setAttribute('role','img');
      canvas.setAttribute('aria-label','Interactive simplified F-15 model. Drag to rotate. Arrow keys rotate, plus and minus zoom. Use the topic buttons to inspect a system.');
      this.append(canvas);
      this.controls=new OrbitControls(this.camera,canvas);this.controls.target.set(0,.8,-.5);
      this.controls.enablePan=false;this.controls.enableZoom=false;this.controls.enableDamping=false;
      this.controls.minPolarAngle=.025;this.controls.maxPolarAngle=Math.PI*.57;
      this.controls.rotateSpeed=.65;canvas.style.touchAction='pan-y';
      this.controls.addEventListener('change',()=>{this.setAttribute('data-camera',`${this.camera.position.x.toFixed(2)},${this.camera.position.y.toFixed(2)},${this.camera.position.z.toFixed(2)}`);this.draw();});
      this.controls.addEventListener('end',()=>{if(this.dragged)this.dispatchEvent(new CustomEvent('model-interact',{detail:{kind:'rotate'}}));});
      this.controls.update();
      canvas.addEventListener('keydown',e=>this.onKey(e),{signal:this.life.signal});
      canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();this.fail();},{signal:this.life.signal});
      this.raycaster=new THREE.Raycaster();
      let down=null;
      canvas.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY];this.dragged=false;canvas.focus({preventScroll:true});},{signal:this.life.signal});
      canvas.addEventListener('pointerup',e=>{
        if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>6){down=null;return;}
        down=null;const hit=this.hitAt(e);
        if(hit)this.selectTopic(hit.object.userData.topic);
      },{signal:this.life.signal});
      canvas.addEventListener('pointercancel',()=>{down=null;},{signal:this.life.signal});
      canvas.addEventListener('pointermove',e=>{
        if(e.buttons&&down){if(Math.hypot(e.clientX-down[0],e.clientY-down[1])>6)this.dragged=true;return;}
        if(e.pointerType!=='mouse')return;
        const rect=canvas.getBoundingClientRect();
        this.keyLight.position.x=-9+(e.clientX-rect.left)/rect.width*4;
        const hit=this.hitAt(e),topic=hit?.object.userData.topic;
        if(topic!==this.hovered){this.hovered=topic;canvas.style.cursor=topic?'pointer':'grab';this.styleModels();}
        this.queueDraw();
      },{signal:this.life.signal});
      canvas.addEventListener('pointerleave',()=>{this.hovered=null;this.styleModels();this.queueDraw();},{signal:this.life.signal});
      this.addDraftingGrid();this.buildModels();
      for(const [index,topic] of TOPICS.entries()) {
        const button=document.createElement('button');button.className='f15-model-pin';button.type='button';
        button.textContent=`0${index+1}`;button.title=topic==='support'?'Tooling and support (conceptual link)':topic;
        button.setAttribute('aria-label',`Inspect ${topic==='support'?'tooling and support':topic}`);
        button.addEventListener('click',()=>this.selectTopic(topic),{signal:this.life.signal});this.append(button);
        this.pins.push({button,topic,anchor:new THREE.Vector3(...ANCHORS[topic])});
      }
      this.styleModels();this.resize=new ResizeObserver(()=>this.resizeScene());this.resize.observe(this);this.resizeScene();
      this.setAttribute('data-ready','true');this.dispatchEvent(new CustomEvent('model-ready'));
    }catch(error){console.warn('F-15 family illustration unavailable',error);this.fail();}
  }
  addDraftingGrid() {
    const grid=new THREE.GridHelper(28,14,0x48686b,0x31535a);grid.position.y=-1.35;
    grid.material.transparent=true;grid.material.opacity=.12;this.world.add(grid);

  }
  buildModels() {
    for(const model of [this.model,this.comparison])if(model){this.world.remove(model);disposeModel(model);}
    const valid=['A','B','C','D','E','EX'];const variant=valid.includes(this.getAttribute('variant'))?this.getAttribute('variant'):'EX';
    const options={conformal:this.getAttribute('conformal')==='true'};
    this.model=createF15(variant,options);this.world.add(this.model);this.meshes=[];
    this.model.traverse(o=>{if(o.isMesh)this.meshes.push(o);});
    this.comparison=null;const compare=this.getAttribute('compare');
    if(valid.includes(compare)&&compare!==variant) {
      this.comparison=createF15(compare,options);this.comparison.scale.setScalar(1.004);
      this.comparison.traverse(o=>{
        if(o.isMesh){o.material.color.set(0xe5b77e);o.material.transparent=true;o.material.opacity=.045;o.material.depthWrite=false;o.material.polygonOffset=true;o.material.polygonOffsetFactor=-1;}
        else if(o.isLine){o.material.color.set(0xe5b77e);o.material.opacity=.38;o.material.depthWrite=false;}
      });this.world.add(this.comparison);
    }
    this.setAttribute('data-model-variant',variant);this.setAttribute('data-comparison',this.comparison?compare:'none');
    this.setAttribute('data-seat-count',String(this.model.userData.twoSeat?2:1));
  }
  hitAt(e) {
    const rect=this.renderer.domElement.getBoundingClientRect();
    this.raycaster.setFromCamera(new THREE.Vector2((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1),this.camera);
    return this.raycaster.intersectObjects(this.meshes,false).find(hit=>TOPICS.includes(hit.object.userData.topic));
  }
  selectTopic(topic) {
    this.dispatchEvent(new CustomEvent('topic-select',{detail:{topic}}));
  }
  styleModels() {
    const selected=this.getAttribute('selected'),blueprint=this.getAttribute('blueprint')==='true';
    for(const mesh of this.meshes){const active=mesh.userData.topic===selected,hovered=mesh.userData.topic===this.hovered;
      mesh.material.color.copy(mesh.userData.baseColor);mesh.material.emissive.copy(mesh.userData.baseEmissive);
      mesh.material.wireframe=false;mesh.material.transparent=false;mesh.material.opacity=1;
      if(blueprint){
        const role=mesh.userData.materialRole;
        mesh.material.color.set(role==='glass'?0x163944:role==='interior'?0x0b1b20:role==='engine'?0x506562:role==='nose'?0x7b9999:0xb9cdc5);
        mesh.material.emissive.set(0x000000);
      }
      if(active||hovered)mesh.material.emissive.set(active?0x153638:0x0b2328);
      for(const edge of mesh.children){edge.visible=true;edge.material.opacity=blueprint?.58:active?.62:hovered?.45:.2;}
    }
    for(const pin of this.pins||[])pin.button.setAttribute('aria-pressed',String(pin.topic===selected));
  }
  setView(view) {
    const presets={quarter:[30,19,-18],side:[32,2.5,0],top:[0,35,.015],front:[0,3,-35]};
    if(!presets[view])return;
    this.camera.position.set(...presets[view]);this.controls.target.set(0,.8,-.5);this.camera.zoom=1;
    this.camera.updateProjectionMatrix();this.controls.update();this.draw();
    this.dispatchEvent(new CustomEvent('model-interact',{detail:{kind:'view'}}));
  }
  nudge(action) {
    const offset=this.camera.position.clone().sub(this.controls.target),s=new THREE.Spherical().setFromVector3(offset);
    if(action==='left')s.theta-=.16;if(action==='right')s.theta+=.16;
    if(action==='up')s.phi=Math.max(.025,s.phi-.12);if(action==='down')s.phi=Math.min(Math.PI*.57,s.phi+.12);
    if(action==='in')this.camera.zoom=Math.min(2.3,this.camera.zoom*1.12);if(action==='out')this.camera.zoom=Math.max(.65,this.camera.zoom/1.12);
    this.camera.position.copy(this.controls.target).add(new THREE.Vector3().setFromSpherical(s));this.camera.updateProjectionMatrix();this.controls.update();this.draw();
  }
  onKey(e) {
    const actions={ArrowLeft:'left',ArrowRight:'right',ArrowUp:'up',ArrowDown:'down','+':'in','=':'in','-':'out'};
    if(!actions[e.key])return;e.preventDefault();this.nudge(actions[e.key]);
  }
  resizeScene() {
    if(!this.renderer||this.disposed)return;const w=this.clientWidth,h=this.clientHeight;if(!w||!h)return;
    this.renderer.setSize(w,h,false);const half=Math.max(5.7,10.9/(w/h));
    this.camera.left=-half*w/h;this.camera.right=half*w/h;this.camera.top=half;this.camera.bottom=-half;this.camera.updateProjectionMatrix();this.draw();
  }
  queueDraw(){if(this.frame)return;this.frame=requestAnimationFrame(()=>{this.frame=null;this.draw();});}
  draw() {
    if(!this.renderer||this.disposed)return;this.renderer.render(this.world,this.camera);
    const width=this.clientWidth,height=this.clientHeight;
    const placed=[];
    for(const pin of this.pins||[]){const p=pin.anchor.clone().project(this.camera);let x=(p.x+1)*.5*width,y=(-p.y+1)*.5*height;
      x=Math.max(22,Math.min(width-22,x));y=Math.max(22,Math.min(height-22,y));
      for(const other of placed)if(Math.hypot(x-other.x,y-other.y)<44)y=Math.min(height-22,other.y+45);
      placed.push({x,y});pin.button.style.left=`${x}px`;pin.button.style.top=`${y}px`;pin.button.hidden=p.z>1;
    }
  }
  fail(){if(!this.disposed){this.setAttribute('data-error','true');this.dispatchEvent(new CustomEvent('model-error'));}}
  disconnectedCallback(){
    this.disposed=true;this.life?.abort();this.resize?.disconnect();this.controls?.dispose();if(this.frame)cancelAnimationFrame(this.frame);
    if(this.world)disposeModel(this.world);this.renderer?.dispose();this.renderer?.forceContextLoss();this.replaceChildren();
  }
}
if(!customElements.get('f15-family-scene'))customElements.define('f15-family-scene',F15FamilyScene);
