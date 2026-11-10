import bpy, os, math

OUT = os.environ.get("BAKE_OUT", "/home/waldo/repos/deadlight/bake2")
TEX = "/home/waldo/repos/deadlight/looktex"
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = int(os.environ.get('BAKE_SAMPLES', '64'))
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.cycles.diffuse_bounces = 4
RES = int(os.environ.get('BAKE_RES', '1024'))
STAGE = os.environ.get('STAGE', 'a')

# ---------------------------------------------------------------- materials with real textures
def image_tex(nt, path, non_color=False, scale=(1,1)):
    n = nt.nodes.new('ShaderNodeTexImage')
    n.image = bpy.data.images.load(path)
    if non_color:
        n.image.colorspace_settings.name = 'Non-Color'
    m = nt.nodes.new('ShaderNodeMapping')
    m.inputs['Scale'].default_value = (scale[0], scale[1], 1)
    uv = nt.nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'UVMap'
    nt.links.new(uv.outputs['UV'], m.inputs['Vector'])
    nt.links.new(m.outputs['Vector'], n.inputs['Vector'])
    return n

def pbr(name, diff, nor, rough, scale=(2,2), tint=(1,1,1)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (tint[0], tint[1], tint[2], 1.0)

    d = image_tex(nt, diff, False, scale)
    nt.links.new(d.outputs['Color'], b.inputs['Base Color'])

    if nor and os.path.exists(nor):
        n = image_tex(nt, nor, True, scale)
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(n.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])

    if rough and os.path.exists(rough):
        r = image_tex(nt, rough, True, scale)
        nt.links.new(r.outputs['Color'], b.inputs['Roughness'])

    b.inputs['Metallic'].default_value = 0.0
    return m

M_GROUND = pbr('ground',
    TEX + '/forest_ground_04_diff_2k.jpg',
    TEX + '/forest_ground_04_nor_gl_2k.jpg',
    TEX + '/forest_ground_04_rough_1k.jpg',
    scale=(7, 7))

M_STONE = pbr('stone',
    TEX + '/mossy_stone_wall_diff_2k.jpg',
    TEX + '/mossy_stone_wall_nor_gl_2k.jpg',
    TEX + '/mossy_stone_wall_rough_1k.jpg',
    scale=(1.6, 1.6))

M_BARK = pbr('bark',
    TEX + '/bark_brown_02_diff_1k.jpg',
    TEX + '/bark_brown_02_nor_gl_1k.jpg',
    TEX + '/bark_brown_02_rough_1k.jpg',
    scale=(1, 3))

M_MOSS = pbr('mossfloor',
    TEX + '/forest_leaves_02_diffuse_2k.jpg',
    TEX + '/forest_leaves_02_nor_gl_1k.jpg',
    TEX + '/forest_leaves_02_rough_1k.jpg',
    scale=(3, 3),
    tint=(0.55, 0.72, 0.42))

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
objs.append(add_plane('ground', (0, 0, 0), (26, 26), M_GROUND))

objs.append(add_box('wall_back_L', (-5.2, -7.0, 1.6), (4.4, 0.7, 3.2), M_STONE))
objs.append(add_box('wall_back_R', ( 5.2, -7.0, 1.6), (4.4, 0.7, 3.2), M_STONE))
objs.append(add_box('wall_back_top', (0.0, -7.0, 3.35), (6.0, 0.7, 0.6), M_STONE))
objs.append(add_box('wall_back_pier_L', (-1.8, -7.0, 1.45), (0.9, 0.75, 2.9), M_STONE))
objs.append(add_box('wall_back_pier_R', ( 1.8, -7.0, 1.45), (0.9, 0.75, 2.9), M_STONE))
objs.append(add_box('wall_side', (-7.4, 0.0, 1.6), (0.7, 14.0, 3.2), M_STONE))
objs.append(add_box('pillar', (-3.2, -3.4, 1.5), (0.9, 0.9, 3.0), M_STONE))
objs.append(add_box('rubble_1', (-1.2, -4.6, 0.28), (1.5, 1.0, 0.56), M_STONE, (0, 0, 0.4)))
objs.append(add_box('rubble_2', (2.6, -3.2, 0.22), (1.1, 0.9, 0.44), M_STONE, (0, 0, -0.7)))
objs.append(add_box('rubble_3', (-4.8, -1.0, 0.18), (0.8, 1.4, 0.36), M_MOSS, (0, 0, 0.2)))
objs.append(add_box('moss_patch', (1.4, -1.6, 0.02), (3.2, 3.0, 0.04), M_MOSS))

# a fallen trunk across the corner
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.22, depth=4.2,
                                    location=(-5.0, -4.6, 0.25),
                                    rotation=(0, math.radians(88), math.radians(24)))
trunk = bpy.context.object
trunk.name = 'trunk'
trunk.data.materials.append(M_BARK)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
objs.append(trunk)


