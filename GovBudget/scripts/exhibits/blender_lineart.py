"""Run with Blender --background --python scripts/exhibits/blender_lineart.py -- [subjects...]

Line-art plates for the visual field guide. Renders the SAME published GLB
geometry as blender_sources.py, from the SAME orthographic camera, but as a
graphite technical drawing on paper instead of a lit clay model on a drafting
grid: white world, flat near-white faces, Freestyle silhouette + crease +
border lines. Output PNGs land in art/exhibits/<subject>-line.png; convert to
WebP for the site with scripts/exhibits/lineart_to_web.mjs.

Geometry is untouched. This is presentation only — see public/exhibits/README.md.
Does not open or modify an existing user scene. Run in a fresh background process.
"""
from math import radians
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'art/exhibits'
DEST.mkdir(parents=True, exist_ok=True)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
BLUEPRINT = '--blueprint' in argv
argv = [a for a in argv if a != '--blueprint']
SUBJECTS = argv or ['virginia', 'f35', 'cyber']
SUFFIX = '-blueprint' if BLUEPRINT else '-line'

CAMERA = {
    'virginia': dict(location=(9, -15, 7), ortho=15.25),
    'f35':      dict(location=(10, -16, 13), ortho=13.33),
    'cyber':    dict(location=(10, -16, 13), ortho=13.33),
}

if BLUEPRINT:
    # Light drafting lines on the site's navy plate (--plate-bg #0a161f register).
    PAPER = (0.0039, 0.0075, 0.012)
    FACE = (0.0075, 0.0145, 0.023)
    GRAPHITE = (0.80, 0.88, 0.92)
else:
    PAPER = (0.965, 0.955, 0.93)      # matches the site's --stage-paper register
    FACE = (0.985, 0.98, 0.965)       # a whisper lighter than paper so forms read
    GRAPHITE = (0.11, 0.12, 0.12)


def flat_material(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = 1.0
    bsdf.inputs['Specular IOR Level'].default_value = 0.0
    return mat


for subject in SUBJECTS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / f'site/public/exhibits/{subject}.glb'))
    scene = bpy.context.scene

    # Paper world, evenly lit so faces carry almost no shading — the lines do the work.
    scene.world = bpy.data.worlds.new('Paper')
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value = (*PAPER, 1)
    bg.inputs['Strength'].default_value = 1.0

    face_mat = flat_material('Plate face', FACE)
    for obj in list(scene.objects):
        if obj.type != 'MESH':
            continue
        obj.data.materials.clear()
        obj.data.materials.append(face_mat)
        for poly in obj.data.polygons:
            poly.use_smooth = False   # crisp creases for Freestyle to find

    cam_cfg = CAMERA[subject]
    bpy.ops.object.camera_add(location=cam_cfg['location'])
    cam = bpy.context.object
    cam.rotation_euler = (Vector((0, 0, .8)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = cam_cfg['ortho']
    scene.camera = cam

    # One soft overhead light: enough to separate top faces from sides, no drama.
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 20))
    sun = bpy.context.object
    sun.data.energy = 3.4
    sun.rotation_euler = (radians(28), radians(-18), 0)

    # Freestyle: silhouette + crease + border, graphite, thin.
    scene.render.use_freestyle = True
    vl = scene.view_layers[0]
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    fs.crease_angle = radians(112)
    fs.use_culling = True
    for ls in list(fs.linesets):
        fs.linesets.remove(ls)
    lineset = fs.linesets.new('Plate lines')
    lineset.select_silhouette = True
    lineset.select_crease = True
    lineset.select_border = True
    lineset.select_contour = True
    lineset.select_edge_mark = False
    lineset.select_material_boundary = False
    style = lineset.linestyle
    style.color = GRAPHITE
    style.thickness = 2.6
    style.thickness_position = 'CENTER'
    style.alpha = 1.0

    engines = [e for e in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES')]
    for e in engines:
        try:
            scene.render.engine = e
            break
        except TypeError:
            continue
    if scene.render.engine == 'CYCLES':
        scene.cycles.samples = 32
        scene.cycles.use_denoising = True
    # No tone mapping: paper must render as paper, graphite as graphite.
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.render.resolution_x = 1800
    scene.render.resolution_y = 960
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(DEST / f'{subject}{SUFFIX}.png')
    scene['representation'] = 'Simplified public illustration rendered as a line plate; not an engineering model or component cost allocation.'
    bpy.ops.render.render(write_still=True)
    print(f'[lineart] wrote {scene.render.filepath} via {scene.render.engine}')
