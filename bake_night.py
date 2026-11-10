import bpy, os, math, random
import numpy as np

OUT = os.environ.get("BAKE_OUT", "/home/waldo/repos/deadlight/bakenight")
TEX = "/home/waldo/repos/deadlight/looktex"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = int(os.environ.get('BAKE_SAMPLES', '32'))
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 5
sc.cycles.diffuse_bounces = 3
RES = int(os.environ.get('BAKE_RES', '384'))

random.seed(7)

# ---------------------------------------------------------------- window facade texture
W = 512; H = 512
img = np.zeros((H, W, 4), dtype=np.float32)
img[:, :, 3] = 1.0
cols, rows = 14, 20
cw, ch = W // cols, H // rows
for r in range(rows):
    for c in range(cols):
        if random.random() < 0.42:
            v = random.uniform(0.25, 1.0)
            warm = random.random()
            col = np.array([v, v * (0.62 + 0.2 * warm), v * (0.30 + 0.25 * warm)], dtype=np.float32)
            pad = 3
            y0 = r * ch + pad; y1 = min(H, (r + 1) * ch - pad)
            x0 = c * cw + pad; x1 = min(W, (c + 1) * cw - pad)
            img[y0:y1, x0:x1, 0:3] = col
win_path = os.path.join(OUT, "windows.png")
wimg = bpy.data.images.new("windows", W, H, alpha=True)
wimg.pixels = img.ravel().tolist()
wimg.filepath_raw = win_path
wimg.file_format = 'PNG'
wimg.save()

# ---------------------------------------------------------------- materials
def tex_node(nt, path, non_color=False, scale=(1, 1), uv='UVMap'):
    n = nt.nodes.new('ShaderNodeTexImage')
    n.image = bpy.data.images.load(path)
    if non_color:
        n.image.colorspace_settings.name = 'Non-Color'
    m = nt.nodes.new('ShaderNodeMapping')
    m.inputs['Scale'].default_value = (scale[0], scale[1], 1)
    u = nt.nodes.new('ShaderNodeUVMap')
    u.uv_map = uv
    nt.links.new(u.outputs['UV'], m.inputs['Vector'])
    nt.links.new(m.outputs['Vector'], n.inputs['Vector'])
    return n