# ---------------------------------------------------------------- plants (stage B)
if os.environ.get('PLANTS', '0') == '1':
    LM = "/home/waldo/repos/deadlight/lookmodels"
    layout = [
        ('fern_02/fern_02_1k.gltf',                 'fern',  1.1, 2, 22),
        ('grass_medium_01/grass_medium_01_1k.gltf', 'grass', 2.0, 0, 7),
        ('shrub_02/shrub_02_1k.gltf',               'shrub', 1.3, 2, 6),
    ]
    for path, key, target, axis, count in layout:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(LM, path))
        new = [o for o in bpy.data.objects if o not in before]
        meshes_new = [o for o in new if o.type == 'MESH']
        # stand the model up: the scans come in lying flat
        for o in new:
            o.rotation_euler[0] -= math.radians(90)
        bpy.ops.object.select_all(action='DESELECT')
        for o in new:
            o.select_set(True)
        bpy.context.view_layer.objects.active = new[0]
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

        # measure and scale to target height
        import mathutils
        mins = [1e9]*3; maxs = [-1e9]*3
        for o in meshes_new:
            for c in o.bound_box:
                w = o.matrix_world @ mathutils.Vector(c)
                for i in range(3):
                    mins[i] = min(mins[i], w[i]); maxs[i] = max(maxs[i], w[i])
        span = max(0.001, maxs[axis] - mins[axis])
        s = target / span
        for o in new:
            o.scale = (o.scale[0]*s, o.scale[1]*s, o.scale[2]*s)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # scatter copies around the ruin, then join them so one lightmap serves the type
        copies = []
        for i in range(count):
            ang = (i * 2.399 + 0.7)
            rad = 1.8 + ((i * 7) % 19) * 0.42
            px = math.cos(ang) * rad
            pz = math.sin(ang) * rad - 2.4
            if abs(px) < 1.1 and pz < -6.4:
                continue
            for o in new:
                c2 = o.copy()
                c2.data = o.data
                bpy.context.collection.objects.link(c2)
                c2.location = (o.location[0] + px, o.location[1] + pz, o.location[2] - mins[2])
                c2.rotation_euler[2] = (i * 1.7) % 6.28
                copies.append(c2)

        bpy.ops.object.select_all(action='DESELECT')
        for c2 in copies:
            c2.select_set(True)
        bpy.context.view_layer.objects.active = copies[0]
        bpy.ops.object.join()
        joined = bpy.context.object
        joined.name = 'plant_' + key
        objs.append(joined)
        print('PLANTS', key, len(copies), 'joined')

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
env.image = bpy.data.images.load(TEX + '/env.hdr')
nt.links.new(env.outputs['Color'], bg.inputs['Color'])
nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
bg.inputs['Strength'].default_value = 0.6

bpy.ops.object.light_add(type='SUN', location=(0, 0, 12))
sun = bpy.context.object
sun.name = 'sun'
sun.data.energy = 5.0
sun.data.color = (1.0, 0.68, 0.44)
sun.data.angle = math.radians(1.5)
sun.rotation_euler = (math.radians(74), 0.0, math.radians(-38))

# ---------------------------------------------------------------- UVs: albedo in UVMap, lightmap in Lightmap
bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    # albedo unwrap
    o.data.uv_layers[0].name = 'UVMap'
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    # lightmap layer
    lm = o.data.uv_layers.new(name='Lightmap')
    o.data.uv_layers.active = lm
    lm.active_render = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.03)
    bpy.ops.object.mode_set(mode='OBJECT')
    o.select_set(False)

# ---------------------------------------------------------------- bake
results = []
for o in objs:
    bpy.context.view_layer.objects.active = o
    o.select_set(True)

    m = o.data.materials[0]
    m.use_nodes = True
    img = bpy.data.images.new(o.name + '_lm', RES, RES, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'sRGB'
    node = m.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = img
    m.node_tree.nodes.active = node

    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o

    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'},
                        margin=6, use_clear=True)

    img.filepath_raw = os.path.join(OUT, o.name + '_lm.png')
    img.file_format = 'PNG'
    img.save()
    results.append(o.name)
    print('BAKED', o.name, RES)

# strip bake nodes, keep textures
for o in objs:
    m = o.data.materials[0]
    for n in list(m.node_tree.nodes):
        if n.type == 'TEX_IMAGE' and n.image and n.image.name.endswith('_lm'):
            m.node_tree.nodes.remove(n)

for o in bpy.context.scene.objects:
    o.select_set(True)

bpy.ops.export_scene.gltf(
    filepath=os.path.join(OUT, 'room.glb'),
    export_format='GLB',
    use_selection=True,
    export_apply=True,
    export_lights=False,
    export_cameras=False,
)

print('DONE', len(results))
