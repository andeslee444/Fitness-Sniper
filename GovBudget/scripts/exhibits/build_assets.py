"""Build original, simplified exhibit meshes, GLBs and editorial posters.

No third-party model geometry. Run with Python + numpy/Pillow. A companion
Blender script imports these exact GLBs into editable .blend source files.
Coordinates are glTF Y-up; geometry explains categories, not engineering specs.
"""
from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "site/public/exhibits"
PALETTE = {
    "graphite": [0.13, 0.20, 0.26, 1],
    "metal": [0.28, 0.37, 0.43, 1],
    "cyan": [0.24, 0.73, 0.91, 1],
    "glass": [0.10, 0.38, 0.48, 1],
    "ghost": [0.12, 0.27, 0.34, 1],
    "amber": [0.79, 0.47, 0.23, 1],
}
parts: list[dict] = []


def mesh(name, verts, faces, topic, material="graphite"):
    parts.append(dict(name=name, vertices=verts, faces=faces, topic=topic, material=material))


def box(name, center, size, topic, material="graphite"):
    x, y, z = center
    a, b, c = [v / 2 for v in size]
    v = [[x+sx*a, y+sy*b, z+sz*c] for sx,sy,sz in
         [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    mesh(name,v,[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
                 [3,7,6],[3,6,2],[1,2,6],[1,6,5],[0,4,7],[0,7,3]],topic,material)


def profile(name, stations, center, topic, material="graphite", segments=40):
    # Elliptical sections along X: (x, vertical radius, transverse radius).
    verts=[]
    for x, ry, rz in stations:
        for j in range(segments):
            t=2*math.pi*j/segments
            verts.append([center[0]+x,center[1]+ry*math.cos(t),center[2]+rz*math.sin(t)])
    faces=[]
    for i in range(len(stations)-1):
        for j in range(segments):
            a=i*segments+j; b=i*segments+(j+1)%segments
            faces.extend([[a,b,a+segments],[b,b+segments,a+segments]])
    faces.extend([[0,j+1,j] for j in range(1,segments-1)])
    off=(len(stations)-1)*segments
    faces.extend([[off,off+j,off+j+1] for j in range(1,segments-1)])
    mesh(name,verts,faces,topic,material)


def plate(name, points, thickness, topic, material="metal"):
    n=len(points)
    verts=[[x,y+dy,z] for dy in [-thickness/2,thickness/2] for x,y,z in points]
    faces=[]
    for i in range(1,n-1): faces.extend([[0,i+1,i],[n,n+i,n+i+1]])
    for i in range(n):
        j=(i+1)%n
        faces.extend([[i,j,n+i],[j,n+j,n+i]])
    mesh(name,verts,faces,topic,material)


def rod(name, start, end, radius, topic, material="cyan", segments=8):
    a=np.array(start,float); b=np.array(end,float); d=b-a; d/=np.linalg.norm(d)
    ref=np.array([0,1,0] if abs(d[1])<.9 else [1,0,0],float)
    u=np.cross(d,ref); u/=np.linalg.norm(u); v=np.cross(d,u)
    verts=[(p+radius*(math.cos(t)*u+math.sin(t)*v)).tolist() for p in [a,b]
           for t in [j*math.tau/segments for j in range(segments)]]
    faces=[]
    for j in range(segments):
        k=(j+1)%segments
        faces.extend([[j,k,j+segments],[k,k+segments,j+segments]])
    mesh(name,verts,faces,topic,material)


def submarine():
    hull=[(-6,.02,.02),(-5.85,.25,.25),(-5.55,.51,.51),(-5,.69,.69),
          (-4,.74,.74),(-2,.74,.74),(0,.74,.74),(2,.72,.72),(3.4,.62,.62),
          (4.4,.42,.42),(5,.22,.22),(5.35,.12,.12)]
    profile("Pressure_hull_illustration",hull,[0,1.15,0],"construction")
    # Public exterior silhouette only; no internal compartments.
    profile("Sail",[(-2.5,.03,.04),(-2.35,.62,.26),(-1.2,.62,.26),(-.85,.1,.05)],
            [0,2.15,0],"construction","metal",24)
    for x in [-2.05,-1.74,-1.43]: rod("Mast",[x,2.65,0],[x,3.30,0],.035,"construction","metal")
    for sign in [-1,1]:
        plate("Sail_plane",[(-2.15,1.93,sign*.20),(-1.45,1.93,sign*.20),
              (-1.55,1.93,sign*1.22),(-1.98,1.93,sign*1.22)],.065,"construction")
        plate("Stern_plane",[(3.8,1.15,sign*.2),(5.15,1.15,sign*.12),
              (5.05,1.15,sign*1.5),(4.5,1.15,sign*1.45)],.08,"construction")
    mesh("Tail_fin",[[3.8,1.2,-.07],[5.1,1.2,-.07],[5.1,2.62,-.04],[4.5,2.25,-.04],
                     [3.8,1.2,.07],[5.1,1.2,.07],[5.1,2.62,.04],[4.5,2.25,.04]],
         [[0,1,2],[0,2,3],[4,6,5],[4,7,6],[2,6,7],[2,7,3]],"construction","metal")
    profile("Propulsor",[(5.1,.27,.27),(5.4,.33,.33),(5.7,.30,.30)], [0,1.15,0],"construction","metal")
    # Fine external contour rings read like technical linework.
    for x,r in [(-4,.746),(-2.8,.746),(.3,.743),(2.5,.69),(3.4,.626)]:
        for j in range(40):
            a=j*math.tau/40;b=(j+1)*math.tau/40
            rod("Hull_seam",[x,1.15+r*math.cos(a),r*math.sin(a)],
                [x,1.15+r*math.cos(b),r*math.sin(b)],.008,"construction","cyan",4)
    profile("Future_procurement_illustration",[(x*.40,ry*.40,rz*.40) for x,ry,rz in hull],
            [-2,.48,2.8],"future","ghost",24)
    box("Future_sail",[-2.6,.95,2.8],[.55,.45,.18],"future","cyan")
    box("Shipyard_platform",[4,0,-3.1],[3.3,.15,2.1],"shipyard","ghost")
    box("Workshop",[3.5,.4,-3.4],[1.45,.8,1.1],"shipyard","metal")
    for x in [3,5]: box("Gantry_leg",[x,1.1,-2.7],[.13,2.2,.15],"shipyard","metal")
    box("Gantry_beam",[4,2.2,-2.7],[2.3,.2,.23],"shipyard","cyan")
    rod("Crane_cable",[4.4,2.1,-2.7],[4.4,.6,-2.7],.025,"shipyard","metal")


def fighter():
    profile("Airframe",[(-5,.015,.015),(-4.2,.2,.24),(-3,.4,.48),(-1.9,.55,.64),
                         (-.3,.54,.88),(1.5,.44,.85),(3.1,.38,.5),(4.1,.27,.31)],
            [0,1,0],"airframe",segments=24)
    for side in [-1,1]:
        plate("Swept_wing",[(-1.8,1,side*.45),(1.35,1,side*4.2),(2.1,1,side*4.15),
                             (2.25,1,side*.55)],.12,"airframe")
        plate("Tailplane",[(2.1,1.1,side*.4),(3.25,1.1,side*2.3),
                           (4.35,1.1,side*2.3),(3.8,1.1,side*.38)],.08,"airframe")
        mesh("Canted_vertical_tail",[[2,1.23,side*.68],[3.9,1.23,side*.55],
              [3.78,2.85,side*1.7],[3.1,2.85,side*1.62]],[[0,1,2],[0,2,3]],"airframe","metal")
        profile("Intake",[(-1.7,.22,.23),(-1.1,.28,.32),(.7,.25,.3)],
                [0,.9,side*.70],"airframe","ghost",12)
    profile("Canopy",[(-3.2,.02,.02),(-2.8,.35,.29),(-2,.47,.36),(-1.15,.08,.24)],
            [0,1.45,0],"avionics","glass",24)
    profile("Engine_nozzle",[(3.8,.32,.32),(4.3,.29,.29),(4.42,.23,.23)],
            [0,1,0],"propulsion","metal",32)
    box("Ground_support",[3.6,.23,-3.6],[1.7,.46,.8],"support","metal")
    box("Support_panel",[3.6,.49,-3.6],[1.3,.07,.6],"support","cyan")
    # A separate diagram tile symbolizes software, not a physical aircraft part.
    box("Software_tile",[-3.5,.1,-3.4],[1.3,.2,1.3],"software","ghost")
    for i in range(3): box("Software_layer",[-3.5,.38+i*.18,-3.4],[1.0,.035,1.0],"software","cyan")


def cyber():
    box("Research_platform",[0,.05,0],[9,.15,6],"research","graphite")
    box("Compute_base",[0,.22,0],[2.6,.3,2.6],"cognition","metal")
    box("Compute_core",[0,1,0],[1.4,1.2,1.4],"cognition","glass")
    box("Processor_top",[0,1.62,0],[1.6,.05,1.6],"cognition","cyan")
    for s in [-1,1]:
        for k in range(6):
            z=-.65+k*.26
            rod("Chip_contact",[s*.82,.55,z],[s*1.17,.55,z],.025,"cognition","cyan")
    for idx,(x,z) in enumerate([(-3,-1.7),(-3,1.7),(3,-1.7),(3,1.7)]):
        box("Network_node",[x,.58,z],[.95,.9,.8],"networks","metal")
        for k in range(3): box("Node_indicator",[x,.37+k*.24,z+.409],[.65,.045,.025],"networks","cyan")
        rod("Network_connection",[x,.18,z],[x,.18,0],.025,"networks")
        rod("Network_connection",[x,.18,0],[0,.18,0],.025,"networks")
    for idx,x in enumerate([-1,0,1]):
        box("Research_screen",[x,.85,-2.3],[.75,.9,.10],"research","glass")
        box("Screen_base",[x,.3,-2.25],[.65,.07,.4],"research","metal")
        box("Screen_mark",[x,.86,-2.24],[.5,.045,.025],"research","amber")


def write_glb(subject):
    blob=bytearray(); views=[]; accessors=[]; nodes=[]; meshes=[]
    materials=[dict(name=k,pbrMetallicRoughness=dict(baseColorFactor=v,metallicFactor=.35,
                roughnessFactor=.55),doubleSided=True,emissiveFactor=([.10,.32,.42] if k=="cyan" else [0,0,0]))
               for k,v in PALETTE.items()]
    def accessor(array, typ, component):
        while len(blob)%4: blob.append(0)
        start=len(blob); blob.extend(array.tobytes())
        views.append(dict(buffer=0,byteOffset=start,byteLength=len(blob)-start))
        rec=dict(bufferView=len(views)-1,componentType=component,count=len(array),type=typ)
        if typ=="VEC3": rec.update(min=array.min(0).tolist(),max=array.max(0).tolist())
        accessors.append(rec); return len(accessors)-1
    for part in parts:
        verts=np.array(part['vertices'],dtype='<f4'); faces=np.array(part['faces'],dtype='<u4')
        normals=np.zeros_like(verts)
        for f in faces:
            n=np.cross(verts[f[1]]-verts[f[0]],verts[f[2]]-verts[f[0]])
            for v in f: normals[v]+=n
        lengths=np.linalg.norm(normals,axis=1);lengths[lengths==0]=1;normals/=lengths[:,None]
        pos=accessor(verts,'VEC3',5126);normal=accessor(normals,'VEC3',5126)
        indices=accessor(faces.ravel(),'SCALAR',5125)
        meshes.append(dict(name=part['name'],primitives=[dict(attributes=dict(POSITION=pos,NORMAL=normal),
                      indices=indices,material=list(PALETTE).index(part['material']))]))
        nodes.append(dict(name=f"{part['name']}_{len(nodes)}",mesh=len(meshes)-1,extras=dict(topic=part['topic'])))
    doc=dict(asset=dict(version='2.0',generator='Fiscal Receipts exhibit mesh builder v1',
             copyright='Original illustrative geometry; CC0 1.0'),scene=0,scenes=[dict(nodes=list(range(len(nodes))))],
             nodes=nodes,meshes=meshes,materials=materials,buffers=[dict(byteLength=len(blob))],bufferViews=views,accessors=accessors)
    raw=json.dumps(doc,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4)
    blob+=b'\x00'*((-len(blob))%4)
    glb=struct.pack('<III',0x46546c67,2,12+8+len(raw)+8+len(blob))
    glb+=struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(blob),0x004e4942)+blob
    (OUT/f'{subject}.glb').write_bytes(glb)
    (OUT/f'{subject}.scene.json').write_text(json.dumps(parts,separators=(',',':')))


def poster(subject):
    # CPU projection of the same meshes. Render at double size for antialiasing.
    w,h=1800,960
    camera=np.array([9,7,15] if subject=='virginia' else [10,13,16],float)
    target=np.array([0,.8,0]); forward=target-camera;forward/=np.linalg.norm(forward)
    right=np.cross(forward,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,forward)
    scale=118 if subject=='virginia' else 135
    image=Image.new('RGB',(w,h),(10,22,31));draw=ImageDraw.Draw(image)
    def proj(v):
        d=np.array(v)-target
        return (w*.5+np.dot(d,right)*scale,h*.55-np.dot(d,up)*scale,np.dot(d,forward))
    for x in range(-10,11):
        a=proj([x,-.2,-9]);b=proj([x,-.2,9]);draw.line([a[:2],b[:2]],fill=(18,38,49),width=1)
    for z in range(-9,10):
        a=proj([-10,-.2,z]);b=proj([10,-.2,z]);draw.line([a[:2],b[:2]],fill=(18,38,49),width=1)
    light=np.array([-3,7,5],float);light/=np.linalg.norm(light)
    # Per-pixel depth avoids painter-order artifacts on crossing parts.
    pixels=np.array(image);depth=np.full((h,w),np.inf)
    for part in parts:
        verts=np.array(part['vertices']); projected=np.array([proj(v) for v in verts])
        base=np.array(PALETTE[part['material']][:3])*255
        for face in part['faces']:
            a,b,c=verts[face];normal=np.cross(b-a,c-a);length=np.linalg.norm(normal)
            if length<1e-8:continue
            normal/=length;shade=.48+.70*abs(float(np.dot(normal,light)))
            if part['material']=='cyan':shade=1.05
            color=np.clip(base*shade,0,255).astype(np.uint8)
            p=projected[face];x0,y0,z0=p[0];x1,y1,z1=p[1];x2,y2,z2=p[2]
            left=max(0,int(min(p[:,0])));right_bound=min(w-1,int(max(p[:,0]))+1)
            top=max(0,int(min(p[:,1])));bottom=min(h-1,int(max(p[:,1]))+1)
            if left>right_bound or top>bottom:continue
            denominator=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
            if abs(denominator)<1e-7:continue
            yy,xx=np.mgrid[top:bottom+1,left:right_bound+1]
            wa=((y1-y2)*(xx-x2)+(x2-x1)*(yy-y2))/denominator
            wb=((y2-y0)*(xx-x2)+(x0-x2)*(yy-y2))/denominator
            wc=1-wa-wb;zz=wa*z0+wb*z1+wc*z2
            subdepth=depth[top:bottom+1,left:right_bound+1]
            mask=(wa>=0)&(wb>=0)&(wc>=0)&(zz<subdepth)
            subdepth[mask]=zz[mask];pixels[top:bottom+1,left:right_bound+1][mask]=color
    image=Image.fromarray(pixels)
    image.resize((1440,768),Image.Resampling.LANCZOS).save(OUT/f'{subject}.webp',quality=90)


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    for subject,build in [('virginia',submarine),('f35',fighter),('cyber',cyber)]:
        parts.clear();build();write_glb(subject);poster(subject)
        print(subject,len(parts),'objects',(OUT/f'{subject}.glb').stat().st_size,'GLB bytes')