def pbr(name, diff, nor, rough, scale=(2, 2), rough_mul=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    d = tex_node(nt, diff, False, scale)
    nt.links.new(d.outputs['Color'], b.inputs['Base Color'])
    if nor:
        n = tex_node(nt, nor, True, scale)
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(n.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    if rough:
        r = tex_node(nt, rough, True, scale)
        mul = nt.nodes.new('ShaderNodeMath')
        mul.operation = 'MULTIPLY'
        mul.inputs[1].default_value = rough_mul
        nt.links.new(r.outputs['Color'], mul.inputs[0])
        nt.links.new(mul.outputs['Value'], b.inputs['Roughness'])
    b.inputs['Metallic'].default_value = 0.0
    return m

M_GROUND = pbr('wet_asphalt', TEX + '/asphalt_02_diff.jpg', TEX + '/asphalt_02_nor_gl.jpg',
               TEX + '/asphalt_02_rough.jpg', scale=(9, 9), rough_mul=0.42)
M_CONC = pbr('concrete', TEX + '/concrete_wall_008_diff.jpg', TEX + '/concrete_wall_008_nor_gl.jpg',
             TEX + '/concrete_wall_008_rough.jpg', scale=(3, 3))

def flat(name, color, rough=0.5, metal=0.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (color[0], color[1], color[2], 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (emit[0], emit[1], emit[2], 1)
        b.inputs['Emission Strength'].default_value = emit_strength
    return m

M_YELLOW = flat('yellow_paint', (0.72, 0.42, 0.02), rough=0.42, metal=0.15)
M_METAL = flat('dark_metal', (0.09, 0.10, 0.11), rough=0.55, metal=0.75)
M_LAMP = flat('lamp', (0.02, 0.02, 0.02), rough=0.3, emit=(1.0, 0.72, 0.40), emit_strength=14.0)
M_RED = flat('beacon', (0.02, 0.0, 0.0), rough=0.3, emit=(1.0, 0.06, 0.03), emit_strength=26.0)

# building with lit windows
M_BUILD = bpy.data.materials.new('facade')
M_BUILD.use_nodes = True
nt = M_BUILD.node_tree
bb = nt.nodes['Principled BSDF']
cd = tex_node(nt, TEX + '/concrete_wall_008_diff.jpg', False, (10, 4))
nt.links.new(cd.outputs['Color'], bb.inputs['Base Color'])
bb.inputs['Roughness'].default_value = 0.75
we = nt.nodes.new('ShaderNodeTexImage')
we.image = bpy.data.images.load(win_path)
uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'
nt.links.new(uvn.outputs['UV'], we.inputs['Vector'])
nt.links.new(we.outputs['Color'], bb.inputs['Emission Color'])
bb.inputs['Emission Strength'].default_value = 9.0

# ---------------------------------------------------------------- geometry
objs = []

def box(name, loc, size, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    o.data.materials.append(mat)
    objs.append(o)
    return o

def cyl(name, loc, r, h, mat, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    objs.append(o)
    return o

# wet platform
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 10, 0))
g = bpy.context.object; g.name = 'ground'; g.dimensions = (70, 70, 1)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
g.data.materials.append(M_GROUND); objs.append(g)

# curb under the railing
box('curb', (0, 2.2, 0.16), (26, 0.7, 0.32), M_CONC)

# yellow railing
for i in range(9):
    box('rail_post_%d' % i, (-8 + i * 2.0, 2.2, 0.62), (0.07, 0.07, 1.26), M_YELLOW)
box('rail_bar_low', (0, 2.2, 1.2), (17.0, 0.06, 0.06), M_YELLOW)
box('rail_bar_high', (0, 2.2, 0.72), (17.0, 0.05, 0.05), M_YELLOW)

# pipes running across the middle ground
cyl('pipe_a', (0, 7.0, 1.35), 0.34, 34, M_METAL, rot=(0, math.radians(90), 0))
cyl('pipe_b', (0, 7.9, 0.75), 0.22, 34, M_METAL, rot=(0, math.radians(90), 0))
cyl('pipe_c', (0, 8.6, 2.1), 0.16, 34, M_METAL, rot=(0, math.radians(90), 0))

# tank on the left
cyl('tank', (-10.5, 12.0, 3.4), 3.0, 6.8, M_METAL, verts=32)
cyl('tank_cap', (-10.5, 12.0, 6.9), 3.05, 0.18, M_METAL, verts=32)
box('tank_leg_a', (-10.5, 12.0, 1.6), (6.4, 6.4, 0.2), M_METAL)

# gantry on the right
box('gantry_post_a', (7.4, 10.0, 2.6), (0.3, 0.3, 5.2), M_METAL)
box('gantry_post_b', (11.4, 10.0, 2.6), (0.3, 0.3, 5.2), M_METAL)
box('gantry_beam', (9.4, 10.0, 5.2), (4.4, 0.35, 0.35), M_METAL)
box('gantry_deck', (9.4, 10.0, 4.2), (4.4, 1.4, 0.12), M_METAL)

# building facade far back
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 34, 10))
bld = bpy.context.object; bld.name = 'building'; bld.dimensions = (56, 20, 1)
bld.rotation_euler = (math.radians(90), 0, 0)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bld.data.materials.append(M_BUILD); objs.append(bld)
box('parapet', (0, 34, 20.2), (56, 0.6, 0.6), M_CONC)
box('wing_left', (-20, 26, 8.0), (12, 14, 16), M_CONC)
box('wing_right', (24, 28, 6.0), (10, 10, 12), M_CONC)

# practical lamps on poles
lamps = []
for i, x in enumerate((-5.4, -1.8, 1.8, 5.4)):
    cyl('lamp_pole_%d' % i, (x, 4.2, 1.7), 0.05, 3.4, M_METAL)
    lamps.append(box('lamp_head_%d' % i, (x, 4.2, 3.35), (0.5, 0.16, 0.1), M_LAMP))
# strip light along the gantry
box('strip_light', (9.4, 10.0, 4.28), (4.0, 0.1, 0.06), M_LAMP)

# red beacons
for i, (x, y, z) in enumerate(((-20, 26, 21.0), (24, 28, 15.0), (0, 34, 21.0), (-10.5, 12, 7.1))):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14, location=(x, y, z))
    b = bpy.context.object; b.name = 'beacon_%d' % i
    b.data.materials.append(M_RED); objs.append(b)

# a couple of crates for foreground interest
box('crate_a', (-2.6, 0.2, 0.42), (0.85, 0.85, 0.85), M_METAL, (0, 0, 0.3))
box('crate_b', (2.2, -0.6, 0.33), (0.66, 0.66, 0.66), M_METAL, (0, 0, -0.2))

# ---------------------------------------------------------------- world: night sky + faint city glow
world = bpy.data.worlds.new('night'); sc.world = world
world.use_nodes = True
ntw = world.node_tree
for n in list(ntw.nodes): ntw.nodes.remove(n)
out = ntw.nodes.new('ShaderNodeOutputWorld')
bg = ntw.nodes.new('ShaderNodeBackground')
grad = ntw.nodes.new('ShaderNodeTexGradient')
mp = ntw.nodes.new('ShaderNodeMapping')
tc = ntw.nodes.new('ShaderNodeTexCoord')
ramp = ntw.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.012, 0.020, 0.035, 1)
ramp.color_ramp.elements[1].color = (0.05, 0.055, 0.062, 1)
ntw.links.new(tc.outputs['Generated'], mp.inputs['Vector'])
ntw.links.new(mp.outputs['Vector'], grad.inputs['Vector'])
ntw.links.new(grad.outputs['Fac'], ramp.inputs['Fac'])
ntw.links.new(ramp.outputs['Color'], bg.inputs['Color'])
ntw.links.new(bg.outputs['Background'], out.inputs['Surface'])
bg.inputs['Strength'].default_value = 0.55

