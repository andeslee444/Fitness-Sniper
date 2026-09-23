"""Run with Blender --background --python scripts/exhibits/blender_sources.py.

Imports the published original GLBs into separate editable .blend files. Use
-- --render-posters to also render PNGs under art/exhibits. Each
file retains named mesh objects and topic custom properties. Does not open or
modify an existing user scene. Run in a fresh background Blender process.
"""
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'art/exhibits'
DEST.mkdir(parents=True,exist_ok=True)
RENDER = '--render-posters' in sys.argv

def emissive_material(name, color, strength):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Emission Color'].default_value=(*color,1)
    shader.inputs['Emission Strength'].default_value=strength
    return mat

for subject in ['virginia','f35','cyber']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/f'site/public/exhibits/{subject}.glb'))
    scene=bpy.context.scene
    scene.world=bpy.data.worlds.new('Exhibit world')
    scene.world.use_nodes=True
    background=scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value=(.014,.035,.052,1)
    background.inputs['Strength'].default_value=.5
    # Preserve the public-model geometry; shading and a drafting grid are presentation only.
    for obj in list(scene.objects):
        if obj.type!='MESH': continue
        if any(word in obj.name for word in ['platform','Platform','Workshop','Gantry','panel','Panel','tile','layer','base','Base','core','top','node','screen','Screen']):
            for face in obj.data.polygons: face.use_smooth=False
            bevel=obj.modifiers.new('Soft manufacturing edges','BEVEL');bevel.width=.025;bevel.segments=2
        for mat in obj.data.materials:
            if mat and mat.use_nodes:
                shader=mat.node_tree.nodes.get('Principled BSDF')
                shader.inputs['Roughness'].default_value=.38
    grid=emissive_material('Drafting grid',(.025,.075,.105),.65)
    curves=bpy.data.curves.new('Reference grid','CURVE');curves.dimensions='3D';curves.bevel_depth=.004;curves.bevel_resolution=0
    for axis in range(2):
        for offset in range(-14,15):
            line=curves.splines.new('POLY');line.points.add(1)
            for point,end in zip(line.points,[-16,16]):
                point.co=(offset,end,-.23,1) if axis==0 else (end,offset,-.23,1)
    grid_obj=bpy.data.objects.new('Presentation grid - not program geometry',curves)
    scene.collection.objects.link(grid_obj);curves.materials.append(grid)
    bpy.ops.object.camera_add(location=(9,-15,7) if subject=='virginia' else (10,-16,13))
    cam=bpy.context.object
    cam.rotation_euler=(Vector((0,0,.8))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO';cam.data.ortho_scale=15.25 if subject=='virginia' else 13.33;scene.camera=cam
    for location,power,size,color in [((-5,-8,10),1100,8,(.73,.88,1)),((4,5,9),2100,7,(.25,.72,1)),((-5,5,3),650,5,(.32,.55,.75))]:
        bpy.ops.object.light_add(type='AREA',location=location)
        light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.data.color=color
        light.rotation_euler=(Vector((0,0,1))-light.location).to_track_quat('-Z','Y').to_euler()
    scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
    scene.render.resolution_x=1800;scene.render.resolution_y=960
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(DEST/f'{subject}.png')
    scene['representation']='Simplified public illustration; not an engineering model or component cost allocation.'
    bpy.ops.wm.save_as_mainfile(filepath=str(DEST/f'{subject}.blend'))
    if RENDER: bpy.ops.render.render(write_still=True)
