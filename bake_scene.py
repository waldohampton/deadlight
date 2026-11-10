import bpy, os, math, sys

OUT = "/home/waldo/repos/deadlight/bake"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = int(os.environ.get('BAKE_SAMPLES', '48'))
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.cycles.diffuse_bounces = 4

RES = int(os.environ.get('BAKE_RES', '512'))

# ---------------------------------------------------------------- materials
def mat(name, rgb, rough=0.92, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m

M_STONE = mat('stone', (0.42, 0.41, 0.36), 0.88)
M_MOSS  = mat('moss',  (0.20, 0.25, 0.14), 0.95)
M_EARTH = mat('earth', (0.17, 0.16, 0.12), 0.97)

# ---------------------------------------------------------------- geometry
def add_box(name, loc, size, material, rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    o.data.materials.append(material)
    return o

def add_plane(name, loc, size, material):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = (size[0], size[1], 1)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    o.data.materials.append(material)
    return o

objs = []
objs.append(add_plane('ground', (0, 0, 0), (26, 26), M_EARTH))

# back wall with an arch opening
objs.append(add_box('wall_back_L', (-5.2, -7.0, 1.6), (4.4, 0.7, 3.2), M_STONE))
objs.append(add_box('wall_back_R', ( 5.2, -7.0, 1.6), (4.4, 0.7, 3.2), M_STONE))
objs.append(add_box('wall_back_top', (0.0, -7.0, 3.35), (6.0, 0.7, 0.6), M_STONE))
objs.append(add_box('wall_back_pier_L', (-1.8, -7.0, 1.45), (0.9, 0.75, 2.9), M_STONE))
objs.append(add_box('wall_back_pier_R', ( 1.8, -7.0, 1.45), (0.9, 0.75, 2.9), M_STONE))

# side wall
objs.append(add_box('wall_side', (-7.4, 0.0, 1.6), (0.7, 14.0, 3.2), M_STONE))

# pillar + rubble
objs.append(add_box('pillar', (-3.2, -3.4, 1.5), (0.9, 0.9, 3.0), M_STONE))
objs.append(add_box('rubble_1', (-1.2, -4.6, 0.28), (1.5, 1.0, 0.56), M_STONE, (0, 0, 0.4)))
objs.append(add_box('rubble_2', (2.6, -3.2, 0.22), (1.1, 0.9, 0.44), M_STONE, (0, 0, -0.7)))
objs.append(add_box('rubble_3', (-4.8, -1.0, 0.18), (0.8, 1.4, 0.36), M_MOSS, (0, 0, 0.2)))

# mossy patch on the ground (a low slab, so the bake has a different albedo to bounce)
objs.append(add_box('moss_patch', (1.4, -1.6, 0.02), (3.2, 3.0, 0.04), M_MOSS))

# ---------------------------------------------------------------- world + sun
world = bpy.data.worlds.new('W')
scene.world = world
world.use_nodes = True
nt = world.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
out = nt.nodes.new('ShaderNodeOutputWorld')
bg = nt.nodes.new('ShaderNodeBackground')
env = nt.nodes.new('ShaderNodeTexEnvironment')
env.image = bpy.data.images.load('/home/waldo/repos/deadlight/looktex/env.hdr')
nt.links.new(env.outputs['Color'], bg.inputs['Color'])
nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
bg.inputs['Strength'].default_value = 0.55

bpy.ops.object.light_add(type='SUN', location=(0, 0, 12))
sun = bpy.context.object
sun.name = 'sun'
sun.data.energy = 5.0
sun.data.color = (1.0, 0.68, 0.44)
sun.data.angle = math.radians(1.5)
sun.rotation_euler = (math.radians(74), 0.0, math.radians(-38))

# ---------------------------------------------------------------- bake
bpy.ops.object.select_all(action='DESELECT')

results = []
for o in objs:
    # lightmap UVs
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    o.select_set(False)

    m = o.data.materials[0]
    m.use_nodes = True
    img = bpy.data.images.new(o.name + '_lm', RES, RES, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'sRGB'
    node = m.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = img
    m.node_tree.nodes.active = node
    node.select = True

    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o

    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'},
                        margin=6, use_clear=True)

    path = os.path.join(OUT, o.name + '_lm.png')
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    results.append((o.name, path))
    print('BAKED', o.name, img.size[0])

# ---------------------------------------------------------------- export
for o in objs:
    m = o.data.materials[0]
    for n in list(m.node_tree.nodes):
        if n.type == 'TEX_IMAGE':
            m.node_tree.nodes.remove(n)

for o in bpy.context.scene.objects:
    o.select_set(True)

bpy.ops.export_scene.gltf(
    filepath=os.path.join(OUT, 'baked.glb'),
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_lights=False,
    export_cameras=False,
)

names = []
with open(os.path.join(OUT, 'manifest.txt'), 'w') as f:
    for name, path in results:
        f.write(name + '\n')
        names.append(name)
print('DONE', len(results), 'objects')