# a very dim fill sun so unlit surfaces are not pure black
bpy.ops.object.light_add(type='SUN', location=(0, 0, 20))
sun = bpy.context.object
sun.data.energy = 0.35
sun.data.color = (0.45, 0.58, 0.9)
sun.rotation_euler = (math.radians(62), 0, math.radians(170))
objs.append(sun)

# ---------------------------------------------------------------- UVs
bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    if o.type != 'MESH':
        continue
    o.data.uv_layers[0].name = 'UVMap'
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    lm = o.data.uv_layers.new(name='Lightmap')
    o.data.uv_layers.active = lm
    lm.active_render = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.03)
    bpy.ops.object.mode_set(mode='OBJECT')
    o.select_set(False)

# ---------------------------------------------------------------- bake
for o in objs:
    if o.type != 'MESH':
        continue
    m = o.data.materials[0]
    img_lm = bpy.data.images.new(o.name + '_lm', RES, RES, alpha=False)
    img_lm.colorspace_settings.name = 'sRGB'
    node = m.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = img_lm
    m.node_tree.nodes.active = node

    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=6, use_clear=True)

    img_lm.filepath_raw = os.path.join(OUT, o.name + '_lm.png')
    img_lm.file_format = 'PNG'
    img_lm.save()
    print('BAKED', o.name, RES)

for o in objs:
    if o.type != 'MESH':
        continue
    m = o.data.materials[0]
    for n in list(m.node_tree.nodes):
        if n.type == 'TEX_IMAGE' and n.image and n.image.name.endswith('_lm'):
            m.node_tree.nodes.remove(n)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'night.glb'), export_format='GLB',
                          use_selection=True, export_apply=True,
                          export_lights=False, export_cameras=False)
print('DONE', len([o for o in objs if o.type == 'MESH']))
